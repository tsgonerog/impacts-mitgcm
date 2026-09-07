#!/bin/bash
# Build the Tapenade ADJOINT against a SOURCE-MODIFIED MITgcm tree that carries
# the hooks IN THE TREE, instead of taking them from the shared -mods directory.
#   sources : code_tap/ + input_tap/   (no mods_tapenade_hooks/)
#   tree    : $IMPACTS_HOOKS_TREE, default $HOME/MITgcm_c69m_tapenade_hooks/MITgcm
#          -> build_tapAdj_hooksInTree/mitgcmuv_tap_adj
#
# WHY THIS BUILD EXISTS (2026-09-05, simplified 2026-09-07). The hooks that
# give the adjoint its ADJ* output are the seven files of
# MITgcm_c69m/mods_tapenade_hooks/, which every other adjoint build takes as
# a -mods directory ahead of code_tap/ (the build body does that; the README
# there says how). Those files are, file for file, the upstream proposal.
# This definition builds the same setup against a git copy of checkpoint69m
# in which they have been applied to the tree (branch tapenade-hooks), with
# the shared directory left out (HOOKS_MODS empty), and its run must
# reproduce the default build bitwise in fc, adxx_*, ADJ* and %MON -- run
# 31107 against 31101 on 2026-09-05, when the same files were still
# code_tap/ shadows. It is the proof that the directory and the tree form
# are the same thing. Nothing in the vendored MITgcm/ is touched.
#
# Same -nocheckpoint list as the default build. HOOK_CHECKS and DUMP_CALLS
# are the setup's own (scripts/setup_params.sh): the tree and the directory
# generate the same calls.
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
MODS=(../code_tap)
HOOKS_MODS=""                                   # the tree carries the hooks
CKP=nocheckpoint; CKP_NOTE="routines in nocheckpoint_list differentiated in split _FWD/_BWD mode"
VARIANT=hooksInTree; VARIANT_NOTE="hooks compiled from the MITgcm tree (branch tapenade-hooks), not from mods_tapenade_hooks/"
RUN_TOKEN=tapAdj_nocheckpoint_hooksInTree

NOCP_FILE="$SETUP_DIR/code_tap/tap_nocheckpoint.txt"
HOOK_FILES=(model/src/forward_step.F model/src/integr_continuity.F
            pkg/tapenade/stubs_tap_adj.F pkg/tapenade/dummy_tap.F
            pkg/tapenade/dummy_in_stepping_tap.F pkg/tapenade/tapenade_ad_diff.list
            tools/TAP_support/flow_tap)

pre_configure() {
    [ -x "$MITGCM_TREE/tools/genmake2" ] || { echo "ERROR: no MITgcm tree at $MITGCM_TREE (set IMPACTS_HOOKS_TREE)"; exit 1; }
    local f
    for f in "${HOOK_FILES[@]}"; do
        [ -f "$MITGCM_TREE/$f" ] || { echo "ERROR: $MITGCM_TREE has no $f: not the tapenade-hooks branch?"; exit 1; }
    done
    grep -q '^subroutine dummy_in_stepping_xyz_rl:' "$MITGCM_TREE/tools/TAP_support/flow_tap" \
        || { echo "ERROR: $MITGCM_TREE/tools/TAP_support/flow_tap lacks the hook stanzas"; exit 1; }
    echo "MITgcm tree: $MITGCM_TREE ($(git -C "$MITGCM_TREE" log -1 --format='%h %s' 2>/dev/null || echo 'not a git tree'))"

    # The tree must carry exactly what the shared directory carries, or this
    # build proves nothing about it.
    local hooks="$SETUP_DIR/../../mods_tapenade_hooks" differ=""
    for f in "${HOOK_FILES[@]}"; do
        cmp -s "$MITGCM_TREE/$f" "$hooks/$(basename "$f")" || differ="$differ $(basename "$f")"
    done
    [ -z "$differ" ] || { echo "ERROR: the tree differs from mods_tapenade_hooks/ in:$differ"; exit 1; }
    echo "OK: the tree's hook files are identical to mods_tapenade_hooks/."

    # -nocheckpoint list, exactly as build_tapAdj_nocheckpoint.sh reads it
    [ -f "$NOCP_FILE" ] || { echo "ERROR: $NOCP_FILE not found"; exit 1; }
    mapfile -t NOCP_LIST < <(sed -e 's/#.*//' -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' "$NOCP_FILE" | grep -v '^$' | tr 'A-Z' 'a-z')
    [ "${#NOCP_LIST[@]}" -gt 0 ] || { echo "ERROR: $NOCP_FILE names no routine"; exit 1; }
    NOCP="${NOCP_LIST[*]}"
    TAP_EXTRA="-nocheckpoint \"$NOCP\""
    echo "-nocheckpoint list (${#NOCP_LIST[@]} routines): $NOCP"
}

post_build_checks() {
    local bad=0 f
    # every hook source really came from the tree, and the shared directory did not ride in
    for f in forward_step.F integr_continuity.F stubs_tap_adj.F dummy_tap.F dummy_in_stepping_tap.F; do
        case "$(readlink -f "$f")" in
            "$MITGCM_TREE"/*) ;;
            *) echo "ERROR: $f was compiled from $(readlink -f "$f"), not from $MITGCM_TREE"; bad=1 ;;
        esac
    done
    if grep -q 'mods_tapenade_hooks' Makefile; then echo "ERROR: Makefile references mods_tapenade_hooks"; bad=1; fi
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
}

source "$SETUP_DIR/../../../tools/lib/build_body.sh"
