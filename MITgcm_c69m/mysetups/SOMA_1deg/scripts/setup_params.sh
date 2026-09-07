#!/bin/bash
# scripts/setup_params.sh -- what makes SOMA_1deg different from the other
# setups, for the shared build and submit bodies (tools/lib/build_body.sh,
# tools/lib/submit_body.sh). Sourced by them, never executed; every build_*.sh
# and submit_*.sh definition beside this file gets these without repeating them.

# ---------- time stepping ----------
DELTA_T=1200              # s
DURATION_KEY=endTime      # SOMA's namelist states the run length as endTime
                          # (seconds), not DINO's nTimeSteps
DAYS_PER_YEAR=360         # SOMA uses a 360-day year: whole years label a run <n>yr

# ---------- generated-hook assertions (adjoint builds) ----------
# The hooks come from MITgcm_c69m/mods_tapenade_hooks/ (its README says how):
# one external call per output field, so every generated _B call has a fixed
# argument count whatever the configuration -- a scalar field hook carries
# fld, fldb, diagName, dumpName, myTime, myIter, myThid = 7; a C-grid vector
# pair 11; the etaN dump hook and the two adjoint-mode switches fld, fldb,
# myTime, myIter, myThid = 5. F77 would silently misalign a mismatch, so the
# build body counts each generated call's arguments after make. Changing a
# hook's argument list means touching the hook, its _B body, its flow_tap
# stanza (all in that directory) AND this list together.
HOOK_CHECKS=(
    "DUMMY_IN_STEPPING_XYZ_RL_B 7 dummy_in_stepping_tap_b.f"
    "DUMMY_IN_STEPPING_XY_RS_B 7 dummy_in_stepping_tap_b.f"
    "DUMMY_IN_STEPPING_UV_XYZ_RL_B 11 dummy_in_stepping_tap_b.f"
    "DUMMY_IN_STEPPING_UV_XY_RS_B 11 dummy_in_stepping_tap_b.f"
    "DUMMY_FOR_ETAN_TAP_B 5 integr_continuity_b.f"
    "AUTODIFF_INADMODE_SET_TAP_B 5 forward_step_b.f"
    "AUTODIFF_INADMODE_UNSET_TAP_B 5 forward_step_b.f"
)
# The compiled hook bodies (dummy_tap.f, the tree's stub file with the bodies
# appended) must still carry their five DUMP_ADJ_* calls (XYZ, XY, XYZ_UV,
# XY_UV and etaN); they vanish silently if the file loses its AD_CONFIG.h
# include.
DUMP_CALLS=5

# No run_suffix_from_namelist: a run of the live namelist is named by its
# duration alone (SOMA_1deg_<run_token>_<duration>_run<jobid>), as SOMA runs
# always were. Define one here if SOMA ever gains namelist variants worth
# telling apart by name.
