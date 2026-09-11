# kappa_v ensemble under the 2026-09-10 production configuration

The vertical-diffusivity perturbation ensemble rerun under the configuration
decided on 2026-09-10: reference viscosity files + `viscAhReMax=2.`, the
flux-limited DST3 scheme 33 with explicit vertical tracer advection in the
forward model, and the approximate adjoint (scheme 30 in the adjoint sweep,
`useApproxAdvectionInAdMode` through the `approxAdv` build), GM on in the
forward model and off in the adjoint. Eight members (the reference and the seven
κ_v factors of the 2026-08 campaign, `../kappa_v_ensemble/`), each a 10-yr
forward leg from the 2× spin-up's year-170 pickup and a 5-yr adjoint from the
leg's year-180 pickup. Runs on scratch under
`runs/{forward,adjoint}/kappa_v_ensemble_ReMax2_approxAdv/` once filed (unfiled
at `runs/{forward,adjoint}/` level while their dependents run); figures under
`analysis/kappa_v_ensemble_ReMax2_approxAdv/figures/`.

| member | κ_v [m² s⁻¹] | × ref | forward leg | adjoint |
| --- | --- | --- | --- | --- |
| REF | 1.2e-5 | 1 | 31205 | 31206 (also the early production adjoint) |
| M1 | 3.0e-6 | 0.25 | 31207 | 31208 |
| M2 | 6.0e-6 | 0.5 | 31209 | 31210 |
| M3 | 2.4e-5 | 2 | 31211 | 31212 |
| M4 | 4.8e-5 | 4 | 31213 | 31214 |
| M5 | 9.6e-5 | 8 | 31215 | 31216 |
| M6 | 1.92e-4 | 16 | 31217 | 31218 |
| M7 | 3.84e-4 | 32 | 31219 | 31220 |

Two more runs belong to the campaign without being ensemble members: **31203**,
the 200-yr spin-up from rest under the same forward configuration (filed under
`runs/forward/spinup_200yr_viscRef_ReMax2/`, analysed in
`../../forward/spinup_200yr_from_rest_viscRef_ReMax2.ipynb` against the 2×
spin-up 30983), and **31204**, the production adjoint proper: the same 5-yr
adjoint as 31206 started from 31203's own year-180 pickup instead of the
reference leg's (`runs/adjoint/spinup_200yr_viscRef_ReMax2/` once done; read
by `production_adjoint_stability_and_pathways.ipynb` beside 31206 and 31171).

The first submission of the same campaign that morning (31180–31196) ran the
implicit vertical advection this setup had used since its import; two legs
(8× and 16×) blew up within two years through the flux-limited implicit
vertical solve in a convectively homogenised column, and the whole set was
cancelled, deleted and resubmitted (setup README, "Scheme 30 or scheme 33";
the diagnostic runs 31193, 31198–31202 are under `runs/forward/stability_study/`).

## Notebooks, in reading order

| notebook | question |
| --- | --- |
| `forward_legs.ipynb` | Did the eight legs run, what does the overturning do as a function of κ_v, and what did the switch to explicit vertical advection change in the reference state (against 31164)? |
| `production_adjoint_stability_and_pathways.ipynb` | Is the 5-yr approximate adjoint finite and smooth over its whole window, how does the sensitivity evolve and along which pathways, and how does it compare lead by lead with the exact scheme-30 adjoint 31171? |
| `ensemble_adjoints.ipynb` | Are all eight adjoints stable; how do the cost and the adjoint gradient with respect to κ_v compare with the finite differences across members; how does the sensitivity structure change with κ_v? |

The 2026-08 campaign's suite (`../kappa_v_ensemble/`) is the record of the
previous configuration (2× viscosity, exact adjoint of scheme 33); its
`ensemble_common.py` and cache are not reused here.
