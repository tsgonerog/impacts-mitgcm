# `stability_study/` — adjoint half: what makes the adjoint blow up, and what holds it

Started 2026-09-09 on branch `dino-stability-study`; the forward half is
[`../../../input/variants/stability_study/`](../../../input/variants/stability_study/).
All `from180yrPk_*` files are `baseline/data_from180yrPk_visc2x` with the lines
their headers name changed; the `_gm*` tags carry `data.pkg`, `data.gmredi`
(the spin-up's, K = 571 with the ldd97 taper — the live `input_tap/data.gmredi`
is a different file, K = 1000 with dm95) and, for `_gmOn`, a `data.autodiff`
sibling with `useGMRediInAdMode=.TRUE.`. Growth is read from the `ADJ*`
dumps (there is no adjoint monitor stream): wet-RMS of `ADJtheta` per dump.

**Two facts about the configuration every earlier adjoint ran with.** The
spin-up ran with GM/Redi on (`input/data.pkg`) and every adjoint with it off
(`input_tap/data.pkg`), unchanged since the initial import; and MITgcm's
`useApproxAdvectionInAdMode` (DST3 without its flux limiter in the adjoint
sweep) is inert in the Tapenade build, because `gad_advection.F` guards it with
`ALLOW_AUTODIFF_TAMC`, a TAF-only macro (`gad_calc_rhs.F` uses
`ALLOW_AUTODIFF`, but with multi-dimensional advection the horizontal fluxes
come from `gad_advection`): runs 31158/31159 are byte-identical to 31140/31152.

| Tag | Setting | 30 d from the 180-yr pickup |
| --- | --- | --- |
| (31140) | 2× viscosity, GM off — the reference adjoint | rms(`ADJtheta`) 2.3e-4 → 4.3e-4 over 30 d |
| `viscRef` | reference viscosity, GM off | 31152: the same curve (4.2e-4) |
| `viscRef_vort3` | + `selectVortScheme=3` | 31153: the same curve |
| `viscRef_ReMax2` | + `viscAhReMax=2.` | 31163 |
| `visc2x_gmOn` | GM on in both sweeps | 31154: a transient burst at lead 15 d (rms 1.7e-3, max 0.35), damped again by lead 25 d |
| `viscRef_gmOn` | reference viscosity, GM on in both sweeps | 31155: **explodes** — rms 4e-3 at lead 10 d, 0.15 at 15 d, 1e4 at 20 d, 1e6 at 25 d |
| `visc2x_gmFwd`, `viscRef_gmFwd` | GM on in the forward sweep, off in the adjoint sweep (`useGMRediInAdMode=.FALSE.`) | 31156/31157: **catastrophic at both viscosities** (rms 1e30 by lead 25 d): under Tapenade's checkpoint recomputation the step is re-run without GM from a with-GM state, so this hybrid is unusable here |
| `visc2x_approxAdv`, `viscRef_approxAdv` | `useApproxAdvectionInAdMode=.TRUE.`, `ckpAll` build | 31158/31159: byte-identical to 31140/31152 (the switch is inert, see above) |
| `M7_lastHalfYr` | kappa member M7's namelist restarted at iteration 3241296, the monthly pickup its 5-yr adjoint 31046 wrote 183 d before its end: the same trajectory and cost window, so the last 183 d of that adjoint, which blew up 132 d before the end | 31166 (`ckpAll`, 183 d) |
| `M7_lastHalfYr_adv30` | the same with the unlimited DST3 scheme 30 for T and S in both sweeps | 31167 |
| `M7_lastHalfYr_ReMax2` | the same with `viscAhReMax=2.` | 31168 |

The `M7_*` runs need the pickup override the adjoint submit definitions gained
the same day:

```bash
IMPACTS_PICKUP_RUN_DIR=$SCRATCH_ROOT/DINO_1deg_outputs/runs/adjoint/kappa_v_ensemble/DINO_1deg_tapAdj_ckpAll_5yr_M7_run31046 \
IMPACTS_PICKUP_ITER=3241296 IMPACTS_TEST_CASE=stability_study/M7_lastHalfYr \
IMPACTS_DURATION_DAYS=183 ../../../tools/submit.sh scripts/submit_tapAdj_ckpAll.sh
```
