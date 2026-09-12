# analyses/

Jupyter notebooks that read MITgcm run output from cluster scratch
(`/scratch2/<user>/...`) and produce the diagnostics and figures for this
project. Nothing here reads from the repository itself — the model output lives
outside git.

**Names are descriptive, not numbered** (since 2026-09-03). A notebook is named
for what it shows and, where it matters, the configuration it shows it for;
directories are named for the part of the workflow they belong to. Reading order
is stated in this file and, for the multi-notebook suites, in that suite's own
`README.md` — it is not encoded in the file names, because a numbered name goes
stale the moment anything is inserted, removed or reordered.

## Layout

```
analyses/
├── DINO_1deg/                        primary configuration (51 x 198 x 36)
│   ├── grid_and_cost_sections.ipynb      locates the cost-function section indices
│   ├── first_look_at_output.ipynb        entry point for reading a DINO run
│   ├── forward/
│   │   ├── viscosity_binaries_construction.ipynb   how dino_viscAhD*.bin is built
│   │   ├── spinup_200yr_from_rest_visc2x.ipynb     the 200-year spin-up
│   │   ├── spinup_200yr_from_rest_viscRef_ReMax2.ipynb  the 200-year spin-up under the 2026-09-10 production configuration, against the 2× one
│   │   └── moc_amoc_animation_200yr_visc2x.ipynb   MOC + AMOC frames from it
│   └── adjoint/
│       ├── sensitivity_5yr_from180yrPk_visc2x.ipynb          one 5-year adjoint
│       ├── sensitivity_180d_vs_5yr_from180yrPk_visc2x.ipynb  matched-lead comparison
│       ├── kappa_v_ensemble/            the κ_v perturbation ensemble (7 notebooks)
│       ├── tapenade_profiling/          checkpoint profile + -nocheckpoint validation
│       └── scidac_poster_aug2026/       the SciDAC PI meeting poster
├── SOMA_1deg/                        secondary configuration (62 x 62 x 31)
│   └── adjoint_sensitivity_control_set.ipynb
├── barotropic_gyre/                  the tutorial gyre with a passive temperature (62 x 62 x 1)
│   └── temperature_sensitivity_6months.ipynb   daily ADJtheta snapshots, figures and the animation
├── reference_notebooks/              collaborator material the above derives from
│   ├── dinocean_package_usage_from_matt.ipynb
│   ├── dino_output_walkthrough_from_matt.ipynb
│   └── moc_amoc_animation_reference.ipynb
└── tools/
    ├── install_git_filters.sh
    └── strip_animation_outputs.py    keeps notebooks under GitHub's size limit
```

Three directories carry their own `README.md` — `adjoint/kappa_v_ensemble/`,
`adjoint/tapenade_profiling/` and `adjoint/scidac_poster_aug2026/`. Read those
for the run tables and the reading order inside each.

## Scratch layout

Each setup has one output tree, split into what a thing *is* rather than which
job produced it:

```
/scratch2/<user>/DINO_1deg_outputs/
├── runs/            model output — one directory per job, grouped by campaign
│   ├── forward/
│   │   ├── spinup_200yr_visc2x/                the 2× 200-year spin-up (30983)
│   │   ├── spinup_200yr_viscRef_ReMax2/        the production configuration's spin-up (31203)
│   │   ├── kappa_v_ensemble/                   the 2026-08 κ_v legs (30996–31002)
│   │   ├── kappa_v_ensemble_ReMax2_approxAdv/  the 2026-09-10 κ_v legs (31205–31219)
│   │   ├── stability_study/                    viscosity, advection-scheme and vertical-advection restarts
│   │   └── toolchain_validation/               forward bitwise checks (31100, 31139, 31142)
│   └── adjoint/
│       ├── kappa_v_ensemble/                   2026-08 reference + M1–M7, 5 yr (31039–31046)
│       ├── kappa_v_ensemble_ReMax2_approxAdv/  2026-09-10 adjoints (31206–31220) and the κ_v FD sweeps
│       ├── stability_study/                    30-d and 183-d stability tests, the GM/Redi tests
│       ├── checkpointing_study/                ckpAll / -nocheckpoint / -profile (31052–31054, 31056)
│       ├── adjViscBoost/                       boosted run and its plain control (31025, 31026)
│       ├── toolchain_validation/               build, hook and script checks; 31259, the current setup's smoke test
│       ├── gradient_check/                     grdchk runs (31037, 31172, 31177–31179)
│       └── sensitivity/                        the 2× science runs (28486, 31028)
├── analysis/        multi-run analysis products, one directory per campaign:
│                    kappa_v_ensemble/, kappa_v_ensemble_ReMax2_approxAdv/,
│                    spinup_200yr_viscRef_ReMax2/, stability_study/, gm_in_adjoint/
├── executables/     adjoint binaries kept for provenance, named for their commit
└── logs/            build logs, and validation_reports/ for reruns deleted as duplicates

/scratch2/<user>/SOMA_1deg_outputs/
├── runs/{forward,adjoint}/          five validation runs, no campaign level yet
└── executables/
```

