# `kappa_v_ensemble_gmFwd/` — the κ_v ensemble and the 5-year adjoint under the current configuration

The vertical-diffusivity ensemble and the 5-year production adjoint rerun on 2026-09-13 with the setup
the 2026-09-12 cleanup left on `main`, with finite-difference checks of the adjoint gradients, and the
analysis of both for the neural-network surrogate (does κ_v have to be a surrogate input, and which
control gradients can be trusted as targets). Scripts, no notebook; products, figures and animations
go to scratch `analysis/kappa_v_ensemble_gmFwd/`.

**Status (2026-09-15): finished.** Every run completed and was filed, and `run_analysis.sh` (job 31413) produced the products, figures and animations. The runs and their products were moved back to `/scratch2` on 2026-09-15, where `job_map.tsv` is. The campaign's own spin-up, 31329 with its rerun last 61 days 31365, was deleted on 2026-09-16: every output file of both was byte-identical to the production spin-up 31203's first 170 years (`logs/deleted_run_records/spinup_170yr_viscRef_ReMax2__deletion_evidence.txt`). `campaign.py` names 31203 as the spin-up, `forward_state.py spinup` stops at year 170 so the recorded noise floor reproduces, and `job_map.tsv` keeps both rows as the record of what ran. The page is published at
https://claude.ai/artifact/XRXUEA839efXys3dNTn5KF (private until shared); rebuild it with `python3 build_page.py` and republish `page/`.

## Scripts, in the order they are used

| Script | What it does |
| --- | --- |
| `submit_campaign.sh` | Submits the campaign as one dependency chain with `SCRATCH_ROOT=/scratch/$USER` (or, with `CAMPAIGN_SPINUP_JOB`/`CAMPAIGN_SPINUP_DIR`, from an existing run holding the year-170 pickup): the 170-year spin-up, the eight 10-year legs, the reference and seven member 5-year adjoints, the finite-difference forward sweeps, and the job that writes the perturbed pickups; writes `job_map.tsv` |
| `watch_campaign.sh` | Reports job state changes and cancels each finite-difference sweep once the model has printed its cost (writes `fd_fc_lines.tsv`) |
| `campaign.py` | Run registry (from `job_map.tsv`), grid and MDS readers, the cost proxy, metrics and figure style |
| `forward_state.py` | `spinup`: the cost proxy's internal variability from the spin-up's monthly `dynDiag`; `legs`: indices of the eight legs and, once `/scratch2` is readable, the comparison with 31203 |
| `adjoint_products.py` | Run verification, RMS by lead, member-against-reference metrics, fields at selected leads, control gradients, cost and gradient tables, the decomposition of each member's ΔJ, the finite-difference table, and the structure of the ∂J/∂κ_v target |
| `make_figures.py` | Figures (PNG) and two animations (GIF), each frame normalised to itself to show the pattern |
| `make_films.py` | **Films of every `ADJ*` dump** (2026-09-16), each written twice: a multi-page PDF, one page per frame, which the beamer deck plays with the `animate` package, and a GIF. `profiles` measures the per-level RMS of every 3-D dump and draws `figures/adj_level_choice.png`; `reference` films all twelve dumps of run 31374; `members` films `ADJtheta` and `ADJdiffkr` for all eight members plus the two eight-panel films. One fixed colour scale per film, so growth and decay are visible — the opposite convention from `make_figures.py`'s GIFs. `--deck <dir>` drops the deck's copies into the slide deck's `figures/`. Writes `animations/films_index.tsv` |
| `build_explorer.py`, `explorer_template.html` | **The interactive depth-level explorer** (2026-09-16): one page with a variable selector, a depth slider over all 36 levels plus the column sum, a time slider that plays, and a choice of colour scaling, for the reference adjoint's twelve dumps and for `ADJtheta`/`ADJdiffkr` across all eight members. Build output in `explorer/` (ignored by git; the copy that matters is the one on scratch) |
| `file_runs.py` | Files the run directories under `runs/{forward,adjoint}/kappa_v_ensemble_gmFwd/` and relinks the member adjoints' pickups |
| `build_page.py`, `page_style.css`, `page_text.py`, `page_setup_text.py` | Assemble the published page (build output in `page/`, ignored by git) |
| `previous_campaigns_reference.json` | The earlier campaigns' numbers the comparisons use (the 2026-08 and 2026-09-10 ensembles, the 2026-09-11 GM test), copied from scratch before `/scratch2` failed |

