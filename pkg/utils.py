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
            pkg_name, _, pkg_hash = package.partition('@')
            cursor.execute('''
                INSERT INTO "wanted_packages"
                VALUES (?)
            ''', (package,))

        missing_pkgs = cursor.execute('SELECT name, hash FROM wanted_packages JOIN packages USING (name)').fetchall()
        for pkg_name, pkg_hash in missing_pkgs:
            exact_packages[pkg_name] = f'{pkg_name}@{pkg_hash}'

    return exact_packages


def verify_valid_packages_names(db, packages: List[str]):
    for package in packages:
        if package.count('@') != 1:
            print(f'Package name "{package}" is invalid, use full name (i.e. <name>@<hash>)')
            return False

    with db:
        cursor = db.cursor()
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
        for package in packages:
            pkg_name, _, pkg_hash = package.partition('@')
            cursor.execute('''
                INSERT INTO "wanted_packages"
                VALUES (?, ?)
            ''', (pkg_name, pkg_hash))
        missing_pkgs = cursor.execute('''
            SELECT name, hash
                FROM wanted_packages LEFT OUTER JOIN packages W
                USING (name, hash)
                WHERE W.name IS NULL
        ''').fetchall()
        if len(missing_pkgs) != 0:
            missing_pkgs_str = ', '.join(f'{pkg_name}@{pkg_hash}' for pkg_name, pkg_hash in missing_pkgs)
            print(f'The following packages were not found: {missing_pkgs_str}')
            return False

    return True
