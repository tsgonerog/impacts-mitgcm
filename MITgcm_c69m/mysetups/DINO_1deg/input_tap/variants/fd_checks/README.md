# `fd_checks/` — finite-difference checks of the production adjoint (since 2026-09-12)

Forward sweeps of the adjoint executable from the year-180 state of the reference forward
leg (`input/variants/kappa_v_ensemble/data_REF_ReMax2`, the spin-up's continuation), each cancelled once the forward sweep has printed its cost, so that the change in
J can be compared with the gradient of the reference adjoint (the live `input_tap/data`
from the same pickup). All three namelists stage the live `data.pkg`, `data.gmredi` and
`data.autodiff`.

| Tag | What differs from the live namelist | Compared with |
| --- | --- | --- |
| `REFp10_ReMax2_gmFwd_approxAdv` | `diffKrT = diffKrS = 1.32E-5` (+10 %) | Σ `adxx_diffkr` × 1.2E-6 |
| `REFm10_ReMax2_gmFwd_approxAdv` | `diffKrT = diffKrS = 1.08E-5` (−10 %) | the same |
| `thetaPatchFD_ReMax2_gmFwd_approxAdv` | nothing; the pickup carries the perturbation | Σ `adxx_theta` × δ |
| `fuFDp_…`, `fuFDm_…` | `zonalWindFile` = DINO's zonal stress ± 0.005 N m⁻² | Σ `adxx_fu` × 0.005 |
| `fvFDp_…`, `fvFDm_…` | `meridWindFile` = ± 2e-8 N m⁻² everywhere | Σ `adxx_fv` × 2e-8 |
| `qnetFDp_…`, `qnetFDm_…` | `surfQnetFile` = ± 0.003 W m⁻² everywhere | Σ `adxx_qnet` × 0.003 |
| `empmrFDp_…`, `empmrFDm_…` | `EmPmRFile` = ± 3e-9 kg m⁻² s⁻¹ everywhere | Σ `adxx_empmr` × 3e-9 |

The forcing checks read constant perturbation files (365 daily records, the length of DINO's
forcing cycle) from scratch `analysis/kappa_v_ensemble_gmFwd/perturbed_forcing/`, named by
absolute path in `PARM05`; each is the same perturbation the corresponding control applies,
since `ctrl_map_forcing.F` adds `xx_fu`, `xx_fv`, `xx_qnet` and `xx_empmr` to the forcing fields
those files fill. The amplitudes were chosen so that the adjoint of 31237 predicts a cost change
of about 5e-3.

The temperature checks start from copies of the reference leg's `pickup.0003162240` with Theta raised
or lowered in one box, written by `analyses/DINO_1deg/adjoint/gm_in_adjoint/perturb_pickup.py`
to scratch `analysis/kappa_v_ensemble_gmFwd/perturbed_pickups/`: the deep North
Atlantic box (40–50° N, below 1.5 km, ±0.016 K), the tropical box (0–10° N, 0.5–1.5 km,
±0.035 K) and the upper Southern Ocean box (40–60° S, above 0.5 km, ±0.5 K), the boxes
and amplitudes of the 2026-09-11 test (`stability_study/thetaPatchFD_gmFwd`).

```bash
IMPACTS_TEST_CASE=fd_checks/thetaPatchFD_ReMax2_gmFwd_approxAdv \
IMPACTS_PICKUP_RUN_DIR=$SCRATCH_ROOT/DINO_1deg_outputs/analysis/kappa_v_ensemble_gmFwd/perturbed_pickups/deepN_p \
    ../../../tools/submit.sh scripts/submit_tapAdj.sh --mail-type=NONE
```

The campaign of 2026-09-14 on `/scratch` (`submit_campaign.sh` in the analysis suite): 31382 and
31383 (κ_v), 31384–31391 (forcing, `+` then `−` for `fu`, `fv`, `qnet`, `empmr`), 31392 (the job
that writes the perturbed pickups once the reference leg has finished) and 31393–31398 (Theta
boxes), filed under `runs/adjoint/kappa_v_ensemble_gmFwd/`. Three earlier submissions did not
finish: 31305–31312 were cancelled at start by a watcher error and deleted, 31313–31328, which
started from the production spin-up 31203, died when `/scratch2` failed on 2026-09-12, and
31346–31362 were cancelled with their chain when the spin-up 31329 could not write its final
pickup. Do not put the
words the model prints before the cost value into a namelist comment: the model echoes
every namelist into `STDOUT.0000`, and a script that searches for that line matches the
comment.
