#!/bin/bash
# Submit the Tapenade ADJOINT built against the SOURCE-MODIFIED MITgcm tree
# that carries the hooks in the tree (build_tapAdj_hooksInTree.sh, which says
# why that build exists).      build_tapAdj_hooksInTree/mitgcmuv_tap_adj
#
# Same namelists, pickup and per-run overrides as submit_tapAdj_nocheckpoint.sh;
# only the executable differs, and the run token check below enforces the
# pairing. The committed default duration is 30 days, a validation length
# (tools/compare_adj_runs.sh against a build_tapAdj_nocheckpoint run of the same
# namelist; 31107 against 31101 on 2026-09-05, and again on 2026-09-12 under the
# live namelist), not the 5-year production default of the other adjoint scripts.
#
# This file says WHAT to run; HOW is tools/lib/submit_body.sh. Run it from the
# setup directory through the wrapper:
#     ../../../tools/submit.sh scripts/submit_tapAdj_hooksInTree.sh

#SBATCH -J DINO_1deg_tapAdj_hooksInTree  # job name: names the log file only; the run directory is named from build_info.txt
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

BUILD_DIR=build_tapAdj_hooksInTree
RUN_MODE=tapAdj
PARALLEL=mpi                              # -n above must match code_tap/SIZE.h (nPx=3, nPy=9 = 27 ranks)
EXPECT_RUN_TOKEN=tapAdj_nocheckpoint_hooksInTree     # refuse a build directory holding any other variant

# ========== TEST CASE ==========

# Set to "" for default (i.e., use input_tap/data). IMPACTS_TEST_CASE overrides
# this per run. The `-` (not `:-`) is deliberate: IMPACTS_TEST_CASE= selects the
# live input_tap/data, which `:-` would swallow.
test_cases="${IMPACTS_TEST_CASE-}"      # the live namelist (since 2026-09-12; until then baseline/from180yrPk_visc2x)

# ========== TIME STEPPING PARAMETERS (IN DAYS) ==========

# These are patched into the STAGED namelist in the run directory; the tracked
# file under input_tap/ is never modified. The values here are the committed
# defaults; override per run on the command line, which leaves the tree clean:
#
#     IMPACTS_DURATION_DAYS=3660 ../../../tools/submit.sh scripts/submit_tapAdj.sh
#
duration_days="${IMPACTS_DURATION_DAYS:-30}"                # 30 d; compare with a build_tapAdj_nocheckpoint run of the same namelist and pickup
monitorFreq_days="${IMPACTS_MONITOR_FREQ_DAYS:-5}"
adjMonitorFreq_days="${IMPACTS_ADJ_MONITOR_FREQ_DAYS:-5}"
adjDumpFreq_days="${IMPACTS_ADJ_DUMP_FREQ_DAYS:-5}"

# Which of the *_days above get patched into the namelist (besides the
# duration), listed explicitly -- see the body for why not auto-detected.
TIME_PARAMS=(monitorFreq adjMonitorFreq adjDumpFreq)

# ========== PICKUP ==========

# The run starts from the pickup at the staged namelist's nIter0 (none from rest),
# read from IMPACTS_PICKUP_RUN_DIR or, when that is unset, from the production
# spin-up 31203 -- which a namelist of other settings is refused, and must name
# its run instead. IMPACTS_PICKUP_ITER overrides the iteration. See link_pickup
# in scripts/setup_params.sh (since 2026-09-12; until then the 2x spin-up
# 30983's year-180 pickup was hard-coded here). A variant that starts from another
# run's state names that run (the stability study's rows started from the
# REF_ReMax2 forward leg, which has to be rerun first since 2026-09-12):
#     IMPACTS_TEST_CASE=stability_study/from180yrPk_viscRef_ReMax2_gmFwd \
#     IMPACTS_PICKUP_RUN_DIR=<run directory holding pickup.<nIter0>> \
#         ../../../tools/submit.sh scripts/<this script>
stage_pickups() {
    link_pickup
}

source "$SLURM_SUBMIT_DIR/../../../tools/lib/submit_body.sh"
