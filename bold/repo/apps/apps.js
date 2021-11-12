import {Recipe} from "../utils.js";

export const busybox = ({}) => {
    return new Recipe({
        name: "busybox",
        version: "1.35.0",
        shortDesc: "Tiny utilities for small and embedded systems",
        recipe: {
            externals: {
                src: 'src://busybox',
                config: 'repo:///apps/busybox_config',
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

export const hello_sh = ({}) => {
    return new Recipe({
        name: "hello_sh",
        version: "0.1.0",
        shortDesc: "A simple hello world app",
        recipe: {
            externals: {
                src: 'src://hello_sh',
            },
            phases: {
                unpack: {
                    cmd: '',
                },
                patch: {
                    cmd: '',
                },
                build: {
                    cmd: '',
                },
                check: {
                    cmd: '',
                },
                install: {
                    cmd: 'cp "$EXT_src"/hello "$DESTDIR"',
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