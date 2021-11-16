import json
from pathlib import Path
from typing import Dict, List


# Create a directory that hardlinks from the sources, fails on file conflict
def create_merged_dir(src_dirs: List[Path], output_dir: Path):
    output_dir.mkdir()
    files = {}

    for src_dir in src_dirs:
        for entry in src_dir.iterdir():
            if entry.is_file():
                if entry.name in files:
                    raise RuntimeError(f'File conflict: {output_dir}/{entry.name}')
                files[entry.name] = entry

    for f in files:
        # print(f'Linking {output_dir}/{f} to {files[f]}')
        files[f].link_to(output_dir / f)

    dir_srcs = {}
    for src_dir in src_dirs:
        for entry in src_dir.iterdir():
            if entry.is_dir():
                if entry.name not in dir_srcs:
                    dir_srcs[entry.name] = []
                dir_srcs[entry.name].append(entry)

    for dir in dir_srcs:
        # print(f'Recursing into {dir}')
        create_merged_dir(dir_srcs[dir], output_dir / dir)


def prepare_snapshot(root: Path, parent=None):
    # FIXME
    if parent:
        raise NotImplementedError('Parent is hardcoded to "current" for now')

    snapshot_dir = root / 'snapshot'
    (snapshot_dir / 'next').mkdir(parents=True)

    return snapshot_dir / 'next'


def commit_snapshot(root: Path, metadata: Dict, parent=None, switch=False):
    snapshot_dir = root / 'snapshot'

    # Write metadata
    with (snapshot_dir / 'next' / 'metadata.json').open('w') as f:
        f.write(json.dumps(metadata, sort_keys=True))

    # Generate root
    create_merged_dir([
        root / 'app' / package
        for package in metadata['packages']
        if metadata['packages'][package]['global']
    ], snapshot_dir / 'next' / 'root')
    (snapshot_dir / 'next' / 'root' / 'bold').mkdir()

    # Add snapshot to tree
    if (snapshot_dir / 'current').is_symlink():
        current_id = (snapshot_dir / 'current').readlink()
        highest_id = max(int(snap.name) for snap in snapshot_dir.iterdir() if snap.name.isdigit())
        next_id = str(highest_id + 1)
        (snapshot_dir / 'next').rename(snapshot_dir / next_id)
        (snapshot_dir / next_id / 'parent').symlink_to(f'../{current_id}')
        if switch:
            (snapshot_dir / 'current').unlink()
            (snapshot_dir / 'current').symlink_to(str(next_id))
    else:
        (snapshot_dir / 'next').rename(snapshot_dir / '1')
        (snapshot_dir / 'current').symlink_to('1')


def current_snapshot_metadata(root: Path) -> Dict:
    try:
        with (root / 'snapshot' / 'current' / 'metadata.json').open() as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
