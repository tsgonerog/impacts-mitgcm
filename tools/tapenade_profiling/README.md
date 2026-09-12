# Tapenade profiling and checkpoint tuning

How to find out where the Tapenade adjoint spends its recomputation, and how to
trade that recomputation for tape memory with `-nocheckpoint`. Both were carried
in checkpoint69f as patched `genmake2` copies; on c69m they are plain Tapenade
flags passed through `genmake2 -tap_extra`, and **both are wired into DINO's
build scripts and verified end to end as of 2026-09-01** (developed on
branch `tapenade-profiling`, merged into `main` on 2026-09-02; the pre-merge
`main` is kept as the tag `archive/20260901_pre-tapenade-profiling`). The numbers below are DINO's; the mechanics apply to any
setup.

| Want | Script (DINO) | Tapenade flag it adds |
| --- | --- | --- |
| profile the adjoint's checkpoints | `build_tapAdj_profile.sh` + `submit_tapAdj_profile.sh` | `-profile`, plus the `mods_profile/` runtime |
| stop checkpointing chosen routines | `build_tapAdj_nocheckpoint.sh` + `submit_tapAdj_nocheckpoint.sh` | `-nocheckpoint "<code_tap/tap_nocheckpoint.txt>"` |
| the plain adjoint, every call checkpointed | `build_tapAdj_ckpAll.sh` + `submit_tapAdj_ckpAll.sh` | none (Tapenade's default; was `build_tapAdj.sh` until 2026-09-02) |

The first is a diagnostic. The second gives the plain adjoint, faster. It was
**DINO's default adjoint from 2026-09-02 to 2026-09-10** (the default is now the
`approxAdv` pair), and on 2026-09-12 its list was derived again for the current
configuration and checked against the adjoint-mode switches (section 4). The
plain build lives on as the `ckpAll` pair, the profiler's base and the timing
baseline. `build_tapAdj_adjVisc.sh` does **not** carry the list: under the
adjoint-mode viscosity boost the 2026-09-02 list was not equivalent to joint
mode (run 31056 vs 31025 — `fc` identical, every sensitivity field different
at order one; sections 2 and 4), so the boosted adjoint stays a `ckpAll` build.
Every
build script records what it built in `build_info.txt`, and the submit
scripts name the run directory from its `run_token` (`tapAdj_nocheckpoint`,
`tapAdj_ckpAll`, `tapAdj_ckpAll_profile`, `tapAdj_ckpAll_adjVisc`).

---

## What is being traded

Tapenade's reverse mode **checkpoints every procedure call by default** ("joint"
mode). For `CALL F(...)` inside a differentiated routine it stores a snapshot of
what `F` overwrites, runs the primal `F`, and in the backward sweep restores the
snapshot and calls `F_B`, which re-runs `F`'s body *recording* before running
its adjoint. So `F`'s primal executes twice — and the re-execution compounds
with nesting: a routine three calls deep runs its primal four times. Memory
stays small, because `F`'s tape exists only while `F_B` runs.

`-nocheckpoint "f g"` switches the named routines to "split" mode: Tapenade
generates `F_FWD` (primal + recording, run once in the enclosing forward sweep)
and `F_BWD` (the adjoint, run in the backward sweep). No re-execution, but
`F`'s tape now lives from the forward sweep until the backward sweep reaches it.
Within one MITgcm time step that is a bounded amount of memory; the peak grows
by at most one step's worth of tape, however many inner routines are switched.

**The time loop is a separate mechanism and is not touched by any of this.**
DINO's `code_tap/the_main_loop.F` carries `C$AD BINOMIAL-CKP nTimeSteps+1 98 1`
in front of the time loop (`ALLOW_TAMC_CHECKPOINTING` is `#undef` in
`AUTODIFF_OPTIONS.h`, so the TAF multi-level loops are compiled out). Tapenade
turns that into Griewank–Walther binomial checkpointing over `MAIN_DO_LOOP`:
at most 98 step snapshots in memory, each step re-run a bounded number of times
(≤ 2 extra for a 30-day / 1440-step run, ≤ 3 for the 5-year / 87 840-step
run). Every checkpoint *inside* a step — the 213 routines the generated code
calls as `X_B` — is a joint-mode Tapenade checkpoint, and those are what the
profile ranks and `-nocheckpoint` acts on.

