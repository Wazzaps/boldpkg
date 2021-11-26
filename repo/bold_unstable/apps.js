import {cLibrary, Recipe} from "./utils.js";

export const busybox = ({}) => {
    return new Recipe({
        name: "busybox",
        version: "1.35.0",
        shortDesc: "Tiny utilities for small and embedded systems",
        recipe: {
            externals: {
                src: 'src://busybox',
                config: 'repo:///bold_unstable/app_assets/busybox_config',
            },
            phases: {
                unpack: {
                    cmd: 'cp "$EXT_config" "$EXT_src"/',
                },
                patch: {
                    cmd: '',
                },
                build: {
                    cmd: 'cd "$EXT_src" && make -j8',
                },
                check: {
                    cmd: '',
                },
                install: {
                    cmd: 'cd "$EXT_src" && make CONFIG_PREFIX="$DESTDIR" install',
                },
                fixup: {
                    cmd: '',
                },
                installCheck: {
                    cmd: '',
                },
                dist: {
                    cmd: '',
                },
            },
        },
    });
};

export const hello_sh = (
    {
        message = "Hello, World",
        filename = "hello"
    }
) => {
    return new Recipe({
        name: "hello_sh",
        version: "0.1.0",
        shortDesc: "A simple hello world app",
        depends: {
            busybox,
        },
        recipe: {
            externals: {
                src: 'src://hello_sh',
            },
            buildDepends: {
                busybox,
            },
            phases: {
                unpack: {
                    cmd: '',
                },
                patch: {
                    cmd: `sed -i "s:/bin/sh:$DEP_busybox/bin/sh:g" "$EXT_src"/hello; echo "echo \"${message}\"" >> "$EXT_src"/hello`,
                },
                build: {
                    cmd: '',
                },
                check: {
                    cmd: '',
                },
                install: {
                    cmd: `mkdir -p "$DESTDIR/bin" && install "$EXT_src"/hello "$DESTDIR/bin/${filename}"`,
                },
                fixup: {
                    cmd: '',
                },
                installCheck: {
                    cmd: '',
                },
                dist: {
                    cmd: '',
                },
            }
        },
    });
};

export const libexample = (
    {}
) => {
    return new Recipe({
        name: "libexample",
        version: "0.1.0",
        shortDesc: "A simple hello world library",
        depends: {},
        recipe: {
            externals: {
                src: 'src://libexample',
            },
            buildDepends: {},
            phases: {
                unpack: {
                    cmd: '',
                },
                patch: {
                    cmd: '',
                },
                build: {
                    cmd: 'mkdir -p "$DESTDIR"/lib && gcc -shared "$EXT_src"/libexample.c -o "$DESTDIR"/lib/libexample.so',
                },
                check: {
                    cmd: '',
                },
                install: {
                    cmd: '',
                },
                fixup: {
                    cmd: '',
                },
                installCheck: {
                    cmd: '',
                },
                dist: {
                    cmd: '',
                },
            }
        },
    });
};

export const libexample_bin = (
    {}
) => {
    return new Recipe({
        name: "libexample_bin",
        version: "0.1.0",
        shortDesc: "A binary that uses libexample",
        depends: {
            libexample,
        },
        recipe: {
            externals: {
                libexample: 'src://libexample',
                src: 'src://libexample_bin',
            },
            buildDepends: {
                libexample,
            },
            phases: {
                unpack: {
                    cmd: '',
                },
                patch: {
                    cmd: '',
                },
                build: {
                    cmd: `mkdir -p "$DESTDIR"/bin && gcc "$EXT_src"/main.c ${cLibrary('libexample')} -o "$DESTDIR"/bin/libexample_bin`,
                },
                check: {
                    cmd: '',
                },
                install: {
                    cmd: '',
                },
                fixup: {
                    cmd: '',
                },
                installCheck: {
                    cmd: '',
                },
                dist: {
                    cmd: '',
                },
            }
        },
    });
};

export const libexample_bin_sh = ({}) => {
    return new Recipe({
        name: "libexample_bin_sh",
        version: "0.1.0",
        shortDesc: "A shell script wrapping libexample_bin",
        depends: {
            libexample_bin,
            busybox,
        },
        recipe: {
            externals: {
                src: 'src://libexample_bin_sh',
            },
            buildDepends: {
                busybox,
            },
            phases: {
                unpack: {
                    cmd: '',
                },
                patch: {
                    cmd: `sed -i "s:/bin/sh:$DEP_busybox/bin/sh:g" "$EXT_src"/libexample_bin_sh && sed -i 's:$DEP_libexample_bin:'"$DEP_libexample_bin:g" "$EXT_src"/libexample_bin_sh`,
                },
                build: {
                    cmd: '',
                },
                check: {
                    cmd: '',
                },
                install: {
                    cmd: `mkdir -p "$DESTDIR/bin" && install "$EXT_src"/libexample_bin_sh "$DESTDIR/bin/libexample_bin_sh"`,
                },
                fixup: {
                    cmd: '',
                },
                installCheck: {
                    cmd: '',
                },
                dist: {
                    cmd: '',
                },
            }
        },
    });
};