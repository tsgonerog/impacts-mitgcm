#!/usr/bin/env bash
# The analysis of the campaign once every job has left the queue: file the runs, compute the products, draw the
# figures and animations, and assemble the page. Log: analysis/kappa_v_ensemble_gmFwd/run_analysis.log.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
A=/scratch/$USER/DINO_1deg_outputs/analysis/kappa_v_ensemble_gmFwd
exec > >(tee -a "$A/run_analysis.log") 2>&1
echo "=== $(date) run_analysis start"
python3 file_runs.py --apply
python3 adjoint_products.py verify timeseries members fields tables fd structure
python3 make_figures.py all
python3 build_page.py
echo "=== $(date) run_analysis done"
