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
| `make_figures.py` | Figures (PNG) and two animations (GIF), each frame normalised to itself to show the pattern. `ref_ADJtheta_depth_lead_wide` (2026-09-16) draws the nine temperature-sensitivity maps of `ref_ADJtheta_depth_lead` in one row, grouped by lead, for the 16:9 deck |
| `make_films.py` | **Films of every `ADJ*` dump** (2026-09-16), each written twice: a multi-page PDF, one page per frame, which the beamer deck plays with the `animate` package, and a GIF. `profiles` measures the per-level RMS of every 3-D dump and draws `figures/adj_level_choice.png`; `reference` films all twelve dumps of run 31374; `members` films `ADJtheta` and `ADJdiffkr` for all eight members plus the two eight-panel films. One fixed colour scale per film, so growth and decay are visible — the opposite convention from `make_figures.py`'s GIFs. `--deck <dir>` drops the deck's copies into the slide deck's `figures/` — the six in `DECK_FILMS` and the two eight-panel films (all twelve reference films until 2026-09-16). Writes `animations/films_index.tsv` |
| `adjoint_waves.py` | **Adjoint Kelvin and Rossby waves** (2026-09-16), measured in `ADJtheta` at 915 m for all eight adjoints: `slices` caches the level at every dump (`cache/adjtheta_915m_<run>.npy`), `measure` writes arrival leads along the eastern wall, the equator and the western wall, the interior crossing speeds and, for comparison, the first-mode speed c₁ of each leg's stratification and the long Rossby speed βc₁²/f² (`stats/adjoint_waves.json`), `plot` draws `figures/adjoint_waves.png`. See below |
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

The deck embeds the films of two running totals (`ADJdiffkr`, `ADJqnet`) and the eight-member `ADJdiffkr`
film with `poster=last`: their page 1 is 30 days before the end of the window, where the total holds only
3–16 % of its five-year RMS. The temperature, salinity and eight-member temperature films keep
`poster=first`.

**Every film and the explorer run backwards in model time.** A dump `ADJxxx.<N>` is the adjoint at
*forward* iteration N, so the backward sweep writes the largest N first (in run 31374 `ADJtheta.0003249840`
is the oldest file and `ADJtheta.0003162240` the newest). `make_films.py` and `build_explorer.py` both
take `c.ITERS[::stride][::-1]`: page 1, or frame 0, is lead 0.08 yr and the last is lead 5 yr.
`make_figures.py`'s GIFs step `c.ITERS[::-4]` and `[::-6]` the same way, from lead 0.01 yr. The explorer
ran forward in time until 2026-09-16.

## The films read as adjoint waves

The adjoint runs backwards in time with the transpose of the forward operator, so each wave of the
forward model has an adjoint counterpart travelling the other way as the lead grows. `adjoint_waves.py`
checks that reading against the dumps (915 m, run 31374 unless stated; `stats/adjoint_waves.json`):

- **adjoint Kelvin waves.** From the section the sensitivity reaches the equator down the *eastern*
  wall in 30 days, the western end of the equator by day 65, and 45° N up the *western* wall by day 40
  — the reverse of forward Kelvin waves, which keep the coast on their right in the northern
  hemisphere. The front follows the first-mode speed of the leg's own stratification, c₁ = 1.95 m/s.
- **adjoint Rossby waves.** Crests leave the western wall and move *east*; at 25° N and 25° S they run
  parallel to the long Rossby speed βc₁²/f², 2.7–2.8 cm/s. The zonal-mean flow at 915 m is a few mm/s,
  so this is propagation, not advection. The simple long-wave speed does not follow the crests at every
  latitude — at 35° they are faster than it, at 20° slower — so the figure shows 25°, where it
  does.
- **across the ensemble** the waves speed up with κ_v: c₁ at the equator rises from 1.90 m/s (0.25×) to
  2.65 m/s (32×), the eastern-wall arrival at the equator falls from 35 to 15 days, the western end of
  the equator is reached in 40 days instead of 100, and the crossing at 30° N (lag of best correlation
  between 40.5° W and 20.5° W) rises from 2.1 to 3.5 cm/s against 1.8 to 3.1 cm/s from βc₁²/f².

Arrival leads use a 1 % threshold of the level's largest value and the 5-day dump interval, so they
are good to about 5 days; the crossing speed is noisy where the cost section's own imprint dominates
the Hovmöller (25° N) and at low latitude, and `adjoint_waves.json` gives its correlation for each.

## Running the films and the explorer

```bash
PY=~/tools_and_software/miniforge3/envs/py38/bin/python3
DECK=~/Proj_ImPACTS/impacts-notes/references/dino_sensitivity_vs_mixing/slides/figures
$PY make_films.py profiles                       # -> cache/level_rms_profiles.npz + the level figure
$PY make_films.py reference members --deck $DECK  # 30 films, ~35 min; the deck's six copies land in $DECK
$PY adjoint_waves.py                             # slices (~3 min), measure, plot
$PY build_explorer.py                            # -> analysis/<campaign>/explorer/ (32 MB)
```

The map is drawn on longitude and latitude by default, each grid row as tall as the latitude it spans
(1 wide by 2.74 tall); a **Grid cells** toggle draws every cell the same size instead, which on DINO's
isotropic grid is a Mercator map about three times too tall in the subpolar basin, kept for grid-scale
structure such as tile seams. The toggle is remembered per browser. A change to the page alone needs no
second pass over the dumps: `build_explorer.py --page-only` re-renders it around the existing payloads.

The explorer needs a server even locally — a browser refuses to read the pixels back out of a canvas
drawn from a `file://` image — so `explorer/serve.sh` starts one on port 8765. It is also published
at <https://claude.ai/artifact/M14dASutpLo9EohDruuwwL>, which is the link the slide deck carries.