---

## 1. Profiling — `build_tapAdj_profile.sh`

### What `-profile` does

`-profile` is a hidden Tapenade option (`tapenade -help` does not list it;
`Tapenade.java:hiddenHelp()` does, as "Adds memory and CPU profiling calls").
Around every checkpointed call in the generated adjoint Tapenade emits

```
CALL ADPROFILEADJ_SNPWRITE('thermodynamics'//CHAR(0), 'forward_step.f'//CHAR(0), 750)
CALL PUSHREAL8ARRAY(...)                              <- the snapshot
CALL ADPROFILEADJ_BEGINADVANCE(...)
CALL THERMODYNAMICS(...)                              <- primal
CALL ADPROFILEADJ_ENDADVANCE(...)
...
CALL ADPROFILEADJ_SNPREAD(...)
CALL POPREAL8ARRAY(...)
CALL ADPROFILEADJ_BEGINREVERSE(...)
CALL THERMODYNAMICS_B(...)
CALL ADPROFILEADJ_ENDREVERSE(...)
```

plus `ADPROFILEADJ_TURN` at every `_B` routine's turn point (where its tape
peaks). The runtime behind these calls is `ADFirstAidKit/adProfile.c` — the
**2024 rewrite** shipped with the installed Tapenade (3.16 develop,
2025-12-05). It keeps a tree of the checkpoints currently open and, as each
`ENDREVERSE` closes one, folds its measurements upward so that at the end it
knows, **per static call site**, how much CPU time the run would have saved by
not checkpointing that site (`DeltaT`, summed over every dynamic occurrence)
and how much the adjoint's *peak* tape would have grown (`DeltaPk`).

Two things c69m does not provide, hence `mods_profile/`:

- c69m vendors a **2021** `adProfile.c` with a different API
  (`profileline_`/`printprofile_`) and does not compile it anyway —
  `pkg/tapenade/` symlinks only `adStack.c`, `adBinomial.c`, `adFixedPoint.c`.
  The new runtime must link, so `mods_profile/` carries a verbatim copy of the
  installed Tapenade's `adProfile.c`/`.h`. It needs only
  `adStack_getCurrentStackSize()`, which the vendored `adStack.c` has.
- Tapenade instruments the checkpoints but never emits the final report call.
  `mods_profile/the_model_main.F` (upstream byte-for-byte plus an additive
  `#ifdef ALLOW_TAPENADE` block) calls `ADSTACK_SHOWPEAKSIZE`,
  `ADSTACK_SHOWTOTALTRAFFIC` and `ADPROFILEADJ_SHOWPROFILESFILE` after
  `THE_MAIN_LOOP_B`, writing `tapenade_profile.NNNN.txt` per MPI process.

`build_tapAdj_profile.sh` lists `mods_profile/` **before** `../code_tap` in
`-mods` so both files shadow (the build body puts the shared hooks
directory, `MITgcm_c69m/mods_tapenade_hooks/`, ahead of both), and passes
`-tap_extra "-profile"`, to which the body appends the `-ext` of that
directory's `flow_tap`. After `make` it
asserts the hook argument counts (as
`build_tapAdj_ckpAll.sh` does), that `forward_step_b.f` carries `ADPROFILEADJ_*`
calls, that the compiled `the_model_main.f` is the profiling variant, and that
`adProfile.o` exists. The whole build takes about six minutes.

`-profile` coexists with the binomial time loop: the generated
`the_main_loop_b.f` wraps the `MAIN_DO_LOOP` snapshots in the same
`SNPWRITE`/`SNPREAD` calls inside the revolve schedule, and a toy
binomial-loop test ran to completion with the table written (asserts in
`adProfile.c` are live, so a schedule the profiler could not follow would abort
rather than mislead).

### Running it and reading the table

```bash
cd MITgcm_c69m/mysetups/DINO_1deg
./scripts/build_tapAdj_profile.sh
../../../tools/submit.sh scripts/submit_tapAdj_profile.sh      # 30 days by default
```

