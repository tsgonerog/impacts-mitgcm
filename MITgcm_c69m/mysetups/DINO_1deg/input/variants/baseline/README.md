# `baseline/` — the previous production forward configuration, kept as a record

**Since 2026-09-09 the baseline is the live `input/data` itself**, which
`submit_frd.sh` runs when you give it no `IMPACTS_TEST_CASE`
(`test_cases="${IMPACTS_TEST_CASE-}"`; the run is named from the namelist,
`from_rest_viscRef_ReMax2_adv30`). That configuration is the outcome of the
stability study (`../stability_study/`, the setup README's "Why the reference
viscosity is unstable", `TODO.md`): DINO's reference viscosity files on both D
and Z, the grid-Reynolds floor `viscAhReMax=2.` (DINO's own Re_Δ = 2 criterion
applied with the local speed, so the field is DINO's wherever |u| < 0.27 m/s
and raised only in the jets), and the unlimited DST3 tracer advection, scheme
30, whose adjoint does not blow up where the limited scheme 33's does. Its
200-year spin-up from rest is run 31169 (2026-09-09).

`data_from_rest_visc2x` is the **previous** production configuration, kept as
the record: the 200-year spin-up 30983 (and 28463 before the repository
cleanup), from rest with both viscosity files at `dino_viscAhD_2p00.bin`, 2×
the reference field, scheme 33. It is still what the forward reproducibility
check against 30983 needs, and every kappa_v_ensemble member derives from it.
Every other group here is a departure from one of these two.

The committed *duration* is 10 years, not 200: that is the cheap regression
configuration. A 10-year run from rest reproduces the first 10 years of the
spin-up bit-identically, which is the standing check that a rebuild has not
altered the physics. The full spin-up is the same namelist with
`IMPACTS_DURATION_DAYS=73200`.

`data_from170yrPk_visc2x` (2026-09-09) is the same physics restarted from the
spin-up's year-170 pickup (`nIter0=2986560`, the pickup `submit_frd.sh` already
stages for the `kappa_v_ensemble` members): a cheap from-pickup check with a
mature AMOC. Its first use was the validation of the `diffKrT`/`diffKrS`
setting — 1 year, run 31142, against the spin-up's own year 171.

Both files set the vertical diffusivity as `diffKrT = diffKrS = 1.2E-5` since
2026-09-09 (DINO's `rn_avt0`); `diffKrFile='dino_diffKr.bin'` before, a field
of that one constant, and the two give the same `diffKr` array bit for bit
(31139 ≡ 31100). The setup README, "Lateral viscosity and vertical
diffusivity: file or parameter", says why the viscosity stays a file.

`visc2x` rather than `viscD2x_Zref` is not cosmetic: the spin-up first ran as
`viscD2x_Zref` and **crashed at 126.3 years**. See `analyses/README.md`.
