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
| `viscRef_ReMax2_adv30` | the same with the unlimited DST3 (`tempAdvScheme=saltAdvScheme=30`) — the production scheme since 2026-09-09; the one-setting twin of `viscRef_ReMax2` | 31174 (2 yr) and 31175 (10 yr): peaks a little above `viscRef_ReMax2` (\|u\| 0.59 vs 0.52, \|v\| 0.84 vs 0.79, `ke_max` 0.35 vs 0.31 over the decade), domain-mean KE 15 % higher, mean temperature 0.02 °C lower; **the tracer field stays within the limited run's range** (12-month means: no salinity cell outside it, one surface cell per month above its maximum; global `theta_max` 0.1 °C higher, `salt_min` never below 35.00), mixed-layer statistics identical (mean 12.1 vs 12.2 m; 0.55 vs 0.49 % of the area deeper than 1000 m); the depth-space MOC differs **only in the equatorial band**: the shallow tropical cells are stronger (upper-cell maximum 21.7 vs 8.5 Sv at 3° S, with a 0.9 °C colder equatorial surface layer and upwelling confined to the top 150 m instead of 400 m), while poleward of 15° every cell has the **same depth extent** (bottom of the upper cell −2115 to −2429 m in both, scheme 33 one level deeper at 28–47° N after 10 yr) and is weaker: 0.3–0.6 Sv at 2 yr (4.4 vs 4.8 Sv at 26° N), 1.1–1.6 Sv after 10 yr (2.8 vs 4.4 Sv at 26° N, 5.5 vs 6.8 at 41° N, 4.8 vs 5.9 at 55° N), a steady decline of the AMOC index through the decade that only begins to flatten at its end (figure `amoc_structure_from170yrPk_10yr_*`); the scheme-30 spin-up from rest 31169 shows the same at equal age against 30983 (2.8 vs 4.9 Sv at 26° N at year 35). The equatorial pair, on the other hand, is deeper as well as stronger under scheme 30 (the counter-clockwise cell north of the equator reaches ~900 m instead of ~300 m, 6.9 vs 1.7 Sv at 5° N), fed by an equatorial thermocline 0.5–1.1 °C colder through the top 400 m after 10 yr. Figures in `$SCRATCH_ROOT/DINO_1deg_outputs/analysis/stability_study/figures/` (`moc_depth_from170yrPk_2yr_*`, `zonal_mean_diff_*`) |

Read together: doubling the viscosity acts entirely through its **vorticity**
(Z) part, which sets the strength of the boundary currents and jets; the
divergence part, the vorticity scheme, the Coriolis discretisation and a
biharmonic add-on change little. DINO's closure is a grid-Reynolds-number
closure (A = U·Δx/2 keeps Re_Δ = |u|Δx/A at 2 for |u| = 0.27 m/s), and this
port's boundary currents run at 0.8–1.1 m/s at the reference viscosity, i.e.
Re_Δ ≈ 3–4 in the jets (up to 4.8 at the surface of the 2× state, 7 at
reference). `viscAhReMax=2.` is that same criterion applied with the local
speed instead of the fixed 0.27 m/s: DINO's viscosity everywhere the flow is
slower than 0.27 m/s, and just enough more where it is faster.

**10-yr continuations (31161 `viscRef`, 31164 `viscRef_ReMax2`, monthly
monitor).** Both run the full 10 yr without a flag. `viscRef` keeps its peaks
flat from year 1 on (\|u\| 0.76–0.78, \|v\| 1.02–1.03, `ke_max` 0.53) with the
domain-mean KE creeping up by 3 % over the decade (3.51 → 3.61e-4; the 2×
spin-up is flat at 2.93–2.97e-4) and grid roughness (`*_del2`) flat; so there
is no fast instability at the reference viscosity from a mature state, only a
narrower margin on a slowly intensifying circulation — the crash after ~180 yr
from rest is not reproducible in short runs. `viscRef_ReMax2` holds the 2×
peak levels for the whole decade (\|u\| 0.51–0.52, \|v\| 0.78–0.79, `ke_max`
0.31) at the reference run's mean KE. The floor is the recommended
replacement for the blanket doubling; its adjoint side is in the adjoint
half's README (finite, same 30-d growth; it does **not** cure the adjoint's
own blow-up, which is the flux limiter's).

**The implicit vertical advection blow-up (2026-09-10, later the same day).**
Two kappa-ensemble legs under the production configuration (8× and 16×, runs
31191 and 31193) died within two years with nothing in any diagnostic before
the last day. The tags below reproduced and dissected it; the setup README's
"Scheme 30 or scheme 33" subsection has the account. All from the year-170
pickup at reference viscosity + `viscAhReMax=2.`, scheme 33.

| Tag | Setting | Result |
| --- | --- | --- |
| `from170yrPk_viscRef_ReMax2_kappa8x_diag` | the 8× member (`kappa_v_ensemble/M5_ReMax2`) with monthly pickups and a daily monitor | 31198: dies at the same step as 31191 (iteration 3020238, day 701.6), deterministic; the daily monitor is unremarkable to the last day |
| `from170yrPk_viscRef_ReMax2_kappa8x_crashstep` | restart from 31198's pickup at 3020232, six steps before, snapshot and monitor every step (`IMPACTS_PICKUP_RUN_DIR`/`ITER`, which `submit_frd.sh` honours since this day) | 31199: at the sixth step the temperature of one cell (53° S, 22° W, 1220 m) goes from 4.21 to −105.7 °C, the cells below to −5.7 and +97.5, while salinity and the velocities are unchanged; the column above is uniform to four decimals over five levels — the flux-limited implicit vertical solve, not the dynamics |
| `..._crashstep_explVadv` | the same restart with `tempImplVertAdv=saltImplVertAdv=.FALSE.` | 31200: passes the step and the day, residual and extremes normal — **production since this day** |
| `..._crashstep_vadv3` | the same restart keeping the implicit solve but with the linear third-order upwind vertical scheme (`tempVertAdvScheme=saltVertAdvScheme=3`) | 31201: passes as well; not adopted (a linear vertical scheme is not monotone) |
| `from170yrPk_viscRef_ReMax2_kappa8x_explVadv` | the 8× member's full 10-yr leg with explicit vertical advection, daily monitor | 31202: the long test of the fix |

