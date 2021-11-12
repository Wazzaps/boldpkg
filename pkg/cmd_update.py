import datetime
import json
import sqlite3
import subprocess as sp
from pathlib import Path

from yaspin import yaspin


def _get_sources(db: sqlite3.Connection):
    cursor = db.cursor().execute('select id, name, generator from sources')
    return cursor.fetchall()


def cmd_update(_args):
    db = sqlite3.connect('bold/metadata.sqlite3')

    for source_id, source_name, source_generator in _get_sources(db):
        print(f'Updating from "{source_name}"...')
        if source_generator:
            if source_generator.startswith('file://'):
                generator_path = Path(source_generator[7:])
            else:
                print(f'Unknown generator URI: {source_generator}')
                continue

            generation = datetime.datetime.now().isoformat(timespec='seconds')
            print(f'Creating new generation "{generation}"')
            repo_main = str(generator_path / 'main.js')
            with yaspin(text='Running Generator'):
                try:
                    proc = sp.Popen(
                        ['../src/quickjs/qjs', '-m', repo_main],
                        stdout=sp.PIPE, stderr=sp.PIPE, cwd=str(generator_path)
                    )
                    stdout, stderr = proc.communicate()
                    config = json.loads(stdout)
                except BaseException:
                    print()
                    print(stderr.decode(errors='replace'))
                    return

            # Create generation in transaction
            with db:
                cursor = db.cursor()
                cursor.execute(
                    'INSERT INTO source_generations (source, generation) VALUES (?, ?)', (source_id, generation)
                )

                for app_name, app_metadata in config['recipes'].items():
                    app_name, _, app_hash = app_name.partition('@')

                    app_recipe = app_metadata['recipe']
                    del app_metadata['recipe']

                    cursor.execute(
                        'INSERT INTO packages (name, hash, shortdesc, metadata, recipe, source, source_generation) VALUES (?, ?, ?, ?, ?, ?, ?)',
                        (
                            app_name, app_hash,
                            app_metadata['shortDesc'],
                            json.dumps(app_metadata, sort_keys=True),
                            json.dumps(app_recipe, sort_keys=True),
                            source_id, generation
                        )
                    )
