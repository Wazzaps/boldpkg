import datetime
import hashlib
import json
import sqlite3
import subprocess as sp
from pathlib import Path
from typing import Dict

import toml as toml
from yaspin import yaspin

from cmd_install import install_package
from utils import parse_package_names
from snapshots import current_snapshot_metadata, current_snapshot_repo_hash, prepare_snapshot, commit_snapshot


def _build_repo(root: Path, config: Dict):
    repo_dir = (root / config['repo']).resolve()
    repo_main = repo_dir / 'main.js'
    with yaspin(text='Generating package list'):
        proc = sp.Popen(
            [(root / config['quickjsPath'] / 'qjs').resolve(), '-m', str(repo_main)],
            stdout=sp.PIPE, stderr=sp.PIPE, cwd=str(repo_dir)
        )
        stdout, stderr = proc.communicate()
        if stderr:
            raise RuntimeError(stderr.decode())
        return json.loads(stdout), hashlib.sha256(stdout).hexdigest()


def _repo_to_cache(results, db):
    # Populate cache
    with db:
        # Create schema
        db.execute('''
            CREATE TABLE "packages"
            (
                "name"              TEXT    NOT NULL,
                "hash"              TEXT    NOT NULL,
                "shortdesc"         TEXT    NOT NULL,
                "metadata"          TEXT    NOT NULL,
                "recipe"            TEXT,
                PRIMARY KEY ("name", "hash")
            );
        ''')
        db.execute('''
            CREATE TABLE "named_packages"
            (
                "name"              TEXT    NOT NULL,
                "hash"              TEXT    NOT NULL,
                PRIMARY KEY ("name")
            );
        ''')

        # Insert all packages
        for app_name, app_metadata in results['recipes'].items():
            app_name, _, app_hash = app_name.partition('@')

            app_recipe = app_metadata['recipe']
            del app_metadata['recipe']

            db.execute(
                'INSERT INTO packages (name, hash, shortdesc, metadata, recipe)'
                'VALUES (?, ?, ?, ?, ?)',
                (
                    app_name,
                    app_hash,
                    app_metadata['shortDesc'],
                    json.dumps(app_metadata, sort_keys=True),
                    json.dumps(app_recipe, sort_keys=True)
                )
            )

        # Insert all named packages
        for app_name, app_hash in results['named_recipes'].items():
            db.execute('INSERT INTO named_packages (name, hash) VALUES (?, ?)', (app_name, app_hash))


def read_config(root: Path):
    return toml.load(root / 'config.toml')


def cmd_update(args):
    root = Path(args.root)
    config = read_config(root)
    repo, repo_hash = _build_repo(root, config)
    current_metadata = current_snapshot_metadata(root)
    if current_metadata:
        if current_metadata['repoHash'] == repo_hash:
            print('No updates available')
            return

    current_metadata['packages'] = {}
    current_metadata['named_packages'] = current_metadata.get('named_packages', {})
    current_metadata['systems'] = current_metadata.get('systems', {})

    # TODO: Compare hash of just package part / just systems part

    # Get changed packages
    if config['systemAlias'] in repo['systems']:
        if current_metadata:
            current_system = current_metadata['systems'].get(config['systemAlias'], {})
            current_sys_packages = set(current_system.get('packages', []))
        else:
            current_sys_packages = set()
        next_packages = set(repo['systems'][config['systemAlias']]['packages'])

        added_packages = next_packages - current_sys_packages
        removed_packages = current_sys_packages - next_packages

        for pkg in added_packages:
            # TODO: Not all pkgs should be global
            current_metadata['packages'][pkg] = {'global': True}
        for pkg in removed_packages:
            if pkg in current_metadata['packages']:
                del current_metadata['packages'][pkg]

    # Prepare snapshot
    snapshot_dir = prepare_snapshot(root)
    db = sqlite3.connect(snapshot_dir / 'cache.db3')
    _repo_to_cache(repo, db)

    # Add named packages
    for pkg, exact_pkg in parse_package_names(db, list(current_metadata['named_packages'].keys())).items():
        current_metadata['packages'][exact_pkg] = current_metadata['named_packages'][pkg]

    # Install missing packages
    with yaspin(text='') as spinner:
        for package in current_metadata['packages']:
            if not install_package(package, root, db, spinner):
                return

    metadata = {
        'alias': None,
        'description': 'Updated from local package repository',
        'created': datetime.datetime.now().isoformat(),
        'named_packages': current_metadata['named_packages'],
        'packages': current_metadata['packages'],
        'repoHash': repo_hash,
        'systems': repo['systems'],
    }
    with yaspin(text='Creating snapshot with new updates'):
        commit_snapshot(root, metadata, switch=True)
