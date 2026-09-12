#!/bin/bash
# Submit the Tapenade ADJOINT built with the CHECKPOINTING PROFILER.
#                                  build_tapAdj_profile/mitgcmuv_tap_adj
#
# A diagnostic run: the adjoint is the plain one plus timing calls, so use it
# for the cost/benefit table it writes (tapenade_profile.NNNN.txt in the run
# directory), never for runtime comparisons. Defaults to 30 days, which is
# long enough for per-call-site time gains to clear the profiler's 1-second
# resolution while the binomial schedule stays cheap. Build and submit script
# are a pair, and the run token check below enforces it; see
# tools/tapenade_profiling/README.md.
#
# This file says WHAT to run; HOW is tools/lib/submit_body.sh, shared by every
# submit script. Run it from the setup directory through the wrapper:
#     ../../../tools/submit.sh scripts/submit_tapAdj_profile.sh

#SBATCH -J DINO_1deg_tapAdj_profile   # job name: names the log file only; the run directory is named from build_info.txt
#SBATCH -o logs/%x.%j.out                # %x = job name, %j = job ID; relative to the setup directory, where tools/submit.sh runs sbatch
# No -e: given only -o, sbatch sends both streams to that one file. The set -x
# trace below is stderr, so it lands there.
#SBATCH -N 1
#SBATCH -n 27
#SBATCH -t 24:00:00
#SBATCH --mail-user=tanvirshahriar@utexas.edu   # override: sbatch --mail-user=...
#SBATCH --mail-type=begin
#SBATCH --mail-type=end

set -e      # fail fast if anything is wrong
set -x      # trace every command (with expansions) into the log: the record of what was staged

# ========== WHAT THIS SCRIPT RUNS ==========

BUILD_DIR=build_tapAdj_profile
RUN_MODE=tapAdj
PARALLEL=mpi                                # -n above must match code_tap/SIZE.h (nPx=3, nPy=9 = 27 ranks)
EXPECT_RUN_TOKEN=tapAdj_ckpAll_profile   # refuse a build directory holding any other variant

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
#     IMPACTS_DURATION_DAYS=180 ../../../tools/submit.sh scripts/submit_tapAdj_profile.sh
#
duration_days="${IMPACTS_DURATION_DAYS:-30}"                # 30 days -> nTimeSteps
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
# run's state names that run, as the stability study's rows do with the REF_ReMax2 leg:
#     IMPACTS_TEST_CASE=stability_study/from180yrPk_viscRef_ReMax2_gmFwd \
#     IMPACTS_PICKUP_RUN_DIR=<run directory of the REF_ReMax2 leg, 31205> \
#         ../../../tools/submit.sh scripts/<this script>
stage_pickups() {
    link_pickup
}

# ========== PROFILE OUTPUT ==========

# adProfile.c wrote one cost/benefit table per MPI process (see the_model_main.F
# in tools/tapenade_profiling/mods_profile). Echo rank 0's into the job log so
# the headline numbers are visible without opening scratch; the full analysis
# is analyses/DINO_1deg/adjoint/tapenade_profiling/. Runs in the run directory
# after the model ends.
post_run() {
    set +x
    echo
    echo "Tapenade profile files: $run_dir/tapenade_profile.*.txt"
    grep -h 'Peak stack size\|Total push/pop traffic' output_tap_adj.txt | sort | uniq -c
    echo "--- rank 0 table (first 40 lines) ---"
    head -40 tapenade_profile.0000.txt
}

source "$SLURM_SUBMIT_DIR/../../../tools/lib/submit_body.sh"
