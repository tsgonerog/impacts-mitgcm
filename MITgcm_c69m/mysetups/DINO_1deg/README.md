# DINO_1deg

Idealised single-basin "DINO" ocean, pole to pole. **51 × 198 × 36**, curvilinear,
`delX = 1°`, `delY = 0.77°`, `dT = 1800 s`, 366-day year.

**MPI only.** `code/SIZE.h` and `code_tap/SIZE.h` are the one decomposition
(`nPx=3, nPy=9` over `sNx=17, sNy=22`, 27 ranks); there is no serial variant.

## Quick start

Run everything **from this directory** (`MITgcm_c69m/mysetups/DINO_1deg`).
The scripts live in `scripts/` (since 2026-09-05) and are short *definitions*
that source the shared bodies in `tools/lib/`: a build definition `cd`s here
itself, so it runs from anywhere, while a submit definition must be submitted
from here — `tools/submit.sh` does that for you — because the job resolves
everything against `SLURM_SUBMIT_DIR`. **Nothing needs exporting:**
`tools/machine_env.sh` supplies the optfile, scratch root, MPI launcher and
per-machine sbatch flags.

### Forward model

```bash
./scripts/build_frd.sh                                   # -> build_frd/mitgcmuv
../../../tools/submit.sh scripts/submit_frd.sh           # 10 yr from rest, reference viscosity + viscAhReMax=2, scheme 33
```

### Adjoint model

```bash
./scripts/build_tapAdj.sh                                # -> build_tapAdj_approxAdv/mitgcmuv_tap_adj (since 2026-09-10)
../../../tools/submit.sh scripts/submit_tapAdj.sh        # 5 yr from the 180 yr pickup; scheme 33 forward sweep, scheme 30 adjoint sweep
```

Build and submit scripts are **paired by build directory** — `submit_frd.sh`
runs what `build_frd.sh` produced, `submit_tapAdj.sh` what `build_tapAdj.sh`
produced. Since 2026-09-05 the pairing is enforced: each submit definition
names the `run_token` it expects and the shared body refuses a build directory
holding anything else, so mixing them fails loudly instead of running a
configuration you did not intend; the two tables below give the pairing.

**The two unmarked adjoint names in `scripts/` are symlinks** (since 2026-09-02) to
`build_tapAdj_nocheckpoint.sh` / `submit_tapAdj_nocheckpoint.sh`, the default
adjoint: Tapenade's profile-guided `-nocheckpoint` build, bitwise identical to
the checkpoint-everything one and 1.5× faster. The previous default lives on
as `build_tapAdj_ckpAll.sh` / `submit_tapAdj_ckpAll.sh`. Repointing the two
symlinks is how the default changes; every real script carries a token saying
what it builds.

Always submit through `tools/submit.sh`, never bare `sbatch`: the wrapper adds
the account, QOS, constraint and walltime flags that differ per machine and
cannot be written as `#SBATCH` directives without breaking the other one. On
sverdrup those are empty, so it reduces to `sbatch --export=ALL <script>`.

### Before the first run

Two untracked directories must exist, or staging fails:

| Directory | Needed by | Notes |
| --- | --- | --- |
| `input_binaries/` | both | 179 MB of `dino_*.bin`, produced outside this repo. Two exceptions since 2026-09-09: `dino_viscAhD*.bin` regenerate byte for byte with `scripts/gen_viscAhD.py`, and no namelist reads `dino_diffKr*.bin` any more (`diffKrT`/`diffKrS` in `PARM01` set the same constants) |
| `input_adj_binaries/` | adjoint only | `ones_64b.bin`, the uniform weight every `data.ctrl` entry points at |

### Changing the run without editing anything

The committed values are the cheap regression configurations. Override per run
from the command line — this leaves `git status` clean, so no run produces a
commit:

```bash
# 200-year forward spin-up
IMPACTS_DURATION_DAYS=73200 ../../../tools/submit.sh scripts/submit_frd.sh

# 30-day adjoint, denser monitor output
IMPACTS_DURATION_DAYS=30 IMPACTS_ADJ_MONITOR_FREQ_DAYS=1 \
    ../../../tools/submit.sh scripts/submit_tapAdj.sh

# a different namelist variant
IMPACTS_TEST_CASE=scheme_tests/from_rest_viscRef_adv30 ../../../tools/submit.sh scripts/submit_frd.sh

# one member of a grouped experiment (variants/kappa_v_ensemble/data_M3)
IMPACTS_TEST_CASE=kappa_v_ensemble/M3 ../../../tools/submit.sh scripts/submit_frd.sh
```

| Variable | Patches | Default (`frd` / `tapAdj`) |
| --- | --- | --- |
| `IMPACTS_DURATION_DAYS` | `nTimeSteps` (÷ `dT=1800`) | `3660` (10 yr) / `1830` (5 yr) |
| `IMPACTS_MONITOR_FREQ_DAYS` | `monitorFreq` | `30.5` / `5` |
| `IMPACTS_ADJ_MONITOR_FREQ_DAYS` | `adjMonitorFreq` | — / `5` |
| `IMPACTS_ADJ_DUMP_FREQ_DAYS` | `adjDumpFreq` | — / `5` |
| `IMPACTS_TEST_CASE` | which variant is staged: `<group>/<tag>` → `variants/<group>/data_<tag>` (a bare `<tag>` still works) | `baseline/from_rest_visc2x` / `baseline/from180yrPk_visc2x` |

Durations are whole days; a non-numeric value is rejected before the job stages
anything. `IMPACTS_TEST_CASE=` (explicitly empty) selects the live `input*/data`
rather than a variant. The values reach the compute node because sbatch forwards
the environment, and the run directory name records the result — a duration that
failed to arrive shows up as `_10yr_` instead of `_200yr_`.

**`nIter0` is deliberately not in that table.** The start iteration lives in
whichever `data_<tag>` `test_cases` selects, and the matching pickup is a
hardcoded `ln -s` in the submit definition's `stage_pickups`. Changing the
duration is safe; changing the starting point means editing both by hand.

## Build

