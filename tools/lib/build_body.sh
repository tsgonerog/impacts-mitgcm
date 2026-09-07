#!/bin/bash
# tools/lib/build_body.sh -- the shared body of every build script.
#
# Not a program: sourced, never executed (and deliberately not +x). The build
# scripts in each setup's scripts/ directory
# (MITgcm_c69m/mysetups/<setup>/scripts/build_*.sh) are short definition files
# that say WHAT to build -- build directory, -mods list, Tapenade flags, run
# token, any extra check -- and end with
#
#     source "$SETUP_DIR/../../../tools/lib/build_body.sh"
#
# which does the building: machine profile, genmake2, make, the generated-hook
# assertions and build_info.txt, identically for every variant of every setup.
# Until 2026-09-05 each of those scripts carried its own copy of this body, and
# a fix to it had to be made in each of them.
#
# Interface -- set by the definition before sourcing:
#
#   SETUP_DIR   absolute path of the setup directory (the one holding code*/,
#               input*/ and scripts/)                                   required
#   BUILD_DIR   build directory, relative to SETUP_DIR                   required
#   BUILD_MODE  frd | tapAdj                                             required
#   RUN_TOKEN   written to build_info.txt; the submit body names run
#               directories from it (frd, tapAdj_ckpAll, ...)            required
#   PARALLEL    mpi | serial: genmake2 -mpi with MPI_OPTFILE, or no -mpi with
#               SERIAL_OPTFILE                                        default mpi
#   MODS        array of -mods directories, RELATIVE TO THE BUILD DIRECTORY;
#               on a name clash the earlier directory wins
#                                     default (../code) or (../code_tap) by mode
#   ADOF        tapAdj: the -adof options file (absolute, or relative to the
#               build directory)      default: the tree's stock adjoint_tap
#   TAP_EXTRA   tapAdj: passed verbatim through genmake2 -tap_extra     default ""
#   HOOKS_MODS  tapAdj: the shared Tapenade hooks directory, RELATIVE TO THE
#               BUILD DIRECTORY (MITgcm_c69m/mods_tapenade_hooks, see its
#               README): listed FIRST in -mods, its flow_tap handed to Tapenade
#               as a second -ext through -tap_extra, and the compiled hook
#               sources asserted to come from it. Empty = the tree carries the
#               hooks itself (build_tapAdj_hooksInTree.sh)
#                                             default ../../../mods_tapenade_hooks
#   MITGCM_TREE build against this MITgcm tree instead of the vendored one;
#               recorded as mitgcm_root= in build_info.txt   default (vendored)
#   CKP, CKP_NOTE, VARIANT, VARIANT_NOTE
#               tapAdj: value and trailing comment of the
#               tapenade_checkpointing= and variant= lines of build_info.txt
#
#   pre_configure()      optional; runs in SETUP_DIR before the build directory
#                        is entered -- read a routine list, check an extra
#                        -mods directory exists, set TAP_EXTRA
#   post_build_checks()  optional; runs in the build directory after the
#                        generic checks -- assert a variant was compiled
#   build_info_extra()   optional; echoes extra key=value lines into
#                        build_info.txt
#
# Per-setup constants come from SETUP_DIR/scripts/setup_params.sh:
#
#   HOOK_CHECKS  array of "NAME_B <argument count> <generated file>": each
#                hook's generated _B call is checked after make (tapAdj only)
#   DUMP_CALLS   how many DUMP_ADJ_* calls the compiled DUMP_FILE must carry
#   DUMP_FILE    the preprocessed source holding them (tapAdj only)
#                                                            default dummy_tap.f
#
# The definition runs under `set -euo pipefail`, and so does this file.

# ---------- guard ----------
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    echo "ERROR: $(basename "$0") is a library; source it from a scripts/build_*.sh definition" >&2
    exit 2
fi
for v in SETUP_DIR BUILD_DIR BUILD_MODE RUN_TOKEN; do
    if [ -z "${!v:-}" ]; then
        echo "ERROR: the build definition must set $v before sourcing build_body.sh" >&2
        exit 2
    fi
done
case "$BUILD_MODE" in frd|tapAdj) ;; *) echo "ERROR: BUILD_MODE must be frd or tapAdj, got '$BUILD_MODE'" >&2; exit 2 ;; esac
PARALLEL="${PARALLEL:-mpi}"
case "$PARALLEL" in mpi|serial) ;; *) echo "ERROR: PARALLEL must be mpi or serial, got '$PARALLEL'" >&2; exit 2 ;; esac

