import datetime
import shutil
import sqlite3
from pathlib import Path
import subprocess as sp

from yaspin import yaspin

from building import build_packages
from utils import verify_valid_packages_names, parse_package_names
from snapshots import create_snapshot, current_snapshot_metadata


def install_package(package: str, root: Path, db, spinner):
    spinner.text = f'Installing {package}'
    bincache_archive = root / 'cache' / 'bold' / 'bincache' / f'{package}.tar.zst'

    if (root / 'app' / package).exists():
        return True

    if not bincache_archive.exists():
        # TODO: Download from https repo

        # Last resort, build it
        workspace = (root / 'cache' / 'bold' / 'build' / package)
        phases = ['fetch', 'unpack', 'patch', 'build', 'check', 'install', 'fixup', 'installCheck', 'pack']
        try:
            build_packages(
                [package], root, workspace, phases,
                spinner, db, 'Building package: '
            )
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    (root / 'app' / package).mkdir(parents=True)
    sp.call(['tar', '-xf', str(bincache_archive), '-C', str(root / 'app' / package)])
    return True


def cmd_install(args):
    root = Path(args.root)

    if not (root / 'snapshot' / 'current').exists():
        print('Run `bold update` before installing packages')
        return

    # Make sure all packages are in index
    db = sqlite3.connect(root / 'snapshot' / 'current' / 'cache.db3')
    parsed_packages = parse_package_names(db, args.app)
    if not parsed_packages:
        exit(1)
    parsed_packages = list(parsed_packages.values())

    # TODO: Parallelize
    # TODO: Fetch dependencies

    with yaspin(text='') as spinner:
        for package in parsed_packages:
            if not install_package(package, root, db, spinner):
                return

    current_metadata = current_snapshot_metadata(root)
    if all(pkg in current_metadata['installedPackages']
           and pkg in current_metadata['globalPackages'] for pkg in parsed_packages):
        print('All requested packages already installed')
        return

    # Create new snapshot
    current_metadata['installedPackages'] = sorted(list(set(current_metadata['installedPackages'] + parsed_packages)))
    current_metadata['globalPackages'] = sorted(list(set(current_metadata['globalPackages'] + parsed_packages)))
    with yaspin(text='Creating snapshot with new packages'):
        create_snapshot(
            root=root,
            metadata={
                'alias': None,
                'description': f'Installed {", ".join(parsed_packages)}',
                'created': datetime.datetime.now().isoformat(),
                'installedPackages': current_metadata['installedPackages'],
                'globalPackages': current_metadata['globalPackages'],
                'repoHash': current_metadata['repoHash'],
                'systems': current_metadata['systems'],
            },
            cache_generator=lambda snapshot_dir: (root / 'snapshot/current/cache.db3').link_to(snapshot_dir / 'cache.db3'),
            switch=True
        )
