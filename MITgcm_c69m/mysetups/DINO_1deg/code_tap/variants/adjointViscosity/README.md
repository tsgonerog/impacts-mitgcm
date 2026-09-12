# `code_tap/variants/adjointViscosity/` — sources for the adjoint-mode viscosity inflation

The four files here are the **source half** of the adjoint-mode viscosity
configuration;
the namelist half is `input_tap/variants/adjointViscosity/data.autodiff_additions`,
the lines `submit_tapAdj_adjVisc.sh` adds to the staged `data.autodiff` (a
complete `data.autodiff_adjointViscosity` until 2026-09-12).
`build_tapAdj_adjVisc.sh` compiles them by listing this directory *first*
in `genmake2 -mods`:

```
-mods="../code_tap/variants/adjointViscosity ../code_tap"
```

`genmake2` gives a file in an earlier `-mods` directory preference over a
same-named file anywhere later, so these four shadow both `code_tap/` and the
vendored `MITgcm/pkg/autodiff/`. No other build script names this directory,
and `genmake2` only enumerates `*.F *.h *.c *.flow *.F90` directly inside each
`-mods` directory, so the plain builds never see what is in here. Nothing is
copied into `code_tap/`, and building leaves the working tree clean. The files
carry their real MITgcm names because the compiler, not a script, resolves
them — the directory name is the variant tag. After `make`, the build script
checks that the compiled `autodiff_*.f` really came from here.

| File | Upstream counterpart (vimdiff target) | What the diff shows |
| --- | --- | --- |
| `AUTODIFF_PARAMS.h` | `../../../../../MITgcm/pkg/autodiff/AUTODIFF_PARAMS.h` | declares `inAd*`/`outAd*` (`viscA4Grid`, `viscAhGrid`, `viscArNr`, `diffKh*`, `diffK4*`, `SEAICEadjMODE`) and adds them to the common blocks |
| `autodiff_readparms.F` | `../../../../../MITgcm/pkg/autodiff/autodiff_readparms.F` | reads them from `AUTODIFF_PARM01`, defaults them to `UNSET_RL`, echoes them to STDOUT |
| `autodiff_inadmode_set_ad.F` | `../../../../../MITgcm/pkg/autodiff/autodiff_inadmode_set_ad.F` | the `inAd*` apply block, run at the start of each backward step through `AUTODIFF_INADMODE_SET_TAP_B` in `../../../../../mods_tapenade_hooks/dummy_tap.F` |
| `autodiff_inadmode_unset_ad.F` | `../../../../../MITgcm/pkg/autodiff/autodiff_inadmode_unset_ad.F` | the `outAd*` restore block, run at the end of each backward step through `AUTODIFF_INADMODE_UNSET_TAP_B` in `../../../../../mods_tapenade_hooks/dummy_tap.F`, so checkpoint re-forwards use forward physics |

Each file is the upstream c69m file plus its block, in the same additive
layout as every other shadow in `code_tap/`. The three `.F` files carry a
short header comment saying so; `AUTODIFF_PARAMS.h` deliberately does not,
because the preprocessor copies a header's comments into every `.f` that
includes it (about 25 files here), which would make the generated code of
this build differ from the plain build's in files the variant never touches.

**Provenance.** The apply block and the parameter plumbing were adapted from
the ASTE 90×150×60 regional setup; its original `autodiff_inadmode_set_ad.F`
is archived in `../../../00_archive/code_tap/`, whose README describes the
c69f→c69m port. The restore block has no ASTE ancestor: it was written on
2026-08-31, when the Tapenade mode-switch hooks first made the mechanism reachable
under Tapenade. Until 2026-09-02 these files lived in `code_tap/` itself as
`*_aste_90x150x60` / `*_adapted_frm_aste_90x150x60` siblings that the build
script copied over the bare names; the copy step and the suffixes are gone,
and git history holds the old layout.

Not every parameter the apply block sets reaches the physics here:
`viscA4Grid` is inert because `useBiharmonicVisc` is fixed at initialisation
(`set_parms.F:148`), `viscAhGrid` acts only because the forward namelist's
`viscAh[D/Z]file` keep `useVariableVisc` true (`set_parms.F:132`), and the
stock `viscFacAdj` multiplies only those file fields
(`mom_calc_visc.F:509-511`). The namelist half's README has the table, and
the 2026-09-09 fix of its stale `outAd*` values.

Two rules:

- **The build and the submit script are a pair.** This directory only makes
  the parameters exist; `submit_tapAdj_adjVisc.sh` adds the lines that give
  them values to the staged `data.autodiff`. Either half alone would run plain
  physics, which is why each submit script refuses a build of another run
  token.
- **The boost stays a checkpoint-everything build.** The `-nocheckpoint`
  list of 2026-09-02 changed the boosted adjoint at order one (run 31056 vs
  31025, 2026-09-02) — see `../../../README.md`, "Profiling and checkpoint
  tuning".

**Validated 2026-09-02.** Run 31070 (this layout, 30 d from rest) reproduces
run 31025 (the same sources while they were still copy-staged) bit for bit:
`fc`, all 32 `adxx_*`, all 66 common `ADJ*` dumps and the 441-line `%MON`
stream. Its report went with the 31070 directory, deleted in the 2026-09-03
scratch cleanup; the surviving link in the chain is **31075**
(`runs/adjoint/toolchain_validation/…run31075/`), whose
`comparison_vs_…run31070.txt` records 31075 ≡ 31070, and 31025 is still on
scratch under `runs/adjoint/adjViscBoost/`. So 31025 ≡ 31070 ≡ 31075 is
reconstructible from what is left.

**Tracking the tree (since 2026-09-12).** `TREE_BASE.txt` names the four
`pkg/autodiff` files these copies stand in for and the git blob of each that
they were last checked against. They came from ASTE, not from those blobs, so
they differ by more than a few lines; `tools/check_variant_shadows.sh` (run by
`tools/pre_push_check.sh`) fails when any of the four tree files changes, which
is the moment to carry the change into the copy.
