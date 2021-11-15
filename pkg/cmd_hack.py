import json
import os
import pipes
import shutil
import urllib.parse
import sqlite3
import subprocess as sp
from pathlib import Path

from yaspin.core import Yaspin

from building import build_packages
from utils import parse_package_names


def get_recipe(db, selector):
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
    root = Path(args.root)
    main_app = apps[0]

    # Create workspace
    default_name = f'{main_app.partition("@")[0]}-workspace'
    workspace_name = input(f'Workspace Name [{default_name}]: ')
    if not workspace_name:
        workspace_name = default_name
    workspace = Path(workspace_name).absolute()

    spinner = Yaspin(text=f'Creating workspace "{workspace_name}"')
    spinner.start()

    if workspace.exists():
        print('Workspace already exists')
        exit(1)

    db = sqlite3.connect(root / 'snapshot' / 'current' / 'cache.db3')

    spinner.stop()
    parsed_packages = parse_package_names(db, args.app)
    if not parsed_packages:
        exit(1)
    parsed_packages = list(parsed_packages.values())
    spinner.start()

    if args.build:
        phases = ['fetch', 'unpack', 'patch', 'build', 'check', 'install', 'fixup', 'installCheck', 'pack']
    else:
        phases = ['fetch', 'unpack', 'patch']

    build_packages(
        parsed_packages, root, workspace, phases,
        spinner, db, 'Creating workspace: '
    )

    spinner.stop()
    print(f'Done! Run `source {workspace_name}/activate.sh` to begin working.')
    print(f'Get help by running `bold_help` after activating.')