| Script | Build directory | Executable |
| --- | --- | --- |
| `build_frd.sh` | `build_frd/` | `mitgcmuv` (forward only) |
| `build_tapAdj.sh` → `build_tapAdj_approxAdv.sh` | `build_tapAdj_approxAdv/` | `mitgcmuv_tap_adj` — **the default** (symlink; `_approxAdv` since 2026-09-10, `_nocheckpoint` from 2026-09-02) |
| `build_tapAdj_nocheckpoint.sh` | `build_tapAdj_nocheckpoint/` | `mitgcmuv_tap_adj` (profile-guided `-nocheckpoint`; see below; the default until 2026-09-10 — it cannot honour the adjoint-sweep scheme switch of the live `data.autodiff`) |
| `build_tapAdj_ckpAll.sh` | `build_tapAdj_ckpAll/` | `mitgcmuv_tap_adj` (reference: every call checkpointed; was `build_tapAdj.sh` / `build_tapAdj/` until 2026-09-02) |
| `build_tapAdj_adjVisc.sh` | `build_tapAdj_adjVisc/` | `mitgcmuv_tap_adj` (adjoint-mode viscosity boost, every call checkpointed — the list is not equivalent under the boost; see "Profiling and checkpoint tuning") |
| `build_tapAdj_approxAdv.sh` | `build_tapAdj_approxAdv/` | `mitgcmuv_tap_adj` (**the default since 2026-09-10**: scheme 33 forward, scheme 30 in the adjoint sweep: `code_tap/variants/approxAdvection/` ahead of `code_tap/`, every call checkpointed because the switch is a run-time branch; see "Scheme 30 or scheme 33" below) |
| `build_tapAdj_profile.sh` | `build_tapAdj_profile/` | `mitgcmuv_tap_adj` (diagnostic: ckpAll + Tapenade checkpointing profiler) |
| `build_tapAdj_hooksInTree.sh` | `build_tapAdj_hooksInTree/` | `mitgcmuv_tap_adj` (validation of the **in-tree** form of the hooks: built against a git copy of checkpoint69m outside this repository, `~/MITgcm_c69m_tapenade_hooks/MITgcm`, in which the files of `mods_tapenade_hooks/` are applied to the tree, with the shared directory left out; run 31107 bitwise identical to the default's 31101 on 2026-09-05 — see "The same mechanism from inside the tree" below) |

The **unmarked** adjoint names are symlinks to the current default pair; every
real adjoint script carries a token — `_<ckp>` (`nocheckpoint` / `ckpAll`) or
`_<variant>` (`adjVisc` / `profile`) — and the run directories carry
both (see "Run"). Every build script is a definition in `scripts/` that
sources the shared body `tools/lib/build_body.sh` (since 2026-09-05; what the
definition supplies is its build directory, `-mods` list, Tapenade flags, run
token and any extra check), and the body ends by writing `build_info.txt` into
the build directory: the script, the build directory, the Makefile's
`TAP_EXTRA`, the `-nocheckpoint` list, the commit, `exe_md5` and a `run_token`
— the forward build too, with `run_token=frd`. Every adjoint definition
uses **stock** `genmake2` and the tree's stock Tapenade options: since the
2026-08-31 dump-hook redesign no generated file is post-edited, and since
2026-09-07 no hook file lives in this setup at all. The `ADJ*` dump calls, the
`ADJetan` dump and the two adjoint-mode switches are generated by Tapenade
from the seven files of `../../mods_tapenade_hooks/`, a directory shared with
SOMA that the build body lists first in `-mods` and whose `flow_tap` it hands
to Tapenade as a second external library through `-tap_extra` (its `README.md`
maps each file to its place in the MITgcm tree; see "How the Tapenade hooks
work" below). The mode switches are what make the `adjVisc` parameters
actually engage — before them the TAF-named `ADAUTODIFF_INADMODE_SET` was
never called under Tapenade and adjVisc silently ran plain physics. After
`make`, the build body asserts, over the `HOOK_CHECKS` list in
`scripts/setup_params.sh`, that every generated `_B` call carries exactly the
argument count the hand-written routines declare (a scalar field hook 7, a
vector pair 11, the etaN dump and the mode switches 5 each), that the compiled
`dummy_tap.f` carries its five `ADJ*` dump calls, and that the compiled
hook sources link into the shared directory; it fails loudly otherwise — F77
would silently misalign a mismatch.

There is no `rawTapenade` control build any more: raw Tapenade output *is* the
working configuration. (Since 2026-08-31 the same is true of SOMA, whose
conversion also retired the patched `genmake2` override entirely — the
vendored `MITgcm/` tree deviates from upstream in zero files.)

Build directories symlink back into `code_tap/` (the boost build's into
`code_tap/variants/adjointViscosity/` as well). Since 2026-09-02 no build copies
anything into `code_tap/`, so building one variant leaves every other build
directory consistent; after editing a source, re-run the build script rather
than running bare `make` in a build directory.

### Switching the default adjoint

`scripts/build_tapAdj.sh` and `scripts/submit_tapAdj.sh` are **symlinks**, not
copies: each is a tracked path whose only content is the name of the script it
points at, beside it in `scripts/` (git stores it as mode `120000`; `ls -l`
shows `build_tapAdj.sh -> …`). Running `./scripts/build_tapAdj.sh` runs the
target definition, which uses *its own* build directory, job name and run
token — so repointing the link is the whole change. Always move the pair together; a build link on one variant and a
submit link on another builds one executable and runs a different build
directory.

```bash
cd MITgcm_c69m/mysetups/DINO_1deg/scripts

# approxAdv — the default since 2026-09-10 (scheme 33 forward, scheme 30 adjoint sweep)
ln -sfn build_tapAdj_approxAdv.sh  build_tapAdj.sh
ln -sfn submit_tapAdj_approxAdv.sh submit_tapAdj.sh

# nocheckpoint — the default from 2026-09-02 to 2026-09-10 (exact adjoint; use with a scheme-30 namelist)
ln -sfn build_tapAdj_nocheckpoint.sh  build_tapAdj.sh
ln -sfn submit_tapAdj_nocheckpoint.sh submit_tapAdj.sh

# checkpoint everything — the reference (the default until 2026-09-02)
ln -sfn build_tapAdj_ckpAll.sh  build_tapAdj.sh
ln -sfn submit_tapAdj_ckpAll.sh submit_tapAdj.sh

# profiler — a diagnostic (30-day default, 2 % slower, writes tapenade_profile.*.txt)
ln -sfn build_tapAdj_profile.sh  build_tapAdj.sh
ln -sfn submit_tapAdj_profile.sh submit_tapAdj.sh

ls -l build_tapAdj.sh submit_tapAdj.sh    # confirm both point where you expect
```

`ln -sfn` replaces the link in place (`-f` overwrite, `-n` treat an existing
link as a file, not as a directory to descend into). After repointing, `git
status` shows both links as modified; commit that, and update the "default
since" sentences in this file and in `CLAUDE.md`, or the docs will name the
wrong variant. You rarely need to repoint at all: every variant is callable
by its explicit name (`./scripts/build_tapAdj_ckpAll.sh`, then
`../../../tools/submit.sh scripts/submit_tapAdj_ckpAll.sh`), so the links only
decide what a bare `./scripts/build_tapAdj.sh` means for everyone, including
your future self.

### Profiling and checkpoint tuning

Tapenade checkpoints every call inside a time step by default (store a
snapshot, run the primal, re-run it recording inside the `_B` routine), and
the re-run compounds with nesting depth. `build_tapAdj_profile.sh` adds
Tapenade's `-profile` — plus the runtime and reporting main program it needs,
from `tools/tapenade_profiling/mods_profile/` — and its 30-day run writes a
per-call-site table of the CPU time each checkpoint costs and the peak tape it
would cost not to have it. For DINO (run 31053) that came to **45 % of the
adjoint's CPU time**, almost all of it in routines whose split mode is
memory-neutral or a memory gain (`timestep`, `forward_step`, `grad_sigma`,
`mom_vecinv`, `calc_phi_hyd`, `thermodynamics`, …).

`build_tapAdj_nocheckpoint.sh` acts on that: it passes the 33 routines in
`code_tap/tap_nocheckpoint.txt` to Tapenade's `-nocheckpoint`, which
differentiates them in split `_FWD`/`_BWD` mode instead, and refuses to finish
unless every listed routine actually came out split. The time loop's binomial
checkpointing (`C$AD BINOMIAL-CKP … 98 …` in `code_tap/the_main_loop.F`) is
not involved. **Validated 2026-09-01: a 30-day run of this build (31054) is
bitwise identical to the plain build's (31052) in `fc`, all 32 `adxx_*` and
all 73 `ADJ*` files, and runs in 8:47 instead of 13:13 (1.5×); at 5 years (31055 vs 31039) it is
again bitwise identical — fc, 32 `adxx_*`, 4 393 `ADJ*` — in 9:35:58 instead
of 14:05:45 (1.47×, 4.5 h saved); re-verified 2026-09-02/03 on the whole κ_v
ensemble — all eight 5-yr adjoints (31060–31067 vs the `ckpAll` runs
31039–31046) bitwise identical, the four blow-ups included, 1.45–1.65× per run,
37.8 h saved of 114.6 h.** `tools/tapenade_profiling/README.md`
has the method and the numbers;
`analyses/DINO_1deg/adjoint/tapenade_profiling/` the records and the
three scripts (`parse_tapenade_profile.py`, `compare_adjoint_runs.py`,
`compare_ensemble_ckpAll_vs_nocheckpoint.py`).

**Since 2026-09-02 it is the default adjoint**: `build_tapAdj.sh` and
`submit_tapAdj.sh` are symlinks to the `_nocheckpoint` pair, and the
checkpoint-everything build is `build_tapAdj_ckpAll.sh` /
`submit_tapAdj_ckpAll.sh` (until then it *was* `build_tapAdj.sh`). The
`ckpAll` pair stays for three reasons: the profiler must see every checkpoint
(a profile of the tuned build would only show the residual), it is the
fallback if a configuration change invalidates the list, and it is the timing
baseline. It is no longer needed as a correctness control. The list is a
profile of **one** configuration (KPP/GM off, 27 ranks, this package set); the
build's `_FWD` check catches a name that vanished, not a list that stopped
being the right list, so re-profile whenever the adjoint's package set,
physics or decomposition changes.

The profiling build is a diagnostic — same numbers, 2 % slower — and compiles
the plain sources without the list.

**The adjVisc build does not carry the default `-nocheckpoint` list, on purpose.** Tried 2026-09-02: run 31056 (boost + list, 30 d from rest) vs 31025 (boost, every call checkpointed) — `fc` and all 441 `%MON` lines byte-identical, but all 66 `ADJ*` dumps and all 8 real `adxx_*` gradients differ at order one (RMS ratio 0.3–0.9), whereas the plain pair is bitwise identical under the same list. In joint mode Tapenade re-runs each routine's primal inside the backward sweep *after* `AUTODIFF_INADMODE_SET_B` has boosted the viscosities, so the boost reaches every recomputed intermediate; in split mode those intermediates were taped during the forward sweep at forward viscosities and the boost reaches only what the `_BWD` code reads live — a weaker, different regularisation. So the boosted adjoint stays a `ckpAll` build (run token `tapAdj_ckpAll_adjVisc`, 13 min per 30 d instead of 9), and 31056 stays on scratch as the record; report in `analyses/DINO_1deg/adjoint/tapenade_profiling/compare_30d_adjViscBoost_run31025_vs_nocheckpoint_run31056.md`. Corollary: `-nocheckpoint` is a pure performance change only for an adjoint whose backward sweep leaves the primal's parameters alone.

## Run

Commands are in **Quick start** above; this section covers what the scripts do.

| Submit script | Uses build directory |
| --- | --- |
| `submit_frd.sh` | `build_frd/` |
| `submit_tapAdj.sh` → `submit_tapAdj_nocheckpoint.sh` | `build_tapAdj_nocheckpoint/` (the default; symlink since 2026-09-02) |
| `submit_tapAdj_nocheckpoint.sh` | `build_tapAdj_nocheckpoint/` |
| `submit_tapAdj_ckpAll.sh` | `build_tapAdj_ckpAll/` (was `submit_tapAdj.sh` until 2026-09-02) |
| `submit_tapAdj_adjVisc.sh` | `build_tapAdj_adjVisc/` |
| `submit_tapAdj_profile.sh` | `build_tapAdj_profile/` (30-day default; writes `tapenade_profile.NNNN.txt`) |

**The run directory is named from the build, not from the submit script.**
The shared submit body (`tools/lib/submit_body.sh`, which every submit
definition in `scripts/` sources) reads `run_token` from the build directory's
`build_info.txt` (written by the build body as its last step, after every
check passed), refuses an executable that has no record, whose checksum does
not match the record's `exe_md5` (a by-hand `make`; since 2026-09-03 — the
earlier mtime test misfired on the NFS home and remains only as the fallback for
records without that line), or whose token is not the one the definition names
in `EXPECT_RUN_TOKEN` (since 2026-09-05), copies the record into the run
directory, and names the run

```
$SCRATCH_ROOT/DINO_1deg_outputs/runs/adjoint/
└── DINO_1deg_<run_token>_<duration>[_<tag>]_run<jobid>  run_token = tapAdj_<ckp>[_<variant>]
```

**A new run lands directly in `runs/adjoint/`, unfiled.** Since 2026-09-03 that
directory also holds campaign subdirectories — `kappa_v_ensemble/`,
`checkpointing_study/`, `adjVisc/`, `toolchain_validation/`,
`gradient_check/`, `sensitivity/` — and the forward side has
`spinup_200yr_visc2x/` and `kappa_v_ensemble/`. The submit script does not
choose one: it cannot know which campaign a run belongs to, and often that is
not decided until the run finishes. Move the directory into a campaign when it
joins one (a plain `mv`; the campaign is the parent directory, never part of
the name) and update the notebook that reads it. The scratch tree's own
`README.md` has the campaign map and the filing rules.

with `<ckp>` = `nocheckpoint` | `ckpAll` and `<variant>` = `adjVisc` |
`profile` when present. Both variant tokens were shortened on 2026-09-05
(from `adjViscBoost` and `tapProfile`); runs made before that keep the older
spellings on scratch and in their own `build_info.txt`, and were deliberately
not renamed. So the default gives
`DINO_1deg_tapAdj_nocheckpoint_5yr_from180yrPk_visc2x_run<jobid>`, the boost
`DINO_1deg_tapAdj_ckpAll_adjVisc_…`, the reference
`DINO_1deg_tapAdj_ckpAll_…` and the profiler `DINO_1deg_tapAdj_ckpAll_profile_…`;
a forward run is `DINO_1deg_frd_…` under `runs/forward/`, its token `frd`.
The `#SBATCH -J` name only names the log file. `<tag>` is the last
component of `IMPACTS_TEST_CASE`; when that is **empty** (the live
`input_tap/data`, which has no name of its own) the submit script derives the
`<start>_<viscosity>` tokens from the namelist instead — `nIter0` →
`from_rest` / `from<N>yrPk`, `viscAhDfile`/`viscAhZfile` → `viscRef` / `visc2x`
/ `viscD2x_Zref`, a scalar `viscAhGrid` → `viscGrid<value>`, anything else →
`liveData` — so a run of the live namelist is named
`…_30d_from_rest_viscRef_run<jobid>` rather than `…_30d_run<jobid>`, with the
same vocabulary as the tagged variants (root README, "Namelist variants"). On
2026-09-02 every existing adjoint run directory on scratch was renamed to this
scheme: all runs
up to 31053 were checkpoint-everything builds (checked with `nm` on each run's
copied executable) and carry `ckpAll`; 31025 and 31026 additionally got
`from_rest_viscRef`, read from their staged namelists, in place of the empty
tag they ran with; 31054/31055 already had `nocheckpoint`. Run 31056
(`…_nocheckpoint_adjVisc_30d_from_rest_viscRef_…`) is the rejected
split-mode boost, kept as a record.

A job leaves one log, `logs/<job-name>.<job-id>.out`, holding stdout and stderr
merged. It is gitignored, and the scripts run under `set -x`, so it is a full
trace of the staging steps — a staging failure shows up there rather than in the
model output on scratch, as does a SLURM-level kill (time limit, OOM, node
failure), which never reaches scratch at all. `tools/submit.sh` creates `logs/`
before submitting; sbatch fails a job at launch if that directory is missing.

Nothing prunes these — at ~8 KB apiece they are a record, not clutter. Use
`rm logs/*.out`, or `find logs -mtime +90 -delete`, whenever you want. Do not
delete the log of a *running* job: SLURM holds the file open, so the job keeps
writing to the unlinked inode, which loses the trace without freeing the space
until the job exits.

`adjVisc` runs the adjoint with **larger viscosity and diffusivity than the
forward** — the standard trick for stopping a long adjoint from blowing up.
`viscFacInAd = 10.` against `viscFacInFw = 1.`, `inAdviscArNr = 2.E-3` against a
forward `1.2E-4`, plus added `inAddiffKhT/S`; the `outAd*` values restore the
forward settings on the way out. Values were adapted from the ASTE 90x150x60
regional setup.

It is a **build and a namelist variant**. The build compiles
`code_tap/variants/adjointViscosity/` ahead of `code_tap/` (a second `-mods`
directory, listed first — see the README there), which is what provides the
`inAd*`/`outAd*` parameters at all; the submit script swaps
`data.autodiff_adjointViscosity` in at run time, which is what sets them. **The two must be used together** — pairing the
plain submit script with this build silently runs the ordinary configuration.

**What the switches can reach (reviewed 2026-09-09).** The stock `viscFacInAd`
multiplies **only** the `PARM05` `viscAh[D/Z]file` fields
(`pkg/mom_common/mom_calc_visc.F:509-511`, under `AUTODIFF_ALLOW_VISCFACADJ`);
a scalar `viscAh`/`viscAhD` or `viscAhGrid` is not multiplied, so the
file-based viscosity is what makes this boost work at all, and it boosts
DINO's A_h = ½·U_v·Δx field with its latitude structure intact. The ASTE
`inAdviscAhGrid` term is added inside `MOM_CALC_VISC`, which is only called
because the files set `useVariableVisc` at initialisation
(`model/src/set_parms.F:132`); `inAdviscA4Grid` is inert here because
`useBiharmonicVisc` (`set_parms.F:148`) is fixed `.FALSE.` by a forward
namelist with no biharmonic term; `inAdviscArNr` acts (`viscArNr(k)` is read
every step in `calc_viscosity.F`). The `outAd*` values are what every
checkpoint replay of the forward model runs with after the first backward
step, so each must equal the forward namelist's value: until 2026-09-09
`outAdviscAhGrid` was `1.8E-2` (a value from the `viscGrid1p8e-2` study
namelists; the production namelists set no `viscAhGrid`) and `outAddiffKhT/S`
were `0` (forward: `500`), so every boosted run up to 31138 replayed the
forward with an extra `1.8E-2·L²/(4Δt)` of viscosity and no lateral tracer
diffusion. Fixed in `data.autodiff_adjointViscosity`; run 31141 against 31138
(30 d from rest, same executable) measures what that changed — see `TODO.md`.
Vertical diffusivity cannot be boosted through any `inAd*` scalar: under
`ALLOW_3D_DIFFKR` the run-time diffusivity is the 3-D `diffKr` array
(`model/src/calc_3d_diffusivity.F`), which a boost would have to scale
directly in the set/unset pair.

**27 ranks**, fixed by `code_tap/SIZE.h` (`nPx=3, nPy=9` over `sNx=17, sNy=22`).
Changing the decomposition means changing `code_tap/SIZE.h` *and* `#SBATCH -n`.

Durations are set in **days** — either the committed defaults at the top of the
submit script or the `IMPACTS_*_DAYS` overrides above — and converted to
`nTimeSteps` / `*Freq` seconds automatically.

**The conversion patches the staged namelist in the run directory, never the
tracked file**, so submitting a job leaves the working tree clean. That ordering
is load-bearing rather than cosmetic: the script body executes on the compute
node when the job *starts*, not when you submit, so patching the repo copy in
place made it shared mutable state between every queued job. Two jobs starting
close together would each stage whichever value landed last while their run
directory names each claimed their own duration. If a namelist diff ever appears
after a run, something has regressed — `tools/pre_push_check.sh` watches for it.

The frequency names that get patched are listed explicitly in a `TIME_PARAMS`
array beside the defaults; the duration lands on `nTimeSteps` at `DELTA_T`
because `scripts/setup_params.sh` says so (`DURATION_KEY=nTimeSteps`). Do not
restore the old `compgen -v | grep '_days$'` auto-detection:
`compgen -v` also enumerates *exported environment variables*, so any `*_days`
variable in your shell would silently become a namelist key.

## Files

| Path | Contents |
| --- | --- |
| `code/`, `input/` | forward model |
| `code_tap/`, `input_tap/` | adjoint model — adds `data.autodiff`, `data.cost`, `data.ctrl`, `data.grdchk` |
| `scripts/` | the build and submit definitions (since 2026-09-05), one per build directory, plus the two default symlinks and `setup_params.sh` (dT, duration key, calendar, hook list, run-naming rule); each definition sources a shared body in `tools/lib/` |
| `input*/variants/` | alternative namelists, grouped by purpose, each group with its own `README.md`; the submit script stages the selected `data_<tag>` plus any sibling sharing its tag |
| `input_binaries/` | **untracked, 179 MB.** Produced outside this repo, except that `scripts/gen_viscAhD.py` regenerates every `dino_viscAhD*.bin` byte for byte (since 2026-09-09) and `dino_diffKr*.bin` are no longer read by any namelist |
| `input_adj_binaries/` | **untracked.** `ones_64b.bin`, the uniform control weight every `data.ctrl` entry points at |
| `build_*/` | **gitignored, reproducible.** One per build script: `build_frd/` and `build_tapAdj_{nocheckpoint,ckpAll,adjVisc,profile}/`; each carries the `build_info.txt` the submit body names run directories from |
| `00_archive/` | superseded config in `code_tap/`, `input_tap/`, `scripts/`, mirroring the live dirs — nothing live reads it; has its own `README.md` |

## Namelists and variants

`input/` and `input_tap/` hold exactly the files MITgcm reads — the same list a
run directory ends up with, and every one of them is copied into every run.
Alternatives live one level down, **grouped by what they are for**:

```
input_tap/
├── data              <- the live namelist
├── data.autodiff     <- ... and the other ten MITgcm reads
├── ...
└── variants/
    ├── README.md                 the rule, and an index of the groups
    ├── baseline/                 the config the committed default points at
    │   └── data_from180yrPk_visc2x
    ├── viscosity_study/
    ├── adjointViscosity/         data.autodiff_adjointViscosity
    ├── grdchk_repair/            gradient check on the sensitivity peak (passes; the
    │                             committed data.grdchk's point measures noise)
    └── kappa_v_ensemble/
        ├── README.md
        └── data_M1 ... data_M7
```

`input/variants/` is organised the same way, with the same group names where a
study has both a forward and an adjoint half. **Every variant is in a group**;
there are no loose files. Each group carries a `README.md` saying what it varies,
and [`variants/README.md`](input_tap/variants/README.md) indexes them.

Two rules make the contents legible:

**1. A file is named after the MITgcm file it replaces** — `<mitgcm-file>_<tag>`.
So `data_M3` replaces `data`, `data.pkg_M3` replaces `data.pkg`,
`data.autodiff_M3` replaces `data.autodiff`. Whatever precedes the first
underscore is the file you are overriding.

**2. Everything sharing a tag inside a group is staged together.** Selecting a
tag stages its `data` *and* every sibling `<mitgcm-file>_<tag>` beside it, so one
variant can change a package flag as well as the namelist:

```bash
IMPACTS_TEST_CASE=scheme_tests/from_rest_viscRef_kppON \
    ../../../tools/submit.sh scripts/submit_frd.sh      # stages data AND data.pkg
```

Select a variant without touching any script:

```bash
IMPACTS_TEST_CASE=baseline/from180yrPk_visc2x  ../../../tools/submit.sh scripts/submit_tapAdj.sh
IMPACTS_TEST_CASE=kappa_v_ensemble/M3          ../../../tools/submit.sh scripts/submit_tapAdj.sh
IMPACTS_TEST_CASE=                             ../../../tools/submit.sh scripts/submit_tapAdj.sh   # live input_tap/data
```

or change the committed default, the value `IMPACTS_TEST_CASE` falls back to:

```bash
test_cases="${IMPACTS_TEST_CASE-baseline/from180yrPk_visc2x}"
```

A tag containing `/` resolves as `variants/<group>/data_<tag>`; a bare tag still
resolves as `variants/data_<tag>`, which is kept so a tag from before the
grouping — or a queued job's spooled script — still works. A typo aborts the job
before the run directory is created rather than silently running the wrong
configuration.

**The run directory is named after the tag only, never the group.** A run is
described by its physics, not by where its namelist sits in this repository, so
`kappa_v_ensemble/M3` gives `..._M3_run<jobid>` and `baseline/from_rest_visc2x`
gives `..._from_rest_visc2x_run<jobid>` — the same tag these runs had before
the variants were grouped (the `...` is `DINO_1deg_<run_token>_<duration>`, see
"Run").

**Adding to this:** a new member goes into its group as `data_<tag>` (plus any
`<other-file>_<tag>` it needs); a new study gets `variants/<name>/` with a
`README.md`, and nothing else needs editing. Files placed directly in
`input_tap/` are staged into *every* run, so a stray one there becomes part of
every configuration.

Only the selected variant is copied to scratch, so a run directory contains the
12 namelists MITgcm reads and nothing else.

### Lateral viscosity and vertical diffusivity: file or parameter

DINO (Kamm et al. 2025, GMD 18, 8091, and its `EXPREF/namelist_cfg`) sets at
1°: Laplacian viscosity `nn_ahm_ijk_t = 20` with `rn_Uv = 0.27` m/s, i.e.
A_h = ½·U_v·Δx; background vertical viscosity `rn_avm0 = 1.2e-4` and
diffusivity `rn_avt0 = 1.2e-5`; convective mixing `rn_evd = 100`. How this
port carries each (reviewed 2026-09-09; the runs are in `TODO.md`):

| DINO | Here | Why |
| --- | --- | --- |
| A_h = ½·0.27·Δx | `viscAhDfile` = `viscAhZfile` = `dino_viscAhD.bin` (the reference, and since 2026-09-09 the production setting, with the floor `viscAhReMax=2.` beside it); `dino_viscAhD_2p00.bin` (½·0.54·Δx) was the production setting of the 2× spin-up 30983 | MITgcm has no parameter for a viscosity **linear** in Δx. `viscAhGrid` gives `viscAhGrid·L²/(4Δt)`, ∝ cos²φ on this Mercator grid against the law's cos φ: matched at the domain mean it is 30 % high at mid-domain (`analyses/DINO_1deg/forward/viscosity_binaries_construction.ipynb`). `viscAhReMax` gives \|u\|·L/Re with the *local* speed — state-dependent, so adjoint-active and a different model; Leith and Smagorinsky likewise. So the law stays a `PARM05` field, and the field is now reproducible: `scripts/gen_viscAhD.py` regenerates every `dino_viscAhD*.bin` byte for byte from `input_binaries/tile001.mitgrid` (float32 arithmetic, as the originals). The file is also what the adjoint-mode factor `viscFacInAd` multiplies (see "Run") |
| `rn_avt0 = 1.2e-5` | `diffKrT = diffKrS = 1.2E-5` in `PARM01` (since 2026-09-09; before, `diffKrFile='dino_diffKr.bin'`, a 51×198×36 field of that one constant) | exact: with `ALLOW_3D_DIFFKR` (`code*/CPP_OPTIONS.h`, needed for the `xx_diffkr` control) the 3-D `diffKr` array is initialised from `diffKrNrS(k)` (`model/src/ini_mixing.F`) and only then overwritten by a file, so the two give the same array. 30-day forward and adjoint runs are bitwise identical to their file-based twins (31139 ≡ 31100, 31140 ≡ 31137) and a 1-year restart from year 170 reproduces the spin-up's year 171 (31142, `analyses/DINO_1deg/forward/diffkr_as_parameter_validation_from170yrPk_visc2x.ipynb`). The `kappa_v_ensemble` members carry their κ the same way (`3.E-6` … `3.84E-4`, each an exact power-of-two multiple of the reference, so the double is the one the retired `dino_diffKr_M<n>.bin` held); no namelist reads `dino_diffKr*.bin` any more |
| `rn_avm0 = 1.2e-4` | `viscAr = 1.2E-4` | already a parameter |
| `rn_evd = 100` | `ivdc_kappa = 100.` | already a parameter |

With `diffKrT` set, `ini_parms.F` prints `** WARNING ** INI_PARMS: Ignores
diffKrT (or Kp,Kz) setting in file "data" with ALLOW_3D_DIFFKR` to
`STDERR.0000`. Expected and harmless: under that flag temperature and
salinity share the one `diffKr` array, which is initialised from
`diffKrNrS = diffKrNrT`, so the value is used, through the salinity slot.

### Why the reference viscosity is unstable, and the smallest change that is not (2026-09-09)

The 200-yr spin-up needed twice DINO's viscosity (`visc2x`); the reference
field (`viscRef`) crashed the forward after roughly 180 yr and its adjoints
blow up sooner. No monitor log of a crashed run survives, so the study restarts
the 2× spin-up's mature state under each setting — `input/variants/stability_study/`
(2 yr and 10 yr from year 170) and `input_tap/variants/stability_study/` (30 d
and 183 d adjoints) — and reads the monitor stream and the `ADJ*` dumps;
`analyses/DINO_1deg/stability_study_viscosity_restarts_from170yrPk.ipynb` has
the figures and the READMEs of the two groups the run-by-run tables. What it
found:

- **The doubling acts entirely through the vorticity (Z) part of the
  viscosity.** At the reference viscosity the equatorial western boundary
  current spins up from 0.76 to 1.03 m/s within months (grid Reynolds number
  |u|Δx/A = 7.6; 5.1 in the channel) and the peak kinetic energy doubles;
  doubling only the divergence (D) part changes nothing, doubling only Z
  reproduces the 2× run. The vorticity scheme (`selectVortScheme=2` or 3,
  DINO's EEN), the Jamart Coriolis treatment and a grid biharmonic change the
  peaks by at most 10 %. So it is a question of damping the jets, not of a
  discretisation choice.
- **DINO's closure is a grid-Reynolds-number closure with a fixed velocity
  scale**: A = ½·U_v·Δx with `rn_Uv = 0.27` m/s keeps Re_Δ = 2 for flow at
  that speed and under-damps anything faster. `viscAhReMax=2.` is the same
  criterion with the local speed: a floor A ≥ |u|·Δx/2 that leaves DINO's field
  untouched wherever |u| < 0.27 m/s and raises it only in the jets — in the
  2-yr restart on 0.8 % of the wet points (max 2.5× the reference, in the
  equatorial boundary current), with the peaks held exactly at the 2× level
  and the domain-mean kinetic energy at the reference level, and holds them
  for the whole 10-yr continuation (31164) while the reference run (31161)
  keeps its 1 m/s jets for 10 yr without a flag. Its 30-d adjoint is finite
  with the same growth as the reference run's (31163 vs 31152). This is the
  recommended replacement for the blanket doubling on the forward side, **and
  it is the production configuration since 2026-09-09** together with scheme
  30: the live `input/data` and `input_tap/data` (spin-up 31169). Under that
  configuration the gradient check passes at all five of its points,
  0.0001–0.0035 % (31172), where scheme 33 passed only the strongest at 0.9 %. The
  crash after ~180 yr from rest is not reproducible in short runs: from a
  mature state the reference viscosity gives a narrower margin on a slowly
  intensifying circulation (domain-mean KE +3 % per decade), not a fast
  instability.
- **The adjoint has two separate problems.** GM/Redi, on in the forward
  spin-up and off in every adjoint (see "KPP and GM/Redi" in the root
  `CLAUDE.md`), cannot be switched on in the adjoint sweep (it explodes within
  20 d at the reference viscosity, is marginal at 2×, and still explodes with
  scheme 30 in the adjoint sweep, 31236) but can run in the forward sweep alone
  in the `approxAdv` build (2026-09-11: stable, a better κ_v gradient, no better
  temperature sensitivities; adopted for production the same day, see the stability_study README); and the GM-free
  adjoint's blow-ups (four of the seven kappa members) are episodic bursts with
  1–3-day e-folding seeded at single deep points — the signature the flux
  limiter's adjoint leaves in nearly uniform tracer fields. MITgcm's stock
  cure, `useApproxAdvectionInAdMode`, is inert in the Tapenade build (a
  TAF-only macro in `gad_advection.F`). **Confirmed** by the `M7_lastHalfYr*`
  runs, which reproduce the last 183 d of member M7's blown 5-yr adjoint from
  its own pickup: the control (31166) is byte-identical to 31046 and blows up
  at the same lead (rms `ADJtheta` ×240 between lead 110 and 140 d); with the
  unlimited DST3, `tempAdvScheme=saltAdvScheme=30` in both sweeps (31167),
  there is no blow-up at all and the forward cost moves by 0.45 %; with the
  Reynolds floor alone (31168) the burst is merely halved. So for the adjoint
  the viscosity was never the cure, only a delay: the kappa members that blew
  up were all 2× runs. The change that stabilises the adjoint is scheme 30
  for T and S (what ECCO uses for the same reason), a small change of the
  forward that stays within DINO's family of third-order schemes; the
  adjoint-only variant that would keep the forward at 33 needs a shadow of
  `gad_advection.F` with its guard changed *and* the checkpoint-everything
  build (the tracer-advection routines are in the `-nocheckpoint` list, where
  the forward sweep's taped control flow keeps the limiter) — built and
  validated on 2026-09-10 as `build_tapAdj_approxAdv.sh`, see the next
  subsection.

### Scheme 30 or scheme 33: what the tracer advection scheme does to the forward and to the adjoint (2026-09-10)

Scheme 33 is DST3 with the Sweby flux limiter, monotone and non-linear;
scheme 30 is the same third-order direct-space-time scheme without the
limiter, linear in the tracer, not monotone. DINO itself uses NEMO's FCT
(Zalesak) scheme, a limited one, so 33 is the closer analogue; ECCO v4's
forward model runs scheme 30 (`tempAdvScheme=saltAdvScheme=30`, vertical
scheme 3, in its release-4 `namelist/data`), because its adjoint has to be
smooth. Three things were measured, all from the 2× spin-up's mature state
and all with the reference viscosity + `viscAhReMax=2.`:

- **The unlimited scheme does not deepen the mid-latitude cells; it
  deepens and strengthens the equatorial ones, and slowly weakens the
  AMOC.** One-setting twins, 2 yr from year 170 (31174 vs 31160,
  `input/variants/stability_study/`) and 10 yr (31175 vs 31164): poleward
  of 15° every depth-space overturning cell has the same vertical extent
  under the two schemes (bottom of the upper cell at 2100–2400 m in both,
  scheme 33 one level deeper at 28–47° N after 10 yr) and is weaker under
  scheme 30 — by 0.3–0.6 Sv at 2 yr (4.4 vs 4.8 Sv at 26° N) and 1.1–1.6 Sv
  after 10 yr (2.8 vs 4.4 Sv at 26° N, 5.5 vs 6.8 at 41° N, 4.8 vs 5.9 at
  55° N): the monthly AMOC index declines steadily through the whole decade
  under scheme 30 and only begins to flatten at its end, while the scheme-33
  twin holds level. The two spin-ups from rest tell the same story at equal
  age (`amoc_index_spinups_*` in the figures directory): at year 35 the
  scheme-30 production run 31169 stands at 2.8 Sv at 26° N against 4.9 Sv in
  the scheme-33 2× run 30983 (41° N: 5.6 vs 7.9; 55° N: 5.4 vs 7.1), so a
  scheme-30 spin-up is heading for an AMOC roughly 40 % weaker at 26° N. The
  mixed-layer statistics are identical.
  Within ±10° of the equator the tropical cells are much stronger under
  scheme 30 (21.7–22.5 vs 8.5 Sv at 3° S in the 12-month mean) **and
  deeper**: the counter-clockwise cell north of the equator reaches about
  900 m instead of 300 m (6.9 vs 1.7 Sv at 5° N after 10 yr). If the
  overturning cells were seen to "extend too deep" under scheme 30, this
  equatorial pair is what it was. Behind it is an equatorial thermocline
  0.5–1.1 °C colder through the top 400 m and an upwelling confined to the
  top 150 m instead of 400 m: the limiter, active where the equatorial
  thermocline is sharp and the vertical velocity large, acts as extra
  vertical mixing there, and removing it sharpens the thermocline, cools the
  mean ocean by 0.02 °C over the decade and raises the domain-mean kinetic
  energy by 15 %. Over/undershoots, the classic objection to an unlimited scheme, are
  negligible in this mature state: no salinity cell outside the limited run's
  range, one surface cell per month above its maximum, `salt_min` never below
  35.00. (The 200-yr scheme-30 spin-up 31169 shows the same equatorial
  signature at year 17–18 against the 2× scheme-33 spin-up, with a handful of
  cells below the salinity range at 1000–1200 m.) Which equatorial structure
  is the more realistic one cannot be settled here — it needs DINO's own NEMO
  solution — but "the cells extend too deep" is not what the scheme does at
  this resolution.
- **The scheme-33 cost is not differentiable at the scale of a gradient
  check.** `grdchk_repair/` runs 31177–31179 (30 d, five points, `eps` =
  1e-3 K): the ten perturbed forward integrations are digit-for-digit the
  same whichever adjoint build ran them, and every one of them lands 5–6e-4
  *above* the unperturbed cost for `+eps` and `−eps` alike — a one-signed jump
  of 0.13 % of `fc` that no derivative produces, where the adjoint predicts
  ±4e-5. Under scheme 30 the same perturbations give ±3.7e-5, symmetric, and
  match the adjoint to 1e-6 (31172). So the exact adjoint of scheme 33
  "fails" its own check by 22 % at the strongest point and by factors at the
  others (31178), as it did at 2× viscosity (31037: 0.9 % then 45–318 %),
  only ten times worse in the sharper reference-viscosity state. The
  limiter's branches flip under a 1e-3 K perturbation and the 30-day-mean
  heat transport moves with them (Thuburn & Haine 2001). Scheme 30 is what
  makes the model differentiable at that amplitude; it does not mask an
  instability, it removes a non-smoothness.
- **Scheme 33 forward with scheme 30 in the adjoint sweep works under
  Tapenade** — `code_tap/variants/approxAdvection/` + `build_tapAdj_approxAdv.sh`
  / `submit_tapAdj_approxAdv.sh`, the stock `useApproxAdvectionInAdMode`
  made reachable (its guard is TAF-only, and the implicit vertical advection
  never had the swap). On the M7 restart (31176 against the control 31166 and
  the scheme-30 run 31167): `fc` byte-identical to the control, no blow-up,
  the adjoint fields within 1 % of the scheme-30 run's in rms and correlated
  with them at 0.999 (`adxx_theta`, `adxx_salt`; 0.991 for `adxx_diffkr`).
  The 30-d gradient at the check's strongest point is −3.717e-2 (approximate)
  against −3.835e-2 (exact scheme 33) and −3.735e-2 (exact scheme 30 on its
  own trajectory): the approximation moves the gradient by 3 %, the
  trajectory by 0.5 %. It has to be a checkpoint-everything build (the switch
  is a run-time branch re-evaluated only where the primal is re-run inside
  the backward sweep), so 1.5× the default's reverse-sweep time; with the
  switch off it reproduces the `ckpAll` adjoint to the last digit (31179).

So the choice was between two stable, validated configurations: **scheme 30
in both** (the live `input*/data` from 2026-09-09 to 2026-09-10: exact adjoint of a smooth model, the
default build's speed, ECCO's forward choice; equatorial cells stronger and
deeper, AMOC drifting weaker by ~1.5 Sv per decade relative to 33) and
**scheme 33 forward with the approximate adjoint** (DINO's monotone family,
1.5× slower adjoint, a gradient that is a 3 % approximation and cannot be
finite-difference-verified at all). What is not available is scheme 33 with
an exact, long-stable adjoint. **Decided 2026-09-10: scheme 33 in the forward
model with the approximate adjoint**, because the sensitivity pathways are what
matters and they are set by the realistic trajectory and a well-posed transport
operator; the live `input*/data` carry scheme 33, the live `input_tap/data.autodiff`
the switch, and `build_tapAdj.sh`/`submit_tapAdj.sh` point at the approxAdv pair.
**And one more change the campaign forced the same day: the vertical tracer
advection is explicit** (`tempImplVertAdv = saltImplVertAdv = .FALSE.` in the
live `input*/data`, the MITgcm default; this setup had run it implicitly since
its import). Two of the seven kappa-ensemble legs under the new configuration
(8× and 16×, runs 31191 and 31193) blew up within two years with no
precursor in any diagnostic: the pressure-solver residual goes from 2 to 1e31
in three time steps. The crash is deterministic (31198 reproduces it to the
step), and a restart six steps before it with a snapshot every step (31199)
shows the temperature of one channel cell at 1200 m, 53° S, jumping by 110 K
in a single step while salinity and the velocities stay normal: the column is
convectively homogenised (five levels identical to four decimals), the
flux-limiter ratios of the *implicit* DST3 vertical solve (`gad_dst3fl_impl_r`)
degenerate there, and the unpivoted pentadiagonal solve returns a ±100 K
checkerboard. Strong vertical diffusion makes such columns common, which is
why the high-kappa members found it first; the 2× campaign of 2026-08 never
did, by luck. Both cures pass the crash step and the day that follows: the
explicit vertical advection (31200; the vertical CFL here is below 0.05, and
DINO's own FCT scheme is explicit) and the linear third-order upwind scheme
kept implicit (31201, ECCO's vertical choice). Production takes the first,
which keeps the vertical scheme limited and monotone; run 31202 is the 8×
member's full 10-yr leg with it. Every run of the campaign was resubmitted
under the corrected namelists: spin-up 31203 (200 yr from rest), the
reference leg 31205 (10 yr from the year-170 pickup — 31164 ran with the
implicit form, so it is no longer the reference state) with the production
adjoint 31206 chained on it, the chained adjoint 31204 on the spin-up
(cancelled on 2026-09-11, when GM/Redi in the adjoint's forward sweep was
adopted; its replacement is on the `TODO.md`), and
the kappa ensemble 31207–31220; the runs made with the implicit form that
morning (31180–31196) were cancelled and deleted. The spin-up completed on
2026-09-11 (200 yr in 31 h 39 min, no incident; filed under
`runs/forward/spinup_200yr_viscRef_ReMax2/`, analysed against the 2× spin-up
in `analyses/DINO_1deg/forward/spinup_200yr_from_rest_viscRef_ReMax2.ipynb`):
its overturning is 0.3–0.5 Sv stronger than the 2× run's at 26/41/55° N with
the same history and vertical extent, its tropical cell a third and its deep
cell half of the 2× run's (the Reynolds floor acts in the equatorial band, the
only place the two differ), its tracers inside the forcing range with none of
the 2× run's monthly salinity spikes above 37.0. The ensemble's year-180 state
(the reference leg 31205) is 0.40 K rms from the spin-up's own year 180 and
keeps the 2× state's thick tropical thermocline; the DINO `TODO.md` entry has
the numbers. The production adjoint from the spin-up's own year 180, still to
run, will show what that does to the pathways.

Nothing else in `PARM05` can move to a parameter. Bathymetry, wind, restoring
targets and shortwave are analytic functions in DINO (paper, Sects. 2–3), but
MITgcm has no parameter form for any of them (`dino_utau.bin` and
`dino_S_star.bin` are even constant in time — 365 identical daily records —
and still need to be files); `dino_T0/S0/U0/V0.bin` are a spun-up 3-D state
with non-zero velocities, not a profile, so `tRef`/`sRef` cannot replace them.

## Reading the code

### Where the adjoint actually happens

Four files matter more than the rest when following how a sensitivity is produced:

| File | Role |
| --- | --- |
| `code_tap/the_main_loop.F` | **The differentiation head.** `genmake2` runs `tapenade -b -head 'the_main_loop(fc)/(xx_genarr3d_dummy, xx_genarr2d_dummy, xx_gentim2d_dummy)'` — the cost `fc` is differentiated with respect to those control dummies, so everything reachable from this routine is what gets an adjoint |
| `code_tap/cost_atlantic_heat.F` | **The cost function** `fc`: meridional heat transport across a zonal section. Section indices are compiled in as `parameter` statements, so moving the section means editing this file and rebuilding |
| `../../mods_tapenade_hooks/dummy_tap.F` | **Where `ADJ*` output is written.** The hand-written `DUMMY_IN_STEPPING_XYZ_RL_B` and its three siblings — one per field shape, each a halo fold followed by `CALL DUMP_ADJ_*(..., 'ADJtheta', ...)` over its adjoint argument — produce the files the analysis notebooks read; `DUMMY_FOR_ETAN_TAP_B` in the same file writes `ADJetan`. Each signature must match the call Tapenade generates; the build body asserts this |
| `../../mods_tapenade_hooks/forward_step.F`, `dummy_in_stepping_tap.F` and `flow_tap` | **How the dump calls get generated.** The shadowed `forward_step.F` calls `DUMMY_IN_STEPPING_TAP`, a wrapper Tapenade differentiates, which calls one external per output field; the directory's `flow_tap` declares each field argument read-then-written (active), so Tapenade emits the `_B` call of every active field in the reverse sweep — TAF's `ADNAME` directive has no Tapenade equivalent, and this activity-through-arguments design replaced the old hand-patched `forward_step_b.f_modified` |

### How the Tapenade hooks work — a shared `-mods` directory

Everything Tapenade-specific is delivered **without touching the vendored
`MITgcm/` tree**, and since 2026-09-07 the hooks are not in this setup at all:
they are the seven files of `MITgcm_c69m/mods_tapenade_hooks/`, one directory
shared by DINO and SOMA that the build body (`tools/lib/build_body.sh`) lists
first in `-mods` for every adjoint build. That directory is, file for file,
the proposal for including the mechanism in MITgcm itself. Its `README.md`
maps each file to its place in the tree and says what kind of change it is
(a new file, or an existing file with lines added), and its
`check_against_tree.sh` verifies that shape and generates the patch series
in `patches/`. Read that README first; what follows is the setup's side.

**The problem being solved.** MITgcm's `ADJ*` dumps and its adjoint-mode
parameter switching hang off no-op forward hooks (`DUMMY_IN_STEPPING`,
`DUMMY_FOR_ETAN`, `AUTODIFF_INADMODE_SET/UNSET`). Under TAF, `.flow` directives
(`ADNAME`/`REQUIRED`) force hand-written adjoints of those hooks into the
reverse sweep even though no active data crosses their 3-passive-scalar
interfaces. Tapenade has no such directive — its `-ext` library is purely
data-flow driven, and `tools/TAP_support/flow_tap` declares those hooks
passive, so Tapenade drops them from the backward sweep entirely. The fix:
add, beside each hook, a Tapenade counterpart with **active arguments**, so
that the reverse-sweep call is generated by Tapenade itself, from data flow
alone.

**The mechanism, step by step** (the build body wires it identically for
every adjoint definition of every setup; stock `genmake2` and the tree's
stock `adjoint_tap` options throughout):

1. **The shared directory comes first in `-mods`.** `genmake2` links a file
   from an earlier `-mods` directory ahead of a same-named file anywhere
   later, so the directory's four shadows (`forward_step.F`,
   `integr_continuity.F`, `stubs_tap_adj.F`, `dummy_tap.F`) replace their tree
   counterparts at build time, and its three new files
   (`dummy_in_stepping_tap.F`, `tapenade_ad_diff.list`, `flow_tap`) simply
   join the build. Each shadow carries the tree file's name and is the tree
   file plus added lines — with two exceptions, `stubs_tap_adj.F`, whose five
   `ADEXCH_*` stubs are replaced by implementations, and `dummy_tap.F`, whose
   four empty stubs are removed — and the tree file is never edited. The upstream hooks and their TAF adjoints (`dummy_in_stepping.F`,
   `addummy_in_stepping.F`, ...) compile untouched from the vendored tree;
   under Tapenade the TAF adjoints are dead code, as in the tree's own
   Tapenade verification builds.
2. **The wrapper is differentiated.** `genmake2` reads `*_ad_diff.list` from
   every source directory, `-mods` included, so the one-line
   `tapenade_ad_diff.list` sends `dummy_in_stepping_tap.F` to Tapenade. That
   wrapper, called beside `DUMMY_IN_STEPPING` from the shadowed
   `forward_step.F`, makes one call per output field to an external hook
   (`DUMMY_IN_STEPPING_XYZ_RL(theta, 'ADJtheta', 'ADJtheta.', ...)` and so
   on); `DUMMY_FOR_ETAN_TAP(etaN, ...)` is called beside `DUMMY_FOR_ETAN` in
   the shadowed `integr_continuity.F`, and `AUTODIFF_INADMODE_UNSET_TAP` /
   `SET_TAP(etaN, ...)` beside the stock mode switches at the start and end
   of the step. `etaN` is only the active vehicle in the switches; its
   adjoint is not touched.
3. **The activity declaration reaches Tapenade as a second `-ext`.** The
   directory's `flow_tap` is the tree's file plus seven stanzas declaring
   those externals with their field arguments read-then-written. The build
   body appends `-ext <directory>/flow_tap` to `-tap_extra`, so Tapenade
   reads it beside the stock file that the stock options file passes. The
   hook stanzas carry new names, so the two files do not conflict and the
   order on the command line no longer matters (until 2026-09-07 the setup
   re-declared the stock names, which forced its library to come last and
   needed a setup-local `-adof` file; Tapenade keeps the last declaration of
   an external).
4. **Tapenade does the rest.** Seeing active data enter and leave each hook,
   it generates the `_B` call of every active field hook in
   `dummy_in_stepping_tap_b.f` (as a split-mode `_FWD`/`_BWD` pair, because
   the call site carries `C$AD NOCHECKPOINT`, so each field is stored once
   per step), `DUMMY_FOR_ETAN_TAP_B(etaN, etaNb, ...)` in
   `integr_continuity_b.f`, and the two mode switches in `forward_step_b.f`,
   each at the exact reverse-sweep mirror of its forward call: the dumps
   where TAF's ADNAME directives insert theirs, the mode switches at each
   backward step's start (apply `inAd*`) and end (restore the forward
   parameters, so checkpoint re-forwards always run forward physics). A
   field that is passive in a configuration loses its call entirely — which
   is why there is one hook per field rather than one hook carrying eleven,
   whose generated call would have a configuration-dependent argument list.
5. **Hand-written bodies resolve at link time.** They are the 37 routines
   of `dummy_tap.F`, in place of the tree's four empty stubs (unreachable,
   since `flow_tap` declares the stock hooks read-only and Tapenade never
   calls their derivatives; removed 2026-09-07): for each
   external the forward no-op, the `_B` (halo
   fold with the `ADEXCH_*` of `stubs_tap_adj.F`, then `DUMP_ADJ_*`; the
   switches call the TAF-named `ADAUTODIFF_INADMODE_SET`/`UNSET`, so the
   parameter logic is not duplicated), the `_D` (the `G_J*` tangent output)
   and the `_FWD`/`_BWD` pair. The adjoint state reaches them as arguments,
   so no `adcommon.h` mirror exists. The file must include `AD_CONFIG.h`, the
   only definition of `ALLOW_ADJOINT_RUN`, which guards the dump bodies:
   without it they preprocess to nothing and the adjoint runs correctly but
   writes no `ADJ*` files.
6. **Build-time assertions guard the interface.** F77 checks no signatures,
   so a drift between a generated call and its hand-written routine would
   silently misalign arguments. After `make` the build body counts each
   generated call's arguments (`check_gen_call`, over `HOOK_CHECKS` in
   `scripts/setup_params.sh`: a scalar field hook 7, a vector pair 11, the
   etaN dump and the mode switches 5), checks that the compiled
   `dummy_tap.f` carries its five `DUMP_ADJ_*` calls (`DUMP_CALLS`,
   `DUMP_FILE`), and checks that the compiled hook sources link into the
   shared directory and that the Makefile's `TAP_EXTRA` carries its
   `flow_tap`. Changing a hook's argument list means touching the hook, its
   bodies, its `flow_tap` stanza *and* the `HOOK_CHECKS` entry together.

