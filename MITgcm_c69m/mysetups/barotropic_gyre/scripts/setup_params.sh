#!/bin/bash
# scripts/setup_params.sh -- what makes barotropic_gyre different from the
# other setups, for the shared build and submit bodies (tools/lib/build_body.sh,
# tools/lib/submit_body.sh). Sourced by them, never executed.

# ---------- time stepping ----------
DELTA_T=1200              # s; IMPACTS_DURATION_DAYS -> nTimeSteps at this step (72 per day)
DURATION_KEY=nTimeSteps   # the namelist states the run length as nTimeSteps
DAYS_PER_YEAR=360         # whole years label a run <n>yr (the 2-year spin-up)

# ---------- generated-hook assertions (adjoint builds) ----------
# The hooks come from MITgcm_c69m/mods_tapenade_hooks/ (its README says how).
# In this configuration only the state hooks are active: temperature is the
# stepped tracer (its hook carries theta and, by the same routine, wVel), the
# velocity pair, the free surface and the two mode switches. Salt is not
# stepped and there is no surface heat, freshwater or wind-stress control, so
# Tapenade drops those hooks' calls (one hook per field is what allows that).
HOOK_CHECKS=(
    "DUMMY_IN_STEPPING_XYZ_RL_B 7 dummy_in_stepping_tap_b.f"
    "DUMMY_IN_STEPPING_UV_XYZ_RL_B 11 dummy_in_stepping_tap_b.f"
    "DUMMY_FOR_ETAN_TAP_B 5 integr_continuity_b.f"
    "AUTODIFF_INADMODE_SET_TAP_B 5 forward_step_b.f"
    "AUTODIFF_INADMODE_UNSET_TAP_B 5 forward_step_b.f"
)
# The compiled dummy_tap.f carries all five DUMP_ADJ_* calls whatever the
# configuration; they vanish silently if the file loses its AD_CONFIG.h include.
DUMP_CALLS=5

# No run_suffix_from_namelist: a run of the live namelist is named by its
# duration alone (barotropic_gyre_<run_token>_<duration>_run<jobid>).
