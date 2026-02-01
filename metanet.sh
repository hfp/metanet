#!/usr/bin/env bash
#
HERE=$(cd "$(dirname "$0")" && pwd -P)

"${HERE}/metanet.py" 12345 "mypassword" "$@"
