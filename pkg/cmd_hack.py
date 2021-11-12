import json
import os
import pipes
import shutil
import urllib.parse
import sqlite3
import subprocess as sp
from pathlib import Path

from yaspin.core import Yaspin


def get_recipe(selector):
    db = sqlite3.connect('bold/metadata.sqlite3')
    cursor = db.cursor().execute('select hash, recipe from packages where name=?', (selector,))
    app_hash, recipe = cursor.fetchone()
    return app_hash, json.loads(recipe)


class ExternalResource:
    def __init__(self, app_name, name, uri):
        self.app_name = app_name
        self.name = name
        self.full_name = f'{app_name}.{name}'
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


def cmd_hack(args):
    apps = args.app
    main_app = apps[0]

    # Create workspace
    default_name = f'{main_app}-workspace'
    workspace_name = input(f'Workspace Name [{default_name}]: ')
    if not workspace_name:
        workspace_name = default_name
    workspace = Path(workspace_name).absolute()

    spinner = Yaspin(text=f'Creating workspace "{workspace_name}"')
    spinner.start()

    try:
        workspace.mkdir(parents=True)
    except FileExistsError:
        print('Workspace already exists')
        exit(1)

    # Get recipe for main app
    app_hash, recipe = get_recipe(main_app)

    # Fetch external resources
    externals = []
    for external_name in recipe['externals']:
        external = ExternalResource(main_app, external_name, recipe['externals'][external_name])
        externals.append(external)

    spinner.stop()
    print('Will fetch the following resources:')
    for external in externals:
        print(f'- {external.full_name} ({external.type})')

    print('')
    spinner.start()
    for external in externals:
        spinner.text = f'Fetching: {external.full_name}'

        if external.type == 'Local from src directory':
            # Copy local file
            local_path = Path('bold/src') / external.uri_parsed.netloc
            if local_path.is_dir():
                shutil.copytree(local_path, workspace / external.full_name)
            else:
                shutil.copy(local_path, workspace / external.full_name)
        elif external.type == 'Local from repo':
            # Copy local file
            local_path = Path('bold/repo') / external.uri_parsed.path.lstrip('/')
            if local_path.is_dir():
                shutil.copytree(local_path, workspace / external.full_name)
            else:
                shutil.copy(local_path, workspace / external.full_name)

    spinner.text = 'Creating environment'
    with open(os.open(workspace / 'activate.sh', os.O_CREAT | os.O_WRONLY, 0o755), 'w') as fd:
        script = '#!/bin/echo "This script should be sourced in a shell, not executed directly"\n'

        unset = ['BOLD_WORKSPACE']
        script += f'export BOLD_WORKSPACE={_quote(workspace)}\n\n'

        for phase in ['unpack', 'patch', 'build', 'check', 'install', 'fixup', 'installCheck', 'dist']:
            for app in [main_app]:
                unset.append(f'bold_{phase}_{app}')
                script += f'bold_{phase}_{app}() {{\n'
                script += f'  _oldpath=`pwd`; cd {workspace}\n'
                script += f'  export DESTDIR={_quote(workspace / "dest" / f"{app}@{app_hash}")}\n'
                script += f'  mkdir -p "$DESTDIR"\n'
                # TODO: DEP_* for deps
                for external in externals:
                    if external.app_name == app:
                        script += f'  export EXT_{external.name}={_quote(workspace / external.full_name)}\n'

                script += f'  {recipe["phases"][phase]["cmd"]}\n'

                for external in externals:
                    if external.app_name == app:
                        script += f'  unset EXT_{external.name}\n'
                script += f'  cd $_oldpath\n'
                script += f'}}\n'

            unset.append(f'bold_{phase}')
            script += f'bold_{phase}() {{\n'
            script += f'  bold_{phase}_{main_app}\n'
            script += f'}}\n'

        unset.append('bold_help')
        script += f'bold_help() {{\n'
        script += f'echo "** Welcome to the Bold build environment! **"\n'
        script += f'echo "This environment is ready for developing the following apps: {", ".join(apps)}"\n'
        script += f'echo \'You may build each app by calling `bold_build_<NAME>`, e.g. `bold_build_{main_app}`\'\n'
        script += f'echo \'All apps/libraries can be built by simply running `bold_build`.\'\n'
        script += f'echo \'After building an app, you will likely want to `bold_install_<NAME>` it (or just\'\n'
        script += f'echo \'    `bold_install`) to move it to the expected directory.\'\n'
        script += f'echo \'More info is available in the manual (TODO)\'\n'
        script += f'}}\n'

        unset.append('bold_deactivate')
        script += f'bold_deactivate() {{\n'
        for unset_var in unset:
            script += f'  unset {unset_var}\n'
        script += f'}}\n'

        fd.write(script)

    for phase in ['unpack', 'patch']:
        for app in [main_app]:
            spinner.text = f'Preparing {app} ({phase})'
            sp.call(['sh', '-c', f'. {_quote(workspace / "activate.sh")} && bold_{phase}_{app}'])

    spinner.stop()
    print(f'Done! Run `source {workspace_name}/activate.sh` to begin working.')
    print(f'Get help by running `bold_help` after activating.')
