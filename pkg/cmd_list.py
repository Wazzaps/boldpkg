import sqlite3
from pathlib import Path

import sys

from snapshots import prepare_snapshot, commit_snapshot, current_snapshot_metadata
import colorama


def cmd_list(args):
    root = Path(args.root)

    if not (root / 'snapshot' / 'current').exists():
        print('Run `bold update` before listing packages')
        return

    current_metadata = current_snapshot_metadata(root)

    # Make sure all packages are installed
    db = sqlite3.connect(root / 'snapshot' / 'current' / 'cache.db3')

    packages = db.cursor().execute('''
        SELECT P.name, P.hash, P.shortdesc, N.name
        FROM packages P LEFT JOIN named_packages N using (name, hash)
        ORDER BY P.name ASC, N.name IS NULL
    ''')

    if sys.stdout.isatty():
        BOLD_WHITE = colorama.Style.BRIGHT + colorama.Fore.LIGHTWHITE_EX
        WHITE = colorama.Fore.LIGHTWHITE_EX
        GRAY = colorama.Style.RESET_ALL + colorama.Fore.LIGHTBLACK_EX
        RESET = colorama.Fore.RESET + colorama.Style.RESET_ALL
    else:
        BOLD_WHITE = ''
        WHITE = ''
        GRAY = ''
        RESET = ''

    matched_any = False

    for pkg_name, pkg_hash, pkg_desc, pkg_named in packages:
        if pkg_named:
            pkg_color = BOLD_WHITE
        else:
            pkg_color = WHITE

        tags = []
        if f'{pkg_name}@{pkg_hash}' in current_metadata['packages']:
            tags.append('installed')
        if (pkg_named and pkg_name in current_metadata['named_packages']) \
                or f'{pkg_name}@{pkg_hash}' in current_metadata['named_packages']:
            tags.append('manually')

        if args.installed and 'installed' not in tags:
            continue

        if args.manually and 'manually' not in tags:
            continue

        if args.app and args.app != pkg_name:
            continue

        print(f'{pkg_color}{pkg_name}{GRAY}@{pkg_hash}{RESET}'
              f'{" [" if tags else ""}{",".join(tags)}{"]" if tags else ""}')
        if not args.lines:
            print(f'  {pkg_desc}')
            print(f'')
        matched_any = True

    if not matched_any:
        exit(1)
