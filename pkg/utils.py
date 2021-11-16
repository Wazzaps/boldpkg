from typing import List


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
        missing_packages.update(set(wanted_packages) - set(pkg_name for pkg_name, _ in  found_pkgs))

        if missing_packages:
            print('The following packages weren\'t found:')
            for pkg in sorted(missing_packages):
                print(f'- {pkg}')
            return None

        for pkg_name, pkg_hash in found_pkgs:
            exact_packages[pkg_name] = f'{pkg_name}@{pkg_hash}'

    return exact_packages

