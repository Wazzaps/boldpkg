import sqlite3


def _get_sources():
    db = sqlite3.connect('bold/metadata.sqlite3')
    cursor = db.cursor().execute('select name, generator from sources')
    return cursor.fetchall()


def cmd_source_list(_args):
    for source_name, source_generator in _get_sources():
        print(f'{source_name}\t{source_generator}')