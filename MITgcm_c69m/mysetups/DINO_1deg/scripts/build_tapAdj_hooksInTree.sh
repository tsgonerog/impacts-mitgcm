#!/bin/bash
# Build the Tapenade ADJOINT against a SOURCE-MODIFIED MITgcm tree that carries
# the ADJ* dump hooks, the adjoint-mode switches and the ADEXCH_* halo folds
# IN THE TREE, from a code_tap/ stripped of the shadow files that provide them
# here.
#   sources : code_tap/ minus the hook shadows (listed below) + input_tap/
#   tree    : $IMPACTS_HOOKS_TREE, default $HOME/MITgcm_c69m_tapenade_hooks/MITgcm
#          -> build_tapAdj_hooksInTree/mitgcmuv_tap_adj
#
# WHY THIS BUILD EXISTS (2026-09-05). The default adjoint gets its ADJ* output
# from files in code_tap/ that shadow upstream sources at build time
# (forward_step.F, integr_continuity.F, the four hook interfaces, dummy_tap.F,
# stubs_tap_adj.F, flow_tap_local through adjoint_tap_local). To find out
# whether that mechanism can go INTO MITgcm itself, the same changes were
# integrated into a git copy of checkpoint69m outside this repository, on the
# branch tapenade-hooks, and this definition builds DINO against that copy
# with the shadows removed. Its run must reproduce the default build bitwise
# (fc, adxx_*, ADJ*, %MON) -- validated against run 31101 with
# tools/compare_adj_runs.sh; the write-up and the patch series are beside the
# tree (README.md, patches/). Nothing in the vendored MITgcm/ is touched.
#
# The in-tree hooks are not the shadows moved: the dump hook is one external
# call PER FIELD (DUMMY_IN_STEPPING_XYZ_RL and friends, called from a wrapper
# routine that Tapenade differentiates), because Tapenade drops the adjoint
# argument of a field that is passive in a given configuration, so a single
# 11-field hook would be called with a configuration-dependent number of
# arguments. The mode switches and the etaN hook are new *_TAP routines added
# beside the upstream ones, so pkg/autodiff is untouched. HOOK_CHECKS and
# DUMP_CALLS below are therefore this build's own, set in pre_configure after
# scripts/setup_params.sh has been read.
#
# Same -nocheckpoint list as the default build (code_tap/tap_nocheckpoint.txt),
# same -mods content otherwise, stock adjoint_tap options of the tree (no
# flow_tap_local: the stanzas are in the tree's tools/TAP_support/flow_tap).
#
# This file says WHAT to build; HOW is tools/lib/build_body.sh. Run from the
# setup directory: ./scripts/build_tapAdj_hooksInTree.sh
# Pair with submit_tapAdj_hooksInTree.sh.

set -euo pipefail
SETUP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

BUILD_DIR=build_tapAdj_hooksInTree
BUILD_MODE=tapAdj
PARALLEL=mpi
MITGCM_TREE="${IMPACTS_HOOKS_TREE:-$HOME/MITgcm_c69m_tapenade_hooks/MITgcm}"
MODS_NAME=code_tap_hooksInTree          # assembled by pre_configure inside the build directory
MODS=(./$MODS_NAME)
ADOF="$MITGCM_TREE/tools/adjoint_options/adjoint_tap"   # the tree's STOCK options file
CKP=nocheckpoint; CKP_NOTE="routines in nocheckpoint_list differentiated in split _FWD/_BWD mode"
VARIANT=hooksInTree; VARIANT_NOTE="hooks compiled from the MITgcm tree (branch tapenade-hooks), not from code_tap/ shadows"
RUN_TOKEN=tapAdj_nocheckpoint_hooksInTree

NOCP_FILE="$SETUP_DIR/code_tap/tap_nocheckpoint.txt"

# The code_tap/ files that provide the hooks HERE and are therefore left out of
# this build's -mods directory: what they provide comes from the tree instead.
HOOK_SHADOWS=(adjoint_tap_local flow_tap_local
              forward_step.F integr_continuity.F
              dummy_in_stepping.F dummy_for_etan.F
              autodiff_inadmode_set.F autodiff_inadmode_unset.F
              dummy_tap.F stubs_tap_adj.F)

