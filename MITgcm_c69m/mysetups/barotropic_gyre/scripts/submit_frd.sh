#!/bin/bash
# Submit the FORWARD model: the gyre spin-up.        build_frd/mitgcmuv
#
# This file says WHAT to run -- the #SBATCH header and the committed defaults --
# and HOW is tools/lib/submit_body.sh. Run it from the setup directory through
# the wrapper, which adds the per-machine sbatch flags:
#     ../../../tools/submit.sh scripts/submit_frd.sh
#
# The committed default is the 2-year spin-up from rest whose final pickup
# (pickup.0000051840) starts the adjoint; submit_tapAdj.sh links it by job.

#SBATCH -J barotropic_gyre_frd    # job name: names the log file only; the run directory is named from build_info.txt
#SBATCH -o logs/%x.%j.out         # %x = job name, %j = job ID; relative to the setup directory, where tools/submit.sh runs sbatch
#SBATCH -N 1
#SBATCH -n 1
#SBATCH -t 04:00:00
#SBATCH --mail-user=tanvirshahriar@utexas.edu   # override: sbatch --mail-user=...
#SBATCH --mail-type=end

set -e      # fail fast if anything is wrong
set -x      # trace every command (with expansions) into the log: the record of what was staged

# ========== WHAT THIS SCRIPT RUNS ==========

BUILD_DIR=build_frd
RUN_MODE=frd
PARALLEL=serial             # a bare ./mitgcmuv: code/SIZE.h is one tile
EXPECT_RUN_TOKEN=frd        # refuse a build directory holding anything else

# ========== TEST CASE ==========

# "" = the live input/data. IMPACTS_TEST_CASE overrides per run; the `-` (not
# `:-`) is deliberate, so that IMPACTS_TEST_CASE= still selects the live file.
test_cases="${IMPACTS_TEST_CASE-}"

# ========== TIME STEPPING PARAMETERS (IN DAYS) ==========

# Patched into the STAGED namelist in the run directory; the tracked file is
# never modified. Override per run on the command line:
#     IMPACTS_DURATION_DAYS=360 ../../../tools/submit.sh scripts/submit_frd.sh
duration_days="${IMPACTS_DURATION_DAYS:-720}"            # 2 years at 360 d/yr -> nTimeSteps
monitorFreq_days="${IMPACTS_MONITOR_FREQ_DAYS:-10}"
dumpFreq_days="${IMPACTS_DUMP_FREQ_DAYS:-10}"

# Which of the *_days above get patched into the namelist (besides the
# duration), listed explicitly -- see the body for why not auto-detected.
TIME_PARAMS=(monitorFreq dumpFreq)

# No pickup: the spin-up starts from rest.

source "$SLURM_SUBMIT_DIR/../../../tools/lib/submit_body.sh"