**The rules that make this scale.**

- A **run directory** keeps the name the submit script gave it,
  `<setup>_<mode>[_<run_token>]_<duration>[_<tag>]_run<jobid>` — machine-made,
  self-describing, and never edited by hand. The job ID is the durable key.
  For DINO adjoints `<run_token>` is `tapAdj_<ckp>[_<variant>]` and comes from
  the build's `build_info.txt`, so a run directory cannot claim a build it did
  not get.
- A **campaign** is the directory it sits in. Submit scripts write into
  `runs/forward/` or `runs/adjoint/` directly, so a new run lands unfiled at
  that level; move it into a campaign when it becomes part of one, or add a
  campaign directory if it starts a new line of work. SOMA has no campaign
  level yet — add one when it has more than a handful of runs.
- **Single-run output stays with its run.** A notebook that reads one run
  writes its `figures/` and `animations/` inside that run directory, so
  deleting a run takes its figures with it and nothing is orphaned.
- **Multi-run output goes to `analysis/<campaign>/`**, which is why the κ_v
  suite writes there rather than into any one of its nine runs.
- `executables/` and `logs/` hold things that are neither, and are named for
  what they are rather than for a job.

Durations are quoted in years where the run tag used days: DINO runs on a
366-day year at `dT=1800`, so `73200d` is 200 years, `1830d` is 5 years, and
`366d` is 1 year.

**This layout dates from 2026-09-03**, and replaced two earlier ones the same
day: four flat campaign directories (`DINO_1deg_{frd,tapAdj}_runs/`,
`SOMA_1deg_{frd,tapAdj}_runs/`, `v4_soma_tapAdj_runs/`) with `runs_prod/`,
`runs_exploratory/` and `runs_from_*_pickup/` inside them, then a brief
`<setup>_outputs/{frd,tapAdj}/`. Every path in this tree was rewritten with each
move. Notebook **outputs** were not rewritten — a recorded output showing an old
path is the honest record of the run that produced it, and where a run was
renamed rather than replaced (28463 → 30983) the data behind it is
byte-identical.

## Configuration tokens in file names

DINO notebook names end in the viscosity setting the run used, because that is
the axis most of these experiments vary. The reference field is
`dino_viscAhD.bin`, built as `dxC * 0.27 / 2` by
`DINO_1deg/forward/viscosity_binaries_construction.ipynb`; the `_2p00` file is
that field doubled. That is DINO's own law, A_h = ½·U_v·Δx with `rn_Uv = 0.27`
(NEMO `nn_ahm_ijk_t = 20`), which MITgcm has no parameter for, so it stays a
`PARM05` file; `DINO_1deg/scripts/gen_viscAhD.py` regenerates every
`dino_viscAhD*.bin` byte for byte from the grid file (2026-09-09).