The run directory (`DINO_1deg_tapAdj_ckpAll_profile_30d_..._run<id>`) gets
`tapenade_profile.0000.txt` … `.0026.txt`; every process does the same work,
so read rank 0's. `output_tap_adj.txt` additionally carries each process's
`Peak stack size` and `Total push/pop traffic` lines. The table looks like

```
PEAK STACK:<bytes>
SUGGESTED NOCHECKPOINTs:
 * Peak memory gain:
  - Time gain -NN.000 s. and peak memory gain -<b>b for call <callee> (<n> times), at location#<k>: line <l> of file <f>
 * Peak memory neutral:
  - Time gain -NN.000 s. at peak memory cost zero for call ...
 * Peak memory cost:
  - Time gain -NN.000 s. at peak memory cost <MB> Mb for call ...
```

sorted, within the last section, by time gain per byte of peak-memory cost.
Read it with these caveats:

- **Time gains are truncated to whole seconds** (`showOneCostBenefit`
  integer-divides by `CLOCKS_PER_SEC` before printing), so a call site has to
  save more than 1 s over the run to register at all. That is why the default
  profiling length is 30 days (~14 min of adjoint): a 5-day run prints mostly
  zeros. 30 days is representative for the per-step routines, which is
  everything `-nocheckpoint` can act on; the binomial schedule differs at 5
  years but that is not what is being tuned.
- `DeltaT` is `clock()` CPU time of **one process**; with 27 ranks doing the
  same work the wall-clock saving is roughly the same number, not 27× it.
- A `-nocheckpoint` decision is per **callee**, the table is per **call
  site**. `analyses/DINO_1deg/adjoint/tapenade_profiling/parse_tapenade_profile.py`
  aggregates the sites by callee, ranks them, and can propose a list under a
  peak-memory budget (`--budget-mb`). Summing sites' `DeltaPk` is an upper
  bound on the joint memory cost, since peaks need not coincide.
- The profiled executable is **slower** than the plain one (a `clock()` call
  per checkpoint event) and must not be used for runtime comparisons.

---

## 2. `-nocheckpoint` — `build_tapAdj_nocheckpoint.sh`

Verified facts about this Tapenade build (3.16 develop, 2025-12-05), from a
toy program and from the DINO build:

- `-nocheckpoint "a b c"` is accepted (also hidden from `-help`; the accepted
  spellings are `-nocheckpoint`/`-split` and their inverse
  `-checkpoint`/`-joint`, plus `-defaultnocheckpoint` to make split the
  default). Tapenade confirms it on stderr as `@@ Options:  split(a b c)` and
  generates `A_FWD`/`A_BWD` pairs.
- The list passes through genmake2 intact: `-tap_extra` is written verbatim
  into the Makefile's `TAP_EXTRA`, and the shell that runs the recipe hands
  Tapenade the quoted list as one argument (checked with an argv-echo stub).
- The directive form `C$AD NOCHECKPOINT` placed **before a call** works and is
  per call site; placed before the callee's `SUBROUTINE` line, as the Tapenade
  FAQ also allows, it had **no effect** in the toy test with this build. The
  command-line option is the one to use here anyway: it needs no shadow copies
  of upstream files.
- A name Tapenade does not know, or a routine it never checkpoints, is
  ignored silently. `build_tapAdj_nocheckpoint.sh` therefore greps the
  generated `*_b.f` for a `SUBROUTINE <NAME>_FWD(` per listed routine and
  fails the build if any is missing.
