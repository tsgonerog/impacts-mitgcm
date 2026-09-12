# `scheme_tests/` — one scheme at a time

Viscosity is held at the **reference** field (`viscRef`) so that what changes is
the scheme, not the dissipation.

| Tag | What it turns on |
| --- | --- |
| `from_rest_viscRef_adv30` | advection scheme 30 |

**Two tags were deleted on 2026-09-12**, when `kpp` and `cd_code` stopped being
compiled into DINO (both stay commented in `code/packages.conf`, with what
restoring each needs); git history has the files, and no run on scratch used
either package:

- `from_rest_viscRef_CDscheme` set the C-D scheme for the Coriolis terms
  (`useCDscheme=.TRUE.`, `tauCD=321428.`); it was one of the two variants
  `pkg/cd_code` had been compiled for.
- `from_rest_viscRef_kppON` turned KPP on, and was the two-file case that the
  staging rule exists for: `data_from_rest_viscRef_kppON` commented out
  `ivdc_kappa`, since convective adjustment and KPP should not both be doing
  the job, and `data.pkg_from_rest_viscRef_kppON` set `useKPP=.TRUE.`; the two
  shared a tag, so selecting the variant staged both. Before the variants were
  grouped the `data.pkg` half was named `data.pkg_kppON`, sat in the flat
  directory with a tag matching nothing, and was never staged by any live
  script — so this experiment silently ran with `useKPP=.FALSE.`. Any result
  predating 2026-08-28 that claims to be a KPP run should be treated with
  suspicion.
