# tapenade_profiling — where the adjoint recomputes, and what `-nocheckpoint` bought

> **Runs named in these reports that no longer exist.** The 2026-09-03 scratch
> consolidation deleted 31055 and the `-nocheckpoint` ensemble reruns
> 31060–31067 — every one of them was bitwise identical to the `ckpAll` run it
> was compared against, so the reports below are the record and the duplicates
> were redundant. The `ckpAll` half of every pair survives under
> `/scratch2/<user>/DINO_1deg_outputs/runs/adjoint/`, as do 31052, 31053, 31054 and
> 31056. Re-running `compare_adjoint_runs.py` on a deleted pair is not possible;
> re-establishing the result means re-running the adjoint.

Scripts and records, no notebook. The question was: which of the routines the
Tapenade adjoint checkpoints inside a time step are worth switching to split
(`_FWD`/`_BWD`) mode, and does doing so change the sensitivities? The
mechanics (what `-profile` measures, what `-nocheckpoint` changes, why the
binomial time loop is untouched) are in `tools/tapenade_profiling/README.md`;
this directory holds the evidence.

## Runs

All 27-rank MPI, `/scratch2/<user>/DINO_1deg_outputs/runs/adjoint/`. The runs of
2026-09-01 to 2026-09-03 use `baseline/from180yrPk_visc2x` (the ensemble members:
`kappa_v_ensemble/M1`–`M7`); those of 2026-09-12 the live namelists, GM/Redi in
the forward sweep and scheme 30 in the adjoint sweep (see the last sections).
Run directories carry the build token since the 2026-09-02 rename:
`DINO_1deg_tapAdj_ckpAll_…` for the plain runs, `…_ckpAll_tapProfile_…` for
31053, `…_nocheckpoint_…` for 31054/31055. The `_nocheckpoint` pair was the
default DINO adjoint from 2026-09-02 to 2026-09-10.

| Run | Build | Length | Node | Wall time | Role |
| --- | --- | --- | --- | --- | --- |
| 31052 | `build_tapAdj_ckpAll` (plain; `build_tapAdj` until 2026-09-02) | 30 d | c2-1 | 0:13:13 | fresh plain reference; bitwise identical to 31032 (0:13:31) |
| 31053 | `build_tapAdj_profile` (`build_tapAdj_tapProfile` until 2026-09-05) | 30 d | c2-3 | 0:13:29 | the profile (`tapenade_profile.0000`–`.0026.txt`) |
| 31054 | `build_tapAdj_nocheckpoint` | 30 d | c2-1 | **0:08:47** | validation against 31052 |
| 31039 | `build_tapAdj_ckpAll` (plain; `build_tapAdj` until 2026-09-02) | 5 yr | — | 14:05:45 | production-length reference (2026-09-01) |
| 31055 | `build_tapAdj_nocheckpoint` | 5 yr | c2-1 | **9:35:58** | production-length validation against 31039 |
| 31060–31067 | `build_tapAdj_nocheckpoint` | 5 yr × 8 | c2-4, c3-1, c7-4, c8-1–c8-4, c9-1 | **9:30:47–9:44:50** | the κ_v ensemble (REF + M1–M7) rerun on 2026-09-02, validation against its 2026-09-01 `ckpAll` runs 31039–31046 (14:02:37–15:39:13) |
| 31025 | `build_tapAdj_adjVisc` (ckpAll + boost) | 30 d | — | 0:13:19 | boosted reference (from rest, live `input_tap/data`) |
| 31056 | `build_tapAdj_adjVisc` + the list (**rejected**) | 30 d | c2-1 | 0:08:48 | split mode under the boost is **not** equivalent: `fc` identical, every sensitivity field differs at order one — the list was removed from that build again |
| 31268 | `build_tapAdj_profile` | 31 d | — | 0:15:17 | the 2026-09-12 profile of the live namelists (`checkpointing_study/`) |
| 31269 | `build_tapAdj_approxAdv` (rebuilt 2026-09-12) | 30 d | c1-1 | 0:11:53 | reference under the switches: `stability_study/from180yrPk_viscRef_ReMax2_gmFwd`; every sensitivity file identical to 31234 of 2026-09-11 (0:12:44, c1-1) |
| 31276 | `build_tapAdj_nocheckpoint`, list of 2026-09-12 | 30 d | c1-1 | **0:08:24** | validation against 31269: EQUIVALENT |
| 31259 | `build_tapAdj_approxAdv` | 5 d | — | 0:02:11 | reference: the live namelist from the production spin-up's year-180 pickup (2026-09-11) |
| 31277 | `build_tapAdj_nocheckpoint`, list of 2026-09-12 | 5 d | — | 0:01:40 | validation against 31259: EQUIVALENT |
| 31278 | `build_tapAdj_hooksInTree`, the same list | 5 d | — | 0:01:41 | the in-tree hooks against 31277: EQUIVALENT |
| 31285 | `build_tapAdj_nocheckpoint`, rebuilt after the build consolidation of 2026-09-12 | 5 d | — | 0:01:23 | against 31277: every sensitivity file, `fc` and `%MON` identical |
| 31287 | `build_tapAdj_profile`, rebuilt the same way | 5 d | — | 0:02:03 | against the `ckpAll` run 31281: EQUIVALENT |
| 31284 | `build_tapAdj_hooksInTree`, rebuilt the same way | 5 d | — | 0:01:35 | against 31278: every sensitivity file, `fc` and `%MON` identical |