pre_configure() {
    [ -x "$MITGCM_TREE/tools/genmake2" ] || { echo "ERROR: no MITgcm tree at $MITGCM_TREE (set IMPACTS_HOOKS_TREE)"; exit 1; }
    for f in pkg/tapenade/dummy_in_stepping_tap.F pkg/tapenade/tapenade_ad_diff.list; do
        [ -f "$MITGCM_TREE/$f" ] || { echo "ERROR: $MITGCM_TREE has no $f: not the tapenade-hooks branch?"; exit 1; }
    done
    grep -q '^subroutine dummy_in_stepping_xyz_rl:' "$MITGCM_TREE/tools/TAP_support/flow_tap" \
        || { echo "ERROR: $MITGCM_TREE/tools/TAP_support/flow_tap lacks the hook stanzas"; exit 1; }
    echo "MITgcm tree: $MITGCM_TREE ($(git -C "$MITGCM_TREE" log -1 --format='%h %s' 2>/dev/null || echo 'not a git tree'))"

    # -nocheckpoint list, exactly as build_tapAdj_nocheckpoint.sh reads it
    [ -f "$NOCP_FILE" ] || { echo "ERROR: $NOCP_FILE not found"; exit 1; }
    mapfile -t NOCP_LIST < <(sed -e 's/#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' "$NOCP_FILE" | grep -v '^$' | tr 'A-Z' 'a-z')
    [ "${#NOCP_LIST[@]}" -gt 0 ] || { echo "ERROR: $NOCP_FILE names no routine"; exit 1; }
    NOCP="${NOCP_LIST[*]}"
    TAP_EXTRA="-nocheckpoint \"$NOCP\""
    echo "-nocheckpoint list (${#NOCP_LIST[@]} routines): $NOCP"

    # The -mods directory: every regular file of code_tap/ except the hook
    # shadows, as symlinks, inside the build directory (gitignored, and remade
    # on every build so it cannot go stale).
    mkdir -p "$BUILD_DIR"
    local mods="$BUILD_DIR/$MODS_NAME" name skip f
    rm -rf "$mods"; mkdir "$mods"
    local kept=0 dropped=""
    for f in code_tap/*; do
        [ -f "$f" ] || continue
        name=$(basename "$f"); skip=no
        for s in "${HOOK_SHADOWS[@]}"; do [ "$name" = "$s" ] && skip=yes; done
        if [ $skip = yes ]; then dropped="$dropped $name"; continue; fi
        ln -s "../../code_tap/$name" "$mods/$name"; kept=$((kept+1))
    done
    echo "-mods: $mods ($kept files linked from code_tap/; left out:$dropped)"

    # This build's generated hooks: one field hook per shape (fld, fldb, two
    # names, myTime, myIter, myThid = 7; a vector pair = 11), the etaN hook and
    # the two mode switches (fld, fldb + 3 = 5). Compiled dummy_tap.f carries
    # five DUMP_ADJ_* calls (XYZ, XY, XYZ_UV, XY_UV, etaN).
    HOOK_CHECKS=(
        "DUMMY_IN_STEPPING_XYZ_RL_B 7 dummy_in_stepping_tap_b.f"
        "DUMMY_IN_STEPPING_XY_RS_B 7 dummy_in_stepping_tap_b.f"
        "DUMMY_IN_STEPPING_UV_XYZ_RL_B 11 dummy_in_stepping_tap_b.f"
        "DUMMY_IN_STEPPING_UV_XY_RS_B 11 dummy_in_stepping_tap_b.f"
        "DUMMY_FOR_ETAN_TAP_B 5 integr_continuity_b.f"
        "AUTODIFF_INADMODE_SET_TAP_B 5 forward_step_b.f"
        "AUTODIFF_INADMODE_UNSET_TAP_B 5 forward_step_b.f"
    )
    DUMP_CALLS=5
}

post_build_checks() {
    local bad=0 f
    # every shadow really came from the tree, and no local Tapenade library rode in
    for f in forward_step.F integr_continuity.F dummy_tap.F stubs_tap_adj.F dummy_in_stepping.F; do
        case "$(readlink -f "$f")" in
            "$MITGCM_TREE"/*) ;;
            *) echo "ERROR: $f was compiled from $(readlink -f "$f"), not from $MITGCM_TREE"; bad=1 ;;
        esac
    done
    if grep -q 'flow_tap_local' Makefile; then echo "ERROR: Makefile still references flow_tap_local"; bad=1; fi
    [ -f dummy_in_stepping_tap_b.f ] || { echo "ERROR: Tapenade did not generate dummy_in_stepping_tap_b.f"; bad=1; }
    # the wrapper was differentiated in split mode (the C$AD NOCHECKPOINT directive honoured)
    grep -qE '^ *SUBROUTINE DUMMY_IN_STEPPING_TAP_FWD\(' dummy_in_stepping_tap_b.f \
        || { echo "ERROR: DUMMY_IN_STEPPING_TAP was not split (no _FWD): the C\$AD NOCHECKPOINT directive was not honoured"; bad=1; }
    # every listed routine went split, as in build_tapAdj_nocheckpoint.sh
    local missing="" r R
    for r in "${NOCP_LIST[@]}"; do
        R=$(echo "$r" | tr 'a-z' 'A-Z')
        grep -qE "^ *SUBROUTINE ${R}_FWD\(" ./*_b.f || missing="$missing $r"
    done
    [ -z "$missing" ] || { echo "ERROR: no _FWD/_BWD pair was generated for:$missing"; bad=1; }
    [ $bad -eq 0 ] || exit 1
    echo "OK: hooks compiled from $MITGCM_TREE; wrapper split; all ${#NOCP_LIST[@]} listed routines split."
}

build_info_extra() {
    echo "nocheckpoint_list=$NOCP"
    echo "mitgcm_tree_commit=$(git -C "$MITGCM_TREE" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    echo "hook_shadows_left_out=${HOOK_SHADOWS[*]}"
}

source "$SETUP_DIR/../../../tools/lib/build_body.sh"
