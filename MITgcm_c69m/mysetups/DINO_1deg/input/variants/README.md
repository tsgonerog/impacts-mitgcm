# `input/variants/` — alternative namelists

The **forward** model's variants. The adjoint's are in [`../../input_tap/variants/`](../../input_tap/variants/), organised the same way and using the same group names where a study has both halves.

**Nothing here is staged unless it is asked for.** `input/` itself holds exactly
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
`data_from170yrPk_viscRef_gmOff` replaces `data` and
`data.pkg_from170yrPk_viscRef_gmOff` replaces `data.pkg`. The part before the
first underscore tells you which file you are looking at.

**2. Every file sharing a tag inside a group is staged together.** Selecting a
tag stages its `data` *and* every sibling `<mitgcm-file>_<tag>` beside it. That
is what lets one variant change a package flag as well as the namelist:
`stability_study/from170yrPk_viscRef_gmOff` stages both `data_...gmOff` and
`data.pkg_...gmOff`, so the run really does get `useGMRedi=.FALSE.`. Before this
existed (2026-08-28) only the `data` half was staged, and a KPP variant
(`scheme_tests/from_rest_viscRef_kppON`, deleted on 2026-09-12) silently ran
without KPP.

## Groups

| Group | What it varies |
| --- | --- |
| [`baseline/`](baseline/) | The previous production configuration, kept as a record — the 200-year spin-up at 2× viscosity (`from_rest_visc2x`); since 2026-09-09 the live `input/data` is the baseline |
| [`viscosity_study/`](viscosity_study/) | The lateral-viscosity formulation: `PARM05` files against the `PARM01` `viscAhGrid` scalar, Leith, biharmonic |
| [`scheme_tests/`](scheme_tests/) | One scheme at a time, viscosity held at reference: advection scheme 30 (the C-D scheme and KPP variants were deleted on 2026-09-12) |
| [`stability_study/`](stability_study/) | Why 2× viscosity stabilises the forward model, and what else does: restarts of the 2× spin-up's year-170 pickup |
| [`from70yrPk_sweep/`](from70yrPk_sweep/) | `viscAr` × `diffKr` × advection sweep restarted from the 70-year pickup |
| [`kappa_v_ensemble/`](kappa_v_ensemble/) | The vertical-mixing perturbation ensemble of the surrogate proposal — forward legs |

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
So `kappa_v_ensemble/M3_ReMax2` produces `..._M3_ReMax2_run<jobid>`.
