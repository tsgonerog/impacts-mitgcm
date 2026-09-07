# TODO — DINO_1deg

- [x] ~~**Remove the four stock stubs from the shared `dummy_tap.F`**~~ (added
  and **done 2026-09-07**, the evening after the move below). The tree's
  `pkg/tapenade/dummy_tap.F` is one include and four empty routines,
  `DUMMY_IN_STEPPING_B`/`_D` and `DUMMY_FOR_ETAN_B`/`_D`, and the shared copy
  had kept them verbatim ahead of the appended bodies. They are unreachable:
  `tools/TAP_support/flow_tap` declares both stock hooks with every argument
  read-only, the tree's Tapenade options file passes that declaration to every
  `-tap` build, and Tapenade generates no call to a derivative of a read-only
  external in either mode. Checked before removing them: no generated
  `_b.f`/`_d.f` of the seven adjoint builds here (this setup's five, SOMA's,
  the gyre's) or of the study's eighteen verification builds (nine
  experiments, pristine and modified tree, adjoint and tangent-linear, about
  3 000 generated files) calls them; `nm` finds them defined in `dummy_tap.o`
  and referenced by no object; TAF builds never compile `pkg/tapenade` (no
  `code_ad/packages.conf` lists it) and use `ADDUMMY_IN_STEPPING`; forward
  builds never compile the file. Tapenade run on a toy caller shows where the
  stubs came from: for a hook with no `flow_tap` stanza and an active `myTime`
  it emits `DUMMY_FOR_ETAN_B(myTime, myTimeb, myIter, myThid)`, the stub's
  exact shape; with the stanza, nothing; the three-argument
  `DUMMY_IN_STEPPING_B` matches no call it produces under any declaration.
  The shared `dummy_tap.F` now keeps the tree's opening include and drops the
  35 lines of the stubs; `check_against_tree.sh` classifies it `replace` (the
  second declared exception, beside `stubs_tap_adj.F`), `patches/0002` is
  regenerated and applies cleanly, and the study tree's working copy carries
  the same file, so `build_tapAdj_hooksInTree.sh`'s byte-identity assertion
  holds. All seven adjoint builds rebuilt (17:49–18:28): every
  Tapenade-generated `_b.f` byte-identical to the build before the removal
  (188 files in each of the five DINO builds, 212 in SOMA's, 165 in the
  gyre's), the four symbols gone from every executable, `dummy_tap.o` down
  from 41 routines to 37, every build-body check passed. No run was needed:
  the generated code is unchanged and the removed routines were never
  reached. The build records name commit `c2c64b6` with the shadow and the
  documents modified; rebuild after the commit if a record naming it matters.

- [x] ~~**Move the Tapenade hooks out of `code_tap/` into one shared `-mods`
  directory in the shape of the upstream contribution**~~ (added and **done
  2026-09-07**, branch `tapenade-hooks-shared-mods`, merged into `main` the
  same day as a fast-forward; the pre-merge `main` is tag
  `archive/20260907_pre-hooks-shared-mods`).
  `MITgcm_c69m/mods_tapenade_hooks/` holds the seven files of the in-tree
  study's branch, exported flat: four shadows under the tree files' own names
  (`forward_step.F` +18 lines, `integr_continuity.F` +5, `stubs_tap_adj.F`
  with the five `ADEXCH_*` stubs replaced, `dummy_tap.F` with the 37 hook
  bodies appended after the stock stubs — the stubs themselves removed later
  that day, see the entry above) and three new files
  (`dummy_in_stepping_tap.F`, `tapenade_ad_diff.list`, `flow_tap` as the
  tree's file plus the seven stanzas). `check_against_tree.sh` there verifies
  the shape and writes `patches/` (two patches; they apply cleanly to the
  vendored tree; `tools/pre_push_check.sh` runs the check). The ten hook files
  left this `code_tap/` and the seven left SOMA's. `tools/lib/build_body.sh`
  lists the directory first in `-mods` (`HOOKS_MODS`), uses the tree's stock
  `-adof`, appends `-ext <dir>/flow_tap` to `-tap_extra`, checks the compiled
  `dummy_tap.f` for the five dump calls and that the hook sources link into
  the directory; `scripts/setup_params.sh` carries the seven per-field
  `HOOK_CHECKS` in both setups. All six adjoint builds were rebuilt and pass;
  the in-tree build now asserts the tree's hook files byte-identical to the
  directory (study branch commit `2a2b901c0`). Validation with
  `tools/compare_adj_runs.sh`, all EQUIVALENT: the default build, 30 d from
  the 180-yr pickup, run 31108 vs 31101 (218 files, `fc`, 441 `%MON` lines);
  adjVisc 30 d from rest, 31109 vs 31090 (210 fields, `fc`
  3.99075406661494E-01, 441 `%MON`: the mode switches engage under the boost
  as before); SOMA 5 d, 31110 vs 31076 (186 fields, `fc`, 390 `%MON`; SOMA's
  output no longer carries the "Called not yet defined" line of the `ADEXCH_*`
  stubs it used to compile). The stock `tutorial_tracer_adjsens` experiment
  on the pristine tree, with the checked-in directory supplied through a
  `genmake_local`, gives the study's testreport verdict with identical output
  and gradients. Runs filed under `runs/adjoint/toolchain_validation/` (DINO)
  and `runs/adjoint/` (SOMA). What is left in `code_tap/` is configuration
  only; `the_main_loop.F` with the binomial checkpointing directive stays
  here as a separate matter. After the merge the five adjoint builds of
  this setup were rebuilt from `main` (commit `01aa06a`, clean tree) so
  that each `build_info.txt` names a commit on `main`; the validation runs
  31108 and 31109 keep the records of the executables they actually ran,
  built from the same sources before the commit existed (`git_commit=
  eada304` with the branch's 17 modified files), which is what their
  `build_info.txt` still says.

- [x] ~~**Integrate the Tapenade hooks into the MITgcm source tree and test
  the result**~~ (added and **done 2026-09-05**). The shadows were written into
  a git copy of checkpoint69m outside this repository,
  `~/MITgcm_c69m_tapenade_hooks/MITgcm` (branch `tapenade-hooks`, two commits:
  the `ADEXCH_*` implementations, then the hooks), with `MITgcm_pristine/` as
  the control, the patch series in `patches/`, every testreport output in
  `results/` and the study in `README.md` (copy:
  `impacts-notes/references/tapenade_hooks/in_tree_integration_20260905.md`).
  `scripts/build_tapAdj_hooksInTree.sh` (new; `MITGCM_TREE` support added to
  `tools/lib/build_body.sh`) builds this setup against that tree from a
  `code_tap/` without the ten hook files; run 31107 is EQUIVALENT to 31101
  (210 `ADJ*`/`adxx_*` files, `fc`, 441 `%MON` lines), filed under
  `runs/adjoint/toolchain_validation/`. What the in-tree version changed, and
  why: the dump hook is one external call per field from a wrapper Tapenade
  differentiates, because Tapenade omits the derivative of an argument that is
  passive at the call site and never read afterwards (`Qsw` without
  `SHORTWAVE_HEATING`, `diffKr` in three upstream experiments), so the
  11-field hook has no single adjoint interface that fits every
  configuration; and everything new is an additive `*_TAP` routine in
  `pkg/tapenade`, so `pkg/autodiff` is untouched and non-Tapenade builds
  preprocess byte-identically (572/573 and 836/837 files, the exception being
  the build-date line). The eight upstream Tapenade experiments give the same
  testreport digits in both trees (`global_oce_biogeo_bling` fails in both for
  a NetCDF-detection reason unrelated to the hooks) and the modified tree
  additionally writes their `ADJ*` dumps. Verdict: suitable for upstream in the
  per-field shape, as two pull requests, rebased on `master` after
  MITgcm#1029; the open points are scope and naming, not correctness. The
  shadows here stay as they are.

- [ ] **Exercise the diagnostics route for adjoint output under the Tapenade
  hooks** (added 2026-09-05; **exercised on `global_ocean.cs32x15` with the
  in-tree hooks the same day**, see the entry above: with a snapshot
  `frequency` and a dump every step, the `adjDiag` records are bit-identical
  to the binary `ADJ*` dumps at the same iteration for all stepping fields,
  and `ADJetan` is one step out of phase, as upstream's `addummy_for_etan.F`
  says it must be. The DINO run below is still to do, mainly for the binomial
  re-forwards.) Upstream roadmap issue MITgcm#735, item 3
  ("integrate better with the diagnostics package to manage AD output", high
  priority), is still open as of checkpoint69q. Under TAF that route is three
  hand-written calls in the reverse sweep: `ADDUMMY_IN_STEPPING` filling the
  `ADJ*` diagnostics through `DUMP_ADJ_*`, `ADAUTODIFF_INADMODE_SET` calling
  `DIAGNOSTICS_SWITCH_ONOFF(-1, …)` at the start of each backward step, and
  `ADAUTODIFF_INADMODE_UNSET` calling `DIAGNOSTICS_WRITE_ADJ` at its end.
  Under Tapenade as shipped none of the three is called; with the hooks all
  three are in the generated `forward_step_b.f` of the default build
  (`build_tapAdj_nocheckpoint/`, lines 7359, 7447 and 7464), in TAF's order,
  and the `_B` bodies keep the `useDiag4AdjOutp` branches. So the route is
  wired but has never been exercised: `input_tap/data.diagnostics` lists no
  `ADJ*` field and every validation so far read the binary dumps. Test: a
  namelist variant, say `input_tap/variants/adj_diagnostics/`, holding a
  `data_from180yrPk_visc2x_adjDiag` copied from
  `baseline/data_from180yrPk_visc2x` and a
  `data.diagnostics_from180yrPk_visc2x_adjDiag` that adds a fifth stream of
  the registered adjoint diagnostics (`ADJtheta`, `ADJsalt`, `ADJuvel`,
  `ADJvvel`, `ADJwvel`, `ADJtaux`, `ADJtauy`, `ADJqnet`, `ADJqsw`,
  `ADJempmr`, `ADJdifkr`, `ADJetan`; names from
  `pkg/diagnostics/diagnostics_main_init.F`) at snapshot frequency
  `-432000.` so it lines up with `adjDumpFreq`. Listing any of them switches
  `useDiag4AdjOutp` on by itself (`diagnostics_set_pointers.F`, "Set internal
  parameter useDiag4AdjOutp"), so no `data.autodiff` change is needed. Run 30
  days with the default build,
  `IMPACTS_TEST_CASE=adj_diagnostics/from180yrPk_visc2x_adjDiag
  ../../../tools/submit.sh scripts/submit_tapAdj.sh`, and compare each
  diagnostics record with the binary `ADJ*` dump at the same iteration; the
  part TAF never had to survive is `DIAGNOSTICS_WRITE_ADJ`'s reversed-time
  bookkeeping across Tapenade's binomial re-forwards, so check the record
  count and the iteration stamps, not just the values. If it agrees, the
  upstream note can say the hooks make the standard diagnostics route work
  under Tapenade for the carried fields and cite #735 item 3 as partly
  addressed. Coverage stays a subset either way (the TAF body handles about
  twenty fields plus the seaice and ptracers dumps, and `pkg/exf` writes its
  own snapshots), and the TLM `_D` bodies are no-ops. Assessment and the
  checkpoint69q comparison behind it:
  `impacts-notes/references/tapenade_hooks/review_upstream_checkpoint69q_20260905.md`.

- [x] ~~**Shorten the two adjoint variant tokens**~~ (added and **done
  2026-09-05**). `tapProfile` → `profile` (the `tapAdj_` prefix had already
  said Tapenade, so the token read `tapAdj_ckpAll_tapProfile`) and
  `adjViscBoost` → `adjVisc` (one word for the variant, matching the
  `variants/adjointViscosity/` source directories renamed on 2026-09-04 and
  closing the split that entry documents). Renamed: the four scripts
  (`{build,submit}_tapAdj_{profile,adjVisc}.sh`), their `BUILD_DIR`,
  `VARIANT`, `RUN_TOKEN`, `EXPECT_RUN_TOKEN` and `#SBATCH -J`, the two build
  directories, and every live reference in the READMEs, `tools/`, `CLAUDE.md`
  and the notebooks. **Nothing on scratch was renamed**: runs 31025, 31053,
  31056, 31070, 31075, 31090, 31094, 31095, 31103 and 31104 keep the old
  spellings in their directory names and in their own `build_info.txt`, so
  the "a run directory records the build it actually got" contract still
  holds and the job ID is still the durable key. References that cite a
  specific past run — the `compare_30d_adjViscBoost_run31025_…md` filename,
  the `runs/adjoint/adjViscBoost/` campaign directory, the 31053 rows in the
  profiling README, the 28453/28461 labels in
  `sensitivity_5yr_from180yrPk_visc2x.ipynb` — were deliberately left on the
  old tokens. Both build directories were rebuilt under their new names
  (they are not relocatable: `genmake2` bakes the absolute path into the
  `Makefile`) and pass every hook, dump-call and variant-source assertion.
  `build_tapAdj_tapProfile/` and `build_tapAdj_adjViscBoost/` were deleted
  the same day, leaving five build directories.
  - [ ] Optional: validate the two rebuilds with a run each, as the
    2026-09-04 path move was validated by 31090/31091 —
    `../../../tools/submit.sh scripts/submit_tapAdj_profile.sh` against
    31104, and `scripts/submit_tapAdj_adjVisc.sh` against 31103, then
    `tools/compare_adj_runs.sh`. Source and flags are unchanged, so this
    confirms the path-only rebuild rather than testing new behaviour.

- [x] ~~Rerun the kappa_v ensemble with the ADEXCH-fixed build~~ (added
  2026-08-31, **done 2026-09-01**). Reference 31039 + members 31040–31046,
  fresh `build_tapAdj/` (renamed `build_tapAdj_ckpAll/` on 2026-09-02) from `main`, member pickups repointed per
  the job-chaining recipe. Validated per run against the
  originals (30995, 31003–31009): `fc` + all 32 `adxx_*` bitwise identical;
  `ADJ*` differences seam-confined (0 cells outside the mask in all 4,026
  dump pairs/run) — and only for the 7 horizontal-stencil fields, the 4
  local-operator fields (`ADJdiffkr`, `ADJqnet`, `ADJqsw`, `ADJempmr`) being
  bit-identical; `ADJetan` new, 367 dumps/run, finite except M4 beyond its
  documented overflow lead. Analysis suite re-executed against the new runs;
  the only moved conclusion number is M4's departure lead 0.72 → 0.70 yr
  (52 → 50/366 usable dumps). Old runs cleared for scratch deletion.

- [x] ~~Rerun the kappa_v ensemble with the `-nocheckpoint` build and compare~~
  (added and **done 2026-09-02/03**). Jobs 31060–31067 (REF + M1–M7; same
  pickups and namelists; submitted through temporary copies of
  `submit_tapAdj_nocheckpoint.sh` with the member pickup repointed per the
  job-chaining recipe). Every pair **bitwise
  identical** to 31039–31046 (`fc`, 32 `adxx_*`, 4 393 `ADJ*`, `%MON`), the
  four blow-ups included; wall time 114.6 h → 76.8 h over the eight runs
  (1.45–1.65× per run, 1.54× on the reverse sweep, forward sweep unchanged).
  The executable rebuilt on 2026-09-02 also reproduces 31055 bitwise. Report
  and script in `analyses/DINO_1deg/adjoint/tapenade_profiling/`; the
  ensemble analysis keeps reading 31039–31046 (the sets are interchangeable).

- [x] ~~**Scratch layout: separate runs from analysis, executables and logs**~~
  (added and **done 2026-09-03**). `/scratch2/<user>/DINO_1deg_outputs/` was a
  flat `{frd,tapAdj}/` pair with `kappa_v_ensemble_analysis/` and
  `executables_preserved/` sitting among the run directories. It is now
  `runs/{forward,adjoint}/<campaign>/`, `analysis/<campaign>/`, `executables/`
  and `logs/`, with a `README.md` on scratch giving the campaign map. The five
  DINO submit scripts write to `runs/forward/` or `runs/adjoint/` directly, so
  **a new run lands unfiled at that level** and is moved into a campaign when
  it joins one — filing a run means updating the notebook that reads it. Run
  directory *names* are unchanged, so the `build_info.txt` `run_token` contract
  still holds and the job ID is still the durable key. All six pickup symlink
  targets were re-verified to resolve. Also pruned: `STDOUT.0001`–`0026` from
  every run (20.6 GB; only rank 0 writes `%MON`, the rest are `cg2d:` traces
  with no ERROR or WARNING anywhere) — moved to
  `/scratch2/<user>/_trash_20260903/`, not deleted.

- [ ] **Retry the four blown ensemble members (M1/M4/M5/M7) with adjVisc**
  (added 2026-08-31). Not possible before: the boost was silently inert under
  Tapenade until the 2026-08-31 mode-switch hooks, now `AUTODIFF_INADMODE_SET/UNSET`
  (first working boost: run 31025 vs
  31026 — `fc` bit-identical, adjoints damped). Pair
  `build_tapAdj_adjVisc.sh` with `submit_tapAdj_adjVisc.sh` and the
  member test case.

- [x] ~~Rebuild `build_tapAdj_adjVisc/` (and `build_tapAdj_rawTapenade/`
  if still wanted) so they pick up the ADEXCH fix.~~ Done 2026-08-31 in the
  hook redesign: `build_tapAdj_adjVisc/` was rebuilt with the
  `TAP_*` hooks (validated end to end, run 31025) and
  `build_tapAdj_rawTapenade.sh` was retired — raw Tapenade output *is* the
  working configuration now, so DINO has no control build to keep current.
  (Its leftover `build_tapAdj_rawTapenade/` directory was deleted 2026-09-02.)

- [x] ~~**Decide whether `build_tapAdj_nocheckpoint.sh` becomes the default
  adjoint**~~ (added 2026-09-01 on branch `tapenade-profiling`, merged into
  `main` 2026-09-02; **decided and done 2026-09-02**). Its 30-day run 31054 is
  bitwise identical to the plain build's 31052 (`fc`, 32 `adxx_*`, 73 `ADJ*`)
  and 1.5× faster (8:47 vs 13:13); at 5 years (31055 vs 31039) it is again
  bitwise identical (fc, 32 `adxx_*`, 4 393 `ADJ*`) in 9:35:58 against
  14:05:45 (1.47×, 4.5 h saved). What was done: `build_tapAdj.sh` /
  `submit_tapAdj.sh` are now symlinks to the `_nocheckpoint` pair (kept under
  its explicit name rather than retired, so every report and run name stays
  true); the plain pair was renamed `build_tapAdj_ckpAll.sh` /
  `submit_tapAdj_ckpAll.sh` (build directory `build_tapAdj_ckpAll/`); the list
  was tried in `build_tapAdj_adjVisc.sh` and reverted the same day (next
  item); every build script writes
  `build_info.txt` and the submit scripts name run directories from its
  `run_token`; all adjoint run directories on scratch were renamed to carry
  the build token. **Still open below: the SOMA port.**

- [x] ~~**adjVisc revalidation after the list fold-in**~~ (added and
  **done 2026-09-02 — and it failed, informatively**). Job 31056
  (`DINO_1deg_tapAdj_nocheckpoint_adjViscBoost_30d_from_rest_viscRef_run31056`,
  boost + the list, 8:48) vs 31025 (boost, every call checkpointed, 13:19):
  `fc` and all 441 `%MON` lines byte-identical, but all 66 `ADJ*` dumps and
  all 8 real `adxx_*` gradients differ at order one (RMS ratio 0.3–0.9) —
  where the plain pair is bitwise identical under the same list. Joint-mode
  recomputation runs *after* the mode-switch adjoint (then `TAP_INADMODE_SET_B`,
  now `AUTODIFF_INADMODE_SET_B`) has boosted the viscosities;
  split-mode tapes were taken in the forward sweep at forward viscosities, so
  the boost only reaches what the `_BWD` code reads live. The list was
  removed from `build_tapAdj_adjVisc.sh` again (run token
  `tapAdj_ckpAll_adjVisc`); 31056 stays on scratch as the record, report in
  `analyses/DINO_1deg/adjoint/tapenade_profiling/compare_30d_adjViscBoost_run31025_vs_nocheckpoint_run31056.md`.
  A faster boosted adjoint would need the boost applied to the taped
  intermediates too (i.e. boosting the *forward* sweep's recorded viscosities,
  which changes the forward trajectory) or a list restricted to routines whose
  taped values do not depend on the boosted parameters — a study, not a flag.

- [ ] **SOMA `-nocheckpoint` port needs its own profile** (added 2026-09-02).
  `mods_profile/` is setup-agnostic; a SOMA profiling build is the DINO one
  without `-mpi`. Until then SOMA's `build_tapAdj.sh` is a real script that
  checkpoints every call, so the bare name means different things per setup.

- [ ] **More binomial snapshots for the 5-year adjoint — only with more
  nodes, and for a small gain** (added 2026-09-01, corrected the same day).
  `C$AD BINOMIAL-CKP nTimeSteps+1 98 1` re-runs each step up to three times at
  87 841 steps; 418 snapshots would bring that to two. But 98 is a hard cap in
  the vendored `pkg/tapenade/adBinomial.c` (`nbSnap > 98` fails in
  `adBinomial_init`), so going higher needs a `-mods` shadow of that file with
  larger arrays; a `MAIN_DO_LOOP` snapshot is 8.98 MB per process (107
  arrays), so 418 of them are 3.8 GB per rank, ~109 GB for 27 ranks — three
  nodes, not one; and the binomial re-runs are only 17 % of the 5-year wall
  time (primal step 0.034 s vs 0.48 s per adjoint turn), so the whole exercise
  saves about 47 min of 14 h. It also changes the reverse schedule of the whole
  run and can only be validated at full length. Details under "Other levers" in
  `tools/tapenade_profiling/README.md`.

- [x] ~~**Retire the copy-staged source variants in `code/` and `code_tap/`**~~
  (added and **done 2026-09-02**, branch `code_tap-variants-cleanup`). The
  `_OG` / `_aste_90x150x60` / `_adapted_frm_aste_90x150x60` / `_mpi` /
  `_serial` siblings, and the bare files the build scripts regenerated from
  them, are gone (git history keeps them): `SIZE.h` is the one decomposition,
  the plain builds compile the vendored `pkg/autodiff` files (the `_OG`
  copies were byte-identical to them), the `TAP_INADMODE_*_B/_D` wrappers
  live in `code_tap/tap_inadmode.F` (moved into `code_tap/dummy_tap.F` by the
  next entry), and the four ASTE-derived shadows live
  in `code_tap/variants/adjointViscosity/` under their real names as a second
  `-mods` directory (`-mods="../code_tap/variants/adjointViscosity ../code_tap"`,
  asserted after `make`). Also removed: the debug-print `ini_procs.F` shadow
  (both copies), `code/pc`, the ASTE CVS header in `packages.conf`, SOMA's
  unused `SIZE.h_mpi`/`_serial`, and the staged-variants clause of
  `tools/pre_push_check.sh` — a build now leaves `git status` clean.
  Validation: all five builds rebuilt; against a pre-change snapshot their
  generated `.f` differ only in the files the change touches (the wrapper
  move, `ini_procs`, the build stamp). Run 31069 (default build, 30 d from
  the 180-yr pickup) is bitwise identical to 31054 — `fc`, 32 `adxx_*`,
  73 `ADJ*`, 441 `%MON` lines, 8:45 vs 8:47 — and run 31070 (boost, 30 d
  from rest) to 31025 — `fc`, 32 `adxx_*`, 66 `ADJ*`, 441 `%MON`, 13:15 vs
  13:19; its 14 `ADJetan` files are new only because 31025 predates that
  hook. Reports: `comparison_vs_*.txt` in the two run directories.

- [x] ~~**Give the Tapenade hooks their upstream names and layout**~~ (added and
  **done 2026-09-02**, branch `tapenade-hooks-upstream-shape`). `TAP_DUMMY_IN_STEPPING`,
  `TAP_DUMMY_FOR_ETAN` and `TAP_INADMODE_SET/UNSET` are gone: the upstream hooks
  keep their names and gain the wider interface under `#ifdef ALLOW_TAPENADE`
  in shadows of their own `pkg/autodiff` files (`#else` = upstream), the
  `_B`/`_D` bodies fill the stubs upstream ships in `pkg/tapenade/dummy_tap.F`
  (a shadow that also carries the mode-switch wrappers), and `flow_tap_local`
  re-declares the hooks under their upstream names. Tapenade keeps the *last*
  declaration of an external, so the library now rides in through
  `code_tap/adjoint_tap_local` (a `-adof` file sourcing the stock options and
  appending `-ext ../code_tap/flow_tap_local`) instead of `-tap_extra`. Same in
  SOMA (dump hooks only). Validation: every adjoint build's generated code is
  token-identical to the previous layout's after the renames (the profiling
  build differs only in the routine-name strings its instrumentation embeds);
  run 31074 (default, 30 d from the 180-yr pickup) is bitwise identical to
  31069 — `fc`, 32 `adxx_*`, 73 `ADJ*`, 441 `%MON`, 8:45 — run 31075 (boost,
  30 d from rest) to 31070 — `fc`, 32 `adxx_*`, 73 `ADJ*`, 441 `%MON`, 14:14 —
  and SOMA run 31076 (5 d) to 31033 — `fc`, 32 `adxx_*`, 61 `ADJ*`, 390 `%MON`.
  One trap found on the way: `dummy_tap.F` must include `AD_CONFIG.h`, the only
  definition of `ALLOW_ADJOINT_RUN`; without it the adjoint was still bitwise
  correct but wrote no `ADJ*` files (runs 31071–31073, deleted) — every adjoint
  build script now asserts after `make` that the compiled `dummy_tap.f` carries
  the 10 dump calls. At 5 years (2026-09-03): run 31077 (default build, from the
  180-yr pickup) is bitwise identical to 31055 — `fc`, 32 `adxx_*`, 4 393
  `ADJ*`, 18 801 `%MON` lines — in 9:36:30 against 9:35:58. Merged to `main`
  2026-09-03 (rebased, fast-forward; `main` = ea6f75f); the pre-merge state —
  the last commit with the `TAP_*` names — is tag
  `archive/20260903_pre-hook-upstream-rename`.

- [x] ~~**Write the hook redesign up as a talk, and take the internal name out
  of it**~~ (added and **done 2026-09-04**).
  A 13-frame Beamer deck, kept with the project notes and derived from the
  change note beside it, with its own Overleaf project. Each of the twelve modified
  files appears as `code_tap/<file>` → the checkpoint69m file it shadows, the
  first path linked to its blob on GitHub. DINO-only, and deliberately without
  an evidence table or an open-questions frame — both were cut in review; §4
  and §5 of the change note still hold that material. One error the review
  caught and the note now records: the Tapenade path already writes `adxx_*`
  control gradients through `pkg/ctrl`'s active-file machinery, so it is only
  the `ADJ*` adjoint-state dumps that the hooks supply.
  In the same pass `code_tap/variants/adjViscBoost/` and
  `input_tap/variants/adjViscBoost/` became `…/variants/adjointViscosity/`
  (namelist `data.autodiff_adjointViscosity`), since `adjViscBoost` was an
  internal coinage appearing in a document for outside readers. **The build
  identity kept the old tag** — `build_tapAdj_adjViscBoost.sh`,
  `build_tapAdj_adjViscBoost/`, `run_token=tapAdj_ckpAll_adjViscBoost` —
  because run directories are named from `run_token` and runs 31025, 31056,
  31070 and 31075 already carry it. (**Superseded 2026-09-05**: the build
  identity became `adjVisc`, closing that split; the four runs above keep
  their names, and `*adjVisc*` matches both spellings.)
  `build_tapAdj_adjViscBoost/` was rebuilt afterwards, since the rename left
  its four `-mods` symlinks dangling, and the rebuild was validated by run
  31090 (30 d from rest, the configuration of 31075): all 210 `ADJ*`/`adxx_*`
  files bitwise identical, `fc` = 3.99075406661494E-01 to every printed digit,
  all 441 `%MON` lines byte-identical, 27 `NORMAL END`, 13:50 against 14:14.
  The only file that differs is `build_info.txt`, which records the new
  `exe_md5`, commit and build time and is supposed to. Since 2026-09-04
  `tools/compare_adj_runs.sh` compares that file field by field (next entry),
  and the regenerated report for 31090 reads `EQUIVALENT`.

- [x] ~~**Split the notes out, rebuild every build directory from the new path,
  and stop the comparison tool failing on `build_info.txt`**~~ (added and
  **done 2026-09-04**). `notes/` became the private `impacts-notes` repository
  and this one `impacts-mitgcm`, checked out side by side under
  `Proj_ImPACTS/`; nothing reads across, and the Overleaf sync tool went with
  the notes. `genmake2` bakes the setup's absolute path into every generated
  `Makefile`, so the move invalidated all seven build directories; they were
  rebuilt from the new path and the rebuild validated by run 31091 (default
  build, 30 d from the 180-yr pickup), bitwise identical to 31074 — `fc`, 210
  `ADJ*`/`adxx_*` files, 441 `%MON` lines, 27 `NORMAL END`, 8:59 against 8:45
  — filed under `runs/adjoint/toolchain_validation/` beside it. That
  comparison, like 31090's, first returned `NOT CLEAN` on `build_info.txt`
  alone, because the tool `cmp`'d the record whole and no two builds share a
  build date or `exe_md5`; `tools/compare_adj_runs.sh` now splits the keys —
  provenance (`built`, `exe_md5`, `git_commit`, `git_modified_tracked_files`,
  `invoked_as`) is counted, configuration is checked and any difference
  printed as `CONFIG <key>` — and neither fails the verdict, so both pairs
  read `EQUIVALENT`. Checked on three pairs: 31074/31091 (same configuration),
  31052/31054 (no record on either side, reported as unconfirmed) and
  31075/31056 (four differing `CONFIG` fields, still `NOT CLEAN` on its 80
  differing sensitivities).

- [x] ~~**Move the build and submit scripts into `scripts/` and share their
  bodies**~~ (added and **done 2026-09-05**, on `main`). The ten DINO scripts
  sat at the setup's top level and the eight adjoint ones were near-copies of
  two templates — 270 of ~282 submit lines and 101 of ~150 build lines shared
  with the `ckpAll` copy, and the 2026-09-03 checksum-guard fix had touched all
  eight. Now each is a short *definition* in `scripts/` (build directory,
  `-mods` list, Tapenade flags, run token; `#SBATCH` header, committed
  defaults, pickup lines) that sources `tools/lib/build_body.sh` or
  `tools/lib/submit_body.sh`, with what makes the setup different — dT,
  `nTimeSteps` vs `endTime`, the calendar, the generated-hook list, the
  run-naming rule — in `scripts/setup_params.sh`. SOMA was converted the same
  day as the second consumer. Unchanged: every script name, the two default
  symlinks, `build_info.txt`, the run-directory contents. Changed with it:
  `tools/submit.sh` runs sbatch from the setup directory (the parent of
  `scripts/`); the submit body enforces the build/submit pairing
  (`EXPECT_RUN_TOKEN`) instead of only documenting it; forward builds write a
  record too (`run_token=frd`, forward names unchanged); SOMA runs are named
  from the token (`tapAdj_ckpAll`). One trade-off, documented in the body and
  in `CLAUDE.md`: the body is read at job start, so an edit to it reaches
  queued jobs. **Validation:** reference runs were made first with the old
  scripts and the untouched executables — 31092 (frd, 30 d from rest), 31093
  (ckpAll), 31094 (boost), 31095 (profiler), all 30 d; SOMA 31096 (frd, 30 d)
  and 31097 (adjoint, 5 d); 31091 already existed for the default — then all
  seven builds were rebuilt through the new scripts (every assertion passed,
  `git status` clean) and run once each. 31100 vs 31092: 131 files and 1 665
  `%MON` lines identical. 31101 (nocheckpoint) vs 31091, 31102 (ckpAll) vs
  31093, 31103 (boost) vs 31094: each `EQUIVALENT` — 210 `ADJ*`/`adxx_*`
  files, `fc` and 441 `%MON` lines identical, every configuration field of
  `build_info.txt` matching. 31104 (profiler) vs 31095: the same, and the 27
  `tapenade_profile.*.txt` tables identical once measured seconds are masked
  and rows sorted — now a recognised expected class in
  `tools/compare_adj_runs.sh`, which also learned to read a serial run's `fc`
  and `%MON` from `output_tap_adj.txt`. SOMA 31105 (frd) vs 31096: 117 files
  and 1 665 `%MON` lines identical; SOMA 31106 (adjoint) vs 31097:
  `EQUIVALENT` — 186 sensitivity files, `fc` and 390 `%MON` lines identical.
  The DINO runs are filed under `toolchain_validation/` on both the forward
  and the adjoint side, each new run carrying its `comparison_vs_*.txt`; the
  build logs, the comparison logs and the one-off validation driver are in
  `DINO_1deg_outputs/logs/` and `SOMA_1deg_outputs/logs/`.
