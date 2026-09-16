# `variability_check/` — how much of the overturning's variability the monthly averaging hides

One question, one run. Every DINO forward run writes its `dynDiag` stream as a
**30.5-day time average** (`frequency(2) = 2635200.` — a positive frequency is an
average, a negative one a snapshot), so every AMOC series this project has drawn
is a series of monthly means. The slide deck
`impacts-notes/references/dino_kappa_v_campaign/slides` reports that successive
months of the current setup differ by 0.003 Sv at 26° N, against 0.047 Sv in the
previous setup, and the obvious objection is that the averaging, not the ocean,
is what is smooth.

This group settles it by writing the same field at three sampling rates in one
run, so the three series are of one ocean and differ only in how they were
sampled.

| Tag | What |
| --- | --- |
| `from190yrPk_viscRef_ReMax2_dailyDiag` | One model year from the year-190 pickup of the production spin-up 31203, live `input/data` physics, `VVEL` written as 30.5-day means (`dynDiag`, the production stream), 1-day means (`vvelDay`) and 6-hour snapshots (`vvelQd`), plus `ETAN` at the same 6 hours (`etanQd`) |

```bash
cd MITgcm_c69m/mysetups/DINO_1deg
IMPACTS_TEST_CASE=variability_check/from190yrPk_viscRef_ReMax2_dailyDiag \
IMPACTS_PICKUP_RUN_DIR=$SCRATCH_ROOT/DINO_1deg_outputs/runs/forward/spinup_200yr_viscRef_ReMax2/DINO_1deg_frd_200yr_from_rest_viscRef_ReMax2_run31203 \
IMPACTS_PICKUP_ITER=3337920 IMPACTS_DURATION_DAYS=366 IMPACTS_MONITOR_FREQ_DAYS=1 \
../../../tools/submit.sh scripts/submit_frd.sh
```

Two things about the namelist are deliberate and should not be "tidied":

- **`pChkptFreq=0.` and `chkptFreq=0.`** — the run writes no pickup. `submit_frd.sh`
  symlinks the pickup it starts from into the run directory, so a run that writes
  a pickup under a name it also links writes *through* the symlink into the source
  run. That is how 31203 overwrote 30983's year-170 pickup on 2026-09-11. This run
  needs no pickup of its own.
- **`dynDiag` keeps the production stream's name, frequency and field list**, so
  this run's monthly series is directly comparable with the two 200-year spin-ups'.

The run needs `numDiags` to hold 405 levels, which `code/DIAGNOSTICS_SIZE.h` already
does (`20*Nr = 720`), so no rebuild. It took 9 min 37 s on 27 ranks and wrote
2.6 GB.

## The answer (run 31434, 2026-09-16)

**The averaging hides nothing.** Standard deviation of the overturning cell over
the year, at the five latitudes of Wunsch & Heimbach (2013):

| latitude | 6-hourly (n=1464) | daily (n=366) | 30.5-day (n=12) | mean |
| --- | --- | --- | --- | --- |
| 25° S | 0.0161 | 0.0161 | 0.0159 | 4.008 |
| 10° N | 0.0029 | 0.0029 | 0.0029 | 13.663 |
| 26° N | 0.0064 | 0.0064 | 0.0062 | 5.112 |
| 45° N | 0.0347 | 0.0346 | 0.0340 | 7.118 |
| 55° N | 0.0361 | 0.0361 | 0.0353 | 6.302 |

All in Sv. The monthly means see 97–100 % of the variability the 6-hourly
snapshots do, and the spectrum of the 6-hourly series has essentially no variance
at periods shorter than a month. So the steadiness of the current setup is the
ocean's, not the diagnostic's.

**Why, physically.** `input_binaries/dino_utau.bin` holds 365 daily records that
are all identical — the wind stress has *no* seasonal cycle. Only `dino_T_star.bin`
(±3 K) and `dino_q_solar.bin` vary through the year. The sub-annual variability of
the real overturning is mostly Ekman, driven by the wind, and at 1° there are no
eddies either; both are absent here by construction, leaving a buoyancy-driven
seasonal cycle of 0.008–0.099 Sv peak to peak. **This configuration therefore
cannot be asked about overturning variability — only about its sensitivity.** If
variability ever becomes the question, that wind file is where to start.

The figure and the table come from the slide deck's figure script in the notes
repository (`references/dino_kappa_v_campaign/slides/figures/make_slide_figures.py
sampling`), which writes `amoc_sampling_check.png` and `amoc_sampling_stats.json`;
the numbers above are the whole result, so nothing here depends on that repository.
