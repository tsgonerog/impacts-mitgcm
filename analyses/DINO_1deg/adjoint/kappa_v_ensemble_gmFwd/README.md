# `kappa_v_ensemble_gmFwd/` — the κ_v ensemble and the 5-year adjoint under the current configuration

The vertical-diffusivity ensemble and the 5-year production adjoint rerun on 2026-09-13 with the setup
the 2026-09-12 cleanup left on `main`, with finite-difference checks of the adjoint gradients, and the
analysis of both for the neural-network surrogate (does κ_v have to be a surrogate input, and which
control gradients can be trusted as targets). Scripts, no notebook; products, figures and animations
go to scratch `analysis/kappa_v_ensemble_gmFwd/`.

**Status (2026-09-13): the runs are in progress.** `/scratch2`, which holds the production spin-up
31203, failed on 2026-09-12 at 18:45 and took a first submission from 31203 with it; the campaign
was resubmitted on `/scratch` from a new spin-up (31329) and runs until about 2026-09-15.

## Scripts, in the order they are used

| Script | What it does |
| --- | --- |
| `submit_campaign.sh` | Submits the campaign as one dependency chain with `SCRATCH_ROOT=/scratch/$USER`: the 170-year spin-up, the eight 10-year legs, the reference and seven member 5-year adjoints, the finite-difference forward sweeps, and the job that writes the perturbed pickups; writes `job_map.tsv` |
| `watch_campaign.sh` | Reports job state changes and cancels each finite-difference sweep once the model has printed its cost (writes `fd_fc_lines.tsv`) |
| `campaign.py` | Run registry (from `job_map.tsv`), grid and MDS readers, the cost proxy, metrics and figure style |
| `forward_state.py` | `spinup`: the cost proxy's internal variability from the spin-up's monthly `dynDiag`; `legs`: indices of the eight legs and, once `/scratch2` is readable, the comparison with 31203 |
| `adjoint_products.py` | Run verification, RMS by lead, member-against-reference metrics, fields at selected leads, control gradients, cost and gradient tables, the decomposition of each member's ΔJ, the finite-difference table, and the structure of the ∂J/∂κ_v target |
| `make_figures.py` | Figures (PNG) and animations (GIF) |
| `file_runs.py` | Files the run directories under `runs/{forward,adjoint}/kappa_v_ensemble_gmFwd/` and relinks the member adjoints' pickups |
| `build_page.py`, `page_style.css`, `page_setup_text.py` | Assemble the published page (build output in `page/`, ignored by git) |
| `previous_campaigns_reference.json` | The earlier campaigns' numbers the comparisons use (the 2026-08 and 2026-09-10 ensembles, the 2026-09-11 GM test), copied from scratch before `/scratch2` failed |

The namelists are `input/variants/kappa_v_ensemble/` (legs), `input_tap/variants/kappa_v_ensemble/`
(member adjoints) and `input_tap/variants/fd_checks/` (finite-difference sweeps) in the DINO setup.