# The identity of the definition that sourced us, resolved before any cd:
# invoked_as is the name typed (build_tapAdj.sh when the default symlink was
# used), build_script the file it resolves to.
INVOKED_AS="$(basename "${BASH_SOURCE[1]}")"
BUILD_SCRIPT="$(basename "$(readlink -f "${BASH_SOURCE[1]}")")"

# ---------- machine profile ----------
# The MITgcm tree to build against: the vendored one, unless the definition
# names another in MITGCM_TREE (build_tapAdj_hooksInTree.sh builds against a
# source-modified copy of checkpoint69m outside the repository). A definition
# variable rather than an environment one on purpose: ~/.bashrc could export
# MITGCM_ROOT and silently repoint every build, the trap machine_env.sh
# already closes for the optfiles.
if [ -n "${MITGCM_TREE:-}" ]; then
    MITGCM_ROOT="$MITGCM_TREE"
    [ -x "$MITGCM_ROOT/tools/genmake2" ] || { echo "ERROR: MITGCM_TREE=$MITGCM_TREE has no tools/genmake2"; exit 1; }
else
    MITGCM_ROOT="$SETUP_DIR/../../MITgcm"
fi

# Per-machine optfiles, module stack and Tapenade check. Defaults reproduce the
# sverdrup settings, so nothing changes here; on another machine add a case
# block to tools/machine_env.sh rather than editing anything in a setup.
source "$SETUP_DIR/../../../tools/machine_env.sh"
impacts_load_modules

# The optfile is defaulted by machine_env.sh; this catches a machine with none.
if [ "$PARALLEL" = mpi ]; then
    OPTFILE="${MPI_OPTFILE:-}"; OPTFILE_VAR=MPI_OPTFILE
else
    OPTFILE="${SERIAL_OPTFILE:-}"; OPTFILE_VAR=SERIAL_OPTFILE
fi
if [ -z "$OPTFILE" ] || [ ! -f "$OPTFILE" ]; then
    echo "ERROR: $OPTFILE_VAR is unset or missing: '$OPTFILE'"
    echo "       Set it for machine '$MACHINE' in tools/machine_env.sh, or export it."
    exit 1
fi

# ---------- per-setup constants ----------
SETUP_PARAMS="$SETUP_DIR/scripts/setup_params.sh"
if [ ! -f "$SETUP_PARAMS" ]; then
    echo "ERROR: $SETUP_PARAMS not found (every setup's scripts/ carries one)"; exit 1
fi
# shellcheck source=/dev/null
source "$SETUP_PARAMS"

# ---------- what to build ----------
cd "$SETUP_DIR"
if [ "$BUILD_MODE" = tapAdj ]; then
    EXE=mitgcmuv_tap_adj
    MAKE_TARGET=tap_adj
    if [ -z "${MODS+set}" ] || [ "${#MODS[@]}" -eq 0 ]; then MODS=(../code_tap); fi
    ADOF="${ADOF:-$MITGCM_ROOT/tools/adjoint_options/adjoint_tap}"   # explicit: genmake2 would else honour a MITGCM_AD_OF in the environment
    TAP_EXTRA="${TAP_EXTRA:-}"
    HOOKS_MODS="${HOOKS_MODS-../../../mods_tapenade_hooks}"
    DUMP_FILE="${DUMP_FILE:-dummy_tap.f}"
    for v in CKP VARIANT; do
        [ -n "${!v:-}" ] || { echo "ERROR: a tapAdj build definition must set $v (for build_info.txt)"; exit 2; }
    done
else
    EXE=mitgcmuv
    MAKE_TARGET=
    if [ -z "${MODS+set}" ] || [ "${#MODS[@]}" -eq 0 ]; then MODS=(../code); fi
fi

# The definition's own preparation: read the -nocheckpoint list, check the
# profiler's -mods directory is there, and so on. Runs in the setup directory,
# so relative paths like code_tap/ resolve.
if declare -F pre_configure > /dev/null; then
    pre_configure
fi