| Token | Meaning |
| --- | --- |
| `visc2x` | `viscAhDfile` = `viscAhZfile` = `dino_viscAhD_2p00.bin` — both components at **2× reference**, through `PARM05` |
| `viscD2x_Zref` | `viscAhDfile` at 2× but `viscAhZfile` left at the reference field — a **mixed** setting, not the same experiment as `visc2x` |
| `viscRef` | both files at the unscaled reference |
| `ReMax2` | `viscAhReMax=2.` on top, the grid-Reynolds floor; with `viscRef` this is the production viscosity since 2026-09-09 |
| `adv30` | `tempAdvScheme=saltAdvScheme=30`, the unlimited DST3, whose adjoint does not blow up; production in both sweeps from 2026-09-09 to 2026-09-10. No token means scheme 33, the flux-limited DST3 of the forward model since 2026-09-10 |
| `viscGrid<v>` | scalar `viscAhGrid` in `PARM01` instead, `PARM05` files commented out; `viscGrid1p8e-2` is `viscAhGrid=1.8E-2` |
| `adjVisc` | adjoint-mode viscosity inflation: `viscFacInAd = 10.` against `viscFacInFw = 1.`, from `data.autodiff_adjointViscosity`. Needs the matching build *and* submit script |
| `ckpAll` / `nocheckpoint` | which Tapenade checkpointing the adjoint was built with; `nocheckpoint` is bitwise identical to `ckpAll` except under an adjoint-mode switch (`adjVisc`, `approxAdv`, GM in the forward sweep only), and was the DINO default from 2026-09-02 to 2026-09-10 |
| `approxAdv` | the `ckpAll` build with `code_tap/variants/approxAdvection/`: scheme 33 in the forward sweep, scheme 30 in the adjoint sweep through `useApproxAdvectionInAdMode`; the DINO default adjoint since 2026-09-10 |
| `gmFwd` | GM/Redi on in the adjoint's forward sweep and off in its adjoint sweep (`useGMRedi=.TRUE.`, `useGMRediInAdMode=.FALSE.`); the live `input_tap/` namelist since 2026-09-11, in the `approxAdv` or `ckpAll` build only |

Reading `p` as the decimal point keeps the tokens shell-safe: `1p135e-2` is
`1.135E-2`. Every notebook repeats its setting in full in a banner directly
under the title, with the run number, so nothing depends on decoding the name.

The distinction `visc2x` vs `viscD2x_Zref` is not cosmetic. The 200-year
spin-up first ran as `viscD2x_Zref` and **crashed at 126.3 years** (run 19369);
raising `viscAhZ` to 2× as well is what produced the run that completed
(run 30983). Both that crash and the `viscGrid1p8e-2` one at 13 years (28452)
are recorded in `forward/spinup_200yr_from_rest_visc2x.ipynb`; the runs and the
notebooks that read them are gone.

## DINO_1deg

`grid_and_cost_sections.ipynb` is the one other parts of the repo point at — it
is how `isecbeg/isecend/jsec` in `code_tap/cost_atlantic_heat.F` were chosen,
and both `README.md` and `CLAUDE.md` cite it by name. It reads grid only, from
the 30-day adjoint 31022.

`stability_study_viscosity_restarts_from170yrPk.ipynb` (2026-09-09) is the
record of why the reference DINO viscosity is unstable here and what else
stabilises it: 2-yr and 10-yr forward restarts of the 2× spin-up's year-170
pickup under `input/variants/stability_study/` (31143–31151, 31160, 31161,
31164), 30-d adjoints from the 180-yr pickup under
`input_tap/variants/stability_study/` (31152–31159, 31163) and the 183-d
restarts of kappa member M7's blown 5-yr adjoint (31166–31168 against 31046).
Figures go to `analysis/stability_study/figures/`.

`first_look_at_output.ipynb` is the entry point for reading any DINO run:
`dynDiag` through `xmitgcm`, nothing configuration-specific. It reads the
200-year spin-up 30983.

### forward/

