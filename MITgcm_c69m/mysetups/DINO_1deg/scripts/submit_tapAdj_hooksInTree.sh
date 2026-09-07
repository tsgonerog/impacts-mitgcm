#!/bin/bash
# Submit the Tapenade ADJOINT built against the SOURCE-MODIFIED MITgcm tree
# that carries the hooks in the tree (build_tapAdj_hooksInTree.sh, which says
# why that build exists).      build_tapAdj_hooksInTree/mitgcmuv_tap_adj
#
# Same namelists, pickup and per-run overrides as submit_tapAdj_nocheckpoint.sh;
# only the executable differs, and the run token check below enforces the
# pairing. The committed default duration is 30 days, the configuration this
# build is validated in (tools/compare_adj_runs.sh against run 31101), not the
# 5-year production default of the other adjoint scripts.
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
test_cases="${IMPACTS_TEST_CASE-baseline/from180yrPk_visc2x}"

# ========== TIME STEPPING PARAMETERS (IN DAYS) ==========

# These are patched into the STAGED namelist in the run directory; the tracked
# file under input_tap/ is never modified. The values here are the committed
# defaults; override per run on the command line, which leaves the tree clean:
#
#     IMPACTS_DURATION_DAYS=3660 ../../../tools/submit.sh scripts/submit_tapAdj.sh
#
duration_days="${IMPACTS_DURATION_DAYS:-30}"                # 30 d: the validation configuration of this build (run 31101)
monitorFreq_days="${IMPACTS_MONITOR_FREQ_DAYS:-5}"
adjMonitorFreq_days="${IMPACTS_ADJ_MONITOR_FREQ_DAYS:-5}"
adjDumpFreq_days="${IMPACTS_ADJ_DUMP_FREQ_DAYS:-5}"

# Which of the *_days above get patched into the namelist (besides the
# duration), listed explicitly -- see the body for why not auto-detected.
TIME_PARAMS=(monitorFreq adjMonitorFreq adjDumpFreq)

# ========== PICKUP ==========

# The 180-yr state of the 200-yr visc2x spin-up, matching the nIter0=3162240
# baked into baseline/data_from180yrPk_visc2x. Changing test_cases to another
# from*Pk tag means changing these two lines to the matching pickup as well.
stage_pickups() {
    ln -s $SCRATCH_ROOT/DINO_1deg_outputs/runs/forward/spinup_200yr_visc2x/DINO_1deg_frd_200yr_from_rest_visc2x_run30983/pickup.0003162240.data pickup.0003162240.data
    ln -s $SCRATCH_ROOT/DINO_1deg_outputs/runs/forward/spinup_200yr_visc2x/DINO_1deg_frd_200yr_from_rest_visc2x_run30983/pickup.0003162240.meta pickup.0003162240.meta
}

source "$SLURM_SUBMIT_DIR/../../../tools/lib/submit_body.sh"
