import os
import sys
import pipes
import subprocess as sp
from pathlib import Path


def cmd_search(args):
    cache = Path(args.root) / 'snapshot' / 'current' / 'cache.db3'

    if not cache.exists():
        print('Run `bold update` before searching for packages')
        return

    LONG_SQLITE_CMD = ['sqlite3', str(cache), '.mode tabs', 'select hash, name, shortdesc from packages']
    SHORT_SQLITE_CMD = ['sqlite3', str(cache), '.mode tabs', 'select name, shortdesc from packages']

    if len(args.keyword) == 0:
        if sys.stdout.isatty():
            # If no args provided and output is a tty, use fzf to filter packages
            pipe_in, pipe_out = os.pipe()
            sqlite_proc = sp.Popen(LONG_SQLITE_CMD, stdout=os.fdopen(pipe_out))
            fzf_proc = sp.Popen(
                [
                    'fzf', '--with-nth=2..',
                    f'--preview=sqlite3 {pipes.quote(str(cache))} '
                    '"SELECT metadata FROM packages WHERE hash = {1} and name = {2}" | jq'
                ],
                stdin=os.fdopen(pipe_in),
                env={'SHELL': '/bin/sh'},
            )

            sqlite_proc.wait()
            fzf_proc.wait()
        else:
            # If no args provided and output is NOT a tty, simply echo all packages
            sp.Popen(SHORT_SQLITE_CMD).wait()
    else:
        # Use ripgrep to filter results when keywords provided
        pipe_in, pipe_out = os.pipe()
        sqlite_proc = sp.Popen(SHORT_SQLITE_CMD, stdout=os.fdopen(pipe_out))
        fzf_proc = sp.Popen(
            ['rg', *sum((['-e', keyword] for keyword in args.keyword), [])],
            stdin=os.fdopen(pipe_in),
        )

        sqlite_proc.wait()
        fzf_proc.wait()