| Notebook | Run | What it shows |
| --- | --- | --- |
| `viscosity_binaries_construction.ipynb` | 30983 | builds and verifies `dino_viscAhD.bin` against `dxC * 0.27 / 2` (exact: `max\|diff\| = 0`), and scales it to the `_2p50`/`_3p00`/`_5p00` variants. Also carries the retired `viscAhGrid` comparison results |
| `spinup_200yr_from_rest_visc2x.ipynb` | 30983 | the 200-year spin-up that completed: MOC in depth and density space, barotropic streamfunction, AMOC timeseries. Writes everything into `figures/` |
| `spinup_200yr_from_rest_viscRef_ReMax2.ipynb` | 31203 vs 30983, with 31205 and 31256 | the 200-year spin-up from rest under the 2026-09-10 production configuration (reference viscosity + `viscAhReMax=2.`, scheme 33 with explicit vertical advection, GM on), completed 2026-09-11: `%MON` statistics over 200 yr, the overturning history (AMOC at 26/41/55° N, deep, tropical and Deacon cells) against the 2× spin-up, decade-mean MOC for years 170–180 and 190–200, zonal-mean T/S and MLD for years 190–200, and the year-180 state against the reference kappa leg's (the state the ensemble and 31206 used: 0.40 K rms apart, the 2× state's thick tropical thermocline inherited). Its last cell is the forward reproducibility check, 31256 against the first 10 years. Figures to `analysis/spinup_200yr_viscRef_ReMax2/figures/` |
| `moc_amoc_animation_200yr_visc2x.ipynb` | 30983 | renders the MOC + AMOC-timeseries frames into `moc_anim/` and `moc_anim_jpg_std2/` |
| `diffkr_as_parameter_validation_from170yrPk_visc2x.ipynb` | 31142 vs 30983 (and 31139 vs 31100, 31140 vs 31137, 31141 vs 31138) | the 2026-09-09 review of file-based mixing inputs: `diffKrT`/`diffKrS` in place of `diffKrFile` — 1 yr restarted from the spin-up's year 170 against the spin-up's own year 171 (dynDiag bitwise, MOC and 26°N AMOC overlaid), the 30-day forward and adjoint bitwise pairs, why no `viscAhGrid` reproduces the viscosity file (∝ cos²φ against cos φ), and what the stale `outAd*` values changed in the adjoint-viscosity boost. Writes into 31142's `figures/` |
| `advection_scheme_30_vs_33_from170yrPk.ipynb` | 31174 vs 31160 (2 yr), 31175 vs 31164 (10 yr) | the 2026-09-10 scheme question: one-setting twins from the year-170 pickup at reference viscosity + `viscAhReMax=2.` with `tempAdvScheme=saltAdvScheme` 30 against 33 — depth-space MOC and per-latitude cell metrics, tracer excursions outside the limited run's range, `MXLDEPTH` statistics, zonal-mean T/S/ρ/w differences. Finds the mid-latitude cells no deeper (weaker by 1.1–1.6 Sv after 10 yr), the equatorial pair stronger and deeper under 30, negligible over/undershoots. Figures to `analysis/stability_study/figures/`; the adjoint side is in the setup README's "Scheme 30 or scheme 33" |

### adjoint/

`kappa_v_ensemble_ReMax2_approxAdv/` (2026-09-10) is the vertical-diffusivity
ensemble rerun under the production configuration of that day (scheme 33
forward with explicit vertical advection, approximate adjoint, reference
viscosity + `viscAhReMax=2.`): runs 31205–31220, its own README gives the
reading order. `kappa_v_ensemble/` stays the record of the 2026-08 campaign.

All read `/scratch2/<user>/DINO_1deg_outputs/runs/adjoint/`.

| Notebook | Run | Start (`nIter0`) | Viscosity / mods |
| --- | --- | --- | --- |
| `sensitivity_5yr_from180yrPk_visc2x.ipynb` | 28486 | 180-year pickup (3162240) | `viscAhD` = `viscAhZ` = 2× reference. Also carries the results of the three retired companion 5-year adjoints |
| `sensitivity_180d_vs_5yr_from180yrPk_visc2x.ipynb` | 31028 vs 31039 | 180-year pickup (3162240) | `visc2x`, Tapenade-native-hook builds; matched-lead comparison against the 5-yr reference 31039 (the 2026-09-01 seam-clean rerun of 30995; seam mask retained for metric continuity). Figures/animations go to 31028's run directory |

Settings in this table were read back from each run's own staged `data`
namelist, not from the run-directory tag.

`kappa_v_ensemble/` is a seven-notebook suite (2026-08-30; re-executed
2026-09-01 on the hook-build adjoint rerun) analysing the vertical-diffusivity
perturbation ensemble of the neural-network surrogate proposal,
Part I: the reference adjoint 31039 (fc/adxx bit-identical to 30995 and 28486;
seam-clean `ADJ*` + new `ADJetan`) against members M1–M7 (runs 31040–31046,
reruns of 31003–31009, κ_v scaled 0.25×–32×), plus the internal-variability
noise floor reconstructed from spin-up 30983's 2,402 pickups. It has its own
`README.md` (run table, reading order, conventions); shared code lives in
`ensemble_common.py`, and `build_cache.py` / `build_jproxy.py` must be run once
before re-executing the notebooks — they write the intermediates the notebooks
read. Unlike the single-run notebooks, this suite spans nine runs, so everything
it generates goes to the sibling scratch directory
`/scratch2/<user>/DINO_1deg_outputs/analysis/kappa_v_ensemble/`
(`cache/`, `figures/`, `animations/`, `stats/`) rather than into any one run
directory. All eight adjoints ran a third time on 2026-09-02 with the
`-nocheckpoint` build (31060–31067): bitwise identical to 31039–31046 in `fc`,
`adxx_*` and `ADJ*`, so the suite still reads the 2026-09-01 set. Those
`-nocheckpoint` reruns were themselves deleted in the 2026-09-03 consolidation
once the comparison reports had recorded the result.

