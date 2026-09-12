# `input_tap/variants/` — alternative namelists

The **adjoint** model's variants. The forward model's are in [`../../input/variants/`](../../input/variants/), organised the same way and using the same group names where a study has both halves.

**Nothing here is staged unless it is asked for.** `input_tap/` itself holds exactly
the files MITgcm reads and every one of them is copied into every run; this
directory is skipped entirely (`find -maxdepth 1`), and only the variant a run
selects is staged.

## How a variant is selected

```bash
IMPACTS_TEST_CASE=<group>/<tag> ../../../tools/submit.sh scripts/<submit script>
```

which stages `variants/<group>/data_<tag>` as `data`.

## The two rules

**1. A file is named after the MITgcm file it replaces.** The name is
`<mitgcm-file>_<tag>` — so in `stability_study/`,
`data_from180yrPk_viscRef_ReMax2_gmOn` replaces `data`,
`data.pkg_from180yrPk_viscRef_ReMax2_gmOn` replaces `data.pkg` and
`data.autodiff_from180yrPk_viscRef_ReMax2_gmOn` replaces `data.autodiff`. The
part before the first underscore tells you which file you are looking at.

**2. Every file sharing a tag inside a group is staged together.** Selecting a
tag stages its `data` *and* every sibling `<mitgcm-file>_<tag>` beside it. That
is what lets one variant change a package flag as well as the namelist:
`grdchk_repair/from180yrPk_viscRef_ReMax2_adv30_grdchkON` stages
`data_...grdchkON`, `data.pkg_...grdchkON` and `data.grdchk_...grdchkON`, so the
run really does get `useGrdchk=.TRUE.` and the moved perturbation point. Before this existed
(2026-08-28) only the `data` half was staged, and a forward KPP variant (deleted
on 2026-09-12) silently ran without KPP.

## The adjoint-mode switches (since 2026-09-12)

DINO's adjoint is approximate by design: GM/Redi, where `data.pkg` turns it on,
acts in the forward sweep only (`useGMRediInAdMode=.FALSE.`), and the
flux-limited DST3 (scheme 33) is replaced by the unlimited one (scheme 30) in
the adjoint sweep (`useApproxAdvectionInAdMode=.TRUE.`). Every DINO adjoint
build honours both, and the submit body refuses a staged namelist that turns
GM/Redi on or advects with scheme 33 without the matching switch
(`check_staged_namelists` in `scripts/setup_params.sh`). A variant without a
`data.autodiff` sibling gets the live one, which sets both. A record of an
exact adjoint runs only when that is asked for:

```bash
IMPACTS_ALLOW_EXACT_ADJOINT=1 IMPACTS_TEST_CASE=<group>/<tag> ../../../tools/submit.sh scripts/submit_tapAdj.sh
```

Those records are `grdchk_repair/from180yrPk_viscRef_ReMax2_approxAdvOff_grdchkON`
and `stability_study/from180yrPk_viscRef_ReMax2_gmOn`. A record without its own
`data.pkg` or `data.autodiff` stages the live file, so it runs today's
configuration (GM/Redi in the forward sweep since 2026-09-11, scheme 30 in the
adjoint sweep); the records for which that meant a different configuration from
their runs' were removed on 2026-09-12 (next section), and every record left
gives the configuration of its runs (`stability_study/from180yrPk_viscRef_ReMax2`
that of 31279 and 31282, not of its first run 31163, which was GM-free and exact).

## Groups

| Group | What it varies |
| --- | --- |
| [`baseline/`](baseline/) | The GM-free configuration of 31206 and of the 2026-09-10 κ ensemble adjoints (`from180yrPk_viscRef_ReMax2_gmOff`), kept as a record (the runs deleted 2026-09-12; provenance in `logs/deleted_run_records/`); since 2026-09-09 the live `input_tap/data` is the baseline |
| [`adjointViscosity/`](adjointViscosity/) | `data.autodiff_additions`, the adjoint-mode viscosity inflation (`viscFacInAd = 10.`): lines that `submit_tapAdj_adjVisc.sh` adds to the staged `data.autodiff`, not a tag. **Needs the matching build and submit script** — `build_tapAdj_adjVisc.sh` + `submit_tapAdj_adjVisc.sh` |
| [`grdchk_repair/`](grdchk_repair/) | The finite-difference gradient check with its perturbation moved onto the sensitivity peak and `useGrdchk` switched on — the check that can actually pass (all five points to 0.0035 % under scheme 30, run 31172), unlike the committed `data.grdchk` point |
| [`stability_study/`](stability_study/) | What makes the adjoint blow up, and what holds it: GM/Redi in either sweep, and the finite differences of the 2026-09-11 test; its README keeps the record of the 2026-09-09 viscosity and flux-limiter rows |

## Removed on 2026-09-12

Variants that no longer gave the configuration of their runs were removed
(git history has them). Each tag was staged as the submit body stages it today
and compared with the namelists its runs staged, counting only differences that
change a run, and with whether the run's build applied its switches as every
build does now. That removed the whole `kappa_v_ensemble/` group (M1–M7,
`M<k>_ReMax2`, `REFm10_ReMax2`, `REFp10_ReMax2`) and the whole
`viscosity_study/` group, `baseline/from180yrPk_visc2x`,
`grdchk_repair/from180yrPk_visc2x_grdchkON` and `…adv33_grdchkON`, and thirteen
`stability_study/` tags (listed in its README). The runs no analysis read were
deleted with their variants (31032, 31037, 31052–31054, 31074, 31093, 31095,
31152–31159, 31178), and the others (28486, 31022, 31028, 31039–31046, 31137,
31140, 31166–31168, 31176, 31208–31220 even, 31231, 31232 and 31247–31252)
later the same day, with both κ_v ensembles, which are to be rerun under the
cleaned setup. Each deleted run keeps its staged namelists and provenance in
`logs/deleted_run_records/` of the scratch output tree.

The kept `baseline/` record (its run 31206 deleted the same day) and the kept
2026-09-11 `stability_study/` rows started from the year-180 pickup of the
REF_ReMax2 forward leg 31205, also deleted. Repeating those runs first reruns
that leg (`input/variants/kappa_v_ensemble/data_REF_ReMax2`), except for
`thetaPatchFD_gmFwd`, whose perturbed copies of the pickup are still on scratch
(`stability_study/README.md`).

## Adding to this

- **A new member of an existing study** — drop `data_<tag>` into that group. If
  it needs another MITgcm file changed, add `<that-file>_<tag>` beside it with
  the *same* tag and it is staged automatically.
- **A new study** — make `variants/<name>/`, give it a `README.md` saying what
  it varies and why, and put its members in. Nothing else needs editing: the
  submit scripts resolve any `<group>/<tag>`.
- Name the group for the question it asks, not the method, so it survives a
  change of approach. Keep the same group name on both sides where a study has a
  forward and an adjoint half.

The run directory is named after the **tag only**, not the group — a run is
described by its physics, not by where its namelist lives in this repository.
So `grdchk_repair/from180yrPk_viscRef_ReMax2_adv30_grdchkON` produces
`..._from180yrPk_viscRef_ReMax2_adv30_grdchkON_run<jobid>`.
