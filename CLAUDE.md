# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

MITgcm adjoint-sensitivity experiments built with the **Tapenade** AD toolchain (`pkg/tapenade`) instead of TAF/OpenAD. It contains experiment configurations, build/SLURM scripts, and analysis notebooks — plus a **fully vendored MITgcm source tree** (byte-for-byte upstream since 2026-08-31). Model output is not here; it lives on cluster scratch.

`README.md` documents the science and the layout; each setup has its own `README.md` (grid, build/submit pairings, quirks); `analyses/README.md` indexes the notebooks; `PORTING.md` covers other clusters. This file covers the mechanics that only become clear from reading several scripts at once.

**The project notes are a separate repository.** `notes/` — the planning documents for work underway and proposed, and the write-ups of workflows that have already run — was split out on 2026-09-04 into `impacts-notes`, which is private; this repository is the one shared with collaborators. The two are checked out as siblings under `Proj_ImPACTS/`. Nothing here reads from it, and no build, submit or notebook path crosses between them, so a reference to "the project notes" in any document here is a pointer to context, never a dependency. Anything a reader of this repository actually needs is stated here.

`./tools/pre_push_check.sh` is the one standing check in this repository: a read-only
pre-push sanity check covering the nbstrip filter, submit-script namelist churn,
stray images under `analyses/`, the shape of `mods_tapenade_hooks/`, the
variant copies of tree files against the tree they were derived from
(`tools/check_variant_shadows.sh`), and notebook scratch paths that no longer
resolve. Exits non-zero only on real breakage. Run
it before concluding a tree is clean — `git status` alone does not distinguish a
change the user authored from one a build or submit script made.

There is no root build system, no linter, and no package manifest, and nothing that tests the Fortran or the notebooks — that check covers tooling only. (Until 2026-09-04 there was a second one, `overleaf_sync_selftest.sh`; it went to the `impacts-notes` repository with the Overleaf sync tool it tests.) Fortran is built per-setup via `genmake2` + `make`; Python analysis happens in notebooks with no checked-in environment file (`numpy`, `xarray`, `xmitgcm`, `matplotlib`).

## Layout

- `MITgcm_c69m/` — checkpoint69m tree (`MITgcm/`) + setups under `mysetups/`
- `analyses/` — notebooks reading run output from `/scratch2/...`, split `DINO_1deg/` + `SOMA_1deg/` to match the setup names
- `tools/lib/` — the two shared script bodies, `build_body.sh` and `submit_body.sh` (since 2026-09-05). Every build and submit script in every setup is a short definition in that setup's `scripts/` directory that sources one of these; the per-setup constants they need are in `scripts/setup_params.sh`. See "Scripts are definitions, the bodies are shared" under Build.
- `MITgcm_c69m/mods_tapenade_hooks/` — the Tapenade output hooks (the `ADJ*`, `ADJetan` and `G_J*` dumps and the adjoint-mode switches) as one `-mods` directory shared by every adjoint build of both setups (since 2026-09-07), and at the same time the upstream proposal, file for file: four tree files with lines added, each under the tree file's own name, three new files, a README mapping each to its place in the tree, `check_against_tree.sh` and the generated `patches/`. The build body lists it first in `-mods` and hands its `flow_tap` to Tapenade as a second `-ext`. See "The ADJ* dump hook" under Build.
- `00_archive/` — frozen reference copies, at tree level (`MITgcm_c69m/00_archive/`) and setup level (inside each of `DINO_1deg/` and `SOMA_1deg/`). **Every archive mirrors the path its contents came from**, so `00_archive/code_tap/X` means "X, which was or would be `code_tap/X`", and `MITgcm_c69m/00_archive/removed_from_MITgcm/pkg/tapenade/` holds what was pulled out of the vendored `MITgcm/pkg/tapenade/`. Each has its own `README.md` giving what/where-from/why-not-live per file — read that before assuming anything here is revivable. The tree-level archive is empty since 2026-08-31: its one resident, `pkg/tapenade/dummy_tap.F`, went back into the vendored tree when the hook redesign removed the symbol collision that had forced it out. Nothing here is live configuration; no build or submit script reads from it. Grep hits inside these directories are history, not current behaviour. The `00_` prefix exists to keep them sorted above `build*/` and `code*/` in a plain `ls`.

The primary configuration is `MITgcm_c69m/mysetups/DINO_1deg/` (DINO, 51 × 198 × 36 curvilinear). `MITgcm_c69m/mysetups/SOMA_1deg/` is the secondary. `MITgcm_c69m/mysetups/barotropic_gyre/` (since 2026-09-07) is a small demonstration setup, MITgcm's tutorial gyre with temperature as a passive tracer and a box-mean temperature cost, serial, built with the same shared hooks directory; its README says how it differs (its own `cost_test.F` under the tree's name, `ALLOW_SRCG` off, per-tile pickup names, a yearly permanent pickup).

**The checkpoint69f tree is no longer in this repository.** `MITgcm_c69f/` — the c69f source tree, the earlier DINO and `sr_soma` ports, and the `tutorial_*_with_adj` / `tutorial_global_oce_biogeo` test-bed setups — was removed on 2026-08-17 because work has moved entirely to c69m. It survives in full, working tree and history both, as its own repository, `Proj_ImPACTS_old`. Its GitHub remote (`git@github.com:tsgonerog/Proj_ImPACTS_old.git`) no longer answered on 2026-09-11, so the working clone kept on the author's machine is the copy to use; ask for it rather than trying to reconstruct the tree. Several things documented below (Tapenade profiling, the tutorial cross-checks against `code_ad`/`code_oad`) exist only there.

**The vendored `MITgcm/` tree is byte-for-byte upstream since 2026-08-31** (see the next section) — but treat it as read-only: everything project-specific belongs in the setups' `-mods` directories or `tools/`, never as edits inside `MITgcm/`.

### How the vendored tree deviates — none since 2026-08-31

A reference copy of the c69m tree sits outside the repo at `~/tools_and_software/MITgcm_collections/MITgcm_c69m/MITgcm/`. **Since 2026-08-31 the deviation set is empty — the vendored tree is byte-for-byte upstream.** The hook redesign (see "The ADJ* dump hook" below) removed both former deviations: the added `tools/genmake2_override_forward_step_b` was deleted when SOMA converted to the Tapenade-native hooks (no build post-edits generated code any more), and the removed `pkg/tapenade/dummy_tap.F` was restored verbatim once the hook redesign eliminated the symbol collision that had forced it out (from 2026-09-02 to 2026-09-07 both setups shadowed it from `code_tap/dummy_tap.F`; since 2026-09-07 the shadow is `MITgcm_c69m/mods_tapenade_hooks/dummy_tap.F`, the vendored file with its four unreachable stubs removed and the hook bodies added, so the vendored copy is pristine and never compiled).

