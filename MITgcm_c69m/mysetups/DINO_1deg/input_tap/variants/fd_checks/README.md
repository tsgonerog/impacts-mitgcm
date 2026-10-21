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
started from the production spin-up 31203, died when `/scratch2` failed on 2026-09-12 (their
directories were deleted on 2026-09-16, having written no cost), and
31346–31362 were cancelled with their chain when the spin-up 31329 could not write its final
pickup. **Rerun on 2026-10-13 for the 43 N cost section** (campaign `kappa_v_ensemble_gmFwd_sec43N`,
`submit_campaign.sh` reuse mode): 31561 and 31562 (κ_v), 31563–31570 (forcing, `+` then `−` for `fu`,
`fv`, `qnet`, `empmr`) and 31571–31576 (Theta boxes, `+` then `−` for deepN, midTrop, soUpper), from the
same reference leg, the same perturbed pickups and the same forcing files as in September, so the two
campaigns' checks differ only in the cost they measure. One check lost its signal at 43 N: the deep
box (40–50° N below 1500 m) now sits right under the section and moves J by 4e-5, the noise floor
(σ of the monthly cost 8.5e-4 there), as the 43 N adjoint also predicts; a fourth box, 45–60° N below
1500 m (`deepNN` in `campaign.THETA_BOXES`, ±0.016 K, pickups under
`analysis/kappa_v_ensemble_gmFwd_sec43N/perturbed_pickups/`), was run on 2026-10-14 as 31577/31578.
Results at 43 N (adjoint against the central difference): κ_v +12 %, the tropical box +5 %, the
Southern Ocean box +34 %, the deep box north of the section +48 %, the zonal stress −29 %; the net
heat flux and meridional stress have no finite-difference signal and the freshwater flux is over by
13×, as in September. **Rerun on 2026-10-20 for the 60 N and 25 S sections** (campaigns
`kappa_v_ensemble_gmFwd_sec60N`, sweeps 31629–31646, and `_sec25S`, 31655–31672, in the order of the 43 N
campaign with `deepNN` last; the section now a `data.cost` setting the campaign
script passes through `IMPACTS_COST_JSEC` / `IMPACTS_COST_KMAXDEPTH`), with all four Theta boxes for
every section: the `deepNN` pickups moved to `analysis/kappa_v_ensemble_gmFwd/perturbed_pickups/`
beside the other three that day (symlinks left in the 43 N campaign's directory, so 31577/31578 still
resolve), since a perturbed pickup belongs to the state, not to a section. With those amplitudes no check at 60 N and
only two at 25 S (the zonal stress, +8.4e-3, and the upper Southern Ocean box, +8.1e-3) clear twice the
cost's monthly noise (1.8e-3 at 60 N, 1.9e-3 at 25 S: twice the 43 N value), so on 2026-10-21 one pair of
boxes per section was added where that section's own reference adjoint predicts about 5σ
(`campaign.THETA_BOXES`, pickups beside the others): for 60 N the subpolar deep water (`subpolarDeep`,
55–68° N below 1500 m, ±0.05 K; jobs 31677/31678) and the thermocline just north of the section (`secN60`,
56–64° N, 300–1000 m, ±0.10 K; 31679/31680); for 25 S the South Atlantic thermocline (`sAtlThermo`,
35–10° S, 300–1000 m, ±0.06 K; 31681/31682) and deep water (`sAtlDeep`, 35–10° S below 1500 m, ±0.10 K;
31683/31684). The κ_v check itself cannot be made strong at 60 N: the adjoint there gives dJ/dκ_v = −301 per
m² s⁻¹, so a ±10 % sweep predicts 3.6e-4, a fifth of the noise. Results of the targeted pairs (adjoint against the
central difference, 2026-10-21): at 60 N the thermocline box −9 % (the two one-sided differences within 5 % of
each other, the cleanest check of any section) and the deep box −36 % (one-sided −2.0e-2 and −0.7e-2: nonlinear at
0.05 K); at 25 S the thermocline box +23 % (one-sided within 10 %) and the deep box +38 %. The results per section
are in `analysis/cost_sections/stats/` (`compare_sections.py`). Do not put the
words the model prints before the cost value into a namelist comment: the model echoes
every namelist into `STDOUT.0000`, and a script that searches for that line matches the
comment.
