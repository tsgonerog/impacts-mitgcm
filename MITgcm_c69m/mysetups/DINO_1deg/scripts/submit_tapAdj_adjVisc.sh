#!/bin/bash
# Submit the adjoint with ADJOINT-MODE VISCOSITY INFLATION.
#                                  build_tapAdj_adjVisc/mitgcmuv_tap_adj
#
# Besides pointing at that build, this script adds the inAd*/outAd* and
# viscFacIn* lines of input_tap/variants/adjointViscosity/data.autodiff_additions
# to the staged data.autodiff, which is what actually turns the boost on. The
# adjoint-mode switches stay those of the staged namelist (the live
# input_tap/data.autodiff, or a variant's sibling), so this variant cannot drift
# from them; until 2026-09-12 the script replaced data.autodiff with a full copy,
# data.autodiff_adjointViscosity, whose switches had to be kept in step by hand.
# Build and submit script are a pair - neither works as intended without the
# other - and the run token check below enforces it. The build checkpoints every
# call, like build_tapAdj_ckpAll.sh -- the -nocheckpoint list of 2026-09-02 was
# NOT equivalent under the boost (run 31056 vs 31025; see the build script) --
# so its run directories are named tapAdj_ckpAll_adjVisc_*.
#
# This file says WHAT to run; HOW is tools/lib/submit_body.sh, shared by every
# submit script. Run it from the setup directory through the wrapper:
#     ../../../tools/submit.sh scripts/submit_tapAdj_adjVisc.sh

#SBATCH -J DINO_1deg_tapAdj_adjVisc   # job name: names the log file only; the run directory is named from build_info.txt
#SBATCH -o logs/%x.%j.out                  # %x = job name, %j = job ID; relative to the setup directory, where tools/submit.sh runs sbatch
# No -e: given only -o, sbatch sends both streams to that one file. The set -x
# trace below is stderr, so it lands there.
#SBATCH -N 1
#SBATCH -n 27
#SBATCH -t 240:00:00
#SBATCH --mail-user=tanvirshahriar@utexas.edu   # override: sbatch --mail-user=...
#SBATCH --mail-type=begin
#SBATCH --mail-type=end

set -e      # fail fast if anything is wrong
set -x      # trace every command (with expansions) into the log: the record of what was staged

# ========== WHAT THIS SCRIPT RUNS ==========

BUILD_DIR=build_tapAdj_adjVisc
RUN_MODE=tapAdj
PARALLEL=mpi                                  # -n above must match code_tap/SIZE.h (nPx=3, nPy=9 = 27 ranks)
EXPECT_RUN_TOKEN=tapAdj_ckpAll_adjVisc   # refuse a build directory holding any other variant

# ========== TEST CASE ==========

# Set to "" for default (i.e., use input_tap/data). IMPACTS_TEST_CASE overrides
# this per run. The `-` (not `:-`) is deliberate: IMPACTS_TEST_CASE= selects the
# live input_tap/data, which `:-` would swallow. The committed default here IS
# the live namelist, since 2026-09-09 the production adjoint from the year-180
# pickup (the earlier from-rest boost runs 31025/31075/31090/31109/31138/31141
# used its from-rest predecessor); the run is named from the namelist.
test_cases="${IMPACTS_TEST_CASE-}"

# ========== TIME STEPPING PARAMETERS (IN DAYS) ==========

# These are patched into the STAGED namelist in the run directory; the tracked
# file under input_tap/ is never modified. The values here are the committed
# defaults; override per run on the command line, which leaves the tree clean:
#
#     IMPACTS_DURATION_DAYS=3660 ../../../tools/submit.sh scripts/submit_tapAdj_adjVisc.sh
#
duration_days="${IMPACTS_DURATION_DAYS:-1830}"              # 5 years at 366 d/yr -> nTimeSteps
monitorFreq_days="${IMPACTS_MONITOR_FREQ_DAYS:-5}"
adjMonitorFreq_days="${IMPACTS_ADJ_MONITOR_FREQ_DAYS:-5}"
adjDumpFreq_days="${IMPACTS_ADJ_DUMP_FREQ_DAYS:-5}"

# Which of the *_days above get patched into the namelist (besides the
# duration), listed explicitly -- see the body for why not auto-detected.
TIME_PARAMS=(monitorFreq adjMonitorFreq adjDumpFreq)

# ========== THE ADJOINT-MODE VISCOSITY NAMELIST ==========

# Insert the boost's lines into the staged data.autodiff before the line that
# closes &AUTODIFF_PARM01. Runs after the namelist and its siblings are staged. A
# staged data.autodiff that already sets one of the boost's parameters is refused:
# a namelist that names a key twice would silently take one of the two values.
stage_extra() {
    local add="$SLURM_SUBMIT_DIR/input_tap/variants/adjointViscosity/data.autodiff_additions"
    local keys dup
    keys=$(sed -e 's/#.*//' "$add" | awk -F= 'NF > 1 { gsub(/[[:space:]]/, "", $1); print tolower($1) }')
    dup=$(sed -e 's/#.*//' data.autodiff | awk -F= 'NF > 1 { gsub(/[[:space:]]/, "", $1); print tolower($1) }' \
          | grep -xF "$keys" || true)
    if [[ -n "$dup" ]]; then
        echo "ERROR: the staged data.autodiff already sets" $dup "-- the adjoint-viscosity additions would repeat them"
        exit 1
    fi
    awk -v add="$add" '
        /^[[:space:]]*&AUTODIFF_PARM01/ { ingrp = 1 }
        ingrp && /^[[:space:]]*[&\/][[:space:]]*$/ {
            while ((getline line < add) > 0) print line
            ingrp = 0; done = 1
        }
        { print }
        END { exit done ? 0 : 1 }' data.autodiff > data.autodiff.adjVisc \
        || { echo "ERROR: no end of &AUTODIFF_PARM01 found in the staged data.autodiff"; exit 1; }
    mv data.autodiff.adjVisc data.autodiff
    echo "staged: data.autodiff with variants/adjointViscosity/data.autodiff_additions inserted"
}

# ========== PICKUP ==========

# The run starts from the pickup at the staged namelist's nIter0 (none from rest),
# read from IMPACTS_PICKUP_RUN_DIR or, when that is unset, from the production
# spin-up 31203 -- which a namelist of other settings is refused, and must name
# its run instead. IMPACTS_PICKUP_ITER overrides the iteration. See link_pickup
# in scripts/setup_params.sh (since 2026-09-12; until then the 2x spin-up
# 30983's year-180 pickup was hard-coded here). A kappa_v_ensemble member starts
# from its own leg:
#     IMPACTS_TEST_CASE=kappa_v_ensemble/M3_ReMax2 IMPACTS_PICKUP_RUN_DIR=<leg run dir> \
#         ../../../tools/submit.sh scripts/<this script>
stage_pickups() {
    link_pickup
}

source "$SLURM_SUBMIT_DIR/../../../tools/lib/submit_body.sh"
