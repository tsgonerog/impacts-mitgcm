#!/bin/bash
# Submit the Tapenade ADJOINT: the 6-month temperature sensitivity.
#                                                   build_tapAdj/mitgcmuv_tap_adj
# This file says WHAT to run -- the #SBATCH header and the committed defaults --
# and HOW is tools/lib/submit_body.sh. Run it from the setup directory through
# the wrapper, which adds the per-machine sbatch flags:
#     ../../../tools/submit.sh scripts/submit_tapAdj.sh
#
# The committed default: 180 days from the end of the 2-year spin-up, the cost
# being the box-mean surface temperature at day 180 (code_tap/cost_test.F),
# with ADJ* dumps every day (the animation) and adxx_theta at the start.

#SBATCH -J barotropic_gyre_tapAdj # job name: names the log file only; the run directory is named from build_info.txt
#SBATCH -o logs/%x.%j.out         # %x = job name, %j = job ID; relative to the setup directory, where tools/submit.sh runs sbatch
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 12:00:00
#SBATCH --mail-user=tanvirshahriar@utexas.edu   # override: sbatch --mail-user=...
#SBATCH --mail-type=end

set -e      # fail fast if anything is wrong
set -x      # trace every command (with expansions) into the log: the record of what was staged

# ========== WHAT THIS SCRIPT RUNS ==========

BUILD_DIR=build_tapAdj
RUN_MODE=tapAdj
PARALLEL=serial                     # a bare ./mitgcmuv_tap_adj: code_tap/SIZE.h is one tile
EXPECT_RUN_TOKEN=tapAdj_ckpAll      # refuse a build directory holding any other variant

# ========== TEST CASE ==========

# "" = the live input_tap/data (nIter0 = 51840, the spin-up's end). The `-`
# (not `:-`) is deliberate, so that IMPACTS_TEST_CASE= still selects it.
test_cases="${IMPACTS_TEST_CASE-}"

# ========== TIME STEPPING PARAMETERS (IN DAYS) ==========

# Patched into the STAGED namelist in the run directory; the tracked file is
# never modified. Override per run on the command line:
#     IMPACTS_DURATION_DAYS=30 ../../../tools/submit.sh scripts/submit_tapAdj.sh
duration_days="${IMPACTS_DURATION_DAYS:-180}"            # 6 months -> nTimeSteps at 1200 s
monitorFreq_days="${IMPACTS_MONITOR_FREQ_DAYS:-1}"
adjMonitorFreq_days="${IMPACTS_ADJ_MONITOR_FREQ_DAYS:-1}"
adjDumpFreq_days="${IMPACTS_ADJ_DUMP_FREQ_DAYS:-1}"
dumpFreq_days="${IMPACTS_DUMP_FREQ_DAYS:-1}"

# Which of the *_days above get patched into the namelist (besides the
# duration), listed explicitly -- see the body for why not auto-detected.
TIME_PARAMS=(monitorFreq adjMonitorFreq adjDumpFreq dumpFreq)

# ========== PICKUP ==========

# nIter0 = 51840 is baked into input_tap/data; the matching pickup is the end
# of the 2-year spin-up, linked here by its run directory. Changing the start
# means changing both lines and nIter0 together.
SPINUP_RUN="$SCRATCH_ROOT/barotropic_gyre_outputs/runs/forward/barotropic_gyre_frd_2yr_run31115"
stage_pickups() {
    # tiled names: this setup writes per-tile files (one tile), not global ones
    ln -s "$SPINUP_RUN/pickup.0000051840.001.001.data" pickup.0000051840.001.001.data
    ln -s "$SPINUP_RUN/pickup.0000051840.001.001.meta" pickup.0000051840.001.001.meta
}

source "$SLURM_SUBMIT_DIR/../../../tools/lib/submit_body.sh"
