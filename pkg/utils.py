from pathlib import Path
from typing import List
import toml


def read_config(root: Path):
    return toml.load(root / 'config.toml')


def parse_package_names(db, packages: List[str]):
    invalid_packages = [p for p in packages if p.count('@') >= 2]

    if invalid_packages:
        print('The following package names are invalid:')
        for pkg in invalid_packages:
            print(f'- {pkg}')
        return None

    exact_packages = {p: p for p in packages if p.count('@') == 1}
    wanted_packages = [p for p in packages if p.count('@') == 0]

    with db:
        cursor = db.cursor()
        missing_packages = set()

        # Verify exact packages
        cursor.execute('''
            DROP TABLE IF EXISTS wanted_packages
        ''')
        cursor.execute('''
            CREATE TEMPORARY TABLE "wanted_packages"
            (
                "name"              TEXT    NOT NULL,
                "hash"              TEXT    NOT NULL
            )
        ''')
        for package in exact_packages.keys():
            pkg_name, _, pkg_hash = package.partition('@')
            cursor.execute('''
                INSERT INTO "wanted_packages"
                VALUES (?, ?)
            ''', (pkg_name, pkg_hash))

        found_pkgs = cursor.execute('SELECT name, hash FROM wanted_packages JOIN packages USING (name, hash)').fetchall()
        found_pkgs = [f'{pkg_name}@{pkg_hash}' for pkg_name, pkg_hash in found_pkgs]
        missing_packages.update(set(exact_packages.keys()) - set(found_pkgs))

        # Verify and get named packages
        cursor.execute('''
            DROP TABLE IF EXISTS wanted_packages
        ''')
        cursor.execute('''
            CREATE TEMPORARY TABLE "wanted_packages"
            (
                "name"              TEXT    NOT NULL
            )
        ''')
        for package in wanted_packages:
            cursor.execute('''
                INSERT INTO "wanted_packages"
                VALUES (?)
            ''', (package,))

        found_pkgs = cursor.execute('SELECT name, hash FROM wanted_packages JOIN named_packages USING (name)').fetchall()
        missing_packages.update(set(wanted_packages) - set(pkg_name for pkg_name, _ in found_pkgs))

        if missing_packages:
            print('The following packages weren\'t found:')
            for pkg in sorted(missing_packages):
                print(f'- {pkg}')
            return None

        for pkg_name, pkg_hash in found_pkgs:
            exact_packages[pkg_name] = f'{pkg_name}@{pkg_hash}'

    return exact_packages


def parse_system_names(db, systems: List[str]):
    invalid_systems = [s for s in systems if s.count('@') >= 2]

    if invalid_systems:
        print('The following system names are invalid:')
        for sys in invalid_systems:
            print(f'- {sys}')
        return None

    exact_systems = {s: s for s in systems if s.count('@') == 1}
    wanted_systems = [s for s in systems if s.count('@') == 0]

    with db:
        cursor = db.cursor()
        missing_systems = set()

        # Verify exact systems
        cursor.execute('''
            DROP TABLE IF EXISTS wanted_systems
        ''')
        cursor.execute('''
            CREATE TEMPORARY TABLE "wanted_systems"
            (
                "name"              TEXT    NOT NULL,
                "hash"              TEXT    NOT NULL
            )
        ''')
        for system in exact_systems.keys():
            sys_name, _, sys_hash = system.partition('@')
            cursor.execute('''
                INSERT INTO "wanted_systems"
                VALUES (?, ?)
            ''', (sys_name, sys_hash))

        found_systems = cursor.execute('SELECT name, hash FROM wanted_systems JOIN systems USING (name, hash)').fetchall()
        found_systems = [f'{sys_name}@{sys_hash}' for sys_name, sys_hash in found_systems]
        missing_systems.update(set(exact_systems.keys()) - set(found_systems))

        # Verify and get named systems
        cursor.execute('''
            DROP TABLE IF EXISTS wanted_systems
        ''')
        cursor.execute('''
            CREATE TEMPORARY TABLE "wanted_systems"
            (
                "name"              TEXT    NOT NULL
            )
        ''')
        for system in wanted_systems:
            cursor.execute('''
                INSERT INTO "wanted_systems"
                VALUES (?)
            ''', (system,))

        found_systems = cursor.execute('SELECT name, hash FROM wanted_systems JOIN named_systems USING (name)').fetchall()
        missing_systems.update(set(wanted_systems) - set(sys_name for sys_name, _ in found_systems))

        if missing_systems:
            print('The following systems weren\'t found:')
            for sys in sorted(missing_systems):
                print(f'- {sys}')
            return None

        for sys_name, sys_hash in found_systems:
            exact_systems[sys_name] = f'{sys_name}@{sys_hash}'

    return exact_systems


def find_package_deps(db, packages, visited=None, dependencies=None):
    from building import get_metadata

    if visited is None:
        visited = set()
    if dependencies is None:
        dependencies = set()
    for pkg in packages:
        if pkg in visited:
            continue
        pkg_deps = set(get_metadata(db, pkg)['depends'].values())
        dependencies |= pkg_deps
        for dep in pkg_deps:
            dependencies |= find_package_deps(db, [dep], visited, dependencies)
        visited.add(pkg)
    return dependencies