Everything this project supplies is kept *outside* the vendored tree on purpose — the `-mods` directories (the shared `mods_tapenade_hooks/` and the setups' `code_tap/`) shadow sources at build time, the Perlmutter optfile lives in `tools/optfile_templates/` rather than `MITgcm/tools/build_options/`, and the hooks' `flow_tap` reaches Tapenade as a second `-ext` through `-tap_extra`. Re-verify with the commands below rather than trusting this statement; any output from any of the three checks now means an unintended deviation.

### Building writes into the source tree

`genmake2` expands ~210 type-specialised sources from `.template` files **in place, under `MITgcm/`** — not into the build directory — as its first step, before configuring anything (`tools/genmake2:2374` for `eesupp/src`, `:2391` for `pkg/exch2` + `pkg/regrid`, `:2571` for `pkg/mnc`). Each is one `sed 's/RX/RL/g' exch_xy_rx.template > exch_xy_rl.F` per type, per `eesupp/src/Makefile`.

Consequences:

- **A built tree is not a pristine tree.** `eesupp/src/`, `pkg/exch2/`, `pkg/regrid/`, `pkg/mnc/` gain `*_r4`/`*_r8`/`*_rl`/`*_rs` files (~2.1 MB) the moment you first build.
- **They never reach git.** All 210 are ignored by MITgcm's *own* upstream `.gitignore`, which lists them because they are build products. A fresh clone has none; the first build creates them. Nothing to clean up, and deleting them only means `make` regenerates them byte-identically.
- **They make a naive `diff -qr` useless** — they drown the two real deviations in ~210 "Only in" lines. Filtering by extension does not work either: it hides `dummy_tap.F` and leaks `pkg/mnc/MNC_ID_HEADER.h`. The reliable filter is `git check-ignore`, since every build product is covered by MITgcm's own `.gitignore`.

Run from the repo root, and re-verify the table above rather than trusting it:

```bash
GT=~/tools_and_software/MITgcm_collections/MITgcm_c69m/MITgcm

# 1. modified upstream files — MUST be empty
diff -qr "$GT/" MITgcm_c69m/MITgcm/ | grep '^Files '

# 2. removed from the tree
diff -qr "$GT/" MITgcm_c69m/MITgcm/ | grep "^Only in $GT"

# 3. added, excluding build products
diff -qr "$GT/" MITgcm_c69m/MITgcm/ \
  | sed -n 's|^Only in \(MITgcm_c69m[^:]*\): |\1/|p' \
  | xargs -r -n1 sh -c 'git check-ignore -q "$0" || echo "$0"'
```

Any output from (1) means someone edited an upstream source; output from (2) or (3) means a file was removed from or added to the tree — nothing here is supposed to do either any more.

## Machines

`tools/machine_env.sh` is the single place cluster differences live; `PORTING.md`
is the walkthrough. Two blockers are worth knowing before assuming a new machine
will work: **Tapenade is not in this repository** (`genmake2 -tap` calls a
`tapenade` binary on `$PATH`, a Java tool installed out-of-tree), and
`input_binaries/` is untracked — DINO's 179 MB of `dino_*.bin` is produced
outside this repo and, except for `dino_viscAhD*.bin` (regenerated byte for
byte by `DINO_1deg/scripts/gen_viscAhD.py` since 2026-09-09), nothing
regenerates it; `dino_diffKr*.bin` are no longer read, the namelists set
`diffKrT`/`diffKrS` instead. `impacts_check_env` warns about both plus a
missing `NERSC_ACCOUNT`.

The 200-year spin-up's `-t 240:00:00` exceeds every Perlmutter QOS and would need
a pickup/restart chain; that is not automated.

## Build

Each setup builds itself. **Since 2026-09-05 every build and submit script lives in the setup's `scripts/` directory, and each is a short *definition* — what to build or run — that sources a shared *body* from `tools/lib/`** (`build_body.sh`, `submit_body.sh`), which does the work identically for every variant of every setup; the per-setup constants the bodies need (time step, duration key, calendar, generated-hook list, run-naming rule) sit in `scripts/setup_params.sh`. A build definition `cd`s to its own setup, so it can be run from anywhere; the conventional form is from the setup directory:

```bash
cd MITgcm_c69m/mysetups/DINO_1deg
./scripts/build_frd.sh           # -> build_frd/mitgcmuv
./scripts/build_tapAdj.sh        # -> build_tapAdj_nocheckpoint/mitgcmuv_tap_adj (a symlink: see below)
```

Both setups name scripts action-first (`build_*`, `submit_*`), and the `rawTapenade` control builds are retired in both — raw Tapenade output *is* the working configuration. **In DINO, since 2026-09-02, `scripts/build_tapAdj.sh` and `scripts/submit_tapAdj.sh` are symlinks** to `build_tapAdj_nocheckpoint.sh` / `submit_tapAdj_nocheckpoint.sh` beside them, the default adjoint; every real DINO adjoint script carries a token saying what it builds:

| DINO pair (build / submit) | Build directory | What |
| --- | --- | --- |
| `build_tapAdj.sh` → `_approxAdv`, `submit_tapAdj.sh` → `_approxAdv` | `build_tapAdj_approxAdv/` | **the default since 2026-09-10** (was `_nocheckpoint` from 2026-09-02): symlinks, repointed when the default changes |
| `build_tapAdj_nocheckpoint.sh` / `submit_tapAdj_nocheckpoint.sh` | `build_tapAdj_nocheckpoint/` | profile-guided `-nocheckpoint` list (33 routines in split mode); bitwise identical to `ckpAll`, 1.5× faster. **The default from 2026-09-02 to 2026-09-10**; with the live `input_tap/data.autodiff` it silently runs the exact, blow-up-prone adjoint of scheme 33 (the switch is inert in split mode), so pair it with a scheme-30 namelist or use it as a deliberate exact-adjoint control; since 2026-09-11 the submit body also refuses it with the live GM-in-forward-sweep namelist, whose GM switch split mode applies to only half of the recomputation |
| `build_tapAdj_ckpAll.sh` / `submit_tapAdj_ckpAll.sh` | `build_tapAdj_ckpAll/` | the reference: every call checkpointed (Tapenade's default). **Was `build_tapAdj.sh` / `build_tapAdj/` until 2026-09-02** — every run up to job 31055 that is not named `nocheckpoint`/`tapProfile`/`adjViscBoost` came from it. Kept as the profiler's base, the fallback if a configuration change invalidates the list, and the timing baseline; not needed as a correctness control |
| `build_tapAdj_adjVisc.sh` / `submit_tapAdj_adjVisc.sh` | `build_tapAdj_adjVisc/` | `ckpAll` **plus** the ASTE `inAd*` sources, compiled from `code_tap/variants/adjointViscosity/` as a second `-mods` directory. Deliberately without the list: under the boost, split mode changes the adjoint at order one (run 31056 vs 31025, 2026-09-02 — see the `adjVisc` bullet under "Run") |
| `build_tapAdj_approxAdv.sh` / `submit_tapAdj_approxAdv.sh` | `build_tapAdj_approxAdv/` | **the default since 2026-09-10.** `ckpAll` **plus** `code_tap/variants/approxAdvection/` as a second `-mods` directory (since 2026-09-09): `gad_advection.F` with the `useApproxAdvectionInAdMode` block's guard widened from `ALLOW_AUTODIFF_TAMC` to `ALLOW_AUTODIFF`, and `gad_implicit_r.F` with the same swap for the implicit vertical advection. Scheme 33 in the forward sweep, scheme 30 in the adjoint sweep when `data.autodiff` sets the switch; deliberately without the `-nocheckpoint` list, because the switch is a run-time branch that only a joint-mode re-run re-evaluates (the list splits `gad_advection` and the DST3 flux routines). With the switch off it reproduces the `ckpAll` adjoint digit for digit (31179 vs 31178) |
| `build_tapAdj_profile.sh` / `submit_tapAdj_profile.sh` | `build_tapAdj_profile/` | diagnostic: `ckpAll` + Tapenade's `-profile` (deliberately without the list, so the profile sees every checkpoint) |
| `build_tapAdj_hooksInTree.sh` / `submit_tapAdj_hooksInTree.sh` | `build_tapAdj_hooksInTree/` | validation of the **in-tree** form of the hooks (2026-09-05, simplified 2026-09-07): builds against `$HOME/MITgcm_c69m_tapenade_hooks/MITgcm` (a git copy of checkpoint69m + 4 commits on branch `tapenade-hooks`, whose hook files the definition asserts byte-identical to `mods_tapenade_hooks/`; `IMPACTS_HOOKS_TREE` overrides the path) with the shared directory left out (`HOOKS_MODS=""`) and the default `-nocheckpoint` list; run 31107 bitwise identical to 31101. The only build whose `build_info.txt` carries `mitgcm_root=`; `MITGCM_TREE` in the definition is what repoints the build body |

SOMA's `build_tapAdj.sh` / `submit_tapAdj.sh` are real files and still checkpoint every call — no SOMA profile exists yet — so the bare name means different things in the two setups (SOMA's run token is nevertheless `tapAdj_ckpAll`, the same vocabulary, so a tuned SOMA build can be told apart by name when one exists). Optfiles come from `tools/machine_env.sh`, so nothing needs exporting. The build body does the same steps in the same order for every definition, and never copies anything into `code/` or `code_tap/` (since 2026-09-02 a build leaves the working tree clean): `make CLEAN`, run **stock** `genmake2` with the definition's `-mods` list and, for an adjoint, `MITgcm_c69m/mods_tapenade_hooks/` put first in that list, `-tap`, the tree's stock `-adof` and its `TAP_EXTRA` string with `-ext` of the shared directory's `flow_tap` appended (the `_nocheckpoint` definition's `pre_configure` reads `code_tap/tap_nocheckpoint.txt` into `-tap_extra "-nocheckpoint \"<list>\""`, the profiler's sets `-tap_extra "-profile"`; the `adjVisc` definition lists `../code_tap/variants/adjointViscosity` ahead of `../code_tap` and its `post_build_checks` asserts the compiled `autodiff_*.f` came from the variant), `make depend`, `make -j 8 [tap_adj]`, assert every generated hook call's argument count (`check_gen_call`, over the `HOOK_CHECKS` list in `scripts/setup_params.sh` — the same seven hooks in both setups since 2026-09-07), the five `ADJ*` dump calls in the compiled `dummy_tap.f` and that the hook sources link into the shared directory, and — last, so it can only describe a verified executable — write `build_info.txt` into the build directory (script, `TAP_EXTRA`, the list, commit, `exe_md5`, and a `run_token` such as `tapAdj_ckpAll_adjVisc`; since 2026-09-05 forward builds write one too, with `run_token=frd`). The submit body refuses an executable that has no record, whose checksum does not match the record's `exe_md5` (since 2026-09-03; the earlier mtime test fired spuriously on the NFS home and survives only as the fallback for records without that line), or whose `run_token` is not the one the submit definition names in `EXPECT_RUN_TOKEN` (since 2026-09-05 the build/submit pairing is enforced, not just documented), copies the record into the run directory, and takes the run directory's name from `run_token` (see "Where the output lands").

### Scripts are definitions, the bodies are shared (since 2026-09-05)

Until 2026-09-05 the ten DINO scripts sat at the setup's top level and the eight adjoint ones were near-copies of two templates (270 of ~282 submit lines and 101 of ~150 build lines shared with the `ckpAll` copy); the 2026-09-03 checksum-guard fix had to be made in all eight, and the same comment block had already drifted between two of them. Now:

- **`scripts/` holds one definition per build or run, under the old names**, plus the two DINO default symlinks (`build_tapAdj.sh`, `submit_tapAdj.sh`, relative targets in the same directory). A build definition sets `SETUP_DIR`, `BUILD_DIR`, `BUILD_MODE` (`frd`/`tapAdj`), `PARALLEL` (`mpi`/`serial`), `MODS` (relative to the build directory, first wins), `TAP_EXTRA`, `RUN_TOKEN`, optionally `MITGCM_TREE` (build against another MITgcm tree, recorded as `mitgcm_root=`; since 2026-09-05), `HOOKS_MODS` (the shared hooks directory relative to the build directory; default `../../../mods_tapenade_hooks`, empty for a tree that carries the hooks; since 2026-09-07) and the `build_info.txt` notes, may define `pre_configure`, `post_build_checks` and `build_info_extra`, and ends with `source "$SETUP_DIR/../../../tools/lib/build_body.sh"`. A submit definition carries the `#SBATCH` header (directives cannot be sourced, which is why one file per variant is the right shape), `BUILD_DIR`, `RUN_MODE`, `PARALLEL`, `EXPECT_RUN_TOKEN`, the committed defaults (`test_cases`, `duration_days`, the `*Freq_days`, the explicit `TIME_PARAMS` list), may define `stage_extra` (the boost's `data.autodiff` swap), `stage_pickups` (the hardcoded `ln -s` lines) and `post_run` (the profiler's table echo), and ends with `source "$SLURM_SUBMIT_DIR/../../../tools/lib/submit_body.sh"`. The header comment of each definition still says why that variant exists.
- **`scripts/setup_params.sh` is what makes a setup different**: `DELTA_T`, `DURATION_KEY` (`nTimeSteps` in DINO, `endTime` in SOMA), `DAYS_PER_YEAR` (366 / 360), `HOOK_CHECKS`, `DUMP_CALLS`, and DINO's `run_suffix_from_namelist` (the `<start>_<viscosity>` derivation for an empty tag; SOMA defines none, so its live-namelist runs stay named by duration alone).
- **`tools/lib/build_body.sh` and `submit_body.sh` are libraries**: no execute bit, and each refuses to run unless sourced. The build body is invoked from the setup directory it computes; the submit body anchors everything on `SLURM_SUBMIT_DIR` and refuses a directory without `scripts/setup_params.sh`.
- **`tools/submit.sh` runs sbatch from the setup directory**, the parent of `scripts/`, passing `scripts/submit_x.sh` as the script: that is what `SLURM_SUBMIT_DIR`, the `#SBATCH -o logs/%x.%j.out` path and the body's `source` line resolve against. `sbatch scripts/submit_x.sh` from the setup directory is equivalent on sverdrup; `cd scripts && sbatch submit_x.sh` is not, and fails at the `source` line.
- **The submit body is read at job start, not at submission.** sbatch spools only the definition; the body, like `machine_env.sh`, the namelists and the build directory, is read from the repository when the job starts, so an edit to it reaches every queued job. Cancel and resubmit rather than assuming a queued job is frozen. The `set -x` log under `logs/` records what actually ran.
- **Run-directory contents are unchanged** (staged namelists, binaries, executable, `build_info.txt`, `run_timing.txt`, model output), so `tools/compare_adj_runs.sh` needs no change and pre- and post-refactor runs compare cleanly; the 2026-09-05 validation (all seven builds rebuilt, one run each against a reference from the previous scripts) is recorded in the DINO `TODO.md`.

The old shape is still readable in git before 2026-09-05; nothing was renamed, only moved and shortened, so every script name in older reports and run records still refers to the same thing.

**Parallelism is a property of the setup, not a flag you pass.** Only the build scripts that exist are usable: DINO is MPI-only throughout; SOMA's adjoint is serial-only while its forward model (`build_frd.sh`/`submit_frd.sh`, restored 2026-08-31) is MPI over 4 ranks (`code/SIZE.h`, `nPx=nPy=2`). Each source directory carries exactly one `SIZE.h` (since 2026-09-02; the unused `SIZE.h_mpi`/`SIZE.h_serial` siblings are gone and nothing selects a decomposition): DINO's `code/SIZE.h` and `code_tap/SIZE.h` are the 27-rank decomposition, SOMA's `code_tap/SIZE.h` is the single serial tile.

Build directories (`build*/`) are gitignored and fully reproducible. They are **not relocatable**: `genmake2` bakes the setup's absolute path into the generated `Makefile` (~23 references), so renaming or moving a setup directory invalidates any build inside it. Re-run the build script rather than trying to patch the `Makefile`. The 2026-09-04 move of this repository to `Proj_ImPACTS/impacts-mitgcm/` did exactly that to all seven build directories; they were rebuilt from the new path, and the rebuild was validated by run 31091 against 31074 (default build, 30 d from the 180-yr pickup): 210 of 210 `ADJ*`/`adxx_*` files, `fc` and all 441 `%MON` lines identical.

### Variants are directories, not staged copies (since 2026-09-02)

**No build script copies anything into `code/` or `code_tap/`.** Until 2026-09-02 every build overwrote tracked files with suffixed siblings (`SIZE.h_mpi -> SIZE.h`, `AUTODIFF_PARAMS.h_OG -> AUTODIFF_PARAMS.h`, `_aste_90x150x60` / `_adapted_frm_aste_90x150x60` for the boost), so a build dirtied the tree, the bare file was whatever the last build staged, and building a second variant silently repointed every earlier build directory's symlinks. All of that is gone; git history holds the old layout. What replaced it:

- `SIZE.h` is the one tracked decomposition per source directory. Nothing selects it.
- `AUTODIFF_PARAMS.h` and `autodiff_readparms.F` are no longer in `code_tap/` at all: their `_OG` copies were byte-identical to the vendored `pkg/autodiff/` files, so the plain builds compile upstream directly.
- The `AUTODIFF_INADMODE_SET_TAP_B`/`UNSET_TAP_B` wrappers (and `_D` no-ops) live in `mods_tapenade_hooks/dummy_tap.F` with the other hook adjoints (in `code_tap/dummy_tap.F` until 2026-09-07), so the plain builds do not shadow `autodiff_inadmode_{set,unset}_ad.F` either.
- **A variant is a second `-mods` directory.** `code_tap/variants/adjointViscosity/` holds the four ASTE-derived shadows under their real MITgcm names (`AUTODIFF_PARAMS.h`, `autodiff_readparms.F`, `autodiff_inadmode_set_ad.F`, `autodiff_inadmode_unset_ad.F`) plus a README; `build_tapAdj_adjVisc.sh` passes `-mods="../code_tap/variants/adjointViscosity ../code_tap"`. `genmake2` gives a file in an earlier `-mods` directory preference over a same-named file anywhere later (`genmake2:79-83`), and it enumerates only `*.F *.h *.c *.flow *.F90` directly inside each directory (`genmake2:2952`), so the plain builds never see `variants/`. The build script then asserts that the compiled `autodiff_*.f` really came from the variant. This mirrors `input_tap/variants/adjointViscosity/`, the namelist half of the same configuration, and is the pattern `build_tapAdj_profile.sh` already used for `tools/tapenade_profiling/mods_profile/`. **Both halves were renamed from `adjViscBoost/` on 2026-09-04**, that having been an internal coinage nobody outside this project reads, and **the build identity followed on 2026-09-05**: the script, the build directory and the `run_token` are now `adjVisc`, so one word covers the variant end to end. Because the new tag is a truncation of the old one, `*adjVisc*` still matches the scratch run directories written before the rename, which keep `adjViscBoost` in their names — as does every `build_info.txt` already written. The job ID stays the durable key. The 2026-09-04 rename left `build_tapAdj_adjViscBoost/` with dangling `-mods` symlinks; it was rebuilt, and run 31090 against 31075 (boost, 30 d from rest) is bitwise identical in every `ADJ*`/`adxx_*` file, `fc` and `%MON` line. Inside the variant directory the files carry no suffix because the compiler, not a script, resolves them; the directory name is the tag.
- **Every copy of a tree file in a variant directory names its origin** (since 2026-09-12). `TREE_BASE.txt` beside the copies lists, for each, the tree file it shadows and the git blob of that file it was derived from; `tools/check_variant_shadows.sh`, run by `tools/pre_push_check.sh`, fails when a tree file changes under its copy, when a copy is not listed, or when a copy has become identical to the tree. A checkpoint upgrade therefore cannot silently compile the old checkpoint's text through a variant: re-derive the copy, then `--record <dir>`; `--tree=<newer tree>` shows beforehand which copies an upgrade would invalidate. `tools/tapenade_profiling/mods_profile/` carries a manifest too.

So: edit the file under its MITgcm name in the directory that owns it; a build never rewrites a tracked file; and if `git status` shows a change after a build, something regressed. The only suffixed source left anywhere is the archived `00_archive/code_tap/the_model_main.F_ForTapProfile` (the c69f-era profiling main program; the live profiling build shadows `the_model_main.F` from `tools/tapenade_profiling/mods_profile/` instead).

### Build directories symlink back into `code_tap/`

`genmake2` symlinks the sources it takes from `-mods` directories into the build
directory (`build_x/forward_step.F -> ../code_tap/forward_step.F`; for the boost,
`build_tapAdj_adjVisc/AUTODIFF_PARAMS.h -> ../code_tap/variants/adjointViscosity/AUTODIFF_PARAMS.h`)
rather than copying them. Only files written into the build directory itself —
the preprocessed `.f` and Tapenade's generated `*_b.f` — are real files, frozen
at compile time, and they are the reliable evidence of what a build actually
used: to check what a build compiled against, diff its generated `.f` (e.g.
`autodiff_readparms.f`), not its symlinked `.h`. Since no build rewrites
`code_tap/`, building one variant leaves every other build directory's links
valid; an edit to a source in `code_tap/` reaches every build directory through
those links, so after editing re-run the build script of each build you intend
to use rather than `make` in one of them.

### The ADJ* dump hook — Tapenade-native in both setups

The `ADJ*` sensitivity dumps exist because TAF's `.flow` directives (`ADNAME`/`REQUIRED`) can force a hand-written adjoint routine into the reverse sweep even though the hook `DUMMY_IN_STEPPING(myTime,myIter,myThid)` carries no active data. Tapenade has no such directive — its `-ext` library is purely data-flow driven, so a passive external is simply dropped from the backward sweep. Both setups bridge that gap the same way since 2026-08-31 (DINO first, SOMA later the same day):

**Both setups, one shared directory since 2026-09-07: the hooks are `MITgcm_c69m/mods_tapenade_hooks/`, a `-mods` directory that is also the upstream proposal.** The pattern covers the `ADJ*` dump (a wrapper `DUMMY_IN_STEPPING_TAP` called beside `DUMMY_IN_STEPPING`), the `ADJetan` dump (`DUMMY_FOR_ETAN_TAP` beside `DUMMY_FOR_ETAN` in `INTEGR_CONTINUITY`, a separate hook because the free-surface adjoint is half a time step out of phase with the rest) and the two adjoint-mode switches (`AUTODIFF_INADMODE_SET_TAP`/`UNSET_TAP` beside the stock switches; their `_B` bodies call the TAF-named `ADAUTODIFF_INADMODE_SET`/`UNSET`, which apply/revert the `inAd*` adjVisc parameters at the start/end of every backward step and were dead code under Tapenade before 2026-08-31, so adjVisc never actually boosted). The directory's seven files, every one under the name it has or would have in the tree:

- `forward_step.F` and `integr_continuity.F` — shadows of the `model/src` files whose only change is the added calls under `#ifdef ALLOW_TAPENADE` beside the stock three-argument hook calls, which stay (`C$AD NOCHECKPOINT` precedes the wrapper call, so each field is stored once per step). `etaN` in the mode switches is only the activity vehicle that forces `_B` generation.
- `dummy_in_stepping_tap.F` — new, and the one file Tapenade differentiates (listed by the new one-line `tapenade_ad_diff.list`, which genmake2 reads from a `-mods` directory like any package list): one call per output field to an external hook (`DUMMY_IN_STEPPING_XYZ_RL(theta, 'ADJtheta', 'ADJtheta.', …)` and its `XY_RS`, `UV_XYZ_RL`, `UV_XY_RS` siblings), with the field set and guards of `ADDUMMY_IN_STEPPING`. **One field per call is what makes the design upstreamable**: Tapenade omits the derivative of an argument that is passive at the call site, so a hook carrying eleven fields would be called with a configuration-dependent number of arguments (the 2026-09-02 layout's single 25-argument `DUMMY_IN_STEPPING_B` matched only configurations with all eleven active); with one field, a passive field loses its call and an active one is always passed with its derivative.
- `flow_tap` — the tree's Tapenade external library plus seven stanzas declaring those externals with the field argument(s) read-then-written. The build body hands it to Tapenade as a **second** `-ext` through `-tap_extra`, beside the stock file the stock `adjoint_tap` passes; the hook names are new, so the two files do not conflict and order is immaterial (the old setup-local `adjoint_tap_local` `-adof` file existed only because the previous layout re-declared the stock names, which then had to come last: Tapenade keeps the last declaration of an external). Tapenade emits the `_B` call of every active field hook in `dummy_in_stepping_tap_b.f` (as a split `_FWD`/`_BWD` pair), `DUMMY_FOR_ETAN_TAP_B(etaN, etaNb, …)` in `integr_continuity_b.f` and the switches in `forward_step_b.f`, each at the reverse-sweep mirror of its forward call.
- `dummy_tap.F` — shadow of the `pkg/tapenade` file: the tree's opening include kept, its four empty stubs (`DUMMY_IN_STEPPING_B`/`_D`, `DUMMY_FOR_ETAN_B`/`_D`) removed, and the hand-written bodies in their place, 37 routines (for each of the seven externals the forward no-op, `_B`, `_D`, `_FWD`, `_BWD`, plus two helpers). **The stubs were unreachable** (checked and removed 2026-09-07, a few hours after the move, which had kept them verbatim): `flow_tap` declares the two stock hooks with every argument read-only, so Tapenade generates no call to a derivative of either in either mode — no generated file of the seven adjoint builds here or of the study's 18 verification builds (adjoint and tangent-linear) names them, and no object file has an undefined reference to them; TAF builds never compile `pkg/tapenade` and forward builds never compile the file. Their argument lists are what Tapenade emits for a hook that has no `flow_tap` stanza at all with `myTime` active (`DUMMY_FOR_ETAN_B(myTime, myTimeb, myIter, myThid)`, verified on a toy caller), a trace of development before the stanzas existed; the three-argument `DUMMY_IN_STEPPING_B` matches no call Tapenade produces. The `_B` of a field hook ADEXCH-folds its adjoint argument and dumps it with `DUMP_ADJ_*`; `DUMMY_FOR_ETAN_TAP_B` dumps `etaNb` with the separate `dumpAdRecEt` counter and no fold, like upstream. The adjoint state arrives as arguments, so there is no `adcommon.h` mirror to keep in sync (the old one is archived in DINO's `00_archive/code_tap/`). The file must include `AD_CONFIG.h`, the only definition of `ALLOW_ADJOINT_RUN`; without it the adjoint is bit-correct but writes no `ADJ*` files.
- `stubs_tap_adj.F` — shadow of the `pkg/tapenade` file with the five `ADEXCH_*` stubs implemented (the seam fix of 2026-08-31, see below); one of the two files that remove lines from their tree counterpart (the other is `dummy_tap.F`), and the first of the two patches.

`check_against_tree.sh` in that directory verifies the shape (new file, or tree file plus added lines; `stubs_tap_adj.F` and `dummy_tap.F` are the two declared exceptions that also remove lines), regenerates `patches/` and checks that they apply to the vendored tree (`git apply --check`); `tools/pre_push_check.sh` runs its `--check` form. The four `pkg/autodiff` hooks and their TAF adjoints (`addummy_in_stepping.F`, `addummy_for_etan.F`) compile untouched from the vendored tree, as dead code under Tapenade, exactly as in an upstream Tapenade verification build. A stock verification experiment can use the directory through a `genmake_local` in its `build/` (`MODS="../code_tap <dir>"`, `TAP_EXTRA="-ext <dir>/flow_tap"`; genmake2 reads it after the command line) — never leave one in the vendored tree, upstream un-ignores that file.

Each generated `_B` call has a fixed argument count (a scalar field hook 7, a vector pair 11, the etaN dump and the mode switches 5) that **must match what Tapenade generates** — F77 would silently misalign a mismatch, so the build body counts each generated call's arguments after `make` (`check_gen_call`, over `HOOK_CHECKS` in `scripts/setup_params.sh`, the same seven entries in DINO and SOMA), checks that the compiled `dummy_tap.f` still carries the five `ADJ*` dump calls (`DUMP_CALLS`), and checks that the compiled hook sources link into the shared directory and that the Makefile's `TAP_EXTRA` carries its `flow_tap`. Changing a hook's argument list means touching the hook, its bodies, its `flow_tap` stanza *and* the assertion. The `rawTapenade` control builds are retired in both setups — raw Tapenade output *is* the working configuration now, and no generated file is post-edited.

**History: from 2026-09-02 to 2026-09-07 the same mechanism was ten shadow files in DINO's `code_tap/` (seven in SOMA's)** that widened the argument lists of the four upstream hooks under `#ifdef ALLOW_TAPENADE` and filled the `dummy_tap.F` stubs with one 25-argument `DUMMY_IN_STEPPING_B`; the per-field design came from the in-tree study of 2026-09-05 (`~/MITgcm_c69m_tapenade_hooks/`, branch `tapenade-hooks`, four commits since the stub removal; DINO run 31107 against 31101 bitwise; eight upstream adjoint and six tangent-linear experiments identical between the pristine and the modified tree) and moved into the shared directory on 2026-09-07, validated bitwise against the previous layout (the DINO `TODO.md` entry of that date has the runs). From 2026-08-31 to 2026-09-02 the hooks had Tapenade-only names (`TAP_DUMMY_IN_STEPPING`, …).

**History: DINO got the hooks on 2026-08-31, SOMA the same day, and the SOMA conversion was a rescue.** SOMA's `the_main_loop.F` was rebased from a c69f-era copy onto c69m upstream in the process — which restored upstream's `COST_DRIVER` call, a runtime no-op here (it only drives OBCS/ECCO cost terms, both absent). The conversion **fixed SOMA's c69m adjoint, which had never actually run**: the old frozen `forward_step_b.f_modified` had gone stale against the evolving tree (274 diff lines vs freshly generated code), misaligning Tapenade's tape enough to crash every adjoint at the backward-sweep start (`integer divide by zero` in `pkg/longstep` — runs 31029/31030). The hook build's run 31031 is the first successful c69m SOMA adjoint: `fc` bitwise-identical to the crashed baseline's forward value, full `ADJ*`/`adxx_*` output, finite. With the conversion, `genmake2_override_forward_step_b` and the frozen file were deleted and `pkg/tapenade/dummy_tap.F` restored — the vendored tree is pristine.

### Tapenade profiling and `-nocheckpoint` — wired in and validated (DINO, 2026-09-01)

Both live in DINO as ordinary build/submit pairs, driven by `genmake2 -tap_extra` (passed straight to the Tapenade command line, `genmake2:1568`, rule at `:3751`); `tools/tapenade_profiling/README.md` is the full write-up and `analyses/DINO_1deg/adjoint/tapenade_profiling/` holds the profile, the ranked table, the comparison reports and the two scripts that produced them.

| Pair | What it is |
| --- | --- |
| `build_tapAdj_profile.sh` / `submit_tapAdj_profile.sh` | **diagnostic.** `-tap_extra "-profile"` plus a second `-mods` directory, `tools/tapenade_profiling/mods_profile/`, listed *first* so its two files shadow: `adProfile.c`/`.h` (verbatim from the installed Tapenade's ADFirstAidKit — c69m vendors an older, API-incompatible copy and does not compile it) and a `the_model_main.F` (upstream + additive `ALLOW_TAPENADE` block) that writes `tapenade_profile.NNNN.txt` per MPI process after `THE_MAIN_LOOP_B`. Defaults to 30 days; the adjoint is the plain one plus timing calls (2 % slower), so never use it for runtime comparisons. |
| `build_tapAdj_nocheckpoint.sh` / `submit_tapAdj_nocheckpoint.sh` | **the default adjoint since 2026-09-02** (`build_tapAdj.sh` / `submit_tapAdj.sh` are symlinks to this pair; the checkpoint-everything build lives on as `build_tapAdj_ckpAll.sh`). `-tap_extra "-nocheckpoint \"<list>\""`, the list read from `code_tap/tap_nocheckpoint.txt` (33 routines, each annotated with the gain that put it there). Tapenade differentiates those in split `_FWD`/`_BWD` mode instead of checkpointing them; the build fails unless every listed name produced a `_FWD` routine, so the list cannot silently drift. |

What the profile said (run 31053, 30 d, rank 0, 809 s of adjoint): checkpointing costs 363 s of CPU per process — 45 % of the run — spread over 156 call sites / 116 callees, and almost all of it in routines whose split mode is *memory-neutral or a memory gain* (`timestep` 75 s and −31 MB, `forward_step` 71 s, `grad_sigma` 37 s, `mom_vecinv` 22 s, `calc_phi_hyd` 21 s and −8.6 MB, `thermodynamics` 18 s, …); the entries that do cost memory sum to ~54 MB against a 923 MB peak tape per process. The per-level routines dominate because joint-mode Tapenade snapshots whole 3-D arrays on each per-level call. **Validation (30 d, same node): run 31054 vs plain 31052 — `fc` identical, all 32 `adxx_*` and all 73 `ADJ*` files bitwise identical, wall time 8:47 vs 13:13 (1.50×, −33.5 %).** At 5 years (31055 vs 31039): again bitwise identical (`fc`, 32 `adxx_*`, 4 393 `ADJ*`), 9:35:58 vs 14:05:45 (1.47×, 4.5 h saved; forward sweep unchanged at 0.84 h, reverse sweep 8.76 vs 13.24 h = 1.51×). On the full κ_v ensemble (2026-09-02/03, jobs 31060–31067 vs 31039–31046): all eight 5-yr adjoints bitwise identical — `fc`, 32 `adxx_*`, 4 393 `ADJ*` and the `%MON` stream per pair, the four blown-up members included — at 1.45–1.65× per run (reverse sweep 1.54×, forward sweep unchanged), 37.8 h saved over the eight; report in `analyses/DINO_1deg/adjoint/tapenade_profiling/compare_5yr_kappa_ensemble_ckpAll_vs_nocheckpoint.md`. The c69f-era 64-routine list (`tools/tapenade_profiling/nocheckpoint_routines.txt`) shares only 8 routines with the new one and none of the top twelve; under this profile it would have recovered 21 s of the 363 s — re-profiling was not optional.

What is **not** touched: the time loop's `C$AD BINOMIAL-CKP nTimeSteps+1 98 1` in `code_tap/the_main_loop.F` (Griewank–Walther binomial checkpointing over `MAIN_DO_LOOP`, 98 step snapshots; the profile lists that site at 11.3 GB peak cost, i.e. the whole run's tape) — `-nocheckpoint` acts only inside a step, which is why a 30-day run validates it for any length. Externals (`cg2d`, `exch2_rl1_cube`, the hook externals) cannot be split; the two Tapenade options are hidden from `tapenade -help` but accepted (`@@ Options: split(...)` / `profile` on stderr confirms). The `use_TapProfile` switch is gone from every build script and both `code_tap/the_model_main.F` copies (`_OG` was byte-identical to upstream) were deleted from DINO and SOMA — the vendored `model/src/the_model_main.F` is compiled, as it always effectively was; the c69f `_ForTapProfile` variant survives only in `00_archive/code_tap/`, and the c69f `genmake2` copies in `tools/tapenade_profiling/c69f_originals/` must never be installed into `MITgcm/tools/`.

## Run

SLURM batch scripts targeting the **`sverdrup`** cluster:

```bash
cd MITgcm_c69m/mysetups/DINO_1deg
../../../tools/submit.sh scripts/submit_frd.sh        # forward, committed default
../../../tools/submit.sh scripts/submit_tapAdj.sh     # adjoint, committed default (DINO: symlink to submit_tapAdj_approxAdv.sh since 2026-09-10)

# per-run overrides; these leave the working tree clean
IMPACTS_DURATION_DAYS=73200 ../../../tools/submit.sh scripts/submit_frd.sh   # 200 yr
```

A submit definition carries the `#SBATCH` header, the committed defaults and its pickup lines; the shared submit body then selects a namelist via `test_cases`; rewrites time-stepping parameters; stages a job-ID-stamped run directory under `$SCRATCH_ROOT/<setup>_outputs/runs/{forward,adjoint}/`, copying `input*/` and symlinking the gitignored `input_binaries/` (and, for an adjoint, `input_adj_binaries/`); symlinks any pickups; then runs the executable and writes `run_timing.txt`.

Things to know before editing or submitting one:

- **`-n` must match `SIZE.h`.** The MPI DINO adjoint requests 27 ranks because `code_tap/SIZE.h` sets `nPx=3, nPy=9` over `sNx=17, sNy=22` tiles. Changing the decomposition means changing both.
- **Durations are written in days at the top of the script** (`duration_days`, `monitorFreq_days`, `adjMonitorFreq_days`, `adjDumpFreq_days` — the same names in both setups since 2026-09-05; `scripts/setup_params.sh` says whether the duration lands on `nTimeSteps` at `DELTA_T` (DINO) or on `endTime` (SOMA)). The frequency names to patch are listed explicitly in a `TIME_PARAMS` array beside them. **Do not restore the old `compgen -v | grep '_days$'` auto-detection** — `compgen -v` also enumerates *exported environment variables*, and since sbatch forwards the environment by default, any `*_days` variable in the submitting shell would silently become a namelist key.
- **Submitting a job no longer modifies the repo.** The `sed -i` runs *after* the namelist is staged and targets the copy in the run directory, so `git status` stays clean. This is a correctness fix, not just hygiene: the script body executes on the compute node when the job **starts**, not when you submit, so the old in-place `sed` was shared mutable state between every queued job — two jobs starting close together would each stage whichever value landed last while their run-directory names each claimed their own. It bit SOMA hardest, back when its five (now archived) per-duration scripts all patched the same `input_tap/data`. If a namelist diff ever appears after a run, something has regressed; `tools/pre_push_check.sh` watches for it.
- **Per-run overrides go in the environment, not in an edit.** Every live submit script in both setups reads `IMPACTS_TEST_CASE`, `IMPACTS_DURATION_DAYS`, `IMPACTS_MONITOR_FREQ_DAYS` and (adjoint only) `IMPACTS_ADJ_MONITOR_FREQ_DAYS` / `IMPACTS_ADJ_DUMP_FREQ_DAYS`, defaulting to the committed values, so `IMPACTS_DURATION_DAYS=73200 ../../../tools/submit.sh scripts/submit_frd.sh` runs 200 years without touching a tracked file. `IMPACTS_TEST_CASE` uses `${VAR-default}` rather than `${VAR:-default}` so that an explicit empty value selects the live `input*/data`. In DINO the duration patches `nTimeSteps` (dT 1800); in SOMA it patches `endTime` (dT 1200). SOMA joined this scheme on 2026-08-31 — its five pre-made per-duration scripts are archived in `SOMA_1deg/00_archive/scripts/`; a duration is now a submission, not a script. The committed defaults are the cheap regression configurations, not the production ones (SOMA's adjoint default, 5 d with 1-d frequencies, reproduces validated baseline run 31031).
- **`IMPACTS_PICKUP_RUN_DIR` and `IMPACTS_PICKUP_ITER` (since 2026-09-09) repoint the DINO adjoint scripts' pickup** without a script copy: `stage_pickups` in `submit_tapAdj_nocheckpoint.sh` and `submit_tapAdj_ckpAll.sh` links `$IMPACTS_PICKUP_RUN_DIR/pickup.<IMPACTS_PICKUP_ITER>.{data,meta}`, defaulting to the spin-up's `pickup.0003162240` — the two lines that were hard-coded before. The selected namelist's `nIter0` must still equal the iteration; a kappa member's own pickup or a mid-window restart of an adjoint run (which keeps monthly pickups, `pChkptFreq` in `input_tap/data`) are the two uses so far.
- **`nIter0` is *not* one of the auto-patched parameters — the start iteration and the pickup are coupled by hand.** `nIter0` is baked into whichever `data_<tag>` the `test_cases` string selects (`from_rest` → `0`, `from50yrPk` → `878400`, `from70yrPk` → `1229760`, `from180yrPk` → `3162240`), while the pickup itself is a hardcoded `ln -s` line further down the same script. Changing `test_cases` to a different `from*Pk` tag without editing that symlink to the matching `pickup.<nIter0>.{data,meta}` gets you a run that cannot find its pickup. Changing the duration is safe; changing the starting point is not.
- **The adjoint-mode viscosity configuration is a build *and* a namelist variant, not just a build.** Its two source directories are `code_tap/variants/adjointViscosity/` and `input_tap/variants/adjointViscosity/`; its build identity — `build_tapAdj_adjVisc.sh`, `build_tapAdj_adjVisc/`, `run_token=tapAdj_ckpAll_adjVisc` — is the same word shortened, since 2026-09-05 (see the variant bullet above). It runs the adjoint with larger viscosity/diffusivity than the forward (`viscFacInAd = 10.` vs `viscFacInFw = 1.`), intended to keep a long adjoint from blowing up. **Before the 2026-08-31 mode-switch hooks it was inert under Tapenade**: the only routine applying those parameters (`ADAUTODIFF_INADMODE_SET`) is TAF-named and was never called, so every earlier "adjVisc" configuration silently ran plain physics. The boost engages only in builds carrying the Tapenade mode-switch hooks (`AUTODIFF_INADMODE_SET/UNSET`, named `TAP_INADMODE_*` until 2026-09-02; see "The ADJ* dump hook" above). Validated 2026-08-31: with hooks + default parameters, run 31024 reproduces 31023 bitwise; with hooks + the adjVisc pairing, run 31025 vs plain 31026 (same from-rest config) keeps `fc` bit-identical (the boost never touches the forward trajectory) while every nonzero `adxx_*`/`ADJ*` differs and peak sensitivities are damped — the first functioning adjVisc run in this project. `submit_tapAdj_adjVisc.sh` points `build_dir` at `build_tapAdj_adjVisc/` and additionally does `rm data.autodiff` + `cp "$base_dir/input_tap/variants/adjointViscosity/data.autodiff_adjointViscosity" data.autodiff` in the staged run directory (a copy from `variants/`, not a `mv` of an already-staged file). Pairing the plain submit script with the adjVisc build (or the reverse) silently runs a mismatched configuration. **The adjVisc build does not carry the default `-nocheckpoint` list, on purpose.** Tried 2026-09-02: run 31056 (boost + list, 30 d from rest) vs 31025 (boost, every call checkpointed) — `fc` and all 441 `%MON` lines byte-identical, but all 66 `ADJ*` dumps and all 8 real `adxx_*` gradients differ at order one (RMS ratio 0.3–0.9), whereas the plain pair is bitwise identical under the same list. In joint mode Tapenade re-runs each routine's primal inside the backward sweep *after* `AUTODIFF_INADMODE_SET_B` has boosted the viscosities, so the boost reaches every recomputed intermediate; in split mode those intermediates were taped during the forward sweep at forward viscosities and the boost reaches only what the `_BWD` code reads live — a weaker, different regularisation. So the boosted adjoint stays a `ckpAll` build (run token `tapAdj_ckpAll_adjVisc`, 13 min per 30 d instead of 9), and 31056 stays on scratch as the record; report in `analyses/DINO_1deg/adjoint/tapenade_profiling/compare_30d_adjViscBoost_run31025_vs_nocheckpoint_run31056.md`. Corollary: `-nocheckpoint` is a pure performance change only for an adjoint whose backward sweep leaves the primal's parameters alone. **What the switches reach, and a stale-value fix (2026-09-09):** the stock `viscFacInAd` multiplies *only* the `PARM05` `viscAh[D/Z]file` fields (`mom_calc_visc.F:509-511`) — a scalar `viscAh` or `viscAhGrid` is never multiplied, so the file-based viscosity is what makes the boost reachable, and it preserves DINO's A_h ∝ Δx structure; the ASTE `inAdviscAhGrid` term is added in `MOM_CALC_VISC`, which runs only because the files set `useVariableVisc` at init (`set_parms.F:132`); `inAdviscA4Grid` is inert (`useBiharmonicVisc` fixed `.FALSE.` at init); `inAdviscArNr` acts; no `inAd*` scalar can reach the vertical diffusivity, which under `ALLOW_3D_DIFFKR` is the 3-D `diffKr` array. The `outAd*` values are what every checkpoint replay of the forward runs with after the first backward step and must equal the forward namelist's: until 2026-09-09 `outAdviscAhGrid=1.8E-2` (a `viscGrid1p8e-2` study value; production sets none) and `outAddiffKhT/S=0` (forward 500) were stale, so every boosted run up to 31138 replayed the forward with extra viscosity and no lateral tracer diffusion. Fixed in `data.autodiff_adjointViscosity`; 31141 vs 31138 (30 d from rest, same executable) measures the change — DINO `TODO.md`.
- **Scratch paths come from `$SCRATCH_ROOT`, not literals.** Every live build and submit script sources `tools/machine_env.sh`, which sets `SCRATCH_ROOT`, `MPI_LAUNCHER`, `MPI_OPTFILE`, `SERIAL_OPTFILE` and `SBATCH_EXTRA` per machine (sverdrup by default, perlmutter when `$NERSC_HOST` is set). Do not reintroduce a literal `/scratch2/...`; add a case block instead. The notification address is still a hardcoded `#SBATCH --mail-user` directive.
- **Submit with `tools/submit.sh <script>`, not `sbatch`.** Account, QOS, constraint and walltime cannot be `#SBATCH` directives without breaking the other machine, so the wrapper passes them on the command line where sbatch lets them override. On sverdrup `SBATCH_EXTRA` is empty, so it is `sbatch --export=ALL scripts/<script>` run from the setup directory (the parent of `scripts/`, which the wrapper `cd`s to), and plain `sbatch scripts/<script>` from that directory still works. Extra arguments are placed **before** the script name, because sbatch's usage is `sbatch [OPTIONS] script [args]` and anything after the script name goes to the script instead — which is why `submit.sh <script> --test-only` used to submit a real job rather than dry-run it. `--export=ALL` is sbatch's default, made explicit because the jobs depend on it: `impacts_load_modules` is a no-op on sverdrup, so the Intel/MPI stack *and* the `IMPACTS_*` overrides both reach the compute node only through the inherited environment.
- **The optfiles are machine-authoritative, deliberately.** `~/.bashrc` on sverdrup exports `MPI_OPTFILE`; honouring it would silently build Perlmutter with the Intel sverdrup optfile, so `machine_env.sh` overwrites it. `IMPACTS_MPI_OPTFILE` is the explicit override.
- Namelist variants live in `input*/variants/<group>/` and are chosen by `test_cases` as `<group>/<tag>` (a bare `<tag>` still resolves to `variants/data_<tag>`; empty string = plain `input_tap/data`). A file is named for the MITgcm file it replaces, `<mitgcm-file>_<tag>`, and **every sibling sharing the tag is staged too** — so `scheme_tests/from_rest_viscRef_kppON` brings its `data.pkg` along. The run directory takes the tag's last component only, never the group. See the setup README for the vocabulary.
- SOMA has one submit script per mode (`submit_frd.sh` MPI ×4, `submit_tapAdj.sh` serial), like DINO; the `test_cases`/variants machinery is present but inert until an `input*/variants/` directory exists there.

### Where the output lands

Two different places, which matters when a run fails:

- **In the setup directory** (i.e. in the repo, untracked): `logs/<job-name>.<job-id>.out`, carrying stdout and stderr merged. The scripts run under `set -x`, so this file is a full trace of the staging steps — staging failures show up here, not in the model output — and it is also the only place SLURM itself reports a time-limit kill, an OOM or a node failure. `tools/submit.sh` runs `mkdir -p logs` before submitting: sbatch accepts a job whose `-o` directory is missing and then fails it at launch, usually with no log to say why. **Before 2026-09-02 these were `<job-name>.<job-id>.out` plus a separate `.err`, at the setup's top level, cleaned by a per-setup `clean_slurm_logs.sh`.** Both are gone: with only `-o` set sbatch merges the streams, which retired a `.out` that was empty on every job ever run, and with nothing landing beside the source there is no cleanup chore left to script. Logs are ~8 KB each; prune with `find logs -mtime +90 -delete` if they ever accumulate enough to matter.
- **In scratch**: `/scratch2/<user>/DINO_1deg_outputs/runs/adjoint/DINO_1deg_<run_token>_<duration>[_<tag>]_run<job-id>/`, holding `output_tap_adj.txt` (all model stdout/stderr), `run_timing.txt`, `build_info.txt` (copied from the build directory), the staged namelists, and the `ADJ*` / monitor output the notebooks read. `<run_token>` is `tapAdj_<ckp>[_<variant>]` — `<ckp>` is `nocheckpoint` or `ckpAll`, `<variant>` `adjVisc` or `profile` — and comes from the build's `build_info.txt`, never from the submit script, so a run directory cannot claim a build it did not get (the `#SBATCH -J` name only names the log file under `logs/`). `<tag>` is the last component of `test_cases`, so the name records which namelist variant was used — the only durable record of it besides the staged namelist itself; when `test_cases` is empty (the live `input_tap/data`) the submit body derives `<start>_<viscosity>` from the namelist (`nIter0`, `viscAhDfile`/`viscAhZfile`, `viscAhGrid`; DINO's `run_suffix_from_namelist` in `scripts/setup_params.sh`) with the same vocabulary, falling back to `liveData` for anything it cannot classify. Since 2026-09-05 SOMA is named the same way — `SOMA_1deg_<run_token>_<duration>[_<tag>]_run<job-id>` with tokens `frd` and `tapAdj_ckpAll` — while its three older runs keep their `SOMA_1deg_<mode>_<duration>_run<job-id>` names. **The two variant tokens were shortened on 2026-09-05** — `adjViscBoost` to `adjVisc` (one word for the variant, matching `variants/adjointViscosity/`) and `tapProfile` to `profile` (the `tapAdj_` prefix had already said Tapenade). Runs made before that keep the old spellings on scratch, and so does the `run_token` inside their `build_info.txt`; nothing on scratch was renamed, because a run directory records the build it actually got. `*adjVisc*` matches both spellings; `*rofile*` matches both.

**Scratch was consolidated and restructured on 2026-09-03, and a lot of runs were deleted.** Each setup has one output tree, and inside it things are separated by *what they are*, not by which job made them. `/scratch2/<user>/DINO_1deg_outputs/` and `.../SOMA_1deg_outputs/`, each with a `README.md` of its own:

```
runs/            model output — one directory per job, grouped by campaign
├── forward/{spinup_200yr_visc2x,kappa_v_ensemble}/
└── adjoint/{kappa_v_ensemble,checkpointing_study,adjVisc,
             toolchain_validation,gradient_check,sensitivity}/
analysis/        multi-run analysis products, one directory per campaign
└── kappa_v_ensemble/{cache,figures,animations,stats,ckpAll_vs_nocheckpoint_comparison}/
executables/     adjoint binaries kept for provenance, named for their commit
logs/            SLURM logs kept out of the run directories
```

The earlier `runs_prod/`, `runs_prod_viscGrid/`, `runs_exploratory/`, `runs_from_rest/`, `runs_from_*_pickup/` and `crashed_runs/` levels are gone, as is the separate `v4_soma_tapAdj_runs/` tree; the tutorial outputs became `/scratch2/<user>/verification_tutorials_outputs/barotropic_gyre/`. Every path in the repository was rewritten with the move. Notebook *outputs* were deliberately not rewritten: a recorded output is the record of the run that produced it, under the name it had.

**Three rules keep this from rotting.** (1) A run directory keeps the machine-made name the submit script gave it; the campaign is the directory it sits *in*, never part of the name. (2) Submit scripts write to `runs/forward/` or `runs/adjoint/` directly, so a new run lands unfiled at that level and is moved into a campaign when it joins one — filing a run means updating the notebook that reads it. (3) Output from a notebook that reads **one** run stays inside that run (`<run>/figures/`, `<run>/animations/`); output from a notebook that reads **several** goes to `analysis/<campaign>/`. SOMA has no campaign level yet: five runs do not need one.

**`STDOUT.0001`–`STDOUT.0026` are gone from every DINO run, on purpose.** On 27 ranks only rank 0 writes `%MON`; the other 26 files are `cg2d:` residual traces and field-load lines — ~20 GB with one distinct line shape between them (the per-tile origin header, also in the kept `w2_tile_topology.*.log`) and no ERROR or WARNING anywhere. `STDOUT.0000` and all `STDERR.*` are kept, and every comparison report reads rank 0. Do not restore them; if a future run needs per-rank output, read it before it is pruned.

What survives, and what that costs:

| Kept | Gone |
| --- | --- |
| forward: 30983 (200 yr `visc2x` spin-up, 2 402 pickups) and the κ_v ensemble members 30996–31002 | every other forward run — 28463 (a byte-identical duplicate of 30983), the crashed 19369/28452/18277, the `viscGrid` crashes, 28489, 30945, all of `runs_exploratory/` |
| adjoint: 28486, 31022, 31025, 31026, 31028, 31032, 31037, 31039–31046, 31052–31054, 31056, 31074, 31075, 31077, plus what became `executables/` and `analysis/kappa_v_ensemble/` | 31055 and the `-nocheckpoint` ensemble reruns 31060–31067 (their result is in the comparison reports), the c69f-era serial adjoints, 24493/28453/28461 |
| SOMA: 31033, 31034, 31076 | 31031 and the whole c69f `v4_soma` campaign |

**A second pass on 2026-09-11 removed what had become redundant.** It deleted `/scratch2/<user>/_trash_20260903/` (the per-rank `STDOUT` files above and four short test runs no document names), `logs/slurm_run28463/` (the rank-0 log of the deleted duplicate spin-up) and fourteen validation reruns whose every output had been verified identical to a run that stays: DINO 31077 (5 yr; ≡ 31039 through 31055), 31091, 31101, 31107 and 31108 (≡ 31074), 31090 and 31109 (≡ 31075), 31102 (≡ 31093), 31103 (≡ 31094), 31104 (≡ 31095) and the forward 31092 (≡ 31100); SOMA 31105 (≡ 31096), 31106 (≡ 31097) and 31110 (≡ 31076). Each deleted run's comparison report, `build_info.txt` and `run_timing.txt` are kept in `logs/validation_reports/` of its setup's output tree as `<run directory>__<file>`, so every "bitwise identical" statement in this file keeps its evidence. No run that a notebook or script reads was a candidate.

**The `from50yrPk` and `from70yrPk` pickups changed provenance.** They used to come from crashed runs 19369 (`viscD2x_Zref`) and 18277; both are deleted, and 30983 is now the only pickup source. It carries `pickup.0000878400`, `pickup.0001229760`, `pickup.0002986560` and `pickup.0003162240`, so every anchor still resolves — but a 50 yr or 70 yr start today is a `visc2x` state, not the state those tags originally meant. That is a change of experiment, not of path. The live `from180yrPk` start is unaffected: it always came from the visc2x spin-up.

**Run-directory names.** Every run directory is `<setup>_<run_token>_<duration>[_<tag>]_run<jobid>`, the token read from the build's `build_info.txt`: `frd` for a forward run (so forward names are unchanged from the older `<setup>_<mode>_…` form), `tapAdj_<ckp>[_<variant>]` for an adjoint (`<ckp>` is `nocheckpoint` or `ckpAll`; `<variant>` `adjVisc` or `profile`), carried over from the 2026-09-02 renaming that took the token from the build record, and applied to SOMA as well since 2026-09-05. The `<tag>` uses the same configuration tokens the notebooks use (`visc2x`, `viscD2x_Zref`, `viscRef`, `viscGrid<v>`). **The job ID is the durable key** — settings tokens were derived by reading each run's own staged `data` namelist, so if a name and a namelist ever disagree, the namelist wins.

Do not treat a notebook's unresolved path as rot to repair by guessing. Every DINO path resolves as of 2026-09-03; the only unresolved ones are in `analyses/SOMA_1deg/adjoint_sensitivity_control_set.ipynb`, which is deliberately kept as the record of a campaign that no longer exists. `tools/pre_push_check.sh` reports those as notes, not failures.

**Figures and animations are not in this repository.** Each notebook writes its
output into the scratch run directory it reads, under `figures/` and
`animations/`, deriving both from the `run_dir` variable it already defines. The
`analyses/**/*.{png,jpg,gif,html}` ignore rules exist only to catch a cell that
is re-run with a repo-local path.

## Forward vs adjoint configuration

The `code/` + `input/` pair is the forward model; `code_tap/` + `input_tap/` is the adjoint. They differ structurally, not just by a flag:

- `code_tap/packages.conf` drops `cd_code` and adds `tapenade` plus the `adjoint` pkg group (`autodiff, ctrl, cost, grdchk`).
- `input_tap/` adds `data.autodiff`, `data.cost`, `data.ctrl`, `data.grdchk`.
- **`input*/` holds only what MITgcm reads; alternatives live in `input*/variants/`, grouped by purpose.** A submit script resolves `test_cases` to `variants/<group>/data_<tag>` (a bare `<tag>` still resolves to `variants/data_<tag>`; empty `test_cases` means the live `input*/data`) and stages only that one, so a run directory carries no unused namelists. **It also stages every sibling `<mitgcm-file>_<tag>` beside the chosen namelist** — that is how `scheme_tests/from_rest_viscRef_kppON` gets `data.pkg` with `useKPP=.TRUE.` as well as its `data`. Before 2026-08-28 only the `data` half was staged, so that variant silently ran without KPP. The run directory is named after the tag alone, never the group. Anything placed directly in `input*/` is copied into *every* run. The staging uses `find -maxdepth 1 -type f` rather than a glob, because `cp dir/*` would hit `variants/` and abort under `set -e`.
- `code_tap/COST_OPTIONS.h` defines `ALLOW_COST_ATLANTIC_HEAT` and `ALLOW_COST_ATLANTIC_HEAT_DOMASS`.
- **Mixing coefficients: which are files and which are parameters (since 2026-09-09).** Vertical diffusivity is a namelist scalar, `diffKrT = diffKrS = 1.2E-5` (DINO's `rn_avt0`); under `ALLOW_3D_DIFFKR` it initialises the 3-D `diffKr` array (`ini_mixing.F`, from `diffKrNrS(k)`) that `xx_diffkr` perturbs, bitwise the same array the retired `diffKrFile='dino_diffKr.bin'` produced (31139 ≡ 31100 forward, 31140 ≡ 31137 adjoint, 30 d). The `kappa_v_ensemble` members set their κ the same way. Lateral viscosity **stays a `PARM05` file on purpose**: DINO's law is A_h = ½·U_v·Δx (NEMO `nn_ahm_ijk_t=20`, `rn_Uv=0.27`) and MITgcm has no parameter linear in Δx (`viscAhGrid` is ∝ L²/Δt, `viscAhReMax` is flow-dependent); `DINO_1deg/scripts/gen_viscAhD.py` regenerates every `dino_viscAhD*.bin` byte for byte from the grid file. The `_2p00` file, `rn_Uv=0.54`, was the production setting until 2026-09-09; **since 2026-09-10 production is the reference file plus `viscAhReMax=2.` with the flux-limited scheme 33 in the forward model and, through `useApproxAdvectionInAdMode` in the live `input_tap/data.autodiff` and the `approxAdv` build, the unlimited scheme 30 in the adjoint sweep** (from 2026-09-09 to 2026-09-10 it was scheme 30 in both; the DINO README's "Scheme 30 or scheme 33" has the study). The baseline is the live `input/data` (200 yr from rest) and `input_tap/data` (5 yr from a year-180 pickup), which the submit scripts run when `IMPACTS_TEST_CASE` is unset (`baseline/` keeps the `visc2x` predecessors as records); the kappa ensemble under this configuration is `kappa_v_ensemble/REF_ReMax2` and `M<k>_ReMax2`; the run-naming rule appends `_ReMax<v>` and `_adv<n>` (no token for scheme 33, the build token `tapAdj_ckpAll_approxAdv` records the adjoint sweep) and, since 2026-09-11, `_gmFwd` when `data.pkg` turns GM/Redi on while `data.autodiff` keeps it out of the adjoint sweep. **Vertical tracer advection is explicit since 2026-09-10** (`tempImplVertAdv = saltImplVertAdv = .FALSE.`): the implicit flux-limited DST3 solve returns a ±100 K checkerboard in a convectively homogenised column and blew up the 8× and 16× kappa legs within two years (31191/31193, dissected in 31198–31201; the DINO README's "Scheme 30 or scheme 33" has the account). The campaign was resubmitted under the corrected namelists: spin-up 31203, reference leg 31205 with the production adjoint 31206 chained on it, 31204 chained on the spin-up (cancelled on 2026-09-11, when GM/Redi in the adjoint's forward sweep was adopted; its replacement is on the DINO `TODO.md`) and the ensemble 31207–31220. The setup README's "Lateral viscosity and vertical diffusivity: file or parameter" has the table.

The cost function `code_tap/cost_atlantic_heat.F` has its **section indices compiled in as `parameter` statements** — a zonal section (DINO: `isecbeg=1, isecend=51, jsec=127`) and a meridional one (`jsecbeg=1, jsecend=62, isec=30`) are both declared. Moving a section requires editing this file and rebuilding, not a namelist change; `mult_atl` in `data.cost` only scales the result. Indices are located with `analyses/DINO_1deg/grid_and_cost_sections.ipynb`. Because the values are compiled in, the authoritative record of what a past run measured is the `.f` file in that run's build directory, not the current source.

`kmaxdepth` is likewise compiled in, and per-setup: DINO uses 25, SOMA 21. Both live in the `ALLOW_COST_ATLANTIC_HEAT_DOMASS` branch, which is the active one in every setup that enables this cost function — the `#else` value of 14 inherited from `pkg/cost` is dead code here, so don't read it as a default.

Two more things about this cost that are easy to get wrong (verified 2026-08-30
while analysing the kappa_v ensemble; details and the validating proxy in
`analyses/DINO_1deg/adjoint/kappa_v_ensemble/`):

- **fc is a terminal-30-day mean, not a run mean.** `pkg/cost` accumulates
  `cMean*` only over the final `lastinterval` seconds of the run, and the
  default (2,592,000 s = 30 d, `cost_readparms.F`) is not overridden in
  `data.cost`. Direct cost forcing therefore enters the adjoint only during
  the last month; everything at longer lead is adjoint dynamics.
- **fc depends on the domain decomposition.** `countV(k)` is computed per MPI
  tile (the `bi,bj` loop runs `i=1,sNx`), and DINO's 51-cell section spans 3
  tiles, so J sums three per-tile-normalised transports — ~3× a globally
  normalised index. Comparisons at fixed decomposition are fine (everything
  here is `nPx=3, nPy=9`), but rebuilding with a different decomposition
  changes the value of J itself, not just performance.

**KPP is off in every adjoint run; GM/Redi, on in the DINO forward spin-up, has run in the DINO adjoint's forward sweep since 2026-09-11 and never runs in its adjoint sweep.** DINO's `input/data.pkg` sets `useGMRedi=.TRUE.` (with `input/data.gmredi`: `GM_background_K=571`, `ldd97` taper), so the 200-yr spin-up and the kappa forward legs are GM runs, while until 2026-09-11 `input_tap/data.pkg` set it `.FALSE.` and `input_tap/data.gmredi` was a *different* file (K=1000, `dm95`), both unchanged since the initial import and noticed 2026-09-09: every adjoint before that date, 31206 and the `kappa_v_ensemble_ReMax2` adjoints included, integrates a GM-free forward sweep from a GM-equilibrated pickup (the record variant `baseline/from180yrPk_viscRef_ReMax2_gmOff` reproduces that configuration). The stability study (`input_tap/variants/stability_study/`) tried the alternatives from the 180-yr pickup, 30 d: GM on in both sweeps explodes within 20 d of lead at the reference viscosity (31155) and is marginal at 2× (31154, a transient burst); GM on in the forward sweep only (`useGMRediInAdMode=.FALSE.`, the ECCO-style approximation) blew up at both viscosities in 31156/31157 (rms 1e30 by lead 25 d), **but those ran the `-nocheckpoint` build, where the switch half-applies** — the split `DO_OCEANIC_PHYS_BWD` replays the GM-on branch taped in the forward sweep and runs `GMREDI_CALC_TENSOR_B`, while the joint `GMREDI_XTRANSPORT_B` reads the flipped flag and skips the flux adjoint — so they say nothing about the approximation itself. **Retested 2026-09-11 in the `approxAdv` build** from the REF_ReMax2 leg's year-180 pickup (variants `stability_study/*_ReMax2_gmFwd`, `*_gmOn`, `REF*_ReMax2_gmFwd`, `thetaPatchFD_*`; scripts in `analyses/DINO_1deg/adjoint/gm_in_adjoint/`; runs 31234–31252 under `runs/adjoint/stability_study/`): GM in both sweeps still blows up, from one western-boundary cell at lead 4 d, even with scheme 30 in the adjoint sweep (31236); GM in the forward sweep only is stable over 30 d (31234) and 5 yr (31237, 14 h 28), gives the GM model's `fc`, and against finite differences of the GM model brings dJ/dκ_v from +65 % (production 31206) to +22 %, while the temperature-box gradients do not improve (tropics +4 % vs +5 %, upper Southern Ocean +45 % vs +42 %, deep North Atlantic −21 % vs −9 %); its 5-yr sensitivity fields differ from production's by 41–43 % RMS. **Adopted for production the same day**: the live `input_tap/data.pkg` sets `useGMRedi=.TRUE.`, `input_tap/data.gmredi` is a copy of `input/data.gmredi`, `data.autodiff` keeps `useGMRediInAdMode=.FALSE.`, runs of the live namelist are named `_gmFwd`, and the submit body refuses the combination with a `-nocheckpoint` build. **The GM-free adjoint's own blow-ups are the flux limiter's adjoint**, established 2026-09-09 by restarting the last 183 d of kappa member M7's blown 5-yr adjoint from its own pickup: the control (31166) reproduces 31046 byte for byte, blow-up included (rms `ADJtheta` ×240 between lead 110 and 140 d); the same with `tempAdvScheme=saltAdvScheme=30` (DST3 without the limiter, both sweeps; 31167) does not blow up at all, `fc` moving by 0.45 %; `viscAhReMax=2.` alone (31168) only halves the burst. The kappa members that blew up were all 2× runs, so viscosity delays this instability but never removes it; the DINO README's "Why the reference viscosity is unstable" has the study. Both DINO and `SOMA_1deg` set `useKPP` `.FALSE.` statically in `input_tap/data.pkg` (SOMA `useGMRedi` too), and their submit scripts carry the equivalent `sed -i` lines commented out. **`useApproxAdvectionInAdMode` is inert in the plain Tapenade builds**: `gad_advection.F` guards it with `ALLOW_AUTODIFF_TAMC` (TAF only), and with multi-dimensional advection that is where the horizontal DST3 fluxes come from, so the flux-limited scheme 33 is always differentiated as is (31158/31159 byte-identical to 31140/31152; `gad_calc_rhs.F` uses `ALLOW_AUTODIFF` and would honour it, but handles only what is not multi-dimensional). **Since 2026-09-10 the `approxAdv` build makes it work, and it is the default adjoint** (`code_tap/variants/approxAdvection/`: the guard widened in `gad_advection.F`, the same swap added to `gad_implicit_r.F` for the implicit vertical advection; `build_tapAdj_approxAdv.sh`, a `ckpAll` build because the switch is a run-time branch): scheme 33 in the forward sweep, scheme 30 in the adjoint sweep, validated on the M7 restart (31176: `fc` byte-identical to the control, no blow-up, adjoint fields correlated 0.999 with the scheme-30 run's). The other finding of that day: **the scheme-33 cost is not finite-difference-checkable at reference viscosity** — in `grdchk_repair/` runs 31177–31179 every perturbed forward (`±1e-3` K at one cell) shifts `fc` by +5e-4 regardless of sign, so the exact adjoint of 33 fails its own check by 22 % and more (31178) while scheme 30 passes to 1e-6 (31172); the DINO README's "Scheme 30 or scheme 33" has the forward-side comparison (differences confined to the equatorial band; no deepening of the mid-latitude cells, but a steadily weaker AMOC under scheme 30). **So the production adjoint is an approximate adjoint by design**: its gradient is within 3 % of the exact scheme-33 one at 30 d and its sensitivity fields within 1 % of the exact scheme-30 adjoint's on the M7 test; the standard finite-difference check cannot verify it, because the scheme-33 forward is not differentiable at `grdchk_eps`. The `useKPPinAdMode` flag in `data.autodiff` is therefore inert as currently configured, while DINO's `useGMRediInAdMode=.FALSE.` has been live since 2026-09-11. Check both the namelist and the submit script before concluding a package is active — the now-archived `sr_soma` setup did it the other way round, leaving the namelist `.TRUE.` and disabling the packages from the submit script instead.

**`mods_tapenade_hooks/stubs_tap_adj.F` overrides the pkg/tapenade copy (it was
DINO's `code_tap/stubs_tap_adj.F` until 2026-09-07) — and `ADJ*` dumps written
before job 31022 (2026-08-31) carry a tile-edge artifact.**
Upstream ships the five `ADEXCH_*` adjoint halo exchanges as no-op stubs
(printing "Called not yet defined"); the `ADJ*` dump path calls them to fold
tile-halo adjoint contributions into the owning interior cells before writing,
so every pre-fix dump keeps partial sums in the 1–2 cells straddling each
exchange seam: `i=17|18`, `34|35`, every `j` multiple of 22, and the channel's
zonal periodic seam (`i∈{1,2,50,51}`, `j≈13–44`), worst on U-grid fields
(shared C-grid face column). This was **dump-only**: the adjoint dynamics uses
its own correct path (`EXCH2_*_CUBE_AD` via the Tapenade-generated
`EXCH2_*_CUBE_B`), so `fc` and `adxx_*` were never affected — the fix
(implementing the stubs with those same `_AD` routines, via `-mods` same-name
shadowing, keeping the vendored tree pristine) was validated with run 31022 vs
30994: `fc` and all 33 `adxx_*` files bitwise identical, `ADJ*` differences
confined to the seams. The artifact only ever affected the seven dump fields
with horizontal stencils — `ADJdiffkr`/`ADJqnet`/`ADJqsw`/`ADJempmr` have
empty adjoint halos and were never touched. The kappa_v ensemble's dumps were
replaced by the seam-clean 2026-09-01 rerun (31039–31046; the pre-fix
originals are deleted), so 28486 is the only pre-fix run left on scratch —
mask ~2 cells around those seams when reading its `ADJ*`. Do not
"clean up" the override into `MITgcm/pkg/tapenade/` — that would create a
modified-upstream deviation the verification procedure above flags; it is the
first of the two patches in `mods_tapenade_hooks/patches/`. SOMA is
single-tile serial (no seams); since 2026-09-07 it compiles the same
implementation, which folds nothing there.

## Verifying correctness

There are no unit tests. Four things stand in for them, and their status as of
2026-09-01 is:

(Every "bitwise identical" claim here and in the setup `TODO.md` was made with
`tools/compare_adj_runs.sh <ref> <new>`, which `cmp`s every `ADJ*`/`adxx_*`
file, the first `global fc` line and the `%MON` stream and writes a verdict
report into the new run directory. Since 2026-09-04 it compares `build_info.txt`
field by field: the provenance keys — `built`, `exe_md5`, `git_commit`,
`git_modified_tracked_files`, `invoked_as` — are expected to differ and are only
counted, and a configuration key that differs is printed as `CONFIG <key>`
without failing the verdict, so "different build, identical output" reads as the
result it is. Before that the file was `cmp`'d whole, and every comparison of a
rebuilt executable returned `NOT CLEAN` on it alone; a report dated earlier that
fails only on `build_info.txt` is one of those. Since 2026-09-05 it also treats
the profiler build's `tapenade_profile.*.txt` tables as an expected difference
when they match with the measured seconds masked and the rows sorted, and reads
a serial run's `fc` and `%MON` from `output_tap_adj.txt` — before that a SOMA
adjoint comparison always came out `NOT CLEAN` with an empty `fc`.)

**1. Forward reproducibility — verified again on 2026-09-11 under the
production configuration.** A 10-year run from rest under the live `input/data`
(31256, the committed `submit_frd.sh` defaults, same executable) reproduced the
first 10 years of the 200-year production spin-up 31203 **byte for byte**:
every `dynDiag`/`surfDiag`/`atmDiag`/`viscDiag` record and every monthly
pickup (601 files) identical under `cmp`, all 6 050 `%MON` values over 121
blocks identical (last cell of
`analyses/DINO_1deg/forward/spinup_200yr_from_rest_viscRef_ReMax2.ipynb`);
31256 was then deleted, being a copy of what 31203 holds. The 2026-08 form of
the check (30945 against the `visc2x` spin-up, 161 `dynDiag` fields, 1334
monitor values) was deleted in the 2026-09-03 consolidation. To re-run it:
rebuild, `../../../tools/submit.sh scripts/submit_frd.sh` from the setup
directory (10 yr from rest is the default), `cmp` the `*Diag.*.data` files
against 31203's. ~1.6 h on 27 ranks. It catches a compiler or source change
that alters the physics.

**2. Adjoint runs end to end — verified.** A 30-day adjoint from the 180-year
pickup produces `ADJ*` and `adxx*` output with sensitivity concentrated on the
cost section (peak `|adxx_theta|` at `i=2, j=127, k=26`, decaying away from it).
That is consistent with a correct adjoint but is not a proof.

**3. The finite-difference gradient check — repaired 2026-09-01, and it passes
at the sensitive point.** The committed `input_tap/data.grdchk` still perturbs
`xx_theta` at `iGloPos=4, jGloPos=8, kGloPos=1` and fails by ~8 orders of
magnitude, as it always has — the May 2026 production run (28486) shows the
same, with a worse RMS ratio (8.0e+12 against 6.6e+08). The repaired check
lives in `input_tap/variants/grdchk_repair/` (point on the sensitivity peak,
`grdchk_eps=1e-3`) — result below.

The cause is the check point, not the adjoint. `j=8` is near the southern
boundary; the cost section is at `j=127`. Sensitivity there is ~6e-10 against a
field maximum of ~3.9e-02. The cost change the adjoint predicts for
`grdchk_eps=1e-5` is 6e-15, while the perturbed runs differ from the base by
~9e-06 — a billion times larger. Both `FC1` and `FC2` land on the *same side* of
`FC`, which a real first derivative cannot produce. The check is dividing its own
noise by `2*eps` and reporting the result as a gradient.

**That repair was executed on 2026-09-01 and the check now passes where it has
signal.** `input_tap/variants/grdchk_repair/from180yrPk_visc2x_grdchkON` moves
the point onto the 30-day sensitivity peak — global (i=2, j=127, k=26), which
in grdchk's tile-local addressing is `iGloPos=2, jGloPos=17, iGloTile=1,
jGloTile=6` (**naming trap: `i/jGloPos` are bounded by `sNx/sNy`**, the tile
comes from `i/jGloTile`) — with `grdchk_eps=1e-3`. At that point the
finite-difference and adjoint gradients agree to **0.9 %** (−3.8229e-2 vs
−3.8566e-2, run 31037). The four follow-on (weaker) points predict responses
of ~1e-5, at the fc noise floor above, and still return noise — cite only
points whose `|adj grad|·eps` clears ~3e-5. A control run built from the
`main`-tip pre-hook mechanism (31038) reproduces the entire `grdchk` table
digit for digit, and its 62 `adxx_*`/`ADJ*` files bitwise — so the check
verifies the hook-generated adjoint and the hand-patched one identically.
SOMA's always-on check passes at 0.07–1.8 % on all five of its points (5-d
runs 31031/31033, identical output between the pre- and post-refactor
builds). **Under the 2026-09-09 production configuration (scheme 30,
`viscAhReMax=2.`, reference viscosity) the DINO check passes at all five
points, 0.0001–0.0035 % (run 31172,
`grdchk_repair/from180yrPk_viscRef_ReMax2_adv30_grdchkON`)** — the four
weaker points' "noise" above was the flux limiter's non-smoothness, which
scheme 30 removes, so the `|adj grad|·eps` rule of thumb only applies to
scheme-33 runs. At the reference viscosity the limiter's noise is ten times
larger (31178, exact scheme 33 + `viscAhReMax=2.`: every perturbed run +5e-4
above the reference for both signs, 22 % at the strongest point, RMS ratio
21), so a scheme-33 forward has no usable finite-difference check there; the
approximate adjoint of the `approxAdv` build (31177) shares those perturbed
runs digit for digit and its gradient is within 3 % of the exact scheme-33
one.

**4. The kappa_v ensemble's adjoint-vs-finite-difference comparison — executed,
and it fails as a validation for a physical reason.** The 2026-08-28/29 ensemble
(reference 30995 + members 31003–31009; adjoints rerun seam-clean on 2026-09-01
as 31039–31046 with fc/adxx bitwise identical, so every number here stands and
the analysis now reads the rerun; analysed in
`analyses/DINO_1deg/adjoint/kappa_v_ensemble/`) compared measured ΔJ
against the linear adjoint prediction: wrong sign for 4 of 7 members, none
within 30 %. The failure is dominated by nonlinearity of the 10-yr state
adjustment, so it neither confirms nor refutes the adjoint — the trust radius of
the raw gradient is simply below the factor-2 steps tested. The same analysis
did re-verify bit-reproducibility (30995 ≡ 28486 exactly) and found that four
member adjoints **blow up** (linearisation instability, non-monotonic in κ:
0.25×, 4×, 8×, 32× blow; 0.5×, 2×, 16× survive) — so a plain-build adjoint on a
perturbed background state is not guaranteed to stay finite over 5 years, which
is what `adjVisc` exists for (note the ensemble predates the mode-switch
hooks, when adjVisc was silently inert — no working boost had ever run). The repaired gradient
check of item 3 now supplies the adjoint-correctness verification this item
could not, at the points where the check has signal.

**`useGrdchk` differs by setup since 2026-08-28**: DINO's `input_tap/data.pkg`
now sets it `.FALSE.` (verified bit-identical `ADJ*`/`adxx*`; saves 8.2 h per
5-yr adjoint), SOMA still `.TRUE.`. Where it is on, it is not opt-in: every
adjoint job pays for the perturbed forward runs — the 30-day run above recorded
18,622 forward-step calls against the 1,440 the adjoint itself needs. If a SOMA
run is doing far more work than expected, check this flag first.

A further, historical check — the `tutorial_*_with_adj` setups reproducing stock
MITgcm tutorials through the Tapenade path, with `tutorial_global_oce_biogeo/`
holding `code_ad` / `code_oad` / `code_tap` side by side — lived in the c69f tree
and is now only in `Proj_ImPACTS_old`. There is no tutorial-level regression
check here.

## Reading MDS output

`adxx_*` and `xx_*` control files are **`float64`** (hence `ones_64b.bin`), while
the `ADJ*` diagnostic dumps follow `data.diagnostics` and are `float32`. Read the
`.meta` beside a file rather than assuming — guessing the precision silently
reshapes the array and produces plausible-looking garbage.

## Analyses

Notebooks read output directly from cluster scratch with `xmitgcm.open_mdsdataset(grid_dir='/scratch2/...', prefix=['ADJtheta', ...], read_grid=True, delta_t=1800)`, `geometry="curvilinear"` for DINO. Where raw tiled binaries are read instead, shapes are reconstructed from the same `sNx/sNy/OLx/OLy/Nr` values as `SIZE.h` — keep those in sync when the decomposition changes.

The tree mirrors the setup names: `analyses/DINO_1deg/` and `analyses/SOMA_1deg/`, with `forward/` and `adjoint/` under DINO, plus `reference_notebooks/` (collaborator originals) and `tools/`. **Names are descriptive and carry no ordering number** (since 2026-09-03; the old `00_`–`07_` prefixes and the `00_archive/` directories are gone). Reading order lives in `analyses/README.md` and in each suite's own `README.md` — `adjoint/kappa_v_ensemble/`, `adjoint/tapenade_profiling/` and `adjoint/scidac_poster_aug2026/` each have one. `analyses/README.md` is also the per-notebook index saying which scratch run each one reads — that mapping is not recoverable from the file names alone — and its "Retired analyses" section records the thirteen notebooks moved to `~/trash/Proj_ImPACTS/analyses/` when their runs were deleted, and which surviving notebook absorbed each one's findings.

**Paths are the thing to be careful with here.** Notebooks build `run_dir` by
concatenating adjacent string literals across separate lines, so a naive
search-and-replace on a full path silently rewrites only the fragment it matched
and leaves the rest stale. When run directories move, rewrite by *basename* as
well as by full path, then verify by reassembling the literals and checking each
path exists on disk. `code_tap/cost_atlantic_heat.F` also cites
`analyses/DINO_1deg/grid_and_cost_sections.ipynb` by name in a comment.

**Notebook outputs are stripped by a git `clean` filter, not by hand.**
`.gitattributes` points `*.ipynb` at the `nbstrip` filter, defined by
`analyses/tools/strip_animation_outputs.py --filter`. The working tree keeps its
outputs; the committed blob does not. Filters live in `.git/config`, which is
untracked, so **a fresh clone commits notebooks unstripped until
`./analyses/tools/install_git_filters.sh` is run** — check `git config --get
filter.nbstrip.clean` before concluding the filter is active. The default strips
only `to_jshtml` payloads over 1 MB and keeps static figures; `--all-outputs`
strips everything. The script keeps its original in-place mode for one-shot
passes, so `--filter` (stdin to stdout, touches no file) and the default mode
(rewrites files) are different things.

Because git stores the stripped copy, anything that rewrites a notebook in the
working tree (`checkout`, `stash`, `merge`, `reset --hard`) discards the local
outputs.

## Not tracked

`**/build*/` **except `build_options/`**, `**/.ipynb_checkpoints/`, and the `input_binaries/` + `input_adj_binaries/` directories for every DINO and SOMA setup. SOMA inputs regenerate with `input/gendata.py`; DINO's `dino_*.bin` files are produced outside this repository and must be staged into `input_binaries/` before a run — except `dino_viscAhD*.bin`, which `DINO_1deg/scripts/gen_viscAhD.py` regenerates byte for byte from `tile001.mitgrid`, and `dino_diffKr*.bin`, which nothing reads since 2026-09-09.

The `!**/build_options/` negation is load-bearing: `**/build*/` was swallowing
`MITgcm/tools/build_options/`, so all 216 genmake2 optfiles were untracked — the
93 supported ones and the 123 under `unsupported/` — and a fresh clone could not
build on any machine. A negation works only because it un-excludes the directory
itself — git cannot re-include a file inside a directory that stays excluded.

`input_adj_binaries/` is small but not optional: it holds `ones_64b.bin`, the uniform weight file that *every* `xx_gentim2d_weight`/`xx_genarr3d_weight` entry in `data.ctrl` points at. Since it is untracked and the submit script only symlinks the directory contents, a fresh clone has no adjoint run until it is put back.
