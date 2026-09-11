#!/bin/bash
# Submit the FORWARD model.        build_frd/mitgcmuv
#
# This file says WHAT to run -- the #SBATCH header, the committed defaults, the
# pickup -- and HOW is tools/lib/submit_body.sh, the body every submit script
# in every setup shares (variant resolution, build record check, staging,
# namelist patching, the run, timing). Run it from the setup directory through
# the wrapper, which adds the per-machine sbatch flags:
#     ../../../tools/submit.sh scripts/submit_frd.sh

#SBATCH -J DINO_1deg_frd          # job name: names the log file only; the run directory is named from build_info.txt
#SBATCH -o logs/%x.%j.out         # %x = job name, %j = job ID; relative to the setup directory, where tools/submit.sh runs sbatch
# No -e: given only -o, sbatch sends both streams to that one file. The set -x
# trace below is stderr, so it lands there. A separate .err was the only file
# with content and the .out was empty on every job that ever ran.
#SBATCH -N 1
#SBATCH -n 27
#SBATCH -t 240:00:00
#SBATCH --mail-user=tanvirshahriar@utexas.edu   # override: sbatch --mail-user=...
#SBATCH --mail-type=begin
#SBATCH --mail-type=end

set -e      # fail fast if anything is wrong
set -x      # trace every command (with expansions) into the log: the record of what was staged

# ========== WHAT THIS SCRIPT RUNS ==========

BUILD_DIR=build_frd
RUN_MODE=frd
PARALLEL=mpi                # -n above must match code/SIZE.h (nPx=3, nPy=9 = 27 ranks)
EXPECT_RUN_TOKEN=frd        # refuse a build directory holding anything else

# ========== TEST CASE ==========

# Set to "" for default (i.e., use input/data). IMPACTS_TEST_CASE overrides
# this per run. The `-` (not `:-`) is deliberate: IMPACTS_TEST_CASE= selects the
# live input/data, which `:-` would swallow.
test_cases="${IMPACTS_TEST_CASE-}"      # the live input*/data is the baseline (since 2026-09-09); a run of it is named from the namelist

# ========== TIME STEPPING PARAMETERS (IN DAYS) ==========

# These are patched into the STAGED namelist in the run directory; the tracked
# file under input/ is never modified. The values here are the committed
# defaults (the 10-year regression baseline); override per run on the command
# line, which leaves the working tree clean:
#
#     IMPACTS_DURATION_DAYS=73200 ../../../tools/submit.sh scripts/submit_frd.sh
#
duration_days="${IMPACTS_DURATION_DAYS:-3660}"           # 10 years at 366 d/yr -> nTimeSteps
monitorFreq_days="${IMPACTS_MONITOR_FREQ_DAYS:-30.5}"    # on average there is 30.5 days in a month

# Which of the *_days above get patched into the namelist (besides the
# duration), listed explicitly -- see the body for why not auto-detected.
TIME_PARAMS=(monitorFreq)

# ========== PICKUP ==========

# Year-2170 state of the 200-yr spin-up: the start of every kappa_v ensemble
# member's re-equilibration leg (variants/kappa_v_ensemble/data_M<n> bakes the
# matching nIter0=2986560). Runs in the staged run directory.
# IMPACTS_PICKUP_RUN_DIR / IMPACTS_PICKUP_ITER (since 2026-09-10, as in the adjoint
# scripts) override the run directory the pickup is taken from and its iteration,
# for a namelist whose nIter0 is another run's pickup (a crash-step restart, a
# member's own state); the defaults are the 2x spin-up and its year-170 pickup,
# exactly the two lines that were hard-coded here before. A from-rest namelist
# (nIter0=0) ignores the staged pickup.
stage_pickups() {
    local pk_dir="${IMPACTS_PICKUP_RUN_DIR:-$SCRATCH_ROOT/DINO_1deg_outputs/runs/forward/spinup_200yr_visc2x/DINO_1deg_frd_200yr_from_rest_visc2x_run30983}"
    local pk_it; pk_it=$(printf '%010d' "${IMPACTS_PICKUP_ITER:-2986560}")
    ln -s "$pk_dir/pickup.$pk_it.data" "pickup.$pk_it.data"
    ln -s "$pk_dir/pickup.$pk_it.meta" "pickup.$pk_it.meta"
}

source "$SLURM_SUBMIT_DIR/../../../tools/lib/submit_body.sh"
