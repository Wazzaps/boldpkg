import datetime
import sqlite3
from pathlib import Path
from yaspin import yaspin
from utils import parse_package_names
from snapshots import prepare_snapshot, commit_snapshot, current_snapshot_metadata


def cmd_remove(args):
    root = Path(args.root)

    if not (root / 'snapshot' / 'current').exists():
        print('Run `bold update` before removing packages')
        return

    current_metadata = current_snapshot_metadata(root)

    # Make sure all packages are installed
    db = sqlite3.connect(root / 'snapshot' / 'current' / 'cache.db3')
    parsed_packages = parse_package_names(db, args.app)
    if not parsed_packages:
        exit(1)
    missing_packages = [pkg_name for pkg_name, exact_pkg in parsed_packages.items()
                        if exact_pkg not in current_metadata['packages']]
    if len(missing_packages) != 0:
        print(f'The following packages are not installed:')
        for pkg in missing_packages:
            print(f'- {pkg}')
        return

    # Catch named packages specified exactly
    named_packages = {v: k for k, v in parse_package_names(db, list(current_metadata['named_packages'].keys())).items()}

    # Remove the packages
    for pkg, exact_pkg in parsed_packages.items():
        del current_metadata['packages'][exact_pkg]
        if pkg in current_metadata['named_packages']:
            del current_metadata['named_packages'][pkg]
        elif pkg in named_packages:
            del current_metadata['named_packages'][named_packages[pkg]]
        else:
            print(f'WARNING: Removing package "{pkg}" which wasn\'t installed manually')

    # Create new snapshot
    with yaspin(text='Creating snapshot with new packages'):
        metadata = {
            'alias': None,
            'description': f'Removed {", ".join(parsed_packages)}',
            'created': datetime.datetime.now().isoformat(),
            'named_packages': current_metadata['named_packages'],
            'packages': current_metadata['packages'],
            'repoHash': current_metadata['repoHash'],
            'systems': current_metadata['systems'],
        }
        snapshot_dir = prepare_snapshot(root)
        (root / 'snapshot/current/cache.db3').link_to(snapshot_dir / 'cache.db3')
        commit_snapshot(root, metadata, switch=True)