**History.** From 2026-08-31 to 2026-09-02 the hooks had Tapenade-only names
(`TAP_DUMMY_IN_STEPPING`, ...). From 2026-09-02 to 2026-09-07 they kept the
upstream names and widened the upstream hooks' argument lists under
`#ifdef ALLOW_TAPENADE`, as ten shadow files in this `code_tap/` (seven in
SOMA's), validated bitwise against the earlier layout at 30 days, 5 days
(SOMA) and 5 years (31077 vs 31055; see `TODO.md`). That layout could not go
upstream: with one 25-argument adjoint it matched only configurations in
which all eleven fields are active. The per-field design was developed in
the in-tree study of 2026-09-05 (next paragraph) and moved into the shared
directory on 2026-09-07; the last shadow-file state is the `main` commit
before that change, and the validation runs of the move are in `TODO.md`.

**The same mechanism from inside the tree.** To find out whether the
mechanism can become an upstream change, it was integrated into a git copy of
checkpoint69m outside this repository — `~/MITgcm_c69m_tapenade_hooks/MITgcm`,
branch `tapenade-hooks`, four commits on the `checkpoint69m` tag, with the
verification results and the write-up beside it (copy of the write-up in the
project notes, `references/tapenade_hooks/in_tree_integration_20260905.md`).
`scripts/build_tapAdj_hooksInTree.sh` builds this setup against that tree
with the shared directory left out (`HOOKS_MODS` empty), after asserting that
the tree's seven hook files are byte-identical to the directory's; run 31107
reproduced the default build's run 31101 bitwise (`fc`, 32 `adxx_*`, 73
`ADJ*`, 441 `%MON` lines, `tools/compare_adj_runs.sh`). Non-Tapenade builds
of that tree preprocess to byte-identical sources, and its eight Tapenade
verification experiments give the same testreport digits as the pristine
tree. The vendored tree stays pristine; the `MITGCM_TREE` variable of the
build body is what points a build elsewhere.

