#!/bin/bash
# Submit the Tapenade ADJOINT with PROFILE-GUIDED -nocheckpoint tuning.
#                                  build_tapAdj_nocheckpoint/mitgcmuv_tap_adj
#
# THE DEFAULT adjoint submit script from 2026-09-02 to 2026-09-10 (the symlink
# ./scripts/submit_tapAdj.sh now points at submit_tapAdj_approxAdv.sh). With
# the live input_tap/data.autodiff this pair silently runs the EXACT adjoint of
# the flux-limited scheme 33 -- the useApproxAdvectionInAdMode switch is inert
# in split mode -- which blows up over long windows; use it with a scheme-30
# namelist or for a deliberate exact-adjoint control. Identical to submit_tapAdj_ckpAll.sh except
# for the executable it runs: the nocheckpoint build recomputes less and
# stores more inside each time step (see build_tapAdj_nocheckpoint.sh). Build
# and submit script are a pair, and the run token check below enforces it.
#
# This file says WHAT to run; HOW is tools/lib/submit_body.sh, shared by every
# submit script. Run it from the setup directory through the wrapper:
#     ../../../tools/submit.sh scripts/submit_tapAdj.sh

#SBATCH -J DINO_1deg_tapAdj_nocheckpoint   # job name: names the log file only; the run directory is named from build_info.txt
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

BUILD_DIR=build_tapAdj_nocheckpoint
RUN_MODE=tapAdj
PARALLEL=mpi                              # -n above must match code_tap/SIZE.h (nPx=3, nPy=9 = 27 ranks)
EXPECT_RUN_TOKEN=tapAdj_nocheckpoint      # refuse a build directory holding any other variant

# ========== TEST CASE ==========

# Set to "" for default (i.e., use input_tap/data). IMPACTS_TEST_CASE overrides
# this per run. The `-` (not `:-`) is deliberate: IMPACTS_TEST_CASE= selects the
# live input_tap/data, which `:-` would swallow.
test_cases="${IMPACTS_TEST_CASE-}"      # the live input*/data is the baseline (since 2026-09-09); a run of it is named from the namelist

# ========== TIME STEPPING PARAMETERS (IN DAYS) ==========

# These are patched into the STAGED namelist in the run directory; the tracked
# file under input_tap/ is never modified. The values here are the committed
# defaults; override per run on the command line, which leaves the tree clean:
#
#     IMPACTS_DURATION_DAYS=3660 ../../../tools/submit.sh scripts/submit_tapAdj.sh
#
duration_days="${IMPACTS_DURATION_DAYS:-1830}"              # 5 years at 366 d/yr -> nTimeSteps
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
# IMPACTS_PICKUP_RUN_DIR / IMPACTS_PICKUP_ITER (since 2026-09-09) override the run
# directory the pickup is taken from and its iteration, for a namelist whose
# nIter0 is another run's pickup (a kappa_v_ensemble member's own, or a
# mid-window restart of an adjoint run); the defaults are the spin-up and its
# year-180 pickup, exactly the two lines that were hard-coded here before.
stage_pickups() {
    local pk_dir="${IMPACTS_PICKUP_RUN_DIR:-$SCRATCH_ROOT/DINO_1deg_outputs/runs/forward/spinup_200yr_visc2x/DINO_1deg_frd_200yr_from_rest_visc2x_run30983}"
    local pk_it; pk_it=$(printf '%010d' "${IMPACTS_PICKUP_ITER:-3162240}")
    ln -s "$pk_dir/pickup.$pk_it.data" "pickup.$pk_it.data"
    ln -s "$pk_dir/pickup.$pk_it.meta" "pickup.$pk_it.meta"
}

source "$SLURM_SUBMIT_DIR/../../../tools/lib/submit_body.sh"
