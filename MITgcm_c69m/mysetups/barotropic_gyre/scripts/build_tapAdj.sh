#!/bin/bash
# Build the Tapenade ADJOINT of the barotropic gyre.
#   sources : mods_tapenade_hooks/ + code_tap/ + input_tap/  ->  build_tapAdj/mitgcmuv_tap_adj
#
# Stock genmake2 and the tree's stock Tapenade options; the ADJ* dump calls
# come from the shared hooks directory MITgcm_c69m/mods_tapenade_hooks/,
# which the build body lists first in -mods and whose flow_tap it hands to
# Tapenade as a second -ext. Every call is checkpointed (Tapenade's default;
# the time loop itself is binomially checkpointed by the directive in
# code_tap/the_main_loop.F). The cost is the box-mean surface temperature of
# code_tap/cost_test.F at the final step; the control is the initial
# temperature (xx_theta). Serial: code_tap/SIZE.h is one 62 x 62 x 1 tile.
#
# This file says WHAT to build; HOW is tools/lib/build_body.sh. Run from the
# setup directory: ./scripts/build_tapAdj.sh   Pair with submit_tapAdj.sh.

set -euo pipefail
SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BUILD_DIR=build_tapAdj
BUILD_MODE=tapAdj
PARALLEL=serial
MODS=(../code_tap)
TAP_EXTRA=""
CKP=ckpAll;     CKP_NOTE="every call inside a step checkpointed (Tapenade default); no profile for this setup"
VARIANT=plain;  VARIANT_NOTE="code_tap/ alone: no variant directory, no profiler"
RUN_TOKEN=tapAdj_ckpAll

source "$SETUP_DIR/../../../tools/lib/build_body.sh"
