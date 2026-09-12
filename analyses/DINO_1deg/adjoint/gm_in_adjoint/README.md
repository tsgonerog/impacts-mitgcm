# gm_in_adjoint/

Scripts for the 2026-09-11 test of running GM/Redi in the DINO adjoint's forward
sweep only (`useGMRedi=.TRUE.` with the spin-up's `data.gmredi`,
`useGMRediInAdMode=.FALSE.`), in the `approxAdv` build, from the REF_ReMax2
leg's year-180 pickup (31205). The namelists are the variants
`input_tap/variants/stability_study/*_ReMax2_gmFwd`, `*_ReMax2_gmOn`,
`REF*_ReMax2_gmFwd` and `thetaPatchFD_gmFwd`; that directory's `README.md` has
the row for each run and the table of results, and the setup's `TODO.md` the
open decision. The variants of the GM-free finite-difference sweeps,
`stability_study/thetaPatchFD_gmOff` and `kappa_v_ensemble/REFp10_ReMax2`,
`REFm10_ReMax2`, were removed on 2026-09-12, because they stage today's
GM-on `data.pkg`; their runs 31247–31252, 31231 and 31232 stay, since
`fd_summary.py` reads them.

## Runs

All under `/scratch2/<user>/DINO_1deg_outputs/runs/adjoint/stability_study/`.

| Job | What |
| --- | --- |
| 31234 | 30 d, GM in the forward sweep only, daily dumps |
| 31235 | 30 d, GM off in both sweeps (the live namelist), daily dumps |
| 31236 | 30 d, GM in both sweeps, daily dumps; blows up at lead 4 d |
| 31237 | 5 yr, GM in the forward sweep only; its reference is production 31206 |
| 31238, 31239 | GM model, κ_v +10 % and −10 %; forward sweep only, cancelled once `fc` is printed |
| 31241–31246 | GM model, Theta raised and lowered in three boxes; forward sweep only |
| 31247–31252 | GM-free model, the same three boxes |

The GM-free κ_v pair is 31231/31232, under `runs/adjoint/kappa_v_ensemble_ReMax2_approxAdv/`.

## Scripts

| Script | What it does |
| --- | --- |
| `compare_gm_adjoints.py` | `ADJ*` dumps and `adxx_*` gradients of several runs against a reference run, by lead: wet-point RMS, pattern correlation, relative RMS difference; also `fc` and the forward-sweep `%MON` stream |
| `forward_drift.py` | the monthly `dynDiag` of two runs: overturning at 26, 41 and 55° N, the cell at 3° S, the deep cell, mean temperature, RMS and zonal-mean T and S differences |
| `perturb_pickup.py` | a copy of a pickup with one 3-D field changed in a box, and the first-order cost change an adjoint predicts for it |
| `fd_summary.py` | every finite-difference check of the test against both adjoints (31206 and 31237) |

Their CSV and Markdown output, and the perturbed pickups (`perturbed_pickups/`),
are in `/scratch2/<user>/DINO_1deg_outputs/analysis/gm_in_adjoint/`.

## Result

GM in the forward sweep only is stable, costs about 8 % more over five years,
and gives the GM model's trajectory and cost. Against finite differences of the
GM model its dJ/dκ_v is 22 % too large, where production's is 65 %; its
temperature gradients are no better (tropics +4 % against +5 %, upper Southern
Ocean +45 % against +42 %, deep North Atlantic −21 % against −9 %), and still
follow the GM-free model's own differences. GM in both sweeps blows up.
Adopted for production on 2026-09-11 (the setup's `TODO.md`).