## Files

| File | What |
| --- | --- |
| `parse_tapenade_profile.py` | parses a `tapenade_profile.NNNN.txt`, aggregates the per-call-site cost/benefit table by callee, ranks by time gain; `--budget-mb` proposes a list under a peak-memory budget |
| `compare_adjoint_runs.py` | compares two run directories: `fc`, every `adxx_*` (float64) and every `ADJ*` dump (float32) with a true bitwise test plus max abs/relative differences, and the `run_timing.txt` speed-up |
| `tapenade_profile_run31053_rank0000.txt` | rank 0's raw table from run 31053 (the other 26 ranks agree to within 5 % on the total) |
| `profile_run31053_ranked.md` | the parsed, ranked table (116 callees) |
| `tapenade_profile_run31268_rank0000.txt` | rank 0's raw table from run 31268, the profile of 2026-09-12 (ranks 14–26 report about 20 % more, almost all of it in the halo exchange) |
| `profile_run31268_ranked.md` | its parsed, ranked table (118 callees) and the ≥ 1 s proposal the 2026-09-12 list started from |
| `compare_30d_run31052_vs_nocheckpoint_run31054.md` | the 30-day validation report |
| `compare_5yr_run31039_vs_nocheckpoint_run31055.md` | the 5-year validation report |
| `compare_ensemble_ckpAll_vs_nocheckpoint.py` | drives the same comparison over the eight κ_v-ensemble pairs (31039–31046 vs 31060–31067) plus two reference cross-checks; adds the forward/reverse sweep split from the `ADJtheta` write times, a blow-up reproduction check (non-finite counts, onset dump) and the verdict of `tools/compare_adj_runs.sh` |
| `compare_5yr_kappa_ensemble_ckpAll_vs_nocheckpoint.md` and the directory of the same name | the ensemble validation: summary table, one report per pair |
| `compare_30d_adjViscBoost_run31025_vs_nocheckpoint_run31056.md` | the **negative** result: the same script on the boosted pair, with a preamble giving the mechanism (joint-mode recomputation after the mode-switch hook vs split-mode tapes before it) |

## What the 2026-09-01 profile showed (run 31053, rank 0)

- Peak tape **923 MB per process** (27 processes → ~25 GB of a 64 GB node).
- 156 checkpoint locations, 116 distinct callees. Not checkpointing all of
  them would save **363 s of CPU per process out of an 809 s run — 45 %**.
- The gain is concentrated: the top 12 callees carry 308 s. Their split mode is
  memory-neutral or a memory *gain* in 9 of 12 cases:

| callee | gain [s] | Δ peak tape | why |
| --- | --- | --- | --- |
| `timestep` | 75 | −31.1 MB | called per level (36×/step); joint mode snapshots whole 3-D arrays each call |
| `forward_step` | 71 | 0 | the step body: its primal ran once more per step than necessary |
| `grad_sigma` | 37 | 0 | per level |
| `mom_vecinv` | 22 | −0.2 MB | per level |
| `calc_phi_hyd` | 21 | −8.6 MB | per level |
| `thermodynamics` | 18 | 0 | step-level |
| `do_oceanic_phys` | 17 | +28.9 MB | step-level |
| `integrate_for_w` | 13 | 0 | per level |
| `dynamics` | 12 | +9.3 MB | step-level |
| `salt_integrate` | 9 | 0 | step-level |
| `temp_integrate` | 8 | +1.9 MB | step-level |
| `do_fields_blocking_exchanges` | 5 | −1.1 MB | step-level |

- Everything that costs memory sums to ~54 MB per process — irrelevant next to
  the 923 MB peak — so the memory budget never constrained the choice.
- `main_do_loop` appears with a peak-memory cost of 11.3 GB: that is the
  binomial time-loop level, i.e. the whole run's tape, and is exactly what must
  stay checkpointed.
- The profiler truncates gains to whole seconds; 80 callees print 0 s. A
  30-day run (14 min) is the shortest that resolves the ranking.

## The 2026-09-02 list

`code_tap/tap_nocheckpoint.txt` until 2026-09-12: every callee with a measured gain ≥ 1 s that is
not a Tapenade external (`cg2d` and `exch2_rl1_cube` are declared in
`tools/TAP_support/flow_tap`, the dump and mode-switch hooks in the setup's
library of the time, `flow_tap_local` — `TAP_*`-named in the profiled build,
upstream-named since 2026-09-02, per-field in `mods_tapenade_hooks/flow_tap`
since 2026-09-07; externals
have no source to split). 33 routines, 357 of the 363 s. Compared with the
c69f-era 64-routine list (`tools/tapenade_profiling/nocheckpoint_routines.txt`):
8 routines in common, none of the top twelve, and that list would have
recovered 21 s under this profile.

## Validation — 30 days, same node (31054 vs 31052)

| | plain | nocheckpoint |
| --- | --- | --- |
| wall time | 0:13:13 | **0:08:47** (1.505×, −33.5 %) |
| `fc` | 0.348990284064362 | identical |
| `adxx_*` (32 files, float64) | — | **32/32 bitwise identical** |
| `ADJ*` (73 files, float32) | — | **73/73 bitwise identical** |

Bitwise identity is the expected outcome, not a happy accident: split mode
stores values the joint mode recomputed with the same statements, so the
adjoint sees the same numbers. (Two plain-build runs, 31032 and 31052, are
also bitwise identical, which is what makes the test meaningful.)

## Validation — 5 years (31055 vs 31039)

Report: `compare_5yr_run31039_vs_nocheckpoint_run31055.md`.

| | plain (31039) | nocheckpoint (31055) |
| --- | --- | --- |
| wall time | 14:05:45 | **9:35:58** (1.468×, −31.9 %, 4.5 h) |
| forward sweep to the turn | 0.86 h | 0.84 h |
| reverse sweep | 13.24 h | 8.76 h (1.51×) |
| `fc` | 0.330992121938681 | identical |
| `adxx_*` (32 files, float64) | — | **32/32 bitwise identical** |
| `ADJ*` dumps (4 393 files, float32) | — | **4 393/4 393 bitwise identical** |

The reverse-sweep factor equals the 30-day one; the whole-run factor is a
little lower because at 87 840 steps the binomial schedule re-runs each
plain forward step up to three times (two at 1 440), and those re-runs are
outside what `-nocheckpoint` changes. Phase times come from the write times
of the `ADJtheta` dumps relative to each run's start.

## Validation — the κ_v ensemble, 5 years × 8 (31060–31067 vs 31039–31046)