- **`-nocheckpoint` is a pure performance change only while the backward
  sweep leaves the primal's parameters alone.** With the `adjVisc`
  mode-switch hooks it is not: in joint mode every checkpointed routine
  re-runs its primal inside the backward sweep *after* `AUTODIFF_INADMODE_SET_B`
  has boosted the viscosities, so the boost reaches every recomputed
  intermediate; in split mode those intermediates were taped in the forward
  sweep at the forward viscosities. Run 31056 (boost + this list) vs 31025
  (boost, every call checkpointed): `fc` and `%MON` byte-identical, all 66
  `ADJ*` and all 8 real `adxx_*` fields different at order one (RMS ratio
  0.3–0.9) — while 31054 vs 31052 and 31055 vs 31039, the plain pair, are
  bitwise identical. Report:
  `analyses/DINO_1deg/adjoint/tapenade_profiling/compare_30d_adjViscBoost_run31025_vs_nocheckpoint_run31056.md`.
  Section 4 gives the exact condition, which a list can meet under a switch:
  the switch reaches whatever is recorded after `FORWARD_STEP` applies it,
  and that list split `dynamics`, which is recorded before.

The list lives in `code_tap/tap_nocheckpoint.txt` (one lower-case name per
line, `#` comments allowed), the setup's one Tapenade input besides the
shared hooks directory. The build script joins it into
`-tap_extra "-nocheckpoint \"<list>\""`.

What a split routine must satisfy is the same as what a checkpointed one must:
be re-entrant and free of hidden state (the Tapenade FAQ's warning about I/O
inside checkpointed code cuts both ways). Everything inside a DINO time step
already passes that test under joint mode, and the hand-written hook adjoints
(`DUMMY_IN_STEPPING_XYZ_RL_B` and friends) are `-ext` externals, which
`-nocheckpoint` does not touch.

---

## 3. The 2026-09-01 profile and list

The list from 2026-09-02 to 2026-09-12; section 4 has its successor. Runs of
2026-09-01, all 27-rank, `baseline/from180yrPk_visc2x` (KPP compiled but off,
GM off, scheme 33 in both sweeps, implicit vertical advection); records in
`analyses/DINO_1deg/adjoint/tapenade_profiling/`.

**Profile (run 31053, 30 days, rank 0; 809 s of adjoint).** Peak tape 923 MB
per process. 156 checkpoint locations, 116 callees. Checkpointing costs
**363 s of CPU per process — 45 % of the run**, and the top twelve callees
carry 308 s of it:

| callee | gain [s] | Δ peak tape | | callee | gain [s] | Δ peak tape |
| --- | --- | --- | --- | --- | --- | --- |
| `timestep` | 75 | −31.1 MB | | `do_oceanic_phys` | 17 | +28.9 MB |
| `forward_step` | 71 | 0 | | `integrate_for_w` | 13 | 0 |
| `grad_sigma` | 37 | 0 | | `dynamics` | 12 | +9.3 MB |
| `mom_vecinv` | 22 | −0.2 MB | | `salt_integrate` | 9 | 0 |
| `calc_phi_hyd` | 21 | −8.6 MB | | `temp_integrate` | 8 | +1.9 MB |
| `thermodynamics` | 18 | 0 | | `do_fields_blocking_exchanges` | 5 | −1.1 MB |

The per-level routines (`timestep`, `grad_sigma`, `calc_phi_hyd`,
`integrate_for_w`, `mom_vecinv` — 36 calls per step each) dominate because in
joint mode Tapenade snapshots the *whole* 3-D arrays they touch on every
per-level call; split mode records only what each call overwrites, which is
why their memory column is a gain. The step-level routines (`forward_step`,
`thermodynamics`, `dynamics`, `do_oceanic_phys`, `temp/salt_integrate`) gain
by not re-running their primal once more per nesting level. Everything that
costs memory sums to ~54 MB per process, so memory never constrained the
choice. `main_do_loop` shows up at a peak cost of 11.3 GB — the binomial level,
the whole run's tape, correctly left alone.

**The list** (`code_tap/tap_nocheckpoint.txt` until 2026-09-12): every callee
with a measured gain ≥ 1 s except the externals `cg2d` and `exch2_rl1_cube` (declared in
`flow_tap`; no source to split) — 33 routines, 357 of the 363 s. The
build confirmed all 33 went split (`@@ Options: split(...)`, 33 `_FWD`
routines) with the four hook calls intact.

