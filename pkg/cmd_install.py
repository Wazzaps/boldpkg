import datetime
import shutil
import sqlite3
from pathlib import Path
import subprocess as sp

from yaspin import yaspin

from building import build_packages, get_metadata
from utils import parse_package_names, read_config
from snapshots import prepare_snapshot, commit_snapshot, current_snapshot_metadata


def install_package(package: str, root: Path, db, spinner):
    spinner.text = f'Installing {package}'
    bincache_archive = root / 'cache' / 'bold' / 'bincache' / f'{package}.tar.zst'

    if (root / 'app' / package).exists():
        return True

    if not bincache_archive.exists():
        # TODO: Download from https repo
        config = read_config(root)
        for bincache_server in config['binaryCaches']:
            url = f'{bincache_server}/{package}.tar.zst'
            spinner.text = f'Downloading {package} from {bincache_server}'
            try:
                sp.run(
                    ['curl', '--fail', '-L', url, '-o', str(bincache_archive)],
                    check=True,
                    stdout=sp.DEVNULL,
                    stderr=sp.DEVNULL,
                )
            except sp.CalledProcessError:
                continue
            break
        else:
            # Last resort, build it
            spinner.stop()
            print(f'Could not download {package} from any binary cache, building it')
            spinner.start()

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

    current_metadata = current_snapshot_metadata(root)

    # Make sure all packages are in index
    db = sqlite3.connect(root / 'snapshot' / 'current' / 'cache.db3')
    parsed_packages = parse_package_names(db, args.app)
    if not parsed_packages:
        exit(1)
    exact_packages = [p for p in parsed_packages.values() if p not in current_metadata['packages']]

    if len(exact_packages) == 0:
        print('All requested packages already installed')
        return

    # Collect package dependencies
    dependencies = set()
    for pkg in parsed_packages.values():
        dependencies |= set(get_metadata(db, pkg)['depends'].values())

    # Add dependencies
    current_metadata['packages'] |= {pkg: {'global': False} for pkg in dependencies}
    exact_packages += list(dependencies)

    with yaspin(text='') as spinner:
        # TODO: Parallelize
        # TODO: Fetch dependencies
        for package in exact_packages:
            if not install_package(package, root, db, spinner):
                return

    for pkg, exact_pkg in parsed_packages.items():
        current_metadata['packages'][exact_pkg] = {'global': True}
        current_metadata['named_packages'][pkg] = {'global': True}

    # Create new snapshot
    with yaspin(text='Creating snapshot with new packages'):
        metadata = {
            'alias': None,
            'description': f'Installed {", ".join(parsed_packages)}',
            'created': datetime.datetime.now().isoformat(),
            'named_packages': current_metadata['named_packages'],
            'packages': current_metadata['packages'],
            'repoHash': current_metadata['repoHash'],
            'systems': current_metadata['systems'],
        }
        snapshot_dir = prepare_snapshot(root)
        (root / 'snapshot/current/cache.db3').link_to(snapshot_dir / 'cache.db3')
        commit_snapshot(root, metadata, switch=True)
