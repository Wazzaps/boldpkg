#!/bin/sh
sha256sum | xxd -ps -r | base32 | cut -c-32 | tr 'A-Z' 'a-z'