`tapenade_profiling/` (2026-09-01) is scripts and records rather than a
notebook: the Tapenade checkpointing profile of the adjoint (run 31053,
`-profile` build) parsed into a per-routine ranking, the 33-routine
`-nocheckpoint` list derived from it, and the validation of that build against
the plain one — 30 days on the same node, run 31054 vs 31052: `fc` identical,
all 32 `adxx_*` and 73 `ADJ*` files bitwise identical, 8:47 vs 13:13 wall time
(1.5×); at 5 years (run 31055 vs 31039) again bitwise identical across fc,
32 `adxx_*` and 4 393 `ADJ*` files, 9:36 vs 14:06 wall time (1.47×); and on
2026-09-02/03 across the whole κ_v ensemble (31060–31067 vs 31039–31046), all
eight 5-yr pairs bitwise identical, the four blow-ups included, 1.45–1.65× per
run and 37.8 h saved of 114.6 h. Its `README.md` has the run table; two of its
scripts (`parse_tapenade_profile.py`, `compare_adjoint_runs.py`) are general
enough to reuse on any pair of runs, and
`compare_ensemble_ckpAll_vs_nocheckpoint.py` drives the pairwise comparison over
the ensemble. Since 2026-09-02 that tuned build is the DINO default
(`build_tapAdj.sh` is a symlink to `build_tapAdj_nocheckpoint.sh`; the plain
build lives on as `build_tapAdj_ckpAll.sh`), and the directory also records the
one negative result,
`compare_30d_adjViscBoost_run31025_vs_nocheckpoint_run31056.md`: under the
adjoint-mode viscosity boost the same list leaves `fc` identical but changes
every sensitivity field at order one, so that build stays
checkpoint-everything.

Several runs named in those comparison reports (31055, 31060–31067) were
deleted in the 2026-09-03 consolidation. The reports are the record; the
`ckpAll` half of every pair survives.

`gm_in_adjoint/` (2026-09-11) is scripts rather than notebooks: the test of
running GM/Redi in the adjoint's forward sweep only. `compare_gm_adjoints.py`
compares the `ADJ*` dumps and `adxx_*` gradients of runs against a reference by
lead, `forward_drift.py` compares two forward sweeps' monthly `dynDiag`,
`perturb_pickup.py` writes pickups with Theta perturbed in a box, and
`fd_summary.py` sets both adjoints (31206, 31237) against the finite
differences of both models. Its `README.md` has the run table; the runs are
filed under `runs/adjoint/stability_study/`, the outputs under
`analysis/gm_in_adjoint/`.

`scidac_poster_aug2026/` is the poster prepared for the SciDAC PI meeting in
August 2026 — `adj_field_animations.ipynb` animates the 3-D and 2-D `ADJ*`
fields of run 28486, `poster_panel_frames.ipynb` is the trimmed version that
writes the nine `poster_frames/*.png` panels of the 3 × 3 sensitivity grid. It
has its own `README.md`, including the seam caveat that applies to 28486's
dumps.

### Where the outputs go

**No figures or animations live in this repository.** Every notebook writes its
output into the scratch run directory it read, so a run directory is
self-contained and deleting a run takes its figures with it:

```
<run>/
├── figures/       PNGs, and poster_frames/ for the SciDAC panels
└── animations/    gif + html exports, and the frame directories
```

Notebooks derive those paths from the `run_dir` they already define
(`FIG_DIR = run_dir / "figures"`, `ANIM_DIR = os.path.join(run_dir, "animations")`),
so the output follows the run automatically if it is ever moved again. Nothing
needs editing in two places.

