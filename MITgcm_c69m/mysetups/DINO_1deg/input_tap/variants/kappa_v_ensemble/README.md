# `kappa_v_ensemble/` — adjoint runs

**Since 2026-09-10 the members are `M<k>_ReMax2`** (runs 31208, 31210, 31212,
31214, 31216, 31218, 31220; the first submission 31184–31196 was cancelled with
its forward legs): the live `input_tap/data` (scheme 33 in the forward
sweep, reference viscosity + `viscAhReMax=2.`; the live `data.autodiff` switches
the adjoint sweep to scheme 30 through the approxAdv build) with `diffKrT/S` set
to the member's κ, each started from the year-180 pickup its own forward leg
(`../../../input/variants/kappa_v_ensemble/data_M<k>_ReMax2`, runs 31207–31219
odd) wrote:

```bash
IMPACTS_PICKUP_RUN_DIR=$SCRATCH_ROOT/DINO_1deg_outputs/runs/forward/<leg run directory> \
IMPACTS_TEST_CASE=kappa_v_ensemble/M3_ReMax2 ../../../tools/submit.sh scripts/submit_tapAdj.sh
```

The reference member's adjoint is the live namelist from the `REF_ReMax2` leg's
pickup (31205 → run 31206). The bare `M<k>` files below are the 2026-08 members (2× viscosity,
exact adjoint of scheme 33, runs 31039–31046), kept as the record.

Vertical-mixing perturbation ensemble, Part I of the neural-network surrogate
proposal. These seven
namelists are the **5-year adjoint**, year 2180 → 2185, each at its own vertical
diffusivity; the forward legs that produce their pickups live in
[`../../../input/variants/kappa_v_ensemble/`](../../../input/variants/kappa_v_ensemble/),
which carries the κ table.

```bash
cd MITgcm_c69m/mysetups/DINO_1deg
IMPACTS_TEST_CASE=kappa_v_ensemble/M3 ../../../tools/submit.sh scripts/submit_tapAdj.sh
```

Each file is identical to `../data_from180yrPk_visc2x` apart from
`diffKrT`/`diffKrS` (`diffKrFile` until 2026-09-09, see the forward half's
README), because the whole design rests on κ_v being the only difference
between a member and the reference. `nIter0=3162240` is year 2180 and
`nTimeSteps=87840` is five years.

**The pickup must be named.** Each member's adjoint has to read *its own*
forward leg's `pickup.0003162240`, not the spin-up's: pass the leg's run
directory as `IMPACTS_PICKUP_RUN_DIR`, as above. Since 2026-09-12 the adjoint
submit definitions refuse to fall back on the production spin-up for a
namelist of other settings, which catches a bare `M<k>` (2×) member; the
`M<k>_ReMax2` members share the spin-up's settings, so for them the override is
the only safeguard. Chaining the two halves so the
adjoint waits for its forward leg is written up in the project notes, as the
job-chaining recipe.

Members run with `useGrdchk=.FALSE.` (set in `input_tap/data.pkg`, so it applies
to the reference adjoint too). The check cannot pass where it is currently
pointed and costs roughly 2.6× the adjoint proper; the ensemble's own
finite-difference comparison was to serve as the real validation — see the
outcome below for how that turned out.

**Rerun (runs 31040–31046 + reference 31039, 2026-09-01).** The adjoints were
rerun with the Tapenade-native hook build (ADEXCH-fixed `ADJ*` dumps +
`ADJetan`); `fc` and `adxx_*` reproduce the original runs below bitwise, so
the outcome stands — read `ADJ*` from the rerun directories.

**Rerun again (runs 31061–31067 + reference 31060, 2026-09-02).** The same
eight adjoints with the profile-guided `-nocheckpoint` build that became the
DINO default that day: bitwise identical to the 2026-09-01 set in `fc`,
`adxx_*` and `ADJ*`, the four blow-ups included, in 9.5–9.75 h each instead of
14.0–15.7 h. Either set can serve; the analysis reads the 2026-09-01 one.
Members go in through temporary copies of `submit_tapAdj_nocheckpoint.sh` with
the pickup repointed, per the job-chaining recipe.

**Outcome (original runs 31003–31009, 2026-08-29; analysed 2026-08-30;
conclusions re-verified on the 2026-09-01 rerun).** All seven
completed, but only `M2` (0.5×) and `M3` (2×) produced healthy full-length
adjoints; `M6` (16×) is structurally degraded, and `M1`/`M4`/`M5`/`M7` blow up
partway through the reverse sweep (non-monotonically in κ — a property of each
member's adjusted background state, with the plain, non-`adjVisc` build).
The finite-difference comparison ran but fails as a validation: the response is
nonlinear already at factor-2 steps. Full analysis:
`analyses/DINO_1deg/adjoint/kappa_v_ensemble/`; results prose: the surrogate
proposal's Part I §Results and its `kappa_ensemble_results`
brief. Rerunning a blown member as-is reproduces the blow-up — byte for byte,
as the 2026-09-09 stability study showed by restarting the last 183 d of M7's
run from its own monthly pickup (`stability_study/M7_lastHalfYr`, run 31166).
**The blow-up is the flux limiter's adjoint**: the same restart with
`tempAdvScheme=saltAdvScheme=30` (31167) does not blow up at all, while the
`adjVisc` boost and the grid-Reynolds floor only delay or damp it. A stable
large-κ adjoint therefore needs scheme 30 in the member namelists, not more
viscosity; see `../stability_study/README.md`.
