import argparse
from pathlib import Path

from cmd_search import cmd_search
from cmd_hack import cmd_hack
from cmd_source import cmd_source_list
from cmd_update import cmd_update

ROOT = Path(__file__).parent.parent / 'bold'


def unimplemented(_args):
    print('UNIMPLEMENTED')
    exit(1)


def main():
    parser = argparse.ArgumentParser(description='BoldOS Package manager')
    parser.add_argument('--repo', help='Repository path', default=str(ROOT))
    subparsers = parser.add_subparsers(dest='command', required=True)

    parser_install = subparsers.add_parser('install')
    parser_install.add_argument('app', nargs='+', help='Name of the app(s) to install')
    parser_install.add_argument('-q', '--queue', action='store_true', help='Finish install on next `bold switch`')
    parser_install.set_defaults(func=unimplemented)

    parser_install = subparsers.add_parser('remove')
    parser_install.add_argument('app', nargs='+', help='Name of the app(s) to install')
    parser_install.add_argument('-q', '--queue', action='store_true', help='Finish install on next `bold switch`')
    parser_install.set_defaults(func=unimplemented)

    parser_update = subparsers.add_parser('update')
    parser_update.add_argument('app', nargs='*', help='Name of the app(s) to update')
    parser_update.add_argument('-q', '--queue', action='store_true', help='Finish update on next `bold switch`')
    parser_update.add_argument('-c', '--check', action='store_true', help='Check for updates, but don\'t install them')
    parser_update.add_argument('-n', '--no-reload', action='store_true', help='Don\'t reload services')
    parser_update.set_defaults(func=cmd_update)

    parser_search = subparsers.add_parser('search')
    parser_search.add_argument('keyword', nargs='*', help='Keywords to search (leave empty for TUI)')
    parser_search.set_defaults(func=cmd_search)

    parser_run = subparsers.add_parser('run')
    parser_run.add_argument('app', help='Name of the app to run')
    parser_run.set_defaults(func=unimplemented)

    parser_config = subparsers.add_parser('config')
    parser_config.add_argument('app', nargs='?', help='Name of the app to config')
    parser_config.set_defaults(func=unimplemented)

    parser_info = subparsers.add_parser('info')
    parser_info.add_argument('app', help='Name of the app to get info about')
    parser_info.set_defaults(func=unimplemented)

    parser_hack = subparsers.add_parser('hack')
    parser_hack.add_argument('app', nargs='+', help='Name of the app(s) to work on')
    parser_hack.set_defaults(func=cmd_hack)

    parser_switch = subparsers.add_parser('switch')
    parser_switch.add_argument('generation', help='Generation ID to switch to')
    parser_switch.add_argument('-r', '--on-reboot', action='store_true', help='Switch on next reboot')
    parser_switch.set_defaults(func=unimplemented)

    parser_gc = subparsers.add_parser('gc')
    parser_gc.set_defaults(func=unimplemented)
    subparsers_gc = parser_gc.add_subparsers(dest='action', required=True)

    parser_gc_remove = subparsers_gc.add_parser('remove')
    parser_gc_remove.add_argument('-o', '--older-than', help='Remove generations older than... (units: h/d/w/m/y)')
    parser_gc_remove.add_argument('generation', nargs='*', help='Remove specific generation(s)')

    parser_gc_compress = subparsers_gc.add_parser('compress')
    parser_gc_compress.add_argument('-o', '--older-than', help='Compress generations older than... (units: h/d/w/m/y)')
    parser_gc_compress.add_argument('generation', nargs='*', help='Compress specific generation(s)')

    parser_gc_archive = subparsers_gc.add_parser('archive')
    parser_gc_archive.add_argument('-o', '--older-than', help='Archive generations older than... (units: h/d/w/m/y)')
    parser_gc_archive.add_argument('generation', nargs='*', help='Archive specific generation(s)')

    parser_source = subparsers.add_parser('source')
    parser_source.set_defaults(func=cmd_source_list)
    subparsers_source = parser_source.add_subparsers(dest='action')

    parser_source_list = subparsers_source.add_parser('list')
    parser_source_list.set_defaults(func=cmd_source_list)

    # ---------

    # parser_recipe = subparsers.add_parser('recipe')
    # subparsers_recipe = parser_recipe.add_subparsers(dest='command', required=True)
    #
    # parser_recipe_generate = subparsers_recipe.add_parser('generate')
    # parser_recipe_generate.add_argument('--clear', '-c', action='store_true', help='Clear old recipes')
    # parser_recipe_generate.set_defaults(func=gen_recipes)
    #
    # parser_recipe_build = subparsers_recipe.add_parser('build')
    # parser_recipe_build.add_argument('app', nargs='+', help='Name of the app(s) to build')
    # parser_recipe_build.add_argument('-r', '--rebuild', action='store_true', help='Ignore recipes already built')
    # parser_recipe_build.set_defaults(func=build_recipes)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
