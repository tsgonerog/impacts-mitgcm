# `stability_study/` — why 2× viscosity stabilises the model, and what else does (forward half)

Started 2026-09-09 on branch `dino-stability-study`. The question: the 200-yr
spin-up needed **twice** DINO's lateral viscosity (`visc2x`) to survive; at the
reference viscosity (`viscRef`, DINO's `rn_Uv = 0.27` law, A_h = ½·U_v·Δx) the
forward model crashed after roughly 180 yr, and a run with only the divergence
part doubled (`viscD2x_Zref`) crashed at 126 yr. No monitor log of any crashed
run survives, so the study restarts the **2× spin-up's year-170 pickup**
(`nIter0=2986560`, the pickup `submit_frd.sh` already stages) under each
setting and watches the monitor stream (every 5 d) and the monthly `dynDiag`:

```bash
IMPACTS_TEST_CASE=stability_study/from170yrPk_viscRef IMPACTS_DURATION_DAYS=732 \
  IMPACTS_MONITOR_FREQ_DAYS=5 ../../../tools/submit.sh scripts/submit_frd.sh
```

Every file is `baseline/data_from170yrPk_visc2x` with the lines its header names
changed and nothing else. The `_gmOff` tags carry a `data.pkg` sibling.

| Tag | Setting | 2 yr from year 170 (runs 31143–31151, 31160) |
| --- | --- | --- |
| `viscRef` | both `PARM05` files at reference | stable; peak \|u\| 0.59 → 0.76, \|v\| 0.76 → 1.03 m/s, `ke_max` 0.28 → 0.53, saturating within a year |
| `viscRef_vort3` | + `selectVortScheme=3`, DINO's EEN vorticity scheme | as `viscRef` (\|u\| 0.72) |
| `viscRef_vort2` | + `selectVortScheme=2`, Sadourny's energy-conserving scheme | as `viscRef` (\|u\| 0.67) |
| `viscRef_cori1` | + `selectCoriScheme=1`, Jamart wet points | as `viscRef`, noisier (\|u\| 0.85 peak, `ke` 0.42 at 2 yr) |
| `viscRef_A4Grid1p0e-2` | + grid biharmonic `viscA4Grid=1.E-2` | as `viscRef` (\|u\| 0.70) |
| `viscRef_gmOff` | reference viscosity, GM/Redi off — the adjoint's forward configuration | the most energetic: \|u\| 0.85, \|v\| 1.07, `ke_max` 0.57 |
| `visc2x_gmOff` | 2× viscosity, GM/Redi off — exactly the adjoint's forward configuration | close to the spin-up (\|u\| 0.59, \|v\| 0.79, `ke_max` 0.31, still drifting up slowly) |
| `viscD2x_Zref` | D doubled, Z at reference — the 126-yr crash setting | as `viscRef` (\|u\| 0.73, \|v\| 1.00, `ke` 0.51) |
| `viscDref_Z2x` | Z doubled, D at reference | **as the 2× spin-up** (\|u\| 0.58, \|v\| 0.76, `ke` 0.29): the vorticity viscosity is the whole effect |
| `viscRef_ReMax2` | reference viscosity + `viscAhReMax=2.` | **as the 2× spin-up in the peaks** (\|u\| 0.51, \|v\| 0.78, `ke_max` 0.31) with the domain-mean KE of `viscRef`; the viscosity is raised on 0.8 % of the wet points (max 2.5× reference, in the equatorial western boundary current) |

Read together: doubling the viscosity acts entirely through its **vorticity**
(Z) part, which sets the strength of the boundary currents and jets; the
divergence part, the vorticity scheme, the Coriolis discretisation and a
biharmonic add-on change little. DINO's closure is a grid-Reynolds-number
closure (A = U·Δx/2 keeps Re_Δ = |u|Δx/A at 2 for |u| = 0.27 m/s), and this
port's boundary currents run at 0.8–1.1 m/s at the reference viscosity, i.e.
Re_Δ ≈ 3–4 in the jets (up to 4.8 at the surface of the 2× state, 7 at
reference). `viscAhReMax=2.` is that same criterion applied with the local
speed instead of the fixed 0.27 m/s: DINO's viscosity everywhere the flow is
slower than 0.27 m/s, and just enough more where it is faster. The 10-yr
continuations (31161 `viscRef`, 31164 `viscRef_ReMax2`) are the next check.
