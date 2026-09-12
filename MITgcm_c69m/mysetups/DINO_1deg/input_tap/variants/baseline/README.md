# `baseline/` — the previous reference adjoint configuration, kept as a record

**Since 2026-09-11 the live `input_tap/` runs GM/Redi in the adjoint's forward
sweep** (`data.pkg` `useGMRedi=.TRUE.` with the spin-up's `data.gmredi`,
`data.autodiff` `useGMRediInAdMode=.FALSE.`; runs named `..._gmFwd`), and
`data_from180yrPk_viscRef_ReMax2_gmOff` with its `data.pkg` sibling is the
GM-free configuration it replaced: that of 31206 and of the
`kappa_v_ensemble_ReMax2` adjoints (see `../stability_study/README.md`,
"GM/Redi in the forward sweep only"). The paragraphs below describe the earlier
baselines and are kept as they were written.

**Since 2026-09-09 the baseline is the live `input_tap/data` itself**: the 5-yr
adjoint from the production spin-up's year-180 pickup (`nIter0=3162240`),
which `submit_tapAdj.sh` (a symlink to `submit_tapAdj_nocheckpoint.sh`; the
`_ckpAll` and `_adjVisc` definitions read the same default) runs when you give
it no `IMPACTS_TEST_CASE` (`test_cases="${IMPACTS_TEST_CASE-}"`; the run is
named from the namelist, `from180yrPk_viscRef_ReMax2_adv30`). It is
`data_from180yrPk_visc2x` with the three settings of the stability study's
outcome — reference viscosity files, `viscAhReMax=2.`, scheme 30 for T and S
(see the forward half's README and `../stability_study/`). Two 5-yr runs of
it were launched on 2026-09-09: 31171
from the 2× spin-up's year-180 pickup (an early stability check of the new
adjoint on the old state) and 31173 from the year-180 pickup of the new
spin-up 31169, on which it waits (`--dependency=afterok`, the pickup through
`IMPACTS_PICKUP_RUN_DIR`); the gradient check under the new configuration is
31172 (`../grdchk_repair/`).

`data_from180yrPk_visc2x` was the previous **reference adjoint**: 5 years, 2180 → 2185,
started from the year-2180 pickup of the 200-year spin-up, at the same
viscosity the spin-up used. It was the control every 2026-08 `kappa_v_ensemble`
member was compared against, and the configuration of the reference chain 28486
(May 2026) → 30995 → 31039 (2026-09-01, the seam-clean reference)
≡ 31060 (2026-09-02, the same run with the `-nocheckpoint` build, bitwise
identical). **It was removed on 2026-09-12** (git history has it): with no
`data.pkg` or `data.autodiff` of its own it staged the live files, GM/Redi in
the forward sweep and scheme 30 in the adjoint sweep, and no longer gave the
configuration of its runs. Of those runs 28486, 31022, 31028, 31039, 31137 and
31140 are still on scratch; 31032, 31052–31054, 31074, 31093 and 31095 were
deleted the same day (provenance in `logs/deleted_run_records/` of the scratch
output tree).

Since 2026-09-09 the vertical diffusivity is `diffKrT = diffKrS = 1.2E-5` in
`PARM01` rather than `diffKrFile='dino_diffKr.bin'`; the `diffKr` array the
model builds is the same bit for bit, and so is the adjoint (30 d, 31140 ≡
31137: every `ADJ*`/`adxx_*`, `fc`, `%MON`). See the setup README, "Lateral
viscosity and vertical diffusivity: file or parameter".

`data_from180yrPk_viscRef_ReMax2_gmOff`, the one record left here, has a
`data.pkg` sibling and no `data.autodiff`: staged as the submit body stages it
today, it gives the configuration of 31206 (checked on 2026-09-12 against
31206's staged namelists; the live `data.autodiff`'s scheme-30 switch is the
one 31206 ran with). `nIter0=3162240` is year 2180. The adjoint submit
definitions link the pickup at the staged `nIter0` themselves and default to
the production spin-up 31203; 31206 started from the REF_ReMax2 leg 31205, so
name that run in `IMPACTS_PICKUP_RUN_DIR` to repeat it.
