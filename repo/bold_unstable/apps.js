import {Recipe} from "./utils.js";

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
