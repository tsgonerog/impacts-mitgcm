# `from70yrPk_sweep/` — mixing and advection sweep from the 70-year pickup

Six variants restarted from the 70-year pickup (`nIter0=1229760`), at reference
viscosity, varying three things independently and in combination. Verified
against the sweep's own control, `data_from70yrPk_viscRef`:

| Tag suffix | Change |
| --- | --- |
| *(none)* | the control for this sweep |
| `_viscAr0p8e-4` | vertical viscosity `viscAr` 1.2E-4 → **0.8E-4** |
| `_kappa10` | `ivdc_kappa` 100. → **10.** |
| `_adv30` | `tempAdvScheme`/`saltAdvScheme` 33 → **30** |
| `_viscAr0p8e-4_kappa10` | the first two together |
| `_viscAr0p8e-4_kappa10_adv30` | all three |

Restarting from a spun-up state rather than from rest is what makes six runs
affordable.

**`kappa10` is not a background-diffusivity experiment.** `ivdc_kappa` is the
large implicit diffusivity applied *only where the water column is unstable*, so
this tag weakens **convective adjustment** by a factor of ten — it does not
change mixing in a stably stratified column at all. That makes it a different
quantity from the one `kappa_v_ensemble/` perturbs, which is the background
vertical diffusivity `diffKr`, set by `diffKrT`/`diffKrS` (a binary field
through `diffKrFile` until 2026-09-09).
The two are easy to confuse from the tag names alone and are not comparable.