**Validation, 30 days on the same node (31054 vs plain 31052):** wall time
**8:47 vs 13:13 (1.505×, −33.5 %)**; `fc` identical; **32/32 `adxx_*` and
73/73 `ADJ*` files bitwise identical.** Two plain runs (31032, 31052) are also
bitwise identical, so the test has teeth. The 2 % profiler overhead (31053 ran
13:29) confirms the profile itself did not distort the ranking.

**5 years (31055 vs 31039), the production length:** wall time **9:35:58 vs
14:05:45 (1.468×, −31.9 %, 4.5 h saved)**; `fc` identical
(0.330992121938681); **32/32 `adxx_*` and all 4 393 `ADJ*` dump files
bitwise identical.** Split by phase from the dump write times: the forward
sweep to the turn took 0.84 h against 0.86 h (unchanged, as it must be — same
primal code, same binomial schedule) and the reverse sweep 8.76 h against
13.24 h (1.51×, the same factor as at 30 days). The whole-run factor is lower
than the reverse-sweep factor only because the binomial re-runs of plain
forward steps inside the reverse sweep are untouched by `-nocheckpoint`.

**The whole κ_v ensemble, 5 years × 8 (31060–31067 vs 31039–31046,
2026-09-02/03):** the reference and the seven members of
`analyses/DINO_1deg/adjoint/kappa_v_ensemble/`, four of which blow up,
rerun with the tuned build, eight jobs at once on separate nodes as before.
Every pair bitwise identical (`fc`; 32/32 `adxx_*`; 4 393/4 393 `ADJ*`; the
`%MON` stream byte-identical; `tools/compare_adj_runs.sh` EQUIVALENT), the
blow-ups reproduced exactly; wall time **114.6 h → 76.8 h** (1.45–1.65× per
run, the reverse sweep 1.49–1.71×, the forward sweep unchanged at 50–52 min).
Report: `analyses/DINO_1deg/adjoint/tapenade_profiling/compare_5yr_kappa_ensemble_ckpAll_vs_nocheckpoint.md`.

**Against the c69f list.** `nocheckpoint_routines.txt` (64 routines) shares
8 with the new list (`calc_3d_diffusivity`, `exch_xy_rl`, `find_rho_2d`,
`gad_calc_rhs`, `gmredi_calc_tensor_dummy`, `impldiff`, `mom_calc_visc`,
`solve_pentadiagonal`) and none of the top twelve; under this profile it would
have recovered 21 s of the 363 s. It was a memory-motivated list for a
different configuration and checkpoint — keep it as history, not as input.

---

## 4. Adjoint-mode switches, and the list of 2026-09-12

**Why the 2026-09-01 list had to go.** Between the two profiles the adjoint
changed: `kpp` left `code_tap/packages.conf`; GM/Redi runs in the forward sweep
and not in the adjoint sweep (`useGMRediInAdMode=.FALSE.`); the tracers use
scheme 33 in the forward sweep and scheme 30 in the adjoint sweep
(`useApproxAdvectionInAdMode`, which every adjoint build honours since the
`gad_advection.F` guard moved into `mods_tapenade_hooks/`); vertical advection
is explicit; the viscosity is the reference file with `viscAhReMax=2.`. The old
list no longer built (`kpp_calc_dummy` was gone), and nine of its routines are
recorded before the switches and read one.

**Where a switch acts.** `FORWARD_STEP` calls `AUTODIFF_INADMODE_UNSET_TAP`
first and `AUTODIFF_INADMODE_SET_TAP` last, so in its reverse sweep
`AUTODIFF_INADMODE_SET_TAP_B` applies the switches — `inAdMode` (which
`useApproxAdvectionInAdMode` is read with), the `use<PKG>` flags and
`viscFacAdj` — before any other adjoint statement of the step, and the `UNSET`
hook reverts them after the last (`forward_step_b.f`). A switch therefore
reaches only what is recorded after that point. `FORWARD_STEP`'s own recording
sweep comes before it in every build. In the checkpoint-everything build every
routine it calls is checkpointed, so that routine's primal runs again,
recording, inside its `_B` routine — after the switch — and so does everything
below it. A split routine is recorded in its `_FWD`, wherever its caller
records: after the switch below a checkpointed routine, before it when called
from `FORWARD_STEP` or from a split routine that is itself recorded before it.

