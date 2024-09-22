#!/usr/bin/env sh
set -e
self_path="`dirname "${0}"`"

set -x
python3 "${self_path}/build.py" "${@}"
