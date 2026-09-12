# `kappa_v_ensemble/` — forward legs

**Since 2026-09-10 the members are `REF_ReMax2` and `M<k>_ReMax2`** (runs 31205 and
31207, 31209, 31211, 31213, 31215, 31217, 31219; a first submission that morning,
31183–31195, ran with implicit vertical advection, lost two members to it and was
deleted — setup README, "Scheme 30 or scheme 33"): the same seven κ_v, the same 10-yr leg from the 2×
spin-up's year-170 pickup, but under the production configuration of that day —
reference viscosity files, `viscAhReMax=2.`, the flux-limited scheme 33 — i.e.
`../stability_study/data_from170yrPk_viscRef_ReMax2` with `diffKrT/S`, `pChkptFreq`
and the vertical advection (explicit) changed; `REF_ReMax2` is the κ = 1.2e-5
member, needed because 31164 ran the implicit form. The
matching adjoints (31206 and 31208–31220, even) were run from each leg's
year-180 pickup with the default pair of that day (`approxAdv`, merged into
`ckpAll` on 2026-09-12). Their variants,
`input_tap/variants/kappa_v_ensemble/data_M<k>_ReMax2`, were removed on
2026-09-12 (git history has them): with no `data.pkg` of their own they would
now stage GM/Redi, which those GM-free adjoints did not have.

**Both ensembles were deleted on 2026-09-12**, forward legs and adjoints
(30996–31002, 31039–31046 and 31205–31220), and their analysis suites were
retired the same day; each run's provenance, and the ensembles' statistics and
κ gradient tables, are in `logs/deleted_run_records/` of the scratch output
tree. The 2026-08 members' files, `data_M1`–`data_M7`, were removed the same
day (history at the end of this README). The ensemble is to be rerun from
scratch under the cleaned setup from the eight files that remain; the rerun
first recreates the adjoint variants as `M<k>_ReMax2_gmFwd`, with GM/Redi in
the forward sweep (DINO `TODO.md`).

Vertical-mixing perturbation ensemble, Part I of the neural-network surrogate
proposal: **do the adjoint sensitivity patterns depend on the model's vertical
mixing?**

These eight namelists are the **forward re-equilibration leg**, year 2170 →
2180, each at its own vertical diffusivity; the matching adjoint starts from
the leg's year-180 pickup.

| Tag | κ_v (m² s⁻¹) | × reference |
| --- | --- | --- |
| `REF_ReMax2` | 1.2e-5 | 1 |
| `M1_ReMax2` | 3.0e-6 | 0.25 |
| `M2_ReMax2` | 6.0e-6 | 0.5 |
| `M3_ReMax2` | 2.4e-5 | 2 |
| `M4_ReMax2` | 4.8e-5 | 4 |
| `M5_ReMax2` | 9.6e-5 | 8 |
| `M6_ReMax2` | 1.92e-4 | 16 |
| `M7_ReMax2` | 3.84e-4 | 32 |

The reference is 1.2e-5 m² s⁻¹. The members start from the 2× spin-up's state
but run a different configuration, so the reference is a leg of its own,
`REF_ReMax2`, rather than the spin-up.

```bash
cd MITgcm_c69m/mysetups/DINO_1deg
IMPACTS_TEST_CASE=kappa_v_ensemble/M3_ReMax2 ../../../tools/submit.sh scripts/submit_frd.sh
```

`data_REF_ReMax2` differs from `../stability_study/data_from170yrPk_viscRef_ReMax2`
in the first two settings below, and each `data_M<k>_ReMax2` from
`data_REF_ReMax2` in the third only:

- `tempImplVertAdv = saltImplVertAdv = .FALSE.` — explicit vertical tracer
  advection (setup README, "Scheme 30 or scheme 33")
- `pChkptFreq=316224000.` — raised so only the final pickup is written. The
  spin-up's own 2,400 monthly restarts are the Axis-2 dataset and must **not**
  be thinned this way
- `diffKrT` and `diffKrS` — the member's κ

`nIter0=2986560` is the nearest spin-up checkpoint below year 2170, and
`nTimeSteps=175680` lands exactly on year 2180, whose pickup the matching
adjoint run reads. **`nIter0` and the pickup are coupled by hand**:
`stage_pickups` in `scripts/submit_frd.sh` links the 2× spin-up 30983's
`pickup.0002986560` by default, `IMPACTS_PICKUP_RUN_DIR` and
`IMPACTS_PICKUP_ITER` override it, and nothing reads the iteration from the
namelist.

Since 2026-09-09 the κ is the `diffKrT`/`diffKrS` pair in `PARM01`. Every
member value is an exact power-of-two multiple of the reference `1.2E-5`, so
the double the namelist gives is the one the retired
`input_binaries/dino_diffKr_M<n>.bin` held (each 2,908,224 bytes of big-endian
float64 of a single constant), and the `diffKr` array the model builds is the
same bit for bit (`ini_mixing.F` initialises it from `diffKrNrS(k)`; a file
only overwrote it with the same values).

**History: the 2026-08 members (files removed 2026-09-12).** `data_M1`–`data_M7`
were `../baseline/data_from_rest_visc2x` (2× viscosity, implicit vertical
advection) with `nIter0`, `pChkptFreq` and the member's κ changed, the κ read
from `dino_diffKr_M<n>.bin` until 2026-09-09; the 2× spin-up 30983 was their
control, so that design needed seven runs. All seven forward legs (runs
30996–31002, 2026-08-28/29) completed and were healthy; each wrote its
year-2180 pickup and its matching adjoint ran from it. The results were
analysed in `analyses/DINO_1deg/adjoint/kappa_v_ensemble/` (retired
2026-09-12, with its `README.md`) and are in the surrogate proposal's Part I
§Results, including the caveat that four of the seven *adjoint* legs blow up
(the adjoint-side variant README was removed with its variants on 2026-09-12).
The runs were deleted on 2026-09-12; `logs/deleted_run_records/` keeps their
provenance and the ensemble's statistics tables. The files were removed the
same day (git history has them).