The one deliberate exception is `kappa_v_ensemble/`, which reads nine runs and
therefore writes everything to the sibling directory
`/scratch2/<user>/DINO_1deg_outputs/analysis/kappa_v_ensemble/` instead
of into any one run (details in that suite's own `README.md`). Its two
publication figures are additionally kept with the project notes, as LaTeX
sources for the `kappa_ensemble_results` brief. Since the 2026-09-04 split
those live in a separate repository, so **no project-authored image is tracked
here** — the only images in this repository are the vendored MITgcm
documentation figures under `MITgcm_c69m/MITgcm/doc/`.

Current locations:

| Output | Lives in |
| --- | --- |
| 200-year spin-up figures, `moc.gif`, `moc_anim*/` | `DINO_1deg_outputs/runs/forward/spinup_200yr_visc2x/DINO_1deg_frd_200yr_from_rest_visc2x_run30983/` |
| `ADJ*` gif/html, `adj_*_z14/`, `poster_frames/` | `DINO_1deg_outputs/runs/adjoint/sensitivity/DINO_1deg_tapAdj_ckpAll_5yr_from180yrPk_visc2x_run28486/` |

The `.gitignore` rules for `analyses/**/*.{png,jpg,gif,html}` are only a safety
net against a cell being re-run with a repo-local output path.

## SOMA_1deg

| Notebook | Runs | What it shows |
| --- | --- | --- |
| `adjoint_sensitivity_control_set.ipynb` | `pd_v4StP_srl_*` 30/180/360 d (9716, 9717, 9719) | the full control set — temperature, salinity and vertical diffusivity, plus velocities, wind stress, and surface heat and freshwater fluxes |

KPP and GM/Redi are disabled and the cost section is at 40°N, so neither is
repeated in the file name.

**This notebook cannot be re-executed as written.** Its c69f-era `v4_soma` runs
were deleted on 2026-09-03; its outputs are the record. It also absorbed the
content of three retired siblings — the manual tile-stitch/halo utilities, the
sensitivity-sign reading notes, and the run-length study's run list — so it is
now the single SOMA analysis document.

The surviving c69m SOMA runs are the 5-day adjoints
`SOMA_1deg_tapAdj_5d_run31033` and `run31076` and the 30-day forward
`SOMA_1deg_frd_30d_run31034`. c69m SOMA is single-tile serial, so a notebook
repointed at them needs only `xmitgcm.open_mdsdataset` — the manual tile
machinery is not required.

## barotropic_gyre

| Notebook | Runs | What it shows |
| --- | --- | --- |
| `temperature_sensitivity_6months.ipynb` | `barotropic_gyre_tapAdj_ckpAll_180d_run31118` (adjoint, 180 d from the end of the 2-year spin-up `barotropic_gyre_frd_2yr_run31115`) | the sensitivity of the mean temperature over a 200 km box on the western boundary current at day 180 to the temperature field at every earlier day: `adxx_theta`, six of the 180 daily `ADJtheta` snapshots, the amplitude against time, and two animations in the run's `animations/` (the sensitivity from day 180 back to day 0, and the forward temperature). Two built-in checks: the sum of the sensitivity over the ocean is 1 at every day, and the day-0 snapshot equals `adxx_theta` |

Temperature is a passive tracer there (zero thermal expansion), so the
sensitivity is the adjoint of a linear advection-diffusion operator and does
not depend on the temperature field itself. Run 31117, the same adjoint with
the box in the north-eastern interior, is kept beside 31118 on scratch; its
sensitivity is diffusion-dominated because the flow there is a few millimetres
per second.

## Reading the output files

`adxx_*` and `xx_*` control files are **`float64`**; the `ADJ*` diagnostic dumps
follow `data.diagnostics` and are `float32`. Read the `.meta` beside a file rather
than assuming — guessing wrong silently reshapes the array into plausible-looking
garbage. `xmitgcm.open_mdsdataset` handles this for you; raw `np.fromfile` does not.

One run is kept for verification rather than science:

| Run | What it is |
| --- | --- |
| `DINO_1deg_tapAdj_ckpAll_30d_from180yrPk_visc2x_run31032` | 30-day adjoint, confirms `ADJ*`/`adxx*` output (incl. `ADJetan`) and sensitivity on the cost section. Successor of the 2026-08-18 original (30948): 31032 is the current-toolchain rerun of the same config, bitwise-validated back to it through the 31022 chain |

The forward reproducibility check that used to sit beside it — a 10-year run
bit-identical to the first 10 years of the spin-up — was run 30945, deleted in
the 2026-09-03 consolidation. The check is cheap to repeat: build, run 10 years
from rest with `from_rest_visc2x`, and diff against 30983.

## Retired analyses

Thirteen notebooks were moved to `~/trash/Proj_ImPACTS/analyses/` on 2026-09-03
because every run they read had been deleted. Their durable findings were
transferred into the notebooks that remain before the move — the retired
notebook is not the record any more, the receiving notebook is.

| Retired | Runs | Findings went to |
| --- | --- | --- |
| `02_forward/00_archive/` — two crashed 200-yr attempts | 19369, 28452 | `forward/spinup_200yr_from_rest_visc2x.ipynb` |
| `02_forward/01_viscosity_study/` — three `viscAhGrid` comparisons | 28402, 28447, 28448, 28451 | `forward/viscosity_binaries_construction.ipynb` |
| `03_adjoint/00_archive/serial_*` — five serial exploratory runs | 18222, 18232, 22038, 22039, 24020 | nothing unique; the runs were already gone before this cleanup |
| `03_adjoint/02_`, `03_`, `04_` — three 5-yr adjoints | 24493, 28461, 28453 | `adjoint/sensitivity_5yr_from180yrPk_visc2x.ipynb` |
| `SOMA_1deg/01_`, `02_`, `03_` | `v4soma_*`, `v4StP_srl_*`, `pd_v4StP_srl_*` | `SOMA_1deg/adjoint_sensitivity_control_set.ipynb` |

`~/trash/Proj_ImPACTS/analyses/README.md` lists them file by file, with the
path each had before the move.

## Notebook size discipline

`matplotlib`'s `anim.to_jshtml()` embeds *every frame of an animation as a
separate base64 PNG* in a single `text/html` output. Eight such animations were
enough to make one notebook 228 MB — past GitHub's hard 100 MB per-file limit,
which blocks the push outright.

That is handled automatically now, by a git **clean filter**. Outputs stay in
your working copy, so you can open a notebook and show it to someone; git
strips the oversized ones on the way into the index, so what gets committed and
pushed is small. Nothing has to be remembered before a push.

Filters live in `.git/config`, which is not tracked, so **each clone runs this
once**:

```bash
./analyses/tools/install_git_filters.sh                # default: >1 MB animations
./analyses/tools/install_git_filters.sh --all-outputs  # strip every output
./analyses/tools/install_git_filters.sh --uninstall
```

The default removes only animation payloads above 1 MB and leaves static figures
alone, so plots still render for anyone reading the repository on GitHub. Each
stripped output is replaced by a note saying what was removed and that re-running
the cell regenerates it. `--all-outputs` clears everything, which takes the
notebooks here from 29.6 MB to 1.4 MB but leaves no figures visible on GitHub.

Until the installer is run, `.gitattributes` is inert and notebooks commit as-is.

**One caveat.** The stored copy is the stripped one, so any git operation that
overwrites a notebook in the working tree — `checkout`, `stash`, `merge`,
`reset --hard` — replaces it with the stripped version, and whatever was
stripped is gone locally. Re-run the cell, or keep an export outside the repo:

```bash
jupyter nbconvert --to html --output-dir ~/nb_for_advisor <notebook>
```

The same script still works as a one-shot pass over files on disk, which is what
was used before the filter existed:

```bash
python3 analyses/tools/strip_animation_outputs.py            # whole tree
python3 analyses/tools/strip_animation_outputs.py --dry-run  # report only
```

That in-place mode rewrites the files themselves; the filter mode does not.

Before pushing, `./tools/pre_push_check.sh` at the repo root confirms the filter
is installed and that no figures or unresolved scratch paths have crept in. See
"Workflow: before you push" in the root `README.md`.

## What is deliberately not in git

Only code and notebooks. Model output, figures and animations all live on
cluster scratch. The notebooks are committed with their inline outputs, so the
plots still render on GitHub even though no image files are tracked.

Before committing a notebook containing animations, run
`python3 analyses/tools/strip_animation_outputs.py` — `anim.to_jshtml()` embeds
every frame as base64 and has produced single notebooks over GitHub's 100 MB
hard limit.
