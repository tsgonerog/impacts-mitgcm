# `toolchain_validation/` — records that check the toolchain, not the physics

Runs of these land in `runs/adjoint/toolchain_validation/` on scratch, beside
the bitwise comparisons of rebuilt executables that use the live namelist.

| Tag | What it stages | Why |
| --- | --- | --- |
| `from180yrPk_viscRef_ReMax2_dynDiag5d` | the live `data` (a copy, identical on 2026-10-29) and the live `data.diagnostics` with `dynDiag` written every 5 days (`frequency(2) = 432000.`) instead of every 30.5 days | a check of the cost's value against the model's own velocity: `cost_atlantic_heat.F` computes J in Sverdrups since 2026-10-29, and a 5-day record of `VVEL` lets the transport across the cost row be recomputed offline from the run's own output over the same window the cost averaged (a 5-day run) or six of them (a 30-day run). The live frequency never writes a record inside a 30-day run |

Runs: 31737 (5 d) and 31738 (30 d) of 2026-10-29, the validation of the
rewrite, both under `runs/adjoint/toolchain_validation/` with the check's
output and script (`cost_sv_check.txt`, `cost_sv_check.py`) inside each.

The record does not change the trajectory or the adjoint: `data.diagnostics`
only sets what is written. A run of it is comparable with a run of the live
namelist of the same length, up to the cost routine's form. Without its own
`data.pkg` or `data.autodiff` it stages the live ones, so it runs today's
configuration (GM/Redi in the forward sweep, scheme 30 in the adjoint sweep).

```bash
IMPACTS_DURATION_DAYS=5  IMPACTS_TEST_CASE=toolchain_validation/from180yrPk_viscRef_ReMax2_dynDiag5d ../../../tools/submit.sh scripts/submit_tapAdj.sh
IMPACTS_DURATION_DAYS=30 IMPACTS_TEST_CASE=toolchain_validation/from180yrPk_viscRef_ReMax2_dynDiag5d ../../../tools/submit.sh scripts/submit_tapAdj.sh
```

The offline check: with `dxG`, `drF` and `hFacS` from the run directory and
the `VVEL` records of `dynDiag`, sum `VVEL * dxG * drF * hFacS` over the row
`cost_atl_jsec` of the staged `data.cost` and the upper `cost_atl_kmaxdepth`
levels, times 1e-6; the mean over the records that cover the cost's window
(the last 30 days, or the whole of a shorter run) is J to about four digits.
The residual is one time step: the diagnostic samples the velocity at the
start of each step, the cost at its end.