So a list gives the checkpoint-everything adjoint under a switch if no listed
routine reached from `FORWARD_STEP` through listed routines only reads a
switched variable, itself or anywhere below it. Run 31056 split `dynamics`,
whose `mom_calc_visc` reads `viscFacAdj`; runs 31156/31157 of the stability
study split `do_oceanic_phys`, which reads `useGMRedi`, and blew up. A split
routine below a checkpointed one is recorded after the switch, as everything
there is, whatever it reads.

**The check.** `check_nocheckpoint_switches.py BUILD_DIR LIST` (in this
directory) reads the preprocessed primal sources of a build directory, builds
the static call graph, marks the units whose executable statements read a
switched variable — dropping the flags of packages the build does not compile,
which are `.FALSE.` in both sweeps — finds the unit that calls the switch hooks
and reports each listed routine; `--filter=OUT` writes the list without the
routines that must stay checkpointed. `build_tapAdj_nocheckpoint.sh` and
`build_tapAdj_hooksInTree.sh` run it after `make` and record
`nocheckpoint_switch_free=yes` or `no` in `build_info.txt`; the submit body
refuses a `-nocheckpoint` build without `yes` when `data.autodiff` flips a
switch (`use<PKG>InAdMode` off for a package that is on,
`useApproxAdvectionInAdMode`, `viscFacInAd` different from `viscFacInFw`). The
static graph cannot follow a switched value passed as an argument or a call
through a procedure variable; neither occurs in the DINO call tree, and a run
against the checkpoint-everything build is the final check.

**Profile (run 31268, 31 days, the live namelists, rank 0).** Peak tape 837 MB
per process (923 MB on 2026-09-01; the four KPP fields gone from each of the
98 binomial snapshots account for 85 MB of the difference); 161 checkpoint
locations, 118 callees; checkpointing costs 411 s of CPU on rank 0. Ranks
14–26 report 486–499 s against 408–418 s for ranks 0–13, the difference sitting
almost entirely in the halo exchange (`exch_xy_rl` 80–83 s on the slower ranks,
2–31 s on the others). From any rank the ≥ 1 s candidates differ from rank 0's
only in routines at the 1 s margin.

| callee | gain [s] | Δ peak tape | | callee | gain [s] | Δ peak tape |
| --- | --- | --- | --- | --- | --- | --- |
| `timestep` | 101 | −31.1 MB | | `integrate_for_w` | 17 | −0.5 MB |
| `forward_step` | 75 | 0 | | **`dynamics`** | 12 | +9.3 MB |
| `grad_sigma` | 35 | 0 | | `temp_integrate` | 9 | +1.9 MB |
| `calc_phi_hyd` | 30 | −8.6 MB | | `salt_integrate` | 8 | 0 |
| `mom_vecinv` | 30 | −0.2 MB | | `calc_adv_flow` | 7 | −0.9 MB |
| **`thermodynamics`** | 20 | 0 | | `impldiff` | 5 | +0.2 MB |
| **`do_oceanic_phys`** | 19 | +21.4 MB | | `gad_advection` | 4 | +5.8 MB |

(bold: kept checkpointed.) **The list** (`code_tap/tap_nocheckpoint.txt`): the
34 callees with a gain ≥ 1 s, minus the externals `cg2d`, `exch2_rl1_cube` and
`dummy_in_stepping_uv_xyz_rl`, minus what the filter keeps checkpointed —
`thermodynamics`, `do_oceanic_phys` and `dynamics`, the three routines
`FORWARD_STEP` calls that read a switched variable below them (`useGMRedi`;
`useApproxAdvectionInAdMode` with `inAdMode`; `viscFacAdj`). 28 routines, 354
of the 411 s (82–87 % of the total on the five ranks checked), at a summed
peak-memory cost bound of 16 MB. `forward_step`, `temp_integrate`,
`salt_integrate`, `gad_advection` and `gad_calc_rhs`, which the 2026-09-01 list
also split, stay in: every call path to the last four passes a checkpointed
routine. The build confirmed all 28 went split and recorded
`nocheckpoint_switch_free=yes`.

