#!/bin/bash
# Build the Tapenade ADJOINT with PROFILE-GUIDED -nocheckpoint tuning.
#   sources : code_tap/ + input_tap/  ->  build_tapAdj_nocheckpoint/mitgcmuv_tap_adj
#
# THE DEFAULT adjoint build from 2026-09-02 to 2026-09-10; since then the
# symlink ./scripts/build_tapAdj.sh points at build_tapAdj_approxAdv.sh. With
# every call checkpointed the same adjoint is build_tapAdj_ckpAll.sh; given the
# same namelist this build reproduces it bit for bit and faster (31054 vs 31052
# at 30 d, 31055 vs 31039 at 5 yr, 1.5x, with the list of 2026-09-02).
#
# The adjoint-mode switches of the live input_tap/data.autodiff (GM/Redi kept
# out of the adjoint sweep, scheme 30 in it) act only on what is recorded after
# FORWARD_STEP applies them, at the start of its reverse sweep. A routine
# FORWARD_STEP calls is recorded before them when split, so the list keeps the
# ones that read a switched variable checkpointed; post_build_checks verifies
# that with tools/tapenade_profiling/check_nocheckpoint_switches.py and records
# the result, without which the submit body refuses a namelist that switches.
# The scheme swap for implicit vertical advection exists only in the approxAdv
# build (see build_tapAdj_approxAdv.sh); the live namelist advects explicitly.
#
# The routine list is a profile of ONE configuration (run 31268 of 2026-09-12:
# the live namelists, 27 ranks, this package set): the _FWD check below catches
# a name that vanished, not a list that stopped being the right list, so
# re-profile with build_tapAdj_profile.sh whenever the adjoint's package set,
# physics, switches or decomposition change.
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
# setup directory: ./scripts/build_tapAdj_nocheckpoint.sh
# Pair with submit_tapAdj_nocheckpoint.sh.
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

    # Can the list be used with the adjoint-mode switches? Recorded for the submit body,
    # which refuses a namelist that flips a switch unless this says yes.
    if python3 "$SETUP_DIR/../../../tools/tapenade_profiling/check_nocheckpoint_switches.py" . "$NOCP_FILE" > nocheckpoint_switches.txt 2>&1; then
        NOCP_SWITCH_FREE=yes
        echo "OK: no listed routine is recorded before the adjoint-mode switches and reads one (nocheckpoint_switches.txt)."
    else
        NOCP_SWITCH_FREE=no
        echo "NOTE: listed routines are recorded before the adjoint-mode switches and read one; the submit body will refuse namelists that flip a switch:"
        grep -E 'SWITCH|ERROR' nocheckpoint_switches.txt || true
    fi
}

build_info_extra() {
    echo "nocheckpoint_list=$NOCP"
    echo "nocheckpoint_switch_free=$NOCP_SWITCH_FREE"
}

source "$SETUP_DIR/../../../tools/lib/build_body.sh"
