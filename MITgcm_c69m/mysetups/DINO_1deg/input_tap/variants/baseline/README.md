# `baseline/` — the reference adjoint configuration

What `submit_tapAdj.sh` (a symlink to `submit_tapAdj_nocheckpoint.sh` since
2026-09-02; the `_ckpAll` pair reads the same default) runs when you give it
no `IMPACTS_TEST_CASE`:

```bash
test_cases="${IMPACTS_TEST_CASE-baseline/from180yrPk_visc2x}"
```

`data_from180yrPk_visc2x` is the **reference adjoint**: 5 years, 2180 → 2185,
started from the year-2180 pickup of the 200-year spin-up, at the same
viscosity the spin-up used. It is the control every `kappa_v_ensemble/` member
is compared against, and the configuration of the reference chain 28486
(May 2026) → 30995 → 31039 (2026-09-01, the current seam-clean reference)
≡ 31060 (2026-09-02, the same run with the `-nocheckpoint` build, bitwise
identical).

Since 2026-09-09 the vertical diffusivity is `diffKrT = diffKrS = 1.2E-5` in
`PARM01` rather than `diffKrFile='dino_diffKr.bin'`; the `diffKr` array the
model builds is the same bit for bit, and so is the adjoint (30 d, 31140 ≡
31137: every `ADJ*`/`adxx_*`, `fc`, `%MON`). See the setup README, "Lateral
viscosity and vertical diffusivity: file or parameter".

`nIter0=3162240` is year 2180 and is coupled by hand to a pickup symlink in
each `submit_tapAdj*.sh`. Changing the duration is safe; changing the starting point
means editing both.
