#!/bin/bash
# Build the FORWARD model (no adjoint).
#   sources : code/ + input/          ->  build_frd/mitgcmuv
# Serial: code/SIZE.h is the tutorial's single 62 x 62 x 1 tile.
#
# This file says WHAT to build; HOW is tools/lib/build_body.sh, the body every
# build script in every setup shares. Run from the setup directory:
# ./scripts/build_frd.sh   Pair with submit_frd.sh (the 2-year spin-up).

set -euo pipefail
SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BUILD_DIR=build_frd
BUILD_MODE=frd
PARALLEL=serial
MODS=(../code)
RUN_TOKEN=frd

source "$SETUP_DIR/../../../tools/lib/build_body.sh"
