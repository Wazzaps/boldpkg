import datetime
import hashlib
import json
import sqlite3
import subprocess as sp
from pathlib import Path
from typing import Dict

import toml as toml
from yaspin import yaspin

from snapshots import create_snapshot, current_snapshot_metadata, current_snapshot_repo_hash


def _build_repo(root: Path, config: Dict):
    repo_dir = (root / config['repo']).resolve()
    repo_main = repo_dir / 'main.js'
    with yaspin(text='Generating package list'):
        proc = sp.Popen(
            [(root / config['quickjsPath'] / 'qjs').resolve(), '-m', str(repo_main)],
            stdout=sp.PIPE, stderr=sp.PIPE, cwd=str(repo_dir)
        )
        stdout, stderr = proc.communicate()
        return json.loads(stdout), hashlib.sha256(stdout).hexdigest()


def _repo_to_cache(results, snapshot_dir):
    # Populate cache
    db = sqlite3.connect(snapshot_dir / 'cache.db3')
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

    # TODO: Compare hash of just package part / just systems part

    current_installed_packages = current_metadata.get('installedPackages', [])
    current_global_packages = current_metadata.get('globalPackages', [])

    # Get changed packages
    if config['systemAlias'] in repo['systems']:
        if current_metadata:
            current_system = current_metadata['systems'].get(config['systemAlias'], {})
            current_packages = set(current_system.get('packages', []))
        else:
            current_packages = set()
        next_packages = set(repo['systems'][config['systemAlias']]['packages'])

        added_packages = next_packages - current_packages
        removed_packages = current_packages - next_packages

        current_installed_packages = [p for p in current_installed_packages if p not in removed_packages]
        current_installed_packages.extend([p for p in sorted(added_packages) if p not in current_installed_packages])

        current_global_packages = [p for p in current_global_packages if p not in removed_packages]
        current_global_packages.extend([p for p in sorted(added_packages) if p not in current_global_packages])

    with yaspin(text='Creating snapshot with new updates'):
        create_snapshot(
            root=root,
            metadata={
                'alias': None,
                'description': 'Updated from local package repository',
                'created': datetime.datetime.now().isoformat(),
                'installedPackages': current_installed_packages,
                'globalPackages': current_global_packages,
                'repoHash': repo_hash,
                'systems': repo['systems'],
            },
            cache_generator=lambda snapshot_dir: _repo_to_cache(repo, snapshot_dir),
            switch=True
        )
