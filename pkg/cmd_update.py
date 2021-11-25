import datetime
import hashlib
import json
import sqlite3
import subprocess as sp
from pathlib import Path
from typing import Dict
from yaspin import yaspin

from cmd_install import install_package
from building import get_metadata
from utils import parse_package_names, read_config, parse_system_names
from snapshots import current_snapshot_metadata, prepare_snapshot, commit_snapshot


def _build_repo(root: Path, config: Dict):
    repo_dir = (root / config['localRepo']).resolve()
    repo_main = repo_dir / 'main.js'
    with yaspin(text='Generating package list'):
        proc = sp.Popen(
            [(root / config['quickjsPath'] / 'qjs').resolve(), '-m', str(repo_main)],
            stdout=sp.PIPE, stderr=sp.PIPE, cwd=str(repo_dir)
        )
        stdout, stderr = proc.communicate()
        if stderr:
            raise RuntimeError(stdout.decode() + '\n' + stderr.decode())
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
        db.execute('''
            CREATE TABLE "systems"
            (
                "name"              TEXT    NOT NULL,
                "hash"              TEXT    NOT NULL,
                "shortdesc"         TEXT    NOT NULL,
                "metadata"          TEXT    NOT NULL,
                PRIMARY KEY ("name", "hash")
            );
        ''')
        db.execute('''
            CREATE TABLE "named_systems"
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

        # Insert all systems
        for sys_name, sys_metadata in results['systems'].items():
            sys_name, _, sys_hash = sys_name.partition('@')

            db.execute(
                'INSERT INTO systems (name, hash, shortdesc, metadata)'
                'VALUES (?, ?, ?, ?)',
                (
                    sys_name,
                    sys_hash,
                    sys_metadata['shortDesc'],
                    json.dumps(sys_metadata, sort_keys=True),
                )
            )

        # Insert all named packages
        for app_name, app_hash in results['named_recipes'].items():
            db.execute('INSERT INTO named_packages (name, hash) VALUES (?, ?)', (app_name, app_hash))

        # Insert all named systems
        for sys_name, sys_hash in results['named_systems'].items():
            db.execute('INSERT INTO named_systems (name, hash) VALUES (?, ?)', (sys_name, sys_hash))


def get_system_metadata(db, name):
    system_name = list(parse_system_names(db, [name]).values())
    if system_name:
        system_name, _, system_hash = system_name[0].partition('@')
    else:
        return

    with db:
        metadata = db.execute(
            'SELECT metadata FROM systems WHERE name = ? AND hash = ?',
            (system_name, system_hash)
        ).fetchone()
        if metadata:
            return json.loads(metadata[0])
        return None


def cmd_update(args):
    root = Path(args.root)
    config = read_config(root)
    repo, repo_hash = _build_repo(root, config)
    current_metadata = current_snapshot_metadata(root)
    if current_metadata:
        # TODO: Compare hash of just package part / just systems part
        if current_metadata['repoHash'] == repo_hash:
            print('No updates available')
            return

    current_metadata['packages'] = {}
    current_metadata['named_packages'] = current_metadata.get('named_packages', {})

    # Prepare snapshot
    snapshot_dir = prepare_snapshot(root)
    db = sqlite3.connect(snapshot_dir / 'cache.db3')
    _repo_to_cache(repo, db)

    # Get packages in tracked system
    next_system_metadata = get_system_metadata(db, config['systemName'])
    if next_system_metadata:
        next_sys_packages = set(next_system_metadata['packages'])
        for package in next_sys_packages:
            # TODO: Not all pkgs should be global
            current_metadata['packages'][package] = {'global': True}

    # Add named packages
    for pkg, exact_pkg in parse_package_names(db, list(current_metadata['named_packages'].keys())).items():
        current_metadata['packages'][exact_pkg] = current_metadata['named_packages'][pkg]

    # Collect package dependencies
    dependencies = set()
    for pkg in current_metadata['packages']:
        dependencies |= set(get_metadata(db, pkg)['depends'].values())

    # Add dependencies
    current_metadata['packages'] |= {pkg: {'global': False} for pkg in dependencies}

    # Install missing packages
    with yaspin(text='') as spinner:
        total_len = len(current_metadata['packages'])
        for i, package in enumerate(current_metadata['packages']):
            if not install_package(package, root, db, spinner, f'[{i+1}/{total_len}]: '):
                return

    metadata = {
        'alias': None,
        'description': 'Updated from local package repository',
        'created': datetime.datetime.now().isoformat(),
        'named_packages': current_metadata['named_packages'],
        'packages': current_metadata['packages'],
        'repoHash': repo_hash,
    }
    with yaspin(text='Creating snapshot with new updates'):
        commit_snapshot(root, metadata, switch=True)

    print('Done :)')