**Reviewing with vimdiff.** The hook files are meant to be read as diffs
against the tree files they shadow or join;
`../../mods_tapenade_hooks/check_against_tree.sh` does that mechanically, and
its `patches/` are the diffs themselves. What is left in this setup to review
the same way is the adjoint-viscosity variant:

| Setup file | Upstream counterpart (vimdiff target) | What the diff shows, and why |
| --- | --- | --- |
| `code_tap/variants/adjointViscosity/autodiff_inadmode_set_ad.F` | `../../MITgcm/pkg/autodiff/autodiff_inadmode_set_ad.F` | Upstream body + the ASTE-derived `inAd*` apply block (`viscArNr`, `viscAhGrid`, `diffKh*`, … declared in the `AUTODIFF_PARAMS.h` beside it). Compiled only by `build_tapAdj_adjVisc.sh`; a plain build uses the vendored file, unshadowed |
| `code_tap/variants/adjointViscosity/autodiff_inadmode_unset_ad.F` | `../../MITgcm/pkg/autodiff/autodiff_inadmode_unset_ad.F` | Upstream body + the `outAd*` restore block — this half never existed anywhere before (it was unreachable dead code territory), so expect no ASTE original to diff against |
| `code_tap/the_main_loop.F` | `../../MITgcm/model/src/the_main_loop.F` | Only the `C$AD BINOMIAL-CKP nTimeSteps+1 98 1` directive and its comment before the time loop, plus a canary in the non-adjoint branch. The tree has no such directive; it is a setup choice (memory), not part of the hooks proposal |

