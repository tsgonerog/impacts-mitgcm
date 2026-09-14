# `kappa_v_ensemble/` — adjoint half of the κ_v ensemble (since 2026-09-12)

The seven member adjoints of the vertical-diffusivity ensemble under the current
configuration. Each `data_M<k>_ReMax2_gmFwd_approxAdv` is the live `input_tap/data`
with `diffKrT` and `diffKrS` set to the member's κ_v and nothing else changed, so it
stages the live `data.pkg` (GM/Redi on), `data.gmredi` and `data.autodiff`
(`useGMRediInAdMode=.FALSE.`, `useApproxAdvectionInAdMode=.TRUE.`); the tag names those
two settings because a tagged run carries no namelist-derived tokens. The reference
member needs no file: it is the live namelist itself.

| Tag | κ_v (m² s⁻¹) | × reference | Forward leg it starts from |
| --- | --- | --- | --- |
| (live `input_tap/data`) | 1.2e-5 | 1 | `…/data_REF_ReMax2`, the spin-up's own continuation |
| `M1_ReMax2_gmFwd_approxAdv` | 3.0e-6 | 0.25 | `input/variants/kappa_v_ensemble/data_M1_ReMax2` |
| `M2_ReMax2_gmFwd_approxAdv` | 6.0e-6 | 0.5 | `…/data_M2_ReMax2` |
| `M3_ReMax2_gmFwd_approxAdv` | 2.4e-5 | 2 | `…/data_M3_ReMax2` |
| `M4_ReMax2_gmFwd_approxAdv` | 4.8e-5 | 4 | `…/data_M4_ReMax2` |
| `M5_ReMax2_gmFwd_approxAdv` | 9.6e-5 | 8 | `…/data_M5_ReMax2` |
| `M6_ReMax2_gmFwd_approxAdv` | 1.92e-4 | 16 | `…/data_M6_ReMax2` |
| `M7_ReMax2_gmFwd_approxAdv` | 3.84e-4 | 32 | `…/data_M7_ReMax2` |

Each forward leg runs 10 years from the spin-up's year-170 pickup, and the member's adjoint
starts from the leg's year-180 pickup, chained on the leg:

```bash
cd MITgcm_c69m/mysetups/DINO_1deg
O=$SCRATCH_ROOT/DINO_1deg_outputs
leg=$(IMPACTS_TEST_CASE=kappa_v_ensemble/M3_ReMax2 \
      IMPACTS_PICKUP_RUN_DIR=<run directory of the spin-up> \
      ../../../tools/submit.sh scripts/submit_frd.sh --parsable | tail -1)
IMPACTS_TEST_CASE=kappa_v_ensemble/M3_ReMax2_gmFwd_approxAdv \
IMPACTS_PICKUP_RUN_DIR=$O/runs/forward/DINO_1deg_frd_10yr_M3_ReMax2_run$leg \
    ../../../tools/submit.sh scripts/submit_tapAdj.sh --dependency=afterok:$leg
```

The campaign on `/scratch`, submitted as one dependency chain by
`analyses/DINO_1deg/adjoint/kappa_v_ensemble_gmFwd/submit_campaign.sh`: spin-up 31329 (2026-09-13)
and the rerun of its last 61 days, 31365; legs 31366 (reference) and 31367–31373; adjoints 31374
(reference, from the reference leg's year 180) and 31375–31381 (2026-09-14). The analysis is
`analyses/DINO_1deg/adjoint/kappa_v_ensemble_gmFwd/`. Two earlier chains did not run: the first,
of 2026-09-12 from the production spin-up 31203 (legs 31289–31296, adjoints 31297–31304), died when
`/scratch2` failed, and the second (31330–31362) was cancelled when 31329 could not write its final
pickup.

The earlier adjoint variants of this group (`M<k>` of 2026-08 and `M<k>_ReMax2` of
2026-09-10, both GM-free) were removed on 2026-09-12; git history has them.
