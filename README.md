# Bold package manager

## "Functional core, Imperative shell"

A mix of the reproducibility of [`Nix`](https://nixos.org) and the user-friendliness of Debian's [`APT`](https://en.wikipedia.org/wiki/APT_(software)).

## Major features

- Familiarity & Ease of use:
  - Commands such as `install`, `remove`, `search`, `info`, and `update`
  - Migrates running services to new versions (happens automatically on security updates)
  - Application data, cache, and config are managed, to make backups easier
- Performance:
  - No hooks, just extracts an archive
  - Never block the user
  - Delta compression for downloads
  - Compiler absolutely not required on the target system if using the unmodified public repository
- Reproducibility:
  - Every package comes with full instructions on how to build it (a **Recipe**), to enable local building
  - Every package operation (install, update, etc.) creates a new snapshot
  - GRUB/Systemd-boot integration to boot into old snapshots
  - Can be built offline, all assets are clearly defined for centralized downloading
  - Packages can be exported into reproducible standalone archives
- Security:
  - "Dynamic Mode": Semver matching of versions for dynamic libs to deliver security updates faster without full rebuilds
  - Packages are signed by build server
  - Entire `/bold/app` directory can be stored in `dmverity` for secure immutable systems
- Ease of contribution:
  - `bold hack <package1> <package2>...` makes it easy to test and contribute patches
  - New packages are easily created (uses Javascript instead of the Nix language)
  - "Dumb" Binary cache should be trivial to setup (just an HTTPS server)
  - "Smart" Binary cache (build server) should be a single bold package

## Terms

- Package: File or directory tagged by its name and a hash of its recipe
- Recipe: Instructions on how to build a package in an isolated environment
- Repository: A list of packages and recipes
- Repository generator: Creates the repository
- Binary cache: A networked cache of signed compiled packages
- Snapshot: A local list of installed packages
- System: A list of installed packages managed by the repository

## Tasks (todo)

- [x] Evaluate js repository
- [x] Create `snapshot` on update and install
- [x] Search package cache
- [x] Hacking on packages
- [x] `System` support
- [x] Build packages to archives
- [x] Packages installed manually by name stick through updates
- [x] Also install dependencies
  - [x] In `bold install`
  - [x] In `System`s
  - [ ] Handle recursive dependencies
- [ ] Add glibc, gcc, coreutils, bash packages
- [ ] Queue install until reboot
- [x] Package removal
- [x] Actually fetch packages
- [x] Build packages if missing from binary cache
- [x] Mirror server
- [ ] Build server
  - [ ] Generate bsdiff from current + most common named version of the package to each version of package  
  - [ ] Save diff only if smaller than new package
- [ ] Package signatures
- [ ] Add lots of packages
- [ ] Host Build+Mirror server

## CLI Syntax (MVP)

```shell
# Package manipulation
bold install <package>...
bold remove <package>...
bold update
bold search
bold info <package>

# Snapshot manipulation
bold switch [snapshot]

# Development
bold hack <package>...
```

### Stretch Goals

```shell
bold run <package>
bold config <package>
bold gc remove
bold gc compress
bold gc archive
```

## Filesystem

```
/bold/app/: package contents
/bold/cache/: app caches
/bold/cache/bold/bincache: compressed package contents (old snapshots + downloads)
/bold/data/: app data
/bold/etc/: app config
/bold/snapshot/: snapshots
/bold/snapshot/current: symlink to active snapshot
/bold/snapshot/<x>/: snapshot data
/bold/snapshot/<x>/metadata.json: metadata (installed packages, description, etc.)
/bold/snapshot/<x>/cache.db3: available package list
/bold/snapshot/<x>/root/: chroot-able environment for snapshot
/bold/src/: local source code
/bold/src/repo/: (optional) local repo generator
```

## The `cache.db3` database

Not a source of truth, it's just the cache for the output of the repo generator.  
Required for all package operations (including search).

Updated by the `bold update` command.
