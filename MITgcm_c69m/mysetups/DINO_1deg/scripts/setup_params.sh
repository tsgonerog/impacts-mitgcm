#!/bin/bash
# scripts/setup_params.sh -- what makes DINO_1deg different from the other
# setups, for the shared build and submit bodies (tools/lib/build_body.sh,
# tools/lib/submit_body.sh). Sourced by them, never executed; every build_*.sh
# and submit_*.sh definition beside this file gets these without repeating them.

# ---------- time stepping ----------
DELTA_T=1800              # s; IMPACTS_DURATION_DAYS -> nTimeSteps at this step
DURATION_KEY=nTimeSteps   # how input*/data states the run length (SOMA: endTime)
DAYS_PER_YEAR=366         # DINO's calendar: whole years label a run <n>yr

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

# ---------- naming a run of the live namelist ----------
# The live input*/data has no tag of its own, so a run of it would be named by
# duration alone. Derive the <start>_<viscosity> tokens from the namelist the
# way the 2026-08-18 scratch rename did (vocabulary: root README, "Namelist
# variants"): nIter0 -> from_rest / from<N>yrPk (366-day years at dT=1800);
# viscAhDfile/viscAhZfile -> viscRef (dino_viscAhD.bin, both) / visc2x (_2p00,
# both) / viscD2x_Zref (D doubled, Z at reference); a scalar viscAhGrid with no
# files -> viscGrid<value> (1.8E-2 -> viscGrid1p8e-2); viscAhReMax -> _ReMax<v> and a
# tempAdvScheme other than 33 -> _adv<n> are appended (2026-09-09). Anything unrecognised
# gives liveData, so the name never claims a setting the script could not read.
run_suffix_from_namelist() {
  awk -F'[=, ]+' '
    { sub(/^[[:space:]]+/, ""); k=tolower($1) }   # strip the indent, else $1 is empty
    k=="niter0"      {n=$2+0}
    k=="viscahdfile" {d=$2; gsub(/\047/,"",d)}
    k=="viscahzfile" {z=$2; gsub(/\047/,"",z)}
    k=="viscahgrid"  {g=$2}
    k=="viscahremax" {r=$2}
    k=="tempadvscheme" {a=$2}
    END {
      spd=48*366
      s = (n==0) ? "from_rest" : ((n%spd==0) ? "from" n/spd "yrPk" : "liveData")
      if      (d=="dino_viscAhD.bin"      && z=="dino_viscAhD.bin")      v="viscRef"
      else if (d=="dino_viscAhD_2p00.bin" && z=="dino_viscAhD_2p00.bin") v="visc2x"
      else if (d=="dino_viscAhD_2p00.bin" && z=="dino_viscAhD.bin")      v="viscD2x_Zref"
      else if (d=="" && z=="" && g!="") { v=g; gsub(/\./,"p",v); gsub(/E/,"e",v); v="viscGrid" v }
      else v="liveData"
      if (r!="") { rr=r; sub(/\.0*$/,"",rr); gsub(/\./,"p",rr); v=v "_ReMax" rr }   # viscAhReMax=2. -> _ReMax2 (since 2026-09-09)
      if (a!="" && a!=33) v=v "_adv" a                                              # tempAdvScheme other than 33 -> _adv<n>
      print s "_" v
    }' "$1"
}