Report: `compare_5yr_kappa_ensemble_ckpAll_vs_nocheckpoint.md`, one file per
pair in the directory of the same name. The eight adjoints of
`../kappa_v_ensemble/` — the reference and the seven κ_v members, four of
which blow up — were rerun on 2026-09-02 with the `-nocheckpoint` build: same
namelists, same pickups, eight jobs at once on eight separate nodes, as on
2026-09-01. Members went in through temporary copies of
`submit_tapAdj_nocheckpoint.sh` with the pickup repointed, per the
job-chaining recipe in the project notes.

| member | κ | `ckpAll` (2026-09-01) | `nocheckpoint` (2026-09-02) | speed-up | reverse sweep |
| --- | --- | --- | --- | --- | --- |
| REF | 1× | 31039, 14:05:45 | 31060, 9:44:50 | 1.446× | 1.49× |
| M1 | 0.25× | 31040, 14:07:33 | 31061, 9:39:26 | 1.463× | 1.50× |
| M2 | 0.5× | 31041, 14:18:39 | 31062, 9:38:14 | 1.485× | 1.53× |
| M3 | 2× | 31042, 15:39:13 | 31063, 9:30:57 | 1.645× | 1.71× |
| M4 | 4× | 31043, 14:04:21 | 31064, 9:30:47 | 1.479× | 1.52× |
| M5 | 8× | 31044, 14:09:52 | 31065, 9:31:20 | 1.488× | 1.53× |
| M6 | 16× | 31045, 14:02:37 | 31066, 9:38:31 | 1.457× | 1.50× |
| M7 | 32× | 31046, 14:08:27 | 31067, 9:33:58 | 1.478× | 1.52× |

Every pair: `fc` identical, 32/32 `adxx_*` and 4 393/4 393 `ADJ*` bitwise
identical, `%MON` stream byte-identical, `tools/compare_adj_runs.sh`
EQUIVALENT (8 850 sensitivity files and 898 other files per pair). The four
blown-up members blow up identically, being bitwise identical like everything
else: only M4 overflows the float32 dumps (first at lead 2.95 yr, 123 660
non-finite cells at lead 5 yr, in both builds); M1, M5 and M7 stay finite but
huge (max |`ADJtheta`| at lead 5 yr 8.2e5, 1.9e13 and 3.1e6, against
6e-4–1.3e-3 for the reference and the healthy members). Over the eight runs
the wall time went from 114.6 h to 76.8 h (−33.0 %, 37.8 h), 1.45–1.65× per
run; the reverse sweep alone 1.49–1.71× (mean 1.54×), the forward sweep
50–52 min in both builds. M3's 1.65× is the *old* run's slow node, not the new
one: its reverse sweep took 14.8 h against 13.2–13.5 h for the other seven on
2026-09-01, while the eight new runs spread only 9:31–9:45.

Two cross-checks sit in the same report: 31039 vs 31055 recomputed (the table
above), and 31055 vs 31060 — the executable rebuilt on 2026-09-02 after the
`build_info.txt` change (same source; a 32-byte `.rodata` shift, every function
the same size) reproduces the 2026-09-01 one bitwise, at 9:35:58 on c2-1 vs
9:44:50 on c2-4. The ensemble analysis keeps reading 31039–31046; the two sets
are interchangeable.

## The re-profile of 2026-09-12 (run 31268)

The configuration had changed under the list: `kpp` out of
`code_tap/packages.conf`, GM/Redi in the forward sweep and not in the adjoint
sweep, scheme 33 forward and scheme 30 in the adjoint sweep, explicit vertical
advection, `viscAhReMax=2.` at the reference viscosity. The 2026-09-02 list no
longer built (`kpp_calc_dummy`), and it split routines that are recorded before
the adjoint-mode switches act and read them. `tools/tapenade_profiling/README.md`,
section 4, has the rule and the check; this is the record.

