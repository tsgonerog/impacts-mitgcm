# `code_tap/variants/approxAdvection/` — the approximate advection, implicit vertical part

`useApproxAdvectionInAdMode` (`pkg/autodiff`, set in `data.autodiff`) keeps the
flux-limited DST3 scheme (33) in the forward model and linearises the adjoint
sweep about the unlimited DST3 scheme (30), because the adjoint of a flux
limiter is not a well-behaved transport operator (Thuburn & Haine 2001,
*J. Comput. Phys.* 171): in this setup it is what blows up the long adjoints
(`input_tap/variants/stability_study/`, runs 31166/31167, 2026-09-09). ECCO
itself does not need the switch: its v4 forward model runs the unlimited scheme
30 outright (`tempAdvScheme=saltAdvScheme=30`, vertical scheme 3 implicit, in
the ECCOv4 Release 4 `namelist/data`), as this setup's live `input*/data` did
from 2026-09-09 to 2026-09-10. Since 2026-09-10 the live `input*/data` keep
scheme 33 and the live `input_tap/data.autodiff` sets the switch.

Under Tapenade the switch needs two source changes:

| File | Where it lives | What it does |
| --- | --- | --- |
| `gad_advection.F` | `MITgcm_c69m/mods_tapenade_hooks/` since 2026-09-12 (in this directory from 2026-09-09) | The guard of the block that swaps 33 for 30 widened from `ALLOW_AUTODIFF_TAMC`, which every Tapenade build undefines, to `ALLOW_AUTODIFF`: the horizontal fluxes and, with explicit vertical advection, the vertical ones. Every adjoint build of every setup compiles it; it is patch `0003` of the upstream proposal (that directory's README) |
| `gad_implicit_r.F` | here | The same swap added for the implicit vertical advection, which the vendored file selects from its scheme argument alone, so that the stock switch never reaches it, under TAF either. The argument is renamed `advectionSchArg` and a local `advectionScheme` carries the scheme used, the layout `gad_advection.F` already has; everything below that point is the vendored code |

Only `build_tapAdj_approxAdv.sh` compiles this directory, listed ahead of
`code_tap/` in `genmake2 -mods` (`-mods="../code_tap/variants/approxAdvection ../code_tap"`,
behind the shared hooks directory that the build body puts first). With
explicit vertical advection, production since 2026-09-10, `gad_implicit_r.F`
only solves the implicit diffusion and its swap is dormant, so the `approxAdv`
and `ckpAll` builds then give the same adjoint. The submit body refuses a
namelist that sets the switch and advects tracers implicitly in the vertical
with any build other than `approxAdv`.

`TREE_BASE.txt` lists the tree file and git blob the copy here was derived
from; `tools/check_variant_shadows.sh` (run by `tools/pre_push_check.sh`) fails
when that tree file changes under it.

**Why the builds that honour the switch checkpoint every call.** The switch is
a run-time branch on `inAdMode`, which `AUTODIFF_INADMODE_SET_TAP_B` (the
mode-switch hook in `mods_tapenade_hooks/dummy_tap.F`) sets `.TRUE.` at the
start of every backward step and `UNSET_TAP_B` clears at its end. The branch
is re-evaluated only where Tapenade re-runs a routine's primal inside the
backward sweep, that is in joint (checkpointed) mode; in split mode the forward
sweep tapes the control flow with `inAdMode = .FALSE.` and the `_BWD` code
replays the limiter. The `-nocheckpoint` list of `build_tapAdj_nocheckpoint.sh`
splits `gad_advection` and routines above it, so the submit body refuses that
build whenever `data.autodiff` sets the switch.

**What the adjoint then is.** The trajectory is the scheme-33 forward's (the
checkpoint snapshots and the replays between them run with `inAdMode =
.FALSE.`, so `fc` and every forward field are those of the plain run); inside
each backward step the re-run primal of the advection routines takes the
scheme-30 branch, so the tape holds scheme-30 intermediates computed from
scheme-33 states and the `_B` code is the adjoint of scheme 30 about that
state. The result is not the exact gradient of the scheme-33 model: the
gradient check `grdchk_repair/from180yrPk_viscRef_ReMax2_approxAdv_grdchkON`
measures the difference (its finite differences are of the scheme-33 forward).

After `make`, the build script checks that the compiled `gad_advection.f`,
`gad_implicit_r.f` and their generated `_b.f` carry the switch's name, which
no vendored preprocessed form does.
