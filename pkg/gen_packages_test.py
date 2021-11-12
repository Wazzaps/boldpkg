import base64
import hashlib
import random


def make_hash():
    return base64.b32encode(hashlib.sha256(random.randbytes(100)).digest())[:32].lower().decode()


pkgs = open('/var/lib/apt/lists/us.archive.ubuntu.com_ubuntu_dists_hirsute_universe_binary-amd64_Packages', 'rb').read().split(b'\n\n')

print('begin;')

for pkg in pkgs:
    lines = pkg.split(b'\n')
    pkg_name = None
    version = None
    shortdesc = None
    homepage = None
    for line in lines:
        if line.startswith(b'Package: '):
            pkg_name = line[9:].decode()
        if line.startswith(b'Version: '):
            version = line[9:].decode()
        if line.startswith(b'Description: '):
            shortdesc = line[13:].decode().replace('"', '')
        if line.startswith(b'Homepage: '):
            homepage = line[10:].decode()

    if pkg_name and version and shortdesc:
        if homepage:
            homepage = f'"{homepage}"'
        else:
            homepage = 'NULL'
        print(f'INSERT INTO "main"."packages"("name","hash","version","shortdesc","homepage") VALUES ("{pkg_name}","{make_hash()}","{version}","{shortdesc}", {homepage});')

print('end;')