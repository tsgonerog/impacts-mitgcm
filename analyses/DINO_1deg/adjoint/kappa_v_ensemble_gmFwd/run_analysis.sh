#!/usr/bin/env bash
# The analysis of the campaign once every job has left the queue: file the runs, compute the products, draw the
# figures and animations, and assemble the page. Log: analysis/<campaign>/run_analysis.log (CAMPAIGN_NAME selects
# the campaign, as for every script here; the 43 N rerun by default).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
A=${SCRATCH_ROOT:-/scratch2/$USER}/DINO_1deg_outputs/analysis/${CAMPAIGN_NAME:-kappa_v_ensemble_gmFwd_sec43N}
mkdir -p "$A"
exec > >(tee -a "$A/run_analysis.log") 2>&1
echo "=== $(date) run_analysis start"
python3 file_runs.py --apply
python3 adjoint_products.py verify timeseries members fields tables fd structure
python3 make_figures.py all
python3 build_page.py
echo "=== $(date) run_analysis done"
