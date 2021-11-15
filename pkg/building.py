import json
import os
import pipes
import shutil
import urllib.parse
import sqlite3
import subprocess as sp
from pathlib import Path
from typing import List

from yaspin.core import Yaspin


def get_recipe(db, package):
    pkg_name, _, pkg_hash = package.partition('@')
    cursor = db.cursor().execute('select recipe from packages where name=? and hash=?', (pkg_name, pkg_hash))
    recipe, = cursor.fetchone()
    return json.loads(recipe)


class ExternalResource:
    def __init__(self, package, name, uri):
        self.package = package
        self.name = name
        self.full_name = f'{package}.{name}'
        self.full_name_esc = f'{package.replace("@", "_")}.{name}'
        self.uri = uri
        self.uri_parsed = urllib.parse.urlsplit(uri)

        if self.uri_parsed.scheme == 'src':
            self.type = 'Local from src directory'
        elif self.uri_parsed.scheme == 'repo':
            self.type = 'Local from repo'
        elif self.uri_parsed.scheme == 'https':
            self.type = 'Internet'
        else:
            self.type = 'Unknown'


def _quote(s):
    return pipes.quote(str(s))


def fetch_externals(externals: List[ExternalResource], root: Path, workspace: Path, spinner: Yaspin, spinner_prefix=''):
    for external in externals:
        spinner.text = f'{spinner_prefix}Fetching: {external.full_name}'

        if external.type == 'Local from src directory':
            # Copy local file
            local_path = root / 'src' / external.uri_parsed.netloc
            if local_path.is_dir():
                shutil.copytree(local_path, workspace / external.full_name)
            else:
                shutil.copy(local_path, workspace / external.full_name)
        elif external.type == 'Local from repo':
            # Copy local file
            local_path = root / 'src' / 'repo' / external.uri_parsed.path.lstrip('/')
            if local_path.is_dir():
                shutil.copytree(local_path, workspace / external.full_name)
            else:
                shutil.copy(local_path, workspace / external.full_name)


def build_packages(packages: List[str], root: Path, workspace: Path,
                   phases: List[str], spinner: Yaspin, db, spinner_prefix=''):
    spinner.text = f'{spinner_prefix}Getting recipes'

    # Get all recipes
    recipes = {package: get_recipe(db, package) for package in packages}

    # Collect external resources
    externals = []
    for package, recipe in recipes.items():
        for external_name in recipe['externals']:
            external = ExternalResource(package, external_name, recipe['externals'][external_name])
            externals.append(external)

    # Create build environment if needed
    if workspace.exists():
        assert workspace.is_dir()
    else:
        workspace.mkdir(parents=True)

        spinner.text = f'{spinner_prefix}Creating environment'
        with open(os.open(workspace / 'activate.sh', os.O_CREAT | os.O_WRONLY, 0o755), 'w') as fd:
            main_pkg = packages[0].replace('@', '_')
            script = '#!/bin/echo "This script should be sourced in a shell, not executed directly"\n'

            unset = ['BOLD_WORKSPACE']
            script += f'export BOLD_WORKSPACE={_quote(workspace)}\n\n'

            for phase in ['unpack', 'patch', 'build', 'check', 'install', 'fixup', 'installCheck']:
                for package in packages:
                    package_esc = package.replace('@', '_')
                    unset.append(f'bold_{phase}_{package_esc}')
                    script += f'bold_{phase}_{package_esc}() {{\n'
                    script += f'  _oldpath=`pwd`; cd {workspace}\n'
                    script += f'  export DESTDIR={_quote(workspace / "dest" / package)}\n'
                    script += f'  mkdir -p "$DESTDIR"\n'
                    # TODO: DEP_* for deps
                    for external in externals:
                        if external.package == package:
                            script += f'  export EXT_{external.name}={_quote(workspace / external.full_name)}\n'

                    script += f'  {recipes[package]["phases"][phase]["cmd"]}\n'

                    for external in externals:
                        if external.package == package:
                            script += f'  unset EXT_{external.name}\n'
                    script += f'  cd $_oldpath\n'
                    script += f'}}\n'

                unset.append(f'bold_{phase}')
                script += f'bold_{phase}() {{\n'
                script += f'  bold_{phase}_{main_pkg}\n'
                script += f'}}\n'

            unset.append('bold_help')
            script += f'bold_help() {{\n'
            script += f'echo "** Welcome to the Bold build environment! **"\n'
            script += f'echo "This environment is ready for developing the following packages: {", ".join(packages)}"\n'
            script += f'echo \'You may build each package by calling `bold_build_<NAME>`, e.g. `bold_build_{main_pkg}`\'\n'
            script += f'echo \'All packages/libraries can be built by simply running `bold_build`.\'\n'
            script += f'echo \'After building an package, you will likely want to `bold_install_<NAME>` it (or just\'\n'
            script += f'echo \'    `bold_install`) to move it to the expected directory.\'\n'
            script += f'echo \'More info is available in the manual (TODO)\'\n'
            script += f'}}\n'

            unset.append('bold_deactivate')
            script += f'bold_deactivate() {{\n'
            for unset_var in unset:
                script += f'  unset {unset_var}\n'
            script += f'}}\n'

            fd.write(script)

    do_fetch = 'fetch' in phases
    if do_fetch:
        phases.remove('fetch')
    do_pack = 'pack' in phases
    if do_pack:
        phases.remove('pack')

    # Fetch external resources
    if do_fetch:
        spinner.stop()
        print('Fetching the following resources:')
        for external in externals:
            print(f'- {external.full_name} ({external.type})')

        spinner.start()
        fetch_externals(externals, root, workspace, spinner, spinner_prefix)

    # Run requested phases
    for phase in phases:
        for package in packages:
            package_esc = package.replace('@', '_')
            spinner.text = f'{spinner_prefix}Preparing {package} ({phase})'
            sp.check_output(['sh', '-c', f'. {_quote(workspace / "activate.sh")} && bold_{phase}_{package_esc}'])

    # Pack result
    if do_pack:
        spinner.text = f'{spinner_prefix}Packing result'
        for package in packages:
            sp.call([
                'tar', '-Izstd -10',
                '-cf', root / 'cache' / 'bold' / 'bincache' / f'{package}.tar.zst',
                '-C', workspace / 'dest' / package, '.'
            ])
