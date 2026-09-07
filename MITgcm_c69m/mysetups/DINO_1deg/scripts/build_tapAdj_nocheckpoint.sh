#!/bin/bash
# Build the Tapenade ADJOINT with PROFILE-GUIDED -nocheckpoint tuning.
#   sources : code_tap/ + input_tap/  ->  build_tapAdj_nocheckpoint/mitgcmuv_tap_adj
#
# THE DEFAULT adjoint build since 2026-09-02: ./scripts/build_tapAdj.sh is a
# symlink to this file (and ./scripts/submit_tapAdj.sh to
# submit_tapAdj_nocheckpoint.sh). The former default, with every call
# checkpointed, is build_tapAdj_ckpAll.sh; this build is bitwise identical to
# it in fc, adxx_* and ADJ* at 30 d (run 31054 vs 31052) and 5 yr (31055 vs
# 31039) and 1.5x faster. The routine list is a profile of ONE configuration
# (KPP/GM off, 27 ranks, this package set): the _FWD check below catches a
# name that vanished, not a list that stopped being the right list, so
# re-profile with build_tapAdj_profile.sh whenever the adjoint's package
# set, physics or decomposition changes.
#
# Same stock genmake2 and shared-hooks wiring as build_tapAdj_ckpAll.sh
# (see there for where the ADJ* dump calls come from), with one Tapenade flag
# added: -nocheckpoint "<routines>". By default Tapenade checkpoints every
# call inside a time step ("joint" mode): the callee's primal is run once in
# the enclosing forward sweep and run AGAIN, recording, inside its own _B
# routine -- and that re-execution multiplies with nesting depth. For a routine
# named in -nocheckpoint Tapenade generates a _FWD/_BWD pair instead ("split"
# mode): the primal runs once, recording, and its tape simply lives until the
# backward sweep reaches it. Recomputation is traded for tape memory, within a
# single time step -- the binomial checkpointing of the time loop itself
# (C$AD BINOMIAL-CKP in code_tap/the_main_loop.F) is untouched.
#
# The routine list is code_tap/tap_nocheckpoint.txt (one name per line, '#'
# comments allowed). It was derived from the cost/benefit table of the
# build_tapAdj_profile.sh run -- tools/tapenade_profiling/README.md records
# how, and what the validation against build_tapAdj_ckpAll gave. Re-profile
# before editing it: a routine Tapenade never checkpoints is a no-op here and
# the check below rejects it, so the list stays honest.
#
# This file says WHAT to build; HOW is tools/lib/build_body.sh. Run from the
# setup directory: ./scripts/build_tapAdj_nocheckpoint.sh (or the symlink).
# Pair with submit_tapAdj_nocheckpoint.sh (or its submit_tapAdj.sh symlink).
# The adjoint is mathematically the same as build_tapAdj_ckpAll's (same
# values, stored instead of recomputed).

set -euo pipefail
SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BUILD_DIR=build_tapAdj_nocheckpoint
BUILD_MODE=tapAdj
PARALLEL=mpi
MODS=(../code_tap)
CKP=nocheckpoint; CKP_NOTE="routines in nocheckpoint_list differentiated in split _FWD/_BWD mode"
VARIANT=plain;    VARIANT_NOTE="code_tap/ alone: no variant directory, no profiler"
RUN_TOKEN=tapAdj_nocheckpoint

NOCP_FILE="$SETUP_DIR/code_tap/tap_nocheckpoint.txt"

# The routines to differentiate in split mode: strip comments and blank lines,
# one space-separated string for Tapenade. Lower case is how Tapenade names
# units internally; it matches case-insensitively, but keep the file lower case.
# genmake2 writes the -tap_extra string verbatim into the Makefile's TAP_EXTRA,
# so the inner quotes survive to the shell that runs Tapenade.
pre_configure() {
    [ -f "$NOCP_FILE" ] || { echo "ERROR: $NOCP_FILE not found"; exit 1; }
    mapfile -t NOCP_LIST < <(sed -e 's/#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' "$NOCP_FILE" | grep -v '^$' | tr 'A-Z' 'a-z')
    if [ "${#NOCP_LIST[@]}" -eq 0 ]; then
        echo "ERROR: $NOCP_FILE names no routine; use build_tapAdj_ckpAll.sh for the plain adjoint."
        exit 1
    fi
    NOCP="${NOCP_LIST[*]}"
    TAP_EXTRA="-nocheckpoint \"$NOCP\""
    echo "-nocheckpoint list (${#NOCP_LIST[@]} routines): $NOCP"
}

# Every listed routine must actually have gone split: Tapenade emits a
# <NAME>_FWD / <NAME>_BWD pair for it. A name it does not know, or one it never
# checkpoints, is silently ignored by Tapenade -- fail here instead, so the
# list cannot drift out of step with the code.
post_build_checks() {
    local missing="" r R
    for r in "${NOCP_LIST[@]}"; do
        R=$(echo "$r" | tr 'a-z' 'A-Z')
        if ! grep -qE "^ *SUBROUTINE ${R}_FWD\(" ./*_b.f; then
            missing="$missing $r"
        fi
    done
    if [ -n "$missing" ]; then
        echo "ERROR: no _FWD/_BWD pair was generated for:$missing"
        echo "       Either the name is wrong or Tapenade never checkpointed that"
        echo "       routine here. Remove it from $NOCP_FILE or fix the spelling."
        exit 1
    fi
    echo "OK: all ${#NOCP_LIST[@]} listed routines were generated in split (_FWD/_BWD) mode."
}

build_info_extra() {
    echo "nocheckpoint_list=$NOCP"
}

source "$SETUP_DIR/../../../tools/lib/build_body.sh"