Two reading rules: every file carries its real MITgcm name and is the only
copy of itself — the variant shadows sit in `code_tap/variants/adjointViscosity/`
rather than as suffixed siblings (the staged-copy layout ended 2026-09-02);
and the artefacts of the pre-redesign mechanism are gone on purpose
(`forward_step_b.f_modified*` deleted — no generated file is post-edited any
more; `adcommon.h` archived in `00_archive/code_tap/` — its upstream twin
`pkg/autodiff/adcommon.h` still serves the TAF path).

### `code_tap/` — adjoint source overrides

Every file here is compiled as-is under its real MITgcm name; no build script
copies anything into this directory (since 2026-09-02), so a build leaves
`git status` clean. Since 2026-09-07 nothing here is about the hooks: what
remains is the configuration of this setup. `variants/adjointViscosity/` is a
further `-mods` directory that `build_tapAdj_adjVisc.sh` lists ahead of
`code_tap/`; its README explains. The 2026-09-02 relocation reproduces the
previous layout's runs bit for bit (31069 vs 31054 for the default build,
31070 vs 31025 for the boost; see `TODO.md`).

| File | Purpose |
| --- | --- |
| `the_main_loop.F` | differentiation head, see above; the shadow of `model/src/the_main_loop.F` whose only addition is the binomial checkpointing directive for the time loop |
| `cost_atlantic_heat.F` | the cost function |
| `tap_nocheckpoint.txt` | the routines `build_tapAdj_nocheckpoint.sh` (the default) passes to Tapenade's `-nocheckpoint` — `build_tapAdj_adjVisc.sh` deliberately does not (see "Profiling and checkpoint tuning") (split `_FWD`/`_BWD` mode instead of checkpointing), each annotated with the profiling-run gain that put it there — see "Profiling and checkpoint tuning" below |
| `variants/adjointViscosity/` | (named `adjVisc/` until 2026-09-04; the build script, build directory and run token keep the old tag on purpose, because scratch run directories record it) the four ASTE-derived shadows of `pkg/autodiff` (`AUTODIFF_PARAMS.h`, `autodiff_readparms.F`, `autodiff_inadmode_set_ad.F`, `autodiff_inadmode_unset_ad.F`) that declare, read, apply and restore the `inAd*`/`outAd*` parameters; compiled only by `build_tapAdj_adjVisc.sh`, as its first `-mods` directory — see the README inside. A plain build compiles the vendored files |
| `variants/approxAdvection/` | (since 2026-09-09) shadows of `pkg/generic_advdiff/gad_advection.F` (the `useApproxAdvectionInAdMode` block's CPP guard widened from `ALLOW_AUTODIFF_TAMC`, TAF only, to `ALLOW_AUTODIFF`) and `gad_implicit_r.F` (the same scheme swap added for the implicit vertical advection, which the vendored file never covered); compiled only by `build_tapAdj_approxAdv.sh`, as its first `-mods` directory — see the README inside |
| `SIZE.h` | grid and decomposition (`nPx=3, nPy=9` over `sNx=17, sNy=22`); the one and only copy |
| `CTRL_SIZE.h` | control-vector dimensions |
| `DIAGNOSTICS_SIZE.h` | diagnostics buffer sizes |
| `packages.conf` | which packages compile — drops `cd_code`, adds `tapenade` and the `adjoint` group (`autodiff, ctrl, cost, grdchk`) |
| `*_OPTIONS.h` | CPP flags per package, each the upstream c69m header with only `#define`/`#undef` toggles changed (vimdiff-clean). `COST_OPTIONS.h` is the one to check: it defines `ALLOW_COST_ATLANTIC_HEAT` and `..._DOMASS` |

**The `ADEXCH_*` implementations moved with the hooks.** Upstream ships the
five adjoint halo exchanges as no-ops; the hook adjoints call them to fold
tile-halo adjoint contributions back into the owning interior cells before
each `ADJ*` dump, and as no-ops they left 1–2-cell stripes of partial sums
pinned to every exchange seam — the internal tile edges (`i=17|18`, `34|35`;
every `j` multiple of 22) and the zonal periodic seam of the re-entrant
channel (`i∈{1,2,50,51}`, `j≈13–44`), worst on U-grid fields. The
implementation, with the same `EXCH2_*_CUBE_AD` routines the adjoint dynamics
already uses, was this setup's `code_tap/stubs_tap_adj.F` from 2026-08-31 to
2026-09-07 and is now `mods_tapenade_hooks/stubs_tap_adj.F`, the first of the
two patches there. The dynamics never called the stubs, so this changes
*only* the dumps: validated 2026-08-31 (run 31022 vs 30994), `fc` and all 33
`adxx_*` files bitwise identical, `ADJ*` differences confined to the seams.
**`ADJ*` output written before job 31022 still carries the artifact** — treat
values within ~2 cells of those seams as unreliable in older runs; their
`adxx_*` and `fc` are fine.

### `input_tap/` — adjoint namelists

Beyond the forward set, the adjoint adds four:

| Namelist | Controls |
| --- | --- |
| `data.cost` | `mult_atl` — scales the cost function |
| `data.ctrl` | which controls are optimised (`xx_theta`, `xx_salt`, `xx_diffkr`, wind stress, heat and freshwater flux) and their weight files — every `xx_*_weight` points at `ones_64b.bin` |
| `data.autodiff` | checkpointing and adjoint-mode behaviour; `data.autodiff_adjointViscosity` is the inflated-viscosity variant, and a `data.autodiff` sibling with `useApproxAdvectionInAdMode=.TRUE.` (the `*_approxAdv*` tags) is what switches the `approxAdv` build's adjoint sweep to scheme 30 |
| `data.grdchk` | the finite-difference gradient check: `grdchk_eps`, `grdchkvarname`, and the `iGloPos/jGloPos/kGloPos` point to perturb |

Variants are selected by `test_cases` in a submit script as `<group>/<tag>`; see
**Namelists and variants** above for the grouping rules and the root `README.md`
for the `<start>_<viscosity>` vocabulary.

### `code/` and `input/` — the forward model

Much smaller: `SIZE.h`, `packages.conf`, `CPP_OPTIONS.h`, `DIAGNOSTICS_SIZE.h`,
`GMREDI_OPTIONS.h`, `MOM_COMMON_OPTIONS.h`.
`input/` holds `data` and the standard `data.pkg`, `data.diagnostics`,
`data.exch2`; its alternatives live in `input/variants/<group>/`.

---

The cost function is `code_tap/cost_atlantic_heat.F`, with its section indices
compiled in as `parameter` statements (`isecbeg=1, isecend=51, jsec=127`,
`kmaxdepth=25`). Moving the section means editing that file and rebuilding — it is
not a namelist setting. Indices are located with
`analyses/DINO_1deg/grid_and_cost_sections.ipynb`.

Two verified subtleties of what `fc` actually measures (2026-08-30; full
statement in the root `CLAUDE.md` and in
`analyses/DINO_1deg/adjoint/kappa_v_ensemble/ensemble_common.py`):
`pkg/cost` averages only the **final 30 days** of the run (`lastinterval`
default, not overridden in `data.cost`), and the per-level wet-count
normalisation is computed **per MPI tile**, so `fc` depends on the domain
decomposition — comparable across runs only at fixed `nPx`/`nPy`.

`useGrdchk = .FALSE.` in `input_tap/data.pkg` since 2026-08-28 (verified
bit-identical `ADJ*`/`adxx*` output; saves 8.2 h per 5-yr adjoint). It had been
`.TRUE.`, and with it on every adjoint job also ran the finite-difference
gradient check — a 30-day adjoint recorded 18,622 forward-step calls against
the 1,440 the adjoint itself needs. `SOMA_1deg` still runs with it on.

**The check does not currently verify anything.** It perturbs `xx_theta` at
`iGloPos=4, jGloPos=8, kGloPos=1`, but the cost section is at `j=127` and
sensitivity at the check point is ~6e-10 against a field maximum of ~3.9e-02. The
finite difference measures run-to-run noise, not the perturbation, and fails by
~8 orders of magnitude. It has always done so. To make it meaningful use
`iGloPos=2, jGloPos=127, kGloPos=26` with `grdchk_eps` around 1e-3. See
"Verification status" in the root `README.md`.

KPP is off (`input_tap/data.pkg`), which makes `useKPPinAdMode` in
`data.autodiff` inert. GM/Redi is on in the forward sweep since 2026-09-11
(`useGMRedi=.TRUE.` with the spin-up's `data.gmredi`) and kept out of the
adjoint sweep by `useGMRediInAdMode=.FALSE.`, which is therefore live; only the
`approxAdv` and `ckpAll` builds may run it, and the submit body refuses the
`-nocheckpoint` builds.
