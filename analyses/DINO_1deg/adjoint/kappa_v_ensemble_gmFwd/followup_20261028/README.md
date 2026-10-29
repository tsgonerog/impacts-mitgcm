# `followup_20261028/` — the runs and analyses that answered the questions of the meeting of 28 October 2026

On 28 October the κ_v campaign and the surrogate design were discussed with two collaborators from the
computer-science side. Four of their questions could not be answered from the campaigns as they stood, so 25 runs
and three analyses of the existing adjoints were made the same night, and written up as a technical note
(https://claude.ai/artifact/CZGptTdunuHuRgTYNQhAzD). Everything here reads and writes scratch through the suite's
`campaign.py` (the grid, the readers, the metrics, `OUTPUTS`), so it runs from this directory with
`CAMPAIGN_NAME` unset (the 43 N campaign is the default) and `python` from the `py38` environment:

```bash
PY=~/tools_and_software/miniforge3/envs/py38/bin/python3
$PY followup_analysis.py swap|sweep|fd|ownmax      # tables and JSON records
$PY fig_followup.py swap|sweep|ownmax              # their figures
$PY baselines.py compute|figure                    # interpolation baselines on the 32 adjoints
$PY member_diagnostics.py sums|state               # two diagnostics of the 43 N campaign
$PY page_figures.py [line|amplitude|psi|all]       # three figures of the 43 N campaign for the note
```

## The questions, the runs and where the products are

| Question | Runs (campaign on scratch) | Analysis here | Products under `analysis/` |
| --- | --- | --- | --- |
| 1. Why does the sensitivity amplitude fall with κ_v? | 31709–31716, `runs/adjoint/kappa_v_operator_vs_state/`: the reference state (REF leg 31366, year 180) and the 32× state (M7 leg 31373), each with its own and the other's κ_v in the adjoint, 30 d and 1 yr | `followup_analysis.py swap`, `fig_followup.py swap`; `member_diagnostics.py sums` (sum against RMS of ADJtheta by member and lead) and `state` (the members' states at the cost row) | `kappa_v_operator_vs_state/{job_map.tsv,swap_results.csv,figures/fig_swap.png}`; `kappa_v_ensemble_gmFwd_sec43N/stats/{theta_sum_vs_rms_by_member.json,leg_state_at_43N.txt}` |
| 3. How many cost sections does a training set need? | 31721–31734, `runs/adjoint/cost_section_sweep/`: fourteen 1-yr adjoints of the reference state with the cost every ~5° from 30 S to 60 N, all above 848 m (`IMPACTS_COST_JSEC` 69 74 80 90 120 127 131 137 144 148 155 158 166 175) | `followup_analysis.py sweep`, `fig_followup.py sweep`; `baselines.py` (leave-one-section-out and leave-one-κ_v-out on the 32 existing adjoints) | `cost_section_sweep/{job_map.tsv,sweep_results.csv,sweep_corr_1yr.csv,figures/fig_sweep.png}`; `cost_sections/baselines/{baselines.csv,fig_baselines.png}` |
| 5. Does it matter that the fixed section is the reference's maximum? | 31720, `runs/adjoint/cost_section_sweep/`: the 8× member (M5 leg 31371) with the cost at its own maximum, row 196 (68.8 N), 848 m, 5 yr, against its fixed-section adjoint 31558 | `followup_analysis.py ownmax`, `fig_followup.py ownmax` | `cost_section_sweep/{ownmax_result.json,ownmax_1yr_fields.npz,figures/fig_ownmax.png}` |
| 6/7. Is the κ_v gradient *field* right, not only its basin sum? | 31717/31718, `runs/adjoint/kappa_v_ensemble_gmFwd_sec43N/`: κ_v × 1.1 / × 0.9 inside the box 45–65 N, western half, surface to 127 m, through a `diffKrFile` (`input_tap/variants/fd_checks/data_diffkrBoxFD{p,m}_…`), cancelled by `fd_watcher.sh` once the cost was printed | `followup_analysis.py fd` | `kappa_v_ensemble_gmFwd_sec43N/perturbed_diffkr/{box_definition.json,fd_fc_lines.tsv,fd_box_result.json}` |
| the note's figures of the 43 N campaign | — | `page_figures.py` | `kappa_v_ensemble_gmFwd_sec43N/figures/fig_{line_plot,amplitude_by_lead,psi_members}.png` |

`submit_followup.sh` is the record of the 25 submissions (the environment each run was given; it refuses to run
without `--really`), and `fd_watcher.sh` the loop that cancelled the two finite-difference runs after their forward
sweep. The job maps on scratch say which pickup each run started from, which the run-directory names do not.

## Results, in one line each

- **Question 1.** At 30 days of lead the amplitude follows the state alone (reference state with 32× κ_v 0.99; 32×
  state with either κ_v 0.40, the campaign's 0.36); by one year the state gives 0.62 and the diffusivity in the
  adjoint a further 0.69 on the reference state but only 3 % on the already-smooth 32× state (combined 0.60, campaign
  0.65). The sum of the field and the cost itself follow the state throughout.
- **Question 3.** At one year of lead neighbouring sections correlate at 0.79–0.90 in the subtropics of both
  hemispheres, 0.57–0.71 between 30 N and 43 N, 0.43–0.47 at 43–48 N and 55–60 N, 0.07 across the equator; the
  correlation falls below 0.5 beyond 14–20° in the tropics and subtropics, 8–11° at 30–40 N, 5° from 43 N north. The
  baselines: linear interpolation in log κ_v reproduces a held-out member at 0.95–0.98, the nearest section at the
  same κ_v only 0.07 (25 S) to 0.68 (43 N, 60 N).
- **Question 5.** The 8× member's own-maximum cost (69 N) gives fields uncorrelated with its 43 N ones (0.02 at 30 d,
  0.05 at 1 yr, 0.17 at 3 yr, 0.41 at 5 yr; the κ_v gradient's basin sum changes sign): the fixed section is the right
  ensemble design and the section must be an explicit label.
- **Questions 6/7.** The box sum of the field predicts −0.01013; the perturbed runs give −0.01014 (−0.1 %, twelve
  times the noise, one-sided differences within ±4 %). 82 % of the field's absolute value lies at 15–26 m depth.

The sweep's 26 N and 60 N rows use the 848 m interface, not the 982 m of the campaign sections of the same name.
