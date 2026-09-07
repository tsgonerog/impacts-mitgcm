#!/bin/bash
# Build the Tapenade ADJOINT with Tapenade's CHECKPOINTING PROFILER compiled in.
#   sources : code_tap/ + input_tap/ + tools/tapenade_profiling/mods_profile/
#          -> build_tapAdj_profile/mitgcmuv_tap_adj
#
# Same stock genmake2 and shared-hooks wiring as build_tapAdj_ckpAll.sh
# (see there for where the ADJ* dump calls come from), plus two things:
#
#   * "-profile" on the Tapenade command line, through -tap_extra. Tapenade
#     then brackets every checkpointed call in the generated adjoint with
#     ADPROFILEADJ_* calls that time each checkpoint's recomputation and
#     measure the snapshot it stores, and accumulate per call site the time
#     that NOT checkpointing it would save and the peak memory it would cost.
#   * a second -mods directory, tools/tapenade_profiling/mods_profile/, listed
#     FIRST so it shadows code_tap/ and the vendored tree. It supplies
#     adProfile.c (the runtime those calls need, copied from the installed
#     Tapenade's ADFirstAidKit: c69m ships an older, API-incompatible copy and
#     does not compile it) and a the_model_main.F that, after THE_MAIN_LOOP_B,
#     prints the tape peak and writes the per-process cost/benefit table
#     (tapenade_profile.NNNN.txt in the run directory).
#
# This is a DIAGNOSTIC build. Its adjoint does exactly what build_tapAdj_ckpAll's
# does (same checkpointing, same numbers) with timing calls added, so it is
# somewhat slower and must not be used for production runs or as a runtime
# reference. Pair it with submit_tapAdj_profile.sh (30-day default), and
# read tools/tapenade_profiling/README.md for how to turn the table into a
# -nocheckpoint list for build_tapAdj_nocheckpoint.sh. It deliberately does
# NOT carry that list: a profile of the tuned build would only show the
# residual cost, while the list is derived by seeing every checkpoint.
#
# This file says WHAT to build; HOW is tools/lib/build_body.sh. Run from the
# setup directory: ./scripts/build_tapAdj_profile.sh

set -euo pipefail
SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BUILD_DIR=build_tapAdj_profile
BUILD_MODE=tapAdj
PARALLEL=mpi
# The profiler runtime + main program. genmake2 gets the path relative to the
# build directory, like ../code_tap, so the generated Makefile carries no
# extra machine path; the existence check below resolves the same directory
# from the setup.
PROFILE_MODS="../../../../tools/tapenade_profiling/mods_profile"
MODS=("$PROFILE_MODS" ../code_tap)                          # the profiler FIRST
TAP_EXTRA="-profile"
CKP=ckpAll;         CKP_NOTE="every call checkpointed, as the profile must see them"
VARIANT=profile; VARIANT_NOTE="-profile instrumentation + mods_profile/ main program; diagnostic only"
RUN_TOKEN=tapAdj_ckpAll_profile

pre_configure() {
    local f
    for f in adProfile.c the_model_main.F; do
        if [ ! -f "$SETUP_DIR/../../../tools/tapenade_profiling/mods_profile/$f" ]; then
            echo "ERROR: tools/tapenade_profiling/mods_profile/$f not found"
            echo "       (looked from $SETUP_DIR/../../../)"
            exit 1
        fi
    done
}

# Profiler-specific checks: Tapenade must have emitted the instrumentation,
# the shadowed main program must be the one compiled, and its runtime linked.
post_build_checks() {
    if ! grep -q 'CALL ADPROFILEADJ_SNPWRITE' forward_step_b.f; then
        echo "ERROR: forward_step_b.f carries no ADPROFILEADJ_* calls;"
        echo "       -profile did not reach the Tapenade command line."
        exit 1
    fi
    if ! grep -q 'ADPROFILEADJ_SHOWPROFILESFILE' the_model_main.f; then
        echo "ERROR: the compiled the_model_main.f is not the profiling variant;"
        echo "       check the -mods order (mods_profile must come first)."
        exit 1
    fi
    [ -f adProfile.o ] || { echo "ERROR: adProfile.o missing; adProfile.c was not compiled."; exit 1; }
    echo "OK: profiler instrumentation, main program and runtime are all in place."
}

source "$SETUP_DIR/../../../tools/lib/build_body.sh"