---

## Other levers, deliberately not pulled

- **The binomial snapshot count.** `C$AD BINOMIAL-CKP nTimeSteps+1 98 1` caps
  the time loop at 98 step snapshots, and **98 is a genuine hard limit**: the
  vendored `pkg/tapenade/adBinomial.c` that every build compiles sizes its
  bookkeeping for 99 entries (`stack2[297]`) and rejects `nbSnap > 98` in
  `adBinomial_init` — it prints `Binomial-Checkpointing memory exceeded` and,
  unlike the installed 3.16-v2 copy (which exits), carries on with an
  uninitialised schedule, i.e. crashes. Raising it means shadowing
  `adBinomial.c` through `-mods` with larger arrays, the way `mods_profile/`
  shadows `adProfile.c`. A `MAIN_DO_LOOP` snapshot is the 107 arrays pushed
  before the call in `the_main_loop_b.f` (39 3-D fields of 25×30×36 doubles,
  66 2-D, two scalars): **8.98 MB per process**. 98 of them are 880 MB of the
  923 MB `PEAK STACK`, and the schedule always holds all 98 at once. With 98
  snapshots a 5-year run (87 841 steps) re-runs each step 2.94 times as a plain
  primal on average, at most 3 (C(101,3) = 166 650 ≥ 87 842); getting the
  maximum down to 2 needs C(s+2,2) ≥ 87 842, i.e. s = 418 snapshots — 3.8 GB
  per process, ~109 GB for 27 ranks, so three nodes instead of one. The gain
  would be small anyway: a primal step costs 0.034 s (forward runs 30996 and
  30983) against 0.48 s per recorded-plus-adjoint step (0.30 s in the
  `-nocheckpoint` build), so the binomial re-runs are 12 % of the 30-day and
  17 % of the 5-year wall time; 418 snapshots would save about 47 min of the
  14 h, and the largest count that fits on one node (~160) about 5 min.
  (Numbers from replaying Tapenade's own `adBinomial.c` schedule for DINO's
  step counts, 2026-09-01.) Not done here: it changes the reverse schedule of
  the whole run, so it cannot be validated on a 30-day run the way a per-step
  change can, and the per-step cost is the lever that matters.
- **`-defaultnocheckpoint`** (split everything, then `-checkpoint` the
  exceptions) is the TAF-like configuration: no recomputation inside a step at
  all. It is the limit the profile-guided list approaches; the list form was
  preferred because each entry is justified by a measured gain. Under the
  adjoint-mode switches it is not available at all: it would split
  `thermodynamics`, `do_oceanic_phys` and `dynamics` (section 4).

---

## `c69f_originals/` and `nocheckpoint_routines.txt`

`patched_ForTapProfile_genmake2` and `patched_AfterTapProfile_genmake2`,
copied verbatim from `Proj_ImPACTS_old/MITgcm_c69f/MITgcm/tools/` on
2026-08-20, are the record of how checkpoint69f did this: full copies of the
*c69f* `genmake2` with the Tapenade flags hard-wired into the make rule (and a
`cp ../code_tap/forward_step_b.f_modified` post-edit that the 2026-08-31 hook
redesign made unnecessary). **They do not work on c69m and must not be dropped
into `MITgcm/tools/`** — c69m's `genmake2` differs by ~200 lines and
parameterises the Tapenade command through `$(TAP_EXTRA)`. To see exactly what
a variant did:

```bash
OLD=<clone of Proj_ImPACTS_old>/MITgcm_c69f/MITgcm/tools
diff "$OLD/genmake2" tools/tapenade_profiling/c69f_originals/patched_ForTapProfile_genmake2
```

They also compiled the ADFirstAidKit with `-D_ADSTACKPROFILE -D_ADSTACKPREFETCH`;
those macros appear nowhere in the kit, then or now, and were inert.

`nocheckpoint_routines.txt` is the 64-routine list the c69f work settled on
(deduplicated from the 68 entries embedded in `patched_AfterTapProfile_genmake2`).
It came from a *c69f* profile of a different configuration; section 3 records
how it compares with what the c69m profile found.