- **Run 31268** (`build_tapAdj_profile`, 31 d of the live namelists from the
  production spin-up 31203's year-180 pickup, 0:15:17): its forward sweep wrote
  the 30.5-d pickup byte-identical to the spin-up's own. Peak tape 837 MB per
  process, 161 checkpoint locations, 118 callees, 411 s of CPU on rank 0.
- **Ranks.** Ranks 0–13 report 408–418 s and ranks 14–26 486–499 s; the
  difference is the halo exchange (`exch_xy_rl` 2–31 s against 80–83 s). The
  ≥ 1 s candidates from ranks 7, 13, 14, 20 and 26 differ from rank 0's only at
  the 1 s margin.
- **The list.** The 34 callees ≥ 1 s (`profile_run31268_ranked.md`), minus the
  externals `cg2d`, `exch2_rl1_cube` and `dummy_in_stepping_uv_xyz_rl`, minus
  `thermodynamics` (20 s), `do_oceanic_phys` (19 s) and `dynamics` (12 s), which
  `check_nocheckpoint_switches.py --filter` keeps checkpointed: 28 routines,
  354 of the 411 s (82–87 % on the five ranks checked). Against the 2026-09-02
  list it drops `calc_3d_diffusivity`, `do_fields_blocking_exchanges`,
  `do_oceanic_phys`, `dynamics`, `gad_dst3fl_adv_x`, `gad_dst3fl_adv_y`,
  `gad_dst3fl_impl_r`, `gmredi_calc_tensor_dummy`, `kpp_calc_dummy`,
  `solve_pentadiagonal` and `thermodynamics` (below 1 s here, no longer
  called, or kept checkpointed) and adds `adams_bashforth2`, `calc_viscosity`,
  `gad_dst3_adv_r`, `gad_dst3_adv_x`, `solve_tridiagonal` and
  `tracers_correction_step`.
- **Validation** (`tools/compare_adj_runs.sh`; the switches live in every run).
  31276 against 31269, 30 d on the same node: EQUIVALENT — all 786 sensitivity
  files, `fc` 0.322297725058524 and `%MON` identical — in 8:24 against 11:53
  (1.41×); against 31234 the same 786 files are identical, and only the staged
  `data.autodiff`'s comments differ. 31277 against 31259 (5 d, the live
  namelist): EQUIVALENT, 1:40 against 2:11. 31278 (the in-tree hooks) against
  31277: EQUIVALENT. The driver logs and comparison reports are in
  `/scratch2/<user>/DINO_1deg_outputs/logs/validate_20260912_phaseD2/`.
- **After the build consolidation** later on 2026-09-12 (the `approxAdv` build
  merged into `ckpAll`; `code_tap/gad_implicit_r.F` in every DINO adjoint
  build), the list, profile and in-tree builds were rebuilt and run 5 days:
  31285 against 31277, 31287 against the `ckpAll` run 31281 and 31284 against
  31278, each identical in every sensitivity file, `fc` and `%MON`; the
  comparison reports are in the run directories.

## Re-running

From the setup directory:

```bash
cd MITgcm_c69m/mysetups/DINO_1deg
./scripts/build_tapAdj_profile.sh && ../../../tools/submit.sh scripts/submit_tapAdj_profile.sh
python3 ../../../analyses/DINO_1deg/adjoint/tapenade_profiling/parse_tapenade_profile.py \
        /scratch2/$USER/DINO_1deg_outputs/runs/adjoint/<profile run>/tapenade_profile.0000.txt \
        --top 60 --min-gain-s 1 --budget-mb 2000 --list-out candidates.txt
python3 ../../../tools/tapenade_profiling/check_nocheckpoint_switches.py build_tapAdj_profile \
        candidates.txt --filter=switch_safe.txt
# drop the Tapenade externals (cg2d, exch2_*_cube, the dummy_in_stepping_* hooks) from
# switch_safe.txt, annotate it into code_tap/tap_nocheckpoint.txt, then
./scripts/build_tapAdj_nocheckpoint.sh && IMPACTS_DURATION_DAYS=30 ../../../tools/submit.sh scripts/submit_tapAdj_nocheckpoint.sh
#   the reference run: the same namelist with build_tapAdj_ckpAll.sh / submit_tapAdj_ckpAll.sh
../../../tools/compare_adj_runs.sh <reference run dir> <nocheckpoint run dir>
```
