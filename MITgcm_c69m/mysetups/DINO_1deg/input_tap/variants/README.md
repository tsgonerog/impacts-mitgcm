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
`<mitgcm-file>_<tag>` — so `data_M3` replaces `data`, `data.pkg_M3` replaces
`data.pkg`, `data.autodiff_M3` replaces `data.autodiff`. The part before the
first underscore tells you which file you are looking at.

**2. Every file sharing a tag inside a group is staged together.** Selecting a
tag stages its `data` *and* every sibling `<mitgcm-file>_<tag>` beside it. That
is what lets one variant change a package flag as well as the namelist:
`grdchk_repair/from180yrPk_visc2x_grdchkON` stages `data_...grdchkON`,
`data.pkg_...grdchkON` and `data.grdchk_...grdchkON`, so the run really does get
`useGrdchk=.TRUE.` and the moved perturbation point. Before this existed
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
and `stability_study/from180yrPk_{visc2x,viscRef,viscRef_ReMax2}_gmOn`. A record
without its own `data.pkg` or `data.autodiff` stages the live file, so it runs
today's configuration (GM/Redi in the forward sweep since 2026-09-11, scheme 30
in the adjoint sweep), not the one it was run with; the group READMEs say which
of their records that affects.

## Groups

| Group | What it varies |
| --- | --- |
| [`baseline/`](baseline/) | Earlier reference adjoint configurations, kept as records (`from180yrPk_visc2x`, `from180yrPk_viscRef_ReMax2_gmOff`); since 2026-09-09 the live `input_tap/data` is the baseline |
| [`viscosity_study/`](viscosity_study/) | Adjoint runs at the `viscAhGrid` settings of the forward-side study of the same name |
| [`adjointViscosity/`](adjointViscosity/) | `data.autodiff_additions`, the adjoint-mode viscosity inflation (`viscFacInAd = 10.`): lines that `submit_tapAdj_adjVisc.sh` adds to the staged `data.autodiff`, not a tag. **Needs the matching build and submit script** — `build_tapAdj_adjVisc.sh` + `submit_tapAdj_adjVisc.sh` |
| [`kappa_v_ensemble/`](kappa_v_ensemble/) | The vertical-mixing perturbation ensemble of the surrogate proposal — the 5-year adjoints |
| [`grdchk_repair/`](grdchk_repair/) | The finite-difference gradient check with its perturbation moved onto the sensitivity peak and `useGrdchk` switched on — the check that can actually pass (0.9 % at the peak, run 31037), unlike the committed `data.grdchk` point |
| [`stability_study/`](stability_study/) | What makes the adjoint blow up, and what holds it: viscosity, GM/Redi in either sweep, the flux limiter's adjoint (2026-09-09 to 2026-09-11) |

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
So `kappa_v_ensemble/M3` produces `..._M3_run<jobid>`.
