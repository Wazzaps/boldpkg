import argparse
import hashlib
import json
import base64
import shutil

from yaspin import yaspin
from tqdm import tqdm
import subprocess as sp
from typing import Dict

import pydantic
from pathlib import Path

ROOT = Path(__file__).parent.parent / 'bold'


def tqdm_simple(it, desc):
    return tqdm(it, desc=desc, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}', leave=False)


class Recipe(pydantic.BaseModel):
    name: str
    version: str
    externals: Dict[str, str]


def gen_recipes(args):
    print(f'Generating recipes from {args.repo}/repo')

    repo_main = str(Path(args.repo) / 'repo' / 'main.js')
    with yaspin(text='Generating'):
        try:
            proc = sp.Popen(['./bold/src/quickjs/qjs', '-m', repo_main], stdout=sp.PIPE, stderr=sp.PIPE)
            stdout, stderr = proc.communicate()
            config = json.loads(stdout)
        except BaseException:
            print()
            print(stderr.decode(errors='replace'))
            return

    recipes_dir = Path(args.repo) / 'repo' / 'recipes'
    if args.clear:
        shutil.rmtree(recipes_dir, ignore_errors=True)

    for recipe in tqdm_simple(config['apps'], desc='Writing Recipes'):
        if 'name' not in recipe:
            raise ValueError('Recipe with no name: ' + json.dumps(recipe))

        recipe_str = json.dumps(recipe, sort_keys=True).encode('utf8')
        recipe_hash = base64.b32encode(hashlib.sha256(recipe_str).digest())[:32].lower().decode()

        recipes_dir.mkdir(parents=True, exist_ok=True)
        with open(recipes_dir / f'{recipe["name"]}@{recipe_hash}.json', 'wb') as f:
            f.write(recipe_str)

    print(f'Generated {len(config["apps"])} recipes successfully!')


def build_recipes(args):
    recipes = {}
    recipes_dir = Path(args.repo) / 'repo' / 'recipes'
    apps_dir = Path(args.repo) / 'app'
    src_dir = Path(args.repo) / 'src'

    # Load recipes
    for rid in tqdm_simple(args.app, desc='Loading Recipes'):
        try:
            with open(recipes_dir / f'{rid}.json') as fd:
                recipes[rid] = json.load(fd)
        except FileNotFoundError:
            print(f'Error: Recipe "{rid}" not found. Did you "pkg recipe generate"?')
            return

    # Build recipes
    for rid in tqdm_simple(args.app, desc='Building Recipes'):
        recipe = recipes[rid]
        print(f'\n==== {rid} ====')
        target_dir = apps_dir / rid
        target_dir_wip = apps_dir / f'{rid}.wip'

        if args.rebuild:
            # Remove recipes already built
            if target_dir.is_dir():
                print(f'Removing existing build: {rid}')
                shutil.rmtree(str(target_dir))
        else:
            # Ignore recipes already built
            if target_dir.is_dir():
                print(f'Skipping: {rid}')
                continue

        # Resolve external resources
        externals = {}
        for ext in recipe['externals']:
            ext_path = recipe['externals'][ext]
            if ext_path.startswith('src://'):
                externals[f'EXT_'] = None
            else:
                print(f'WARN: Cannot handle unknown external resource path: {ext_path}')

        # Remove partially built recipes
        if target_dir_wip.is_dir():
            print(f'Removing partial build: {rid}')
            shutil.rmtree(str(target_dir_wip))

        target_dir_wip.mkdir(parents=True)

        # Run all phases
        for phase_id in ['unpack', 'patch', 'build', 'check', 'install', 'fixup', 'installCheck', 'dist']:
            if phase_id in recipe['phases']:
                phase = recipe['phases'][phase_id]
                print(f'---- {rid} - phase: {phase_id} ----')
                print(f'=> {phase["cmd"]}')
                sp.call(
                    phase['cmd'],
                    env={
                        'EXT_src': Path(''),
                        'APP_DIR': target_dir_wip,
                    },
                    shell=True
                )

        # Remove 'wip' suffix
        target_dir_wip.rename(target_dir)


def main():
    parser = argparse.ArgumentParser(description='BoldOS Package manager')
    parser.add_argument('--repo', help='Repository path', default=str(ROOT))
    subparsers = parser.add_subparsers(dest='command', required=True)

    parser_recipe = subparsers.add_parser('recipe')
    subparsers_recipe = parser_recipe.add_subparsers(dest='command', required=True)

    parser_recipe_generate = subparsers_recipe.add_parser('generate')
    parser_recipe_generate.add_argument('--clear', '-c', action='store_true', help='Clear old recipes')
    parser_recipe_generate.set_defaults(func=gen_recipes)

    parser_recipe_build = subparsers_recipe.add_parser('build')
    parser_recipe_build.add_argument('app', nargs='+', help='Name of the app(s) to build')
    parser_recipe_build.add_argument('-r', '--rebuild', action='store_true', help='Ignore recipes already built')
    parser_recipe_build.set_defaults(func=build_recipes)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
