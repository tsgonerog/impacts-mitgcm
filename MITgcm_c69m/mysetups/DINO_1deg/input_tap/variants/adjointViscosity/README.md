# `adjointViscosity/` — inflated viscosity during the adjoint sweep

`data.autodiff_adjointViscosity` sets a **larger viscosity and diffusivity in the
adjoint sweep than in the forward**: `viscFacInAd = 10.` against
`viscFacInFw = 1.`, `inAdviscArNr = 2.E-3` against a forward `1.2E-4`, plus
added `inAddiffKhT/S`. The `outAd*` values restore the forward settings on the
way out. It is the standard trick for keeping a long adjoint from blowing up,
and the values were adapted from the ASTE 90×150×60 regional setup.

**This is a build *and* a namelist variant, and the two must be used together.**

| Piece | Supplies |
| --- | --- |
| `build_tapAdj_adjVisc.sh` | compiles `code_tap/variants/adjointViscosity/` ahead of `code_tap/` (its first `-mods` directory; see the README there), which is what makes the `inAd*`/`outAd*` parameters exist at all |
| `submit_tapAdj_adjVisc.sh` | copies this file over `data.autodiff` in the staged run directory, which is what gives them values |

Pairing the plain submit script with the adjVisc build, or the reverse,
silently runs the ordinary configuration.

The build checkpoints every call, like `build_tapAdj_ckpAll.sh`, and its run
directories are named `DINO_1deg_tapAdj_ckpAll_adjVisc_…`. It deliberately
does **not** carry the default build's `-nocheckpoint` list: tried on
2026-09-02 (run 31056 vs 31025), the split-mode boost differs at order one in
every sensitivity field, because joint-mode recomputation happens after the
mode-switch hook has boosted the viscosities and split-mode tapes were taken
before — see `../../README.md`, "Profiling and checkpoint tuning".

This file is *not* selected through `IMPACTS_TEST_CASE`; the submit script
copies it by name, independently of whichever `data` variant is chosen.

## What each switch reaches, and the 2026-09-09 fix

Reviewed against `pkg/mom_common/mom_calc_visc.F`, `model/src/set_parms.F`,
`model/src/calc_viscosity.F` and `model/src/calc_3d_diffusivity.F`:

| Line | Effect in this configuration |
| --- | --- |
| `viscFacInAd = 10.` | multiplies **only** the `PARM05` `viscAh[D/Z]file` fields (`mom_calc_visc.F:509-511`, under `AUTODIFF_ALLOW_VISCFACADJ` in `code_tap/AUTODIFF_OPTIONS.h`). A scalar `viscAh` or `viscAhGrid` is never multiplied. This is the stock, structure-preserving boost of DINO's A_h = ½·U_v·Δx field and the reason the viscosity stays a file (setup README, "Lateral viscosity and vertical diffusivity: file or parameter") |
| `inAdviscAhGrid = 2.5E-2` | adds `2.5E-2·L²/(4Δt)` (43 000 m²/s at the equator, 5 000 at 70°) inside `MOM_CALC_VISC`, which is only called because the files set `useVariableVisc` at initialisation (`set_parms.F:132`); its latitude structure is cos²φ, not the law's cos φ |
| `inAdviscA4Grid = 0.05E0` | **inert**: `useBiharmonicVisc` (`set_parms.F:148`) is fixed `.FALSE.` at initialisation because the forward namelist has no biharmonic term, so `mom_vecinv` never applies the A4 dissipation |
| `inAdviscArNr = 2.E-3` | acts: `viscArNr(k)` is read every step (`calc_viscosity.F:71`) |
| `inAddiffKhT/S = 5.E2` | equal to the forward `diffKhT/S = 500.`, so no boost |
| (`inAddiffKrNrT/S`, commented out) | would be inert even if enabled: under `ALLOW_3D_DIFFKR` the run-time vertical diffusivity is the 3-D `diffKr` array (`calc_3d_diffusivity.F`), not `diffKrNrT(k)`. Boosting it means scaling the array in the set/unset pair |

**The `outAd*` values are not cosmetic.** `AUTODIFF_INADMODE_UNSET_B` writes
them back at the end of every backward step, and every checkpoint replay of
the forward model that follows runs with them, so each must equal the forward
namelist's value or the replayed trajectory drifts from the one the forward
sweep taped. Until 2026-09-09 `outAdviscAhGrid` was `1.8E-2` (the
`viscosity_study/viscGrid1p8e-2` value; the production namelists set no
`viscAhGrid`, so the replays carried an extra `1.8E-2·L²/(4Δt)` — 31 000 m²/s
at the equator) and `outAddiffKhT/S` were `0` against a forward `500` (no
lateral tracer diffusion in the replays). Every boosted run from 31025 to
31138 ran that way; `fc` and the `%MON` stream were unaffected, because they
come from the forward sweep. The values are now `0.` and `5.E2`; run 31141
against 31138 (30 d from rest, same executable, `TODO.md`) records the
difference.
