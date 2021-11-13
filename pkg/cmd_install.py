import datetime
import sqlite3
from pathlib import Path
from typing import List

from yaspin import yaspin

from snapshots import create_snapshot, current_snapshot_metadata


def verify_valid_packages_names(db, packages: List[str]):
    for package in packages:
        if package.count('@') != 1:
            print(f'Package name "{package}" is invalid, use full name (i.e. <name>@<hash>)')
            return False

    with db:
        cursor = db.cursor()
        cursor.execute('''
            DROP TABLE IF EXISTS wanted_packages
        ''')
        cursor.execute('''
            CREATE TEMPORARY TABLE "wanted_packages"
            (
                "name"              TEXT    NOT NULL,
                "hash"              TEXT    NOT NULL
            )
        ''')
        for package in packages:
            pkg_name, _, pkg_hash = package.partition('@')
            cursor.execute('''
                INSERT INTO "wanted_packages"
                VALUES (?, ?)
            ''', (pkg_name, pkg_hash))
        missing_pkgs = cursor.execute('''
            SELECT name, hash
                FROM wanted_packages LEFT OUTER JOIN packages W
                USING (name, hash)
                WHERE W.name IS NULL
        ''').fetchall()
        if len(missing_pkgs) != 0:
            missing_pkgs_str = ', '.join(f'{pkg_name}@{pkg_hash}' for pkg_name, pkg_hash in missing_pkgs)
            print(f'The following packages were not found: {missing_pkgs_str}')
            return False

    return True


def cmd_install(args):
    root = Path(args.root)

    if not (root / 'snapshot' / 'current').exists():
        print('Run `bold update` before installing packages')
        return

    # Make sure all packages are in index
    db = sqlite3.connect(root / 'snapshot' / 'current' / 'cache.db3')
    if not verify_valid_packages_names(db, args.app):
        return

    current_metadata = current_snapshot_metadata(root)
    current_metadata['installedPackages'] = sorted(list(set(current_metadata['installedPackages'] + args.app)))
    current_metadata['globalPackages'] = sorted(list(set(current_metadata['globalPackages'] + args.app)))
    with yaspin(text='Creating snapshot with new packages'):
        create_snapshot(
            root=root,
            metadata={
                'alias': None,
                'description': f'Installed {", ".join(args.app)}',
                'created': datetime.datetime.now().isoformat(),
                'installedPackages': current_metadata['installedPackages'],
                'globalPackages': current_metadata['globalPackages'],
                'repoHash': current_metadata['repoHash'],
                'systems': current_metadata['systems'],
            },
            cache_generator=lambda snapshot_dir: (root / 'snapshot/current/cache.db3').link_to(snapshot_dir / 'cache.db3'),
            switch=True
        )
