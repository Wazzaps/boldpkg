import datetime
import shutil
import sqlite3
import urllib.parse
from pathlib import Path
import subprocess as sp

from yaspin import yaspin

from building import build_packages, get_metadata
from utils import parse_package_names, read_config
from snapshots import prepare_snapshot, commit_snapshot, current_snapshot_metadata


def install_package(package: str, root: Path, db, spinner, spinner_prefix=''):
    spinner.text = f'Installing {package}'
    bincache_archive = root / 'cache' / 'bold' / 'bincache' / f'{package}.tar.zst'

    if (root / 'app' / package).exists():
        return True

    if not bincache_archive.exists():
        # TODO: Download from https repo
        config = read_config(root)
        original_side = spinner.side
        original_color = spinner.color
        spinner.side = 'right'
        spinner.color = 'cyan'
        for bincache_server in config['binaryCaches']:
            url = f'{bincache_server}/{package}.tar.zst'
            bincache_host = urllib.parse.urlparse(bincache_server).hostname
            spinner.text = f'{spinner_prefix}Downloading {package} from {bincache_host}'
            try:
                sp.run(
                    ['curl', '--fail', '-L', url, '-o', str(bincache_archive)],
                    check=True,
                    stdout=sp.DEVNULL,
                    stderr=sp.DEVNULL,
                )
            except sp.CalledProcessError:
                spinner.stop()
                print(spinner.text + ' [FAIL]')
                spinner.start()
                continue

            spinner.stop()
            print(spinner.text + ' [OK]')
            spinner.start()
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
                    spinner, db, f'{spinner_prefix}Building package: '
                )
            finally:
                shutil.rmtree(workspace, ignore_errors=True)
        spinner.side = original_side
        spinner.color = original_color

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
        }
        snapshot_dir = prepare_snapshot(root)
        (root / 'snapshot/current/cache.db3').link_to(snapshot_dir / 'cache.db3')
        commit_snapshot(root, metadata, switch=True)

    print('Done :)')
