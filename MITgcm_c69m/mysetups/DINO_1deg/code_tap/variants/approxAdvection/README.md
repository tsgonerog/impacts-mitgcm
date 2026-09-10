# `code_tap/variants/approxAdvection/` — the approximate-advection adjoint under Tapenade

The two files here are the **source half** of the approximate-advection
adjoint: the flux-limited DST3 scheme (33) stays in the forward model, the
adjoint sweep is linearised about the unlimited DST3 scheme (30). That is what
MITgcm's stock `useApproxAdvectionInAdMode` (`pkg/autodiff`) does under TAF,
for configurations that keep the limited scheme in the forward model, because
the adjoint of a flux limiter is not a well-behaved transport operator
(Thuburn & Haine 2001, *J. Comput. Phys.* 171): in this setup it is what blows
up the long adjoints (`input_tap/variants/stability_study/`, runs 31166/31167,
2026-09-09). ECCO itself does not need the switch: its v4 forward model runs
the unlimited scheme 30 outright (`tempAdvScheme=saltAdvScheme=30`, vertical
scheme 3 implicit, in the ECCOv4 Release 4 `namelist/data`), which is also
the live `input*/data` here since 2026-09-09; this variant is the route for
keeping scheme 33 in the forward model instead. The namelist half is the
`data.autodiff` sibling of whichever variant sets `useApproxAdvectionInAdMode
= .TRUE.`; the live `input_tap/data.autodiff` does not set it.

`build_tapAdj_approxAdv.sh` compiles these by listing this directory *first*
in `genmake2 -mods`, exactly as `build_tapAdj_adjVisc.sh` does for
`adjointViscosity/`:

```
-mods="../code_tap/variants/approxAdvection ../code_tap"
```

| File | Upstream counterpart (vimdiff target) | What the diff shows |
| --- | --- | --- |
| `gad_advection.F` | `../../../../../MITgcm/pkg/generic_advdiff/gad_advection.F` | one CPP guard changed, `ALLOW_AUTODIFF_TAMC` → `ALLOW_AUTODIFF`, around the block that swaps 33 for 30 when `inAdMode .AND. useApproxAdvectionInAdMode`; under Tapenade the TAF-only macro is undefined and the block was preprocessed out, which is why the switch was inert (31158/31159 byte-identical to 31140/31152) |
| `gad_implicit_r.F` | `../../../../../MITgcm/pkg/generic_advdiff/gad_implicit_r.F` | the same swap added for the implicit vertical advection (DINO sets `tempImplVertAdv`/`saltImplVertAdv`), which the vendored file selects from its scheme argument alone and which the stock switch therefore never reached, under TAF either. The argument is renamed `advectionSchArg` and a local `advectionScheme` carries the scheme used, the layout `gad_advection.F` already has; everything below that point is the vendored code |

**Why the build checkpoints every call.** The switch is a run-time branch on
`inAdMode`, which `AUTODIFF_INADMODE_SET_TAP_B` (the mode-switch hook in
`mods_tapenade_hooks/dummy_tap.F`) sets `.TRUE.` at the start of every
backward step and `UNSET_TAP_B` clears at its end. The branch is re-evaluated
only where Tapenade re-runs a routine's primal inside the backward sweep,
that is in joint (checkpointed) mode; in split mode the forward sweep tapes
the control flow with `inAdMode = .FALSE.` and the `_BWD` code replays the
limiter. The default build's `-nocheckpoint` list splits `gad_advection`,
`gad_calc_rhs`, `gad_dst3fl_adv_x/y` and `gad_dst3fl_impl_r`, so the switch
is inert there whatever the guard says. Hence `build_tapAdj_approxAdv.sh` is a
`ckpAll` build (run token `tapAdj_ckpAll_approxAdv`, ~1.5× the default's
reverse-sweep time). A tuned list for this build would have to keep the four
routines above (and `gad_implicit_r`) joint; nothing has been profiled for it.

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