# ---------- configure and build ----------
# Ensure build directory exists
if [ ! -d "$BUILD_DIR" ]; then
    echo "Creating the directory $BUILD_DIR..."
    mkdir "$BUILD_DIR"
fi

# Go to build directory
cd "$BUILD_DIR" || { echo "Failed to enter $BUILD_DIR"; exit 1; }

# Clean any previous build (ignore if Makefile not created yet)
make CLEAN || true

# The shared Tapenade hooks (MITgcm_c69m/mods_tapenade_hooks/): first in -mods,
# so that nothing in a setup or variant directory can shadow them, and their
# flow_tap handed to Tapenade as a second external library beside the stock
# one (the hook stanzas carry new names, so the two files do not conflict).
# Paths are relative to this build directory, like -mods.
if [ "$BUILD_MODE" = tapAdj ] && [ -n "$HOOKS_MODS" ]; then
    for f in flow_tap forward_step.F integr_continuity.F stubs_tap_adj.F \
             dummy_tap.F dummy_in_stepping_tap.F tapenade_ad_diff.list; do
        [ -f "$HOOKS_MODS/$f" ] || { echo "ERROR: $HOOKS_MODS/$f not found from $PWD (HOOKS_MODS is relative to the build directory)"; exit 1; }
    done
    MODS=("$HOOKS_MODS" "${MODS[@]}")
    TAP_EXTRA="${TAP_EXTRA:+$TAP_EXTRA }-ext $HOOKS_MODS/flow_tap"
fi

# Configure the build (this creates the Makefile here). Every path handed to
# genmake2 is relative to the build directory, like -mods, so the generated
# Makefile carries no machine path beyond the setup's own. For the adjoint,
# -adof names the tree's stock Tapenade options file, and -tap_extra carries
# the variant's Tapenade flags plus the shared hooks' -ext, written verbatim
# into the Makefile's TAP_EXTRA so inner quotes survive to the shell that
# runs Tapenade.
genmake_args=()
[ "$PARALLEL" = mpi ] && genmake_args+=(-mpi)
[ "$BUILD_MODE" = tapAdj ] && genmake_args+=(-tap)
genmake_args+=(-rd="$MITGCM_ROOT" -of="$OPTFILE" -mods="${MODS[*]}")
if [ "$BUILD_MODE" = tapAdj ]; then
    genmake_args+=(-adof="$ADOF")
    [ -n "$TAP_EXTRA" ] && genmake_args+=(-tap_extra "$TAP_EXTRA")
fi
"$MITGCM_ROOT/tools/genmake2" "${genmake_args[@]}"

# Generate dependency list
make depend

# Build using 8 threads
# shellcheck disable=SC2086
make -j 8 $MAKE_TARGET

[ -x "$EXE" ] || { echo "ERROR: make finished but $BUILD_DIR/$EXE does not exist"; exit 1; }