The namelists are `input/variants/kappa_v_ensemble/` (legs), `input_tap/variants/kappa_v_ensemble/`
(member adjoints) and `input_tap/variants/fd_checks/` (finite-difference sweeps) in the DINO setup.

## Which depth level a film of a 3-D dump shows

A map has to pick a level, and until 2026-09-16 the films picked 300 m and 1400 m by hand. The rule
now comes from the cost's own geometry: **J is the transport in the upper 982 m** (the upper 25 of 36
levels, `code_tap/cost_atlantic_heat.F`'s `kmaxdepth`), so inside that band a perturbation changes
the transport directly and below it only by changing the circulation. Each film therefore shows the
level of largest time-mean horizontal RMS **inside** 0–982 m and the level of largest RMS **below**
it, read off the `profiles` cache per variable:

| Dump | inside 982 m | below |
| --- | --- | --- |
| `ADJtheta`, `ADJsalt` | 915 m | 1844 m |
| `ADJuvel`, `ADJvvel` | 915 m | 3727 m |
| `ADJwvel` | 15 m | 1059 m |
| `ADJdiffkr` | 15 m | 1220 m |

`figures/adj_level_choice.png` draws the profiles with the chosen levels marked — that figure *is*
the explanation, and the deck uses it. For `ADJtheta`, 915 m carries 3.5 times the RMS that 300 m
does. Every other level is in the explorer.

## Whether a dump decays or accumulates — measured, not assumed

`make_films.py`'s `kind_of` reads it off the RMS-against-lead curve, so a caption cannot contradict
its own data. Ratio of RMS at 5 yr lead to RMS at the end of the cost window:

- **running totals**, peaking at the far end of the window: `ADJdiffkr` ×381, `ADJempmr` ×351,
  `ADJqnet` ×221 — the three controls that act at every time step;
- **neither**: `ADJtauy` ×11 (peaks 0.3 yr back), `ADJqsw` ×1.0 (peaks 1.7 yr back). Both are
  forcings this configuration barely has — DINO's wind file is zonal only, so τ_y is identically
  zero in the trajectory — and both are what the finite-difference check rejects most heavily;
- **adjoint state**, decaying backwards: `ADJtheta` ×0.18, `ADJsalt` ×0.18, `ADJwvel` ×0.056,
  `ADJetan` ×0.042, `ADJtaux` ×0.025, `ADJvvel` ×0.022, `ADJuvel` ×0.019.

The films with a running total are embedded in the deck with `poster=last`, because their page 1
(lead 0) is identically zero.

## Running the films and the explorer

```bash
PY=~/tools_and_software/miniforge3/envs/py38/bin/python3
DECK=~/Proj_ImPACTS/impacts-notes/references/dino_sensitivity_vs_mixing/slides/figures
$PY make_films.py profiles                       # -> cache/level_rms_profiles.npz + the level figure
$PY make_films.py reference members --deck $DECK  # 30 films, ~35 min; the deck's copies land in $DECK
$PY build_explorer.py                            # -> analysis/<campaign>/explorer/ (32 MB)
```

The explorer needs a server even locally — a browser refuses to read the pixels back out of a canvas
drawn from a `file://` image — so `explorer/serve.sh` starts one on port 8765. It is also published
at <https://claude.ai/artifact/M14dASutpLo9EohDruuwwL>, which is the link the slide deck carries.
