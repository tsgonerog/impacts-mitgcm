# `grdchk_repair/` — a gradient check that can actually pass

One tag, `from180yrPk_visc2x_grdchkON`: the `baseline/from180yrPk_visc2x`
namelist plus two sibling overrides — `data.pkg` with `useGrdchk = .TRUE.`
(the committed DINO default is `.FALSE.` since 2026-08-28) and a `data.grdchk`
with the perturbation moved from (4,8,1) to the 30-day sensitivity peak
(i=2, j=127, k=26 on the cost section) and `grdchk_eps` raised to `1e-3`,
per the repair prescribed in the root `README.md` ("Verifying correctness").

Since 2026-09-09 there is a second tag, `from180yrPk_viscRef_ReMax2_adv30_grdchkON`,
the same check under the new production configuration (reference viscosity,
`viscAhReMax=2.`, scheme 30). **Run 31172 (2026-09-09) passes at all five
points**: 1 − fd/adj = −9.8e-7, −1.6e-5, −3.5e-5, +4.9e-6, +5.1e-6 (0.0001 %
to 0.0035 %), against 0.88 % and then 318 %, 78 %, 87 %, 45 % for the same
points under scheme 33 (31037). The four weaker points were never at a noise
floor of the model; they were at the flux limiter's.

**Three more tags the same day, all at reference viscosity + `viscAhReMax=2.`
with the flux-limited scheme 33 in the forward model** (runs 31177–31179,
each 30 d from the year-180 pickup, the same five points, `grdchk_eps=1e-3`):

| Tag | Adjoint | Build / submit pair |
| --- | --- | --- |
| `from180yrPk_viscRef_ReMax2_adv33_grdchkON` | the exact adjoint of scheme 33 (31178) | the default `build_tapAdj.sh` / `submit_tapAdj.sh` |
| `from180yrPk_viscRef_ReMax2_approxAdv_grdchkON` | scheme 33 forward, scheme 30 in the adjoint sweep: the `data.autodiff` sibling sets `useApproxAdvectionInAdMode=.TRUE.` (31177) | `build_tapAdj_approxAdv.sh` / `submit_tapAdj_approxAdv.sh` |
| `from180yrPk_viscRef_ReMax2_approxAdvOff_grdchkON` | the same build with the switch `.FALSE.` — the control (31179) | the same pair |

What they show. The reference cost and all ten perturbed costs are
**digit-for-digit identical across the three runs** (`fcref` = 0.425345777609569,
the plain 30-d run 31163's value; FC1/FC2 of point 1 = 0.42588141290819 /
0.42594121354982): the perturbed runs are primal integrations of the
scheme-33 forward and depend on nothing the adjoint build does, and the
`approxAdv` build with its switch off is the `ckpAll` adjoint (its five
`ADJ GRAD` values equal 31178's to every digit). But those perturbed costs
are **not a derivative's**: at every point both the `+eps` and the `−eps` run
land 5–6e-4 *above* the reference (point 4: one 7e-5 below, the other 6e-4
above), a one-signed jump of 0.13 % of `fc` from a 1e-3 K change in one
cell, where the adjoint predicts ±4e-5. Under scheme 30 (31172) the same
perturbations give ±3.7e-5, symmetric, and agree with the adjoint to 1e-6.
So at this viscosity the scheme-33 cost is non-smooth at the scale of
`grdchk_eps`: the flux limiter's branches flip under the perturbation and
the 30-d mean heat transport moves with them (Thuburn & Haine 2001). The
exact adjoint of scheme 33 "fails" its own check by 22 % at the strongest
point and by factors at the rest (31178, RMS ratio 21.5) — the same pattern
as 31037 at 2× viscosity (0.9 %, then 318 %, 78 %, 87 %, 45 %), ten times
worse because the limiter is busier in the sharper reference-viscosity
state. The three adjoint gradients at the strongest point: exact scheme 33
−3.8353e-2, approximate (scheme 30 about the scheme-33 trajectory)
−3.7173e-2, exact scheme 30 (31172, its own trajectory) −3.7347e-2: the
approximation moves the gradient by 3 %, the trajectory by 0.5 %. The
conclusion is not that any of these adjoints is wrong but that **a
flux-limited forward cannot be gradient-checked at 1e-3 K** — and that the
production choice of scheme 30 is what makes the model differentiable at
that amplitude, not a mask over it.

**Since 2026-09-12 every DINO adjoint build honours `useApproxAdvectionInAdMode`**
(the `approxAdv` build was merged into `ckpAll`, the default pair), so the last
column above records what the runs used, not what a rerun needs. A tag without
a `data.autodiff` sibling stages the live one, which sets the switch:
`adv33_grdchkON` now gives the approximate adjoint of 31177 rather than the
exact one of 31178, and a rerun of `from180yrPk_visc2x_grdchkON` is approximate
too (31037 was exact). `approxAdv_grdchkON` and `adv30_grdchkON` run as they
are. The exact scheme-33 check is `approxAdvOff_grdchkON`, whose sibling turns
the switch off (31179, the same gradients as 31178); the submit body refuses
it unless the exact adjoint is asked for.

Every run here started from the 2× spin-up 30983's year-180 pickup. Since
2026-09-12 the adjoint submit definitions default to the production spin-up
31203 instead (and refuse it for a `visc2x` namelist), so name 30983 to repeat
one:

    P=$SCRATCH_ROOT/DINO_1deg_outputs/runs/forward/spinup_200yr_visc2x/DINO_1deg_frd_200yr_from_rest_visc2x_run30983
    IMPACTS_PICKUP_RUN_DIR=$P IMPACTS_TEST_CASE=grdchk_repair/from180yrPk_visc2x_grdchkON \
    IMPACTS_DURATION_DAYS=30 ../../../tools/submit.sh scripts/submit_tapAdj.sh
    IMPACTS_ALLOW_EXACT_ADJOINT=1 IMPACTS_PICKUP_RUN_DIR=$P \
    IMPACTS_TEST_CASE=grdchk_repair/from180yrPk_viscRef_ReMax2_approxAdvOff_grdchkON \
    IMPACTS_DURATION_DAYS=30 ../../../tools/submit.sh scripts/submit_tapAdj.sh

Each of the 4 checked points costs two extra 30-day forward integrations.
First meaningful result (2026-08-31, run pair on the hook build and a
control build of `main`): see the hook change note in the project notes, and the run
directories' `output_tap_adj.txt` (`grad-res` tables).