# ---------- adjoint checks ----------
if [ "$BUILD_MODE" = tapAdj ]; then
    # Tapenade must have generated each hook's _B call, and the argument lists
    # must match the hand-written routines (a scalar field hook: fld, fldb,
    # two names, myTime, myIter, myThid = 7; a vector pair 11; the etaN hook
    # and the mode switches fld, fldb + 3 = 5). F77 would silently misalign
    # mismatched arguments, so fail the build loudly instead. The list of hooks
    # and counts is the setup's (HOOK_CHECKS in scripts/setup_params.sh).
    check_gen_call() {
        local name=$1 expect=$2 file=$3 n
        n=$(awk -v pat="CALL ${name}\\\\(" '$0 ~ pat {f=1}
             f{buf=buf $0; if (index($0,")")) exit}
             END{if (buf=="") {print 0} else {print gsub(/,/,",",buf)+1}}' \
            "$file")
        if [ "${n:-0}" -ne "$expect" ]; then
            echo "ERROR: generated CALL ${name} in ${file} has ${n:-0}"
            echo "       arguments, expected ${expect}. Align the hand-written"
            echo "       routine with the generated call before using this"
            echo "       executable."
            exit 1
        fi
        echo "OK: generated ${name} call has ${expect} arguments."
    }
    if [ -z "${HOOK_CHECKS+set}" ] || [ "${#HOOK_CHECKS[@]}" -eq 0 ]; then
        echo "ERROR: HOOK_CHECKS is empty in $SETUP_PARAMS"; exit 1
    fi
    for entry in "${HOOK_CHECKS[@]}"; do
        # shellcheck disable=SC2086
        check_gen_call $entry
    done

    # The hook adjoints must have kept their bodies. The file holding them
    # includes AD_CONFIG.h, the only definition of ALLOW_ADJOINT_RUN, which
    # guards the ADJ* dump code: without it the adjoint is still bitwise
    # correct but writes no ADJ* files (2026-09-02, runs 31071-31073). Fail
    # here rather than after a run.
    ndump=$(grep -c 'CALL DUMP_ADJ_' "$DUMP_FILE" || true)
    if [ "${ndump:-0}" -lt "${DUMP_CALLS:-5}" ]; then
        echo "ERROR: the compiled $DUMP_FILE carries only ${ndump:-0} DUMP_ADJ_* calls (expected ${DUMP_CALLS:-5}):"
        echo "       the ADJ* dump bodies were preprocessed away -- check the AD_CONFIG.h include."
        exit 1
    fi
    echo "OK: the compiled $DUMP_FILE carries ${ndump} ADJ* dump calls."

    # The hooks must be the shared directory's, not a same-named file from a
    # setup or the tree: genmake2 links the first match, so a wrong -mods order
    # would silently build something else under this build's name.
    if [ -n "$HOOKS_MODS" ]; then
        hooks_abs="$(cd "$HOOKS_MODS" && pwd)"
        for f in forward_step.F integr_continuity.F stubs_tap_adj.F dummy_tap.F dummy_in_stepping_tap.F; do
            case "$(readlink -f "$f")" in
                "$hooks_abs"/*) ;;
                *) echo "ERROR: $f was compiled from $(readlink -f "$f"), not from $hooks_abs"; exit 1 ;;
            esac
        done
        grep -q -- "-ext $HOOKS_MODS/flow_tap" Makefile \
            || { echo "ERROR: the Makefile's TAP_EXTRA lacks -ext $HOOKS_MODS/flow_tap"; exit 1; }
        echo "OK: hook sources and flow_tap came from $hooks_abs."
    fi
fi

# The definition's own checks: the variant really compiled, every listed
# routine went split, the profiler is instrumented ...
if declare -F post_build_checks > /dev/null; then
    post_build_checks
fi

# ---------- build record ----------
# Written last, after every check above passed, so build_info.txt can only
# describe an executable this script built and verified. The submit body
# refuses an executable without it, or whose checksum does not match, and
# takes run_token from it, so a run directory is named from what was actually
# built, not from what the submit script assumes:
#     <setup>_<run_token>_<duration>[_<tag>]_run<jobid>
dirty=$(git -C "$SETUP_DIR" diff --name-only HEAD -- . 2>/dev/null | wc -l)
{
    echo "build_script=$BUILD_SCRIPT"   # the definition file, symlink resolved
    echo "invoked_as=$INVOKED_AS"
    echo "build_dir=$(basename "$PWD")"
    echo "exe_md5=$(md5sum "$EXE" | cut -d' ' -f1)"   # identity of the binary this record describes; the submit body verifies it
    if [ "$BUILD_MODE" = tapAdj ]; then
        printf 'tapenade_checkpointing=%-13s # %s\n' "$CKP" "${CKP_NOTE:-}"
        printf 'variant=%-28s # %s\n' "$VARIANT" "${VARIANT_NOTE:-}"
    fi
    echo "run_token=$RUN_TOKEN"
    if [ "$BUILD_MODE" = tapAdj ]; then
        echo "tap_extra=$(sed -n 's/^TAP_EXTRA *= *//p' Makefile)"
        echo "hooks_mods=${HOOKS_MODS:-none (the tree carries the hooks)}"
    fi
    if [ -n "${MITGCM_TREE:-}" ]; then
        echo "mitgcm_root=$MITGCM_ROOT"   # not the vendored tree: say which
    fi
    if declare -F build_info_extra > /dev/null; then
        build_info_extra
    fi
    echo "git_commit=$(git -C "$SETUP_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
    echo "git_modified_tracked_files=${dirty}   # in this setup"
    echo "built=$(date '+%Y-%m-%d %H:%M:%S %Z') on $(hostname)"
} > build_info.txt
echo "OK: wrote $(basename "$PWD")/build_info.txt (run_token=$RUN_TOKEN)."
