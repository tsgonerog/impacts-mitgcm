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
# tempAdvScheme other than 33 -> _adv<n> are appended (2026-09-09), and _gmFwd when the
# data.pkg beside the namelist turns GM/Redi on while the data.autodiff beside it keeps GM
# out of the adjoint sweep (2026-09-11; a forward namelist has no data.autodiff and gets no
# GM token), and _approxAdv when that data.autodiff sets useApproxAdvectionInAdMode and
# tempAdvScheme is 33, the flux-limited scheme the switch replaces in the adjoint sweep
# (2026-09-12; the submit body drops it again for the approxAdv build, whose run token
# already says it). Anything unrecognised gives liveData, so the name never claims a
# setting the script could not read.
run_suffix_from_namelist() {
  local dir gm= ax=
  dir=$(dirname "$1")
  if [[ -f "$dir/data.pkg" && -f "$dir/data.autodiff" ]] \
     && grep -qiE '^[[:space:]]*useGMRedi[[:space:]]*=[[:space:]]*\.?t' "$dir/data.pkg" \
     && grep -qiE '^[[:space:]]*useGMRediInAdMode[[:space:]]*=[[:space:]]*\.?f' "$dir/data.autodiff"; then
    gm=_gmFwd
  fi
  if [[ -f "$dir/data.autodiff" ]] \
     && grep -qiE '^[[:space:]]*useApproxAdvectionInAdMode[[:space:]]*=[[:space:]]*\.?t' "$dir/data.autodiff"; then
    ax=_approxAdv
  fi
  awk -F'[=, ]+' -v gm="$gm" -v ax="$ax" '
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
      print s "_" v gm ((a==33) ? ax : "")                                         # _approxAdv only where there is a scheme to replace
    }' "$1"
}

# ---------- the pickup an adjoint run starts from ----------
# stage_pickups in every DINO adjoint submit definition calls link_pickup, in the
# staged run directory. The iteration is the staged namelist's nIter0, so a run
# cannot link a pickup its namelist does not start from (IMPACTS_PICKUP_ITER
# still overrides it); a run from rest links nothing. The run directory is
# IMPACTS_PICKUP_RUN_DIR or, when that is unset, the production spin-up 31203 --
# but only for a namelist of that spin-up's settings: any other namelist is
# refused rather than started silently from the production state, and has to
# name its run (the 2x spin-up 30983 for the visc2x variants, a kappa leg for its
# member). Since 2026-09-12; until then every adjoint definition hard-coded
# 30983's year-180 pickup, which the live namelist had not matched since
# 2026-09-09.
PRODUCTION_SPINUP_RUN=runs/forward/spinup_200yr_viscRef_ReMax2/DINO_1deg_frd_200yr_from_rest_viscRef_ReMax2_run31203
PRODUCTION_SPINUP_SETTINGS=viscRef_ReMax2
link_pickup() {
  local it dir settings
  it=${IMPACTS_PICKUP_ITER:-$(awk -F'[=, ]+' '{ sub(/^[[:space:]]+/, "") } tolower($1)=="niter0" {n=$2+0} END {print n+0}' data)}
  if (( it == 0 )); then
    echo "nIter0 = 0: a run from rest, no pickup linked"; return 0
  fi
  if [[ -n "${IMPACTS_PICKUP_RUN_DIR:-}" ]]; then
    dir=$IMPACTS_PICKUP_RUN_DIR
  else
    settings="_$(run_suffix_from_namelist "$PWD/data")_"
    if [[ "$settings" != *"_${PRODUCTION_SPINUP_SETTINGS}_"* ]]; then
      echo "ERROR: the staged namelist (${settings//_/ }) does not have the settings of the production"
      echo "       spin-up ($PRODUCTION_SPINUP_SETTINGS), the default pickup source. Name the run to start from"
      echo "       with IMPACTS_PICKUP_RUN_DIR (for a visc2x namelist, the 2x spin-up 30983)."
      exit 1
    fi
    dir=$SCRATCH_ROOT/DINO_1deg_outputs/$PRODUCTION_SPINUP_RUN
  fi
  it=$(printf '%010d' "$it")
  if [[ ! -f "$dir/pickup.$it.data" ]]; then
    echo "ERROR: $dir has no pickup.$it.data (nIter0 of the staged namelist)"; exit 1
  fi
  ln -s "$dir/pickup.$it.data" "pickup.$it.data"
  ln -s "$dir/pickup.$it.meta" "pickup.$it.meta"
  echo "pickup: $dir/pickup.$it"
}
