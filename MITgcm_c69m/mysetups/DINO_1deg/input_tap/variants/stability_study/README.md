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
| `viscRef_ReMax2` | + `viscAhReMax=2.` | 31163: the same curve (4.2e-4), finite; the floor is differentiated (`AUTODIFF_DISABLE_REYNOLDS_SCALE` undefined) and costs nothing here |
| `visc2x_gmOn` | GM on in both sweeps | 31154: a transient burst at lead 15 d (rms 1.7e-3, max 0.35), damped again by lead 25 d |
| `viscRef_gmOn` | reference viscosity, GM on in both sweeps | 31155: **explodes** — rms 4e-3 at lead 10 d, 0.15 at 15 d, 1e4 at 20 d, 1e6 at 25 d |
| `visc2x_gmFwd`, `viscRef_gmFwd` | GM on in the forward sweep, off in the adjoint sweep (`useGMRediInAdMode=.FALSE.`) | 31156/31157: **catastrophic at both viscosities** (rms 1e30 by lead 25 d): under Tapenade's checkpoint recomputation the step is re-run without GM from a with-GM state, so this hybrid is unusable here |
| `visc2x_approxAdv`, `viscRef_approxAdv` | `useApproxAdvectionInAdMode=.TRUE.`, `ckpAll` build | 31158/31159: byte-identical to 31140/31152 (the switch is inert, see above) |
| `M7_lastHalfYr` | kappa member M7's namelist restarted at iteration 3241296, the monthly pickup its 5-yr adjoint 31046 wrote 183 d before its end: the same trajectory and cost window, so the last 183 d of that adjoint, which blew up 132 d before the end | 31166 (`ckpAll`, 183 d): `fc` and all 36 dumps **byte-identical to 31046** — the blow-up reproduced: rms(`ADJtheta`) 1.09e-4 at lead 110 d, 4.0e-4 at 125 d, 2.6e-2 at 140 d (max 5.8) |
| `M7_lastHalfYr_adv30` | the same with the unlimited DST3 scheme 30 for T and S in both sweeps | 31167: **no blow-up** — rms decays smoothly 1.36e-4 → 8.5e-5 at 170 d (max 3.7e-3); `fc` 0.5125 against 0.5102, a 0.45 % change of the forward |
| `M7_lastHalfYr_ReMax2` | the same with `viscAhReMax=2.` | 31168: the blow-up at the same lead, halved (1.1e-2 at 140 d); `fc` changes by 0.04 % |
| `M7_lastHalfYr_approxAdv` | the control's namelist (scheme 33 in the forward sweep) with a `data.autodiff` sibling setting `useApproxAdvectionInAdMode=.TRUE.`, run with `build_tapAdj_approxAdv.sh` / `submit_tapAdj_approxAdv.sh` (2026-09-10): scheme 30 in the adjoint sweep only | 31176 (`ckpAll`, 183 d, 1 h 24): **`fc` byte-identical to the control** (the forward trajectory is untouched) and **no blow-up** — rms(`ADJtheta`) 9.9e-5 at lead 125 d, 8.3e-5 at 175 d, within 1 % of 31167's curve; `adxx_theta`/`adxx_salt` correlate with 31167's at 0.999 (rms difference 4–5 %), `adxx_diffkr` at 0.991 (13 %) |

**Verdict.** The adjoint blow-ups of this setup are the adjoint of the DST3
flux limiter (scheme 33): bursts with 1–3-day e-folding seeded where the
tracer field is nearly uniform (the limiter's ratio Rjm/Rj is then wildly
sensitive), which viscosity only delays — the kappa members that blew up were
all 2× runs. The cure is the unlimited DST3 (`tempAdvScheme=saltAdvScheme=30`,
what ECCO uses for the same reason): it removes the M7 blow-up outright. The
stock adjoint-only form of the same cure, `useApproxAdvectionInAdMode`,
keeps the forward at 33 but is inert in the plain builds (the
`ALLOW_AUTODIFF_TAMC` guard in `gad_advection.F`) and, being a run-time
branch, can only act in a checkpoint-everything build (`gad_advection` and
`gad_calc_rhs` are in the `-nocheckpoint` list, where the taped forward
control flow keeps the limiter). **Built and tested 2026-09-10** as
`code_tap/variants/approxAdvection/` + `build_tapAdj_approxAdv.sh` (the guard
widened, and the same swap added to `gad_implicit_r.F` for the implicit
vertical advection, which the stock switch never covered): run 31176 above —
the forward stays scheme 33 to the last bit and the adjoint does not blow up.
So the two stable routes are scheme 30 in both sweeps (exact adjoint of a
smooth model, the live `input*/data`) and scheme 33 forward with scheme 30 in
the adjoint sweep (the approximate adjoint, ECCO's `useApproxAdvectionInAdMode`
practice, 1.5× slower because it must be a `ckpAll` build); which forward
scheme to run was a physics choice, see the setup README's "Scheme 30 or
scheme 33" — decided 2026-09-10 for the second route, now the default pair. What scheme 33 cannot have is a finite-difference-verifiable
adjoint at this viscosity: `grdchk_repair/` runs 31177–31179.

The `M7_*` runs need the pickup override the adjoint submit definitions gained
the same day:

```bash
IMPACTS_PICKUP_RUN_DIR=$SCRATCH_ROOT/DINO_1deg_outputs/runs/adjoint/kappa_v_ensemble/DINO_1deg_tapAdj_ckpAll_5yr_M7_run31046 \
IMPACTS_PICKUP_ITER=3241296 IMPACTS_TEST_CASE=stability_study/M7_lastHalfYr \
IMPACTS_DURATION_DAYS=183 ../../../tools/submit.sh scripts/submit_tapAdj_ckpAll.sh
```
