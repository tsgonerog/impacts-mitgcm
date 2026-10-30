#!/bin/bash
# tools/lib/submit_body.sh -- the shared body of every submit script.
#
# Not a program: sourced, never executed (and deliberately not +x). The submit
# scripts in each setup's scripts/ directory
# (MITgcm_c69m/mysetups/<setup>/scripts/submit_*.sh) are short definition
# files carrying the #SBATCH header, the committed defaults and the pickup
# lines, and they end with
#
#     source "$SLURM_SUBMIT_DIR/../../../tools/lib/submit_body.sh"
#
# Everything from there on -- resolving the namelist variant, checking the
# build record, staging the run directory on scratch, patching the time
# stepping, running the model and timing it -- is this file, identically for
# every mode and variant of every setup. Until 2026-09-05 each submit script
# carried its own copy of this body.
#
# WHERE THIS RUNS: on the compute node, when the job STARTS. sbatch spooled
# the definition file at submission, but this body is read from the
# repository at start time -- exactly as tools/machine_env.sh, the namelists,
# the input binaries and the build directory always were -- so an edit here
# reaches every job still queued. Cancel and resubmit rather than assuming a
# queued job is frozen. The log under logs/ is a full `set -x` trace of what
# actually ran.
#
# Interface -- set by the definition before sourcing:
#
#   BUILD_DIR         build directory, relative to the setup directory  required
#   RUN_MODE          frd | tapAdj: chooses input/ or input_tap/, the
#                     executable, the model output file and
#                     runs/forward or runs/adjoint                       required
#   test_cases        namelist variant: "" (the live input*/data), <tag>, or
#                     <group>/<tag>                                      required
#   duration_days     run length in whole days                          required
#   TIME_PARAMS       array of namelist keys patched from <key>_days
#                     variables (monitorFreq adjMonitorFreq adjDumpFreq);
#                     listed explicitly on purpose -- see below          required
#   PARALLEL          mpi | serial: "$MPI_LAUNCHER $SLURM_NTASKS ./exe", or a
#                     bare ./exe                                      default mpi
#   EXPECT_RUN_TOKEN  refuse the executable unless build_info.txt's run_token
#                     is this: the build/submit pairing, enforced       optional
#   stage_extra()     optional; runs in the run directory after the namelist
#                     and its siblings are staged (swap a data.* file, ...)
#   stage_pickups()   optional; runs in the run directory: the ln -s lines
#                     for the pickup the selected namelist's start needs
#   post_run()        optional; runs in the run directory after the model ends
#
# Per-setup constants come from <setup>/scripts/setup_params.sh:
#
#   DELTA_T           time step in seconds
#   DURATION_KEY      nTimeSteps | endTime: how this setup's namelist states
#                     the run length; duration_days is converted accordingly
#   DAYS_PER_YEAR     whole years label the run directory <n>yr
#   run_suffix_from_namelist()  optional; given the staged namelist, prints the
#                     <start>_<settings> tokens that name a run of the live
#                     input*/data, which has no tag of its own
#   check_staged_namelists()  optional; runs in the run directory once the
#                     namelists are staged (after stage_extra) and exits to
#                     refuse a combination the setup does not allow (DINO: an
#                     adjoint without its adjoint-mode switches)
#   cost_section_token()  optional; given the 1-based row of the cost section
#                     (cost_atl_jsec of the staged data.cost), prints the token
#                     appended to an adjoint run directory's name (DINO: sec43N;
#                     since 2026-10-20)
#
# Per-run overrides from the environment, read here: IMPACTS_COST_JSEC and
# IMPACTS_COST_KMAXDEPTH (adjoint only) set cost_atl_jsec / cost_atl_kmaxdepth
# in the STAGED data.cost -- only for a build whose build_info.txt records
# cost_section=namelist (DINO since 2026-10-20; a build with the section as
# parameter statements is refused, since the namelist would not reach it).
# The duration and frequency overrides are read by the definition.
#
# The definition runs under `set -e` and `set -x`, and so does this file.

# ---------- guard ----------
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
    echo "ERROR: $(basename "$0") is a library; it is sourced by a scripts/submit_*.sh definition" >&2
    exit 2
fi
for v in BUILD_DIR RUN_MODE duration_days; do
    if [ -z "${!v:-}" ]; then
        echo "ERROR: the submit definition must set $v before sourcing submit_body.sh"; exit 2
    fi
done
if [ -z "${test_cases+set}" ]; then
    echo "ERROR: the submit definition must set test_cases (an empty string selects the live namelist)"; exit 2
fi
if [ -z "${TIME_PARAMS+set}" ] || [ "${#TIME_PARAMS[@]}" -eq 0 ]; then
    echo "ERROR: the submit definition must list the namelist keys to patch in TIME_PARAMS"; exit 2
fi
case "$RUN_MODE" in frd|tapAdj) ;; *) echo "ERROR: RUN_MODE must be frd or tapAdj, got '$RUN_MODE'"; exit 2 ;; esac
PARALLEL="${PARALLEL:-mpi}"
case "$PARALLEL" in mpi|serial) ;; *) echo "ERROR: PARALLEL must be mpi or serial, got '$PARALLEL'"; exit 2 ;; esac

# ========== MACHINE SETTINGS & MODULES ==========

# SLURM_SUBMIT_DIR is used rather than BASH_SOURCE because Slurm runs the
# definition from a spooled copy. It must be the SETUP directory, which is
# where tools/submit.sh runs sbatch: the #SBATCH -o logs/... path and every
# input*/ and build directory path below resolve against it.
if [ -z "${SLURM_SUBMIT_DIR:-}" ]; then
    echo "ERROR: SLURM_SUBMIT_DIR is unset -- this body runs inside a Slurm job"; exit 1
fi
SETUP_DIR="$SLURM_SUBMIT_DIR"
if [ ! -f "$SETUP_DIR/scripts/setup_params.sh" ]; then
    echo "ERROR: $SETUP_DIR is not a setup directory (no scripts/setup_params.sh)."
    echo "       Submit from the setup directory: ../../../tools/submit.sh scripts/<submit script>"
    exit 1
fi
SETUP_NAME="$(basename "$SETUP_DIR")"

# Per-machine scratch root, MPI launcher and module stack. On sverdrup this
# reproduces what ~/.bashrc already provides and changes nothing; on Perlmutter
# it loads PrgEnv-gnu and friends.
REPO_ROOT="$(cd "$SETUP_DIR/../../.." && pwd)"
source "$REPO_ROOT/tools/machine_env.sh"
impacts_load_modules

# shellcheck source=/dev/null
source "$SETUP_DIR/scripts/setup_params.sh"
for v in DELTA_T DURATION_KEY DAYS_PER_YEAR; do
    [ -n "${!v:-}" ] || { echo "ERROR: $v is not set in scripts/setup_params.sh"; exit 1; }
done

# ========== MODE ==========

if [ "$RUN_MODE" = tapAdj ]; then
    INPUT_DIR=input_tap; EXE=mitgcmuv_tap_adj; MODEL_OUT=output_tap_adj.txt; RUNS_SUB=adjoint
else
    INPUT_DIR=input;     EXE=mitgcmuv;         MODEL_OUT=output.txt;         RUNS_SUB=forward
fi

# ========== TEST CASE ==========

# Build optional suffix from the tag: "_<tag>" if non-empty, otherwise empty
# (avoids a trailing underscore). Only the LAST component of the tag is used:
# the group says where the namelist lives in this repository, not anything about
# the run, and run directories follow <start>_<settings> (see CLAUDE.md). So
# kappa_v_ensemble/M3_ReMax2 gives "_M3_ReMax2" and baseline/from_rest_visc2x
# gives "_from_rest_visc2x", byte for byte the name its runs had before the
# variants were grouped. Taking the basename also strips the '/', which would
# otherwise create a nested directory here rather than naming the run. Two groups
# sharing a member tag give run directories differing only by job id, which is
# the durable key anyway.
suffix=${test_cases:+_${test_cases##*/}}

# The duration feeds integer arithmetic below; reject junk early rather than
# letting bash evaluate an unset name as 0 and silently run zero timesteps.
if ! [[ "$duration_days" =~ ^[0-9]+$ ]]; then
  echo "ERROR: duration must be a whole number of days, got '$duration_days'"
  exit 1
fi

# Empty test_cases uses the live input*/data. Otherwise the tag names a file
# under input*/variants/, in one of two forms:
#
#   <tag>               -> variants/data_<tag>              a standalone config
#   <experiment>/<tag>  -> variants/<experiment>/data_<tag> one member of an
#                                                           experiment
#
# Every variant now lives in a group; the bare form is kept so that a tag from
# before the grouping, or a queued job's spooled script, still resolves.
if [[ -z "$test_cases" ]]; then
    namelist_data="$SETUP_DIR/$INPUT_DIR/data"
elif [[ "$test_cases" == */* ]]; then
    namelist_data="$SETUP_DIR/$INPUT_DIR/variants/${test_cases%/*}/data_${test_cases##*/}"
else
    namelist_data="$SETUP_DIR/$INPUT_DIR/variants/data_${test_cases}"
fi

# Safety check
if [[ ! -f "$namelist_data" ]]; then
  echo "ERROR: File $namelist_data not found!"
  exit 1
fi

# ---------- empty tag: name the run from the namelist itself ----------
# The live input*/data has no tag of its own, so a run of it would be named by
# duration alone. A setup that can classify its namelist supplies
# run_suffix_from_namelist in scripts/setup_params.sh (DINO derives
# <start>_<viscosity>: nIter0 -> from_rest / from<N>yrPk, the viscosity files
# -> viscRef / visc2x / viscD2x_Zref / viscGrid<value>, anything unrecognised
# -> liveData, so the name never claims a setting the script could not read).
# Without one the run is named by duration alone, as SOMA's always were.
if [[ -z "$test_cases" ]] && declare -F run_suffix_from_namelist > /dev/null; then
  suffix="_$(run_suffix_from_namelist "$namelist_data")"
  echo "empty IMPACTS_TEST_CASE: run named from the namelist as '${suffix#_}'"
fi

# ========== PATHS & NAMES ==========

base_dir="$SETUP_DIR"
build_dir="$base_dir/$BUILD_DIR"

# ---------- build identity: the run directory is named from what was built ----------
# build_info.txt is written by the build body after all its checks pass and
# says what the executable is: run_token = frd, or tapAdj_<ckp>[_<variant>]
# with <ckp> either ckpAll or nocheckpoint and <variant> adjVisc or
# profile. Taking the token from there rather than from this script means
# the run directory cannot claim a build it did not get. An executable with no
# record, or one that does not match its record (a by-hand make), is refused
# rather than run under a guessed name.
build_info="$build_dir/build_info.txt"
if [[ ! -f "$build_info" ]]; then
  echo "ERROR: $build_info not found -- rebuild with the build script"; exit 1
fi
# The executable must be the one build_info.txt describes. Compare checksums,
# not mtimes: /home is NFS, and a large executable's mtime is stamped when its
# writeback completes, which can land AFTER the small build_info.txt the build
# script writes moments later. That inversion is permanent and refuses a
# perfectly good build -- it cost jobs 31085 and 31086 on 2026-09-03, where the
# executable came out 13 s "newer" than its own record. The checksum is also
# strictly stronger: it catches an executable edited or relinked in place, which
# an mtime test only catches by accident. Builds predating exe_md5= (no such
# line in their build_info.txt) fall back to the old mtime test.
exe_md5_rec=$(sed -n 's/^exe_md5=//p' "$build_info" | sed 's/[[:space:]]*#.*$//')
if [[ -n "$exe_md5_rec" ]]; then
  exe_md5_now=$(md5sum "$build_dir/$EXE" | cut -d' ' -f1)
  if [[ "$exe_md5_now" != "$exe_md5_rec" ]]; then
    echo "ERROR: $build_dir/$EXE does not match the exe_md5 in build_info.txt -- rebuild with the build script"; exit 1
  fi
elif [[ "$build_dir/$EXE" -nt "$build_info" ]]; then
  echo "ERROR: $build_dir/$EXE is newer than its build_info.txt -- rebuild with the build script"; exit 1
fi
run_token=$(sed -n 's/^run_token=//p' "$build_info" | sed 's/[[:space:]]*#.*$//')
if [[ -z "$run_token" ]]; then
  echo "ERROR: no run_token line in $build_info"; exit 1
fi
# The build/submit pairing, enforced: a submit definition names the build it
# is written for, and a build directory holding some other variant is refused
# rather than silently run under this script's assumptions.
if [[ -n "${EXPECT_RUN_TOKEN:-}" && "$run_token" != "$EXPECT_RUN_TOKEN" ]]; then
  echo "ERROR: $build_dir holds run_token=$run_token, but this submit script expects $EXPECT_RUN_TOKEN"
  echo "       (build and submit script are a pair; rebuild, or use the matching submit script)"; exit 1
fi
# A token the build record already carries is not repeated from a namelist-derived suffix
# (written 2026-09-12 for DINO's approxAdv build, removed the same day, whose runs of a
# namelist setting the approximate-advection switch were named ..._gmFwd before the
# _approxAdv token existed). Tag-named runs keep the tag byte for byte.
if [[ -z "$test_cases" && -n "$suffix" ]]; then
  kept=""
  for t in ${suffix//_/ }; do [[ "_${run_token}_" == *"_${t}_"* ]] || kept="${kept}_$t"; done
  suffix=$kept
fi
# ---------- the cost section: a namelist setting, named in the run directory ----------
# Since 2026-10-20 DINO's cost section (the row and depth of code_tap/cost_atlantic_heat.F)
# is cost_atl_jsec / cost_atl_kmaxdepth of data.cost, and a build that reads them records
# cost_section=namelist. The effective row of this run is IMPACTS_COST_JSEC, else the
# cost_atl_jsec of the data.cost that will be staged (a variant's data.cost_<tag> sibling,
# else the live one), else the build's compiled default -- and the setup's
# cost_section_token names it in the run directory (_sec43N, ...), so a tag that says
# nothing about the section (the kappa members, the finite-difference sweeps) still gets
# a name that does. Computed here, before the run directory is made; applied to the
# staged data.cost below. An override on a build that compiles the section in is refused:
# the namelist would be read and ignored, and the run would be named for a section it
# does not measure.
cost_section_rec=$(sed -n 's/^cost_section=//p' "$build_info" | sed 's/[[:space:]]*#.*$//')
if [[ -n "${IMPACTS_COST_JSEC:-}${IMPACTS_COST_KMAXDEPTH:-}" ]]; then
  [[ "$RUN_MODE" = tapAdj ]] || { echo "ERROR: IMPACTS_COST_JSEC / IMPACTS_COST_KMAXDEPTH apply to an adjoint run only"; exit 1; }
  [[ "$cost_section_rec" = namelist ]] || {
    echo "ERROR: IMPACTS_COST_JSEC / IMPACTS_COST_KMAXDEPTH are set, but $build_dir's build_info.txt does not record"
    echo "       cost_section=namelist: its cost section is compiled in (${cost_section_rec:-no cost_section line}),"
    echo "       so the namelist would be ignored. Rebuild from a code_tap/ that carries cost.h and cost_readparms.F."
    exit 1; }
  for v in IMPACTS_COST_JSEC IMPACTS_COST_KMAXDEPTH; do
    [[ -z "${!v:-}" || "${!v}" =~ ^[0-9]+$ ]] || { echo "ERROR: $v must be a whole number, got '${!v}'"; exit 1; }
  done
fi
# What J is, record against source (DINO since 2026-10-29). The build body writes
# cost_units=Sv when the compiled cost_atlantic_heat.f is the rewritten routine (the
# transport across the whole row in Sv) and cost_units=tile_normalised for the tree's
# form (each tile's sum divided by its wet-cell count, about 1/16.6 of the transport).
# The source in code_tap/ says which form a build from it would get; a record that
# says otherwise, or says nothing while the source is the rewritten one, is a build
# older than the source, which this refuses: the submit body otherwise checks the
# executable against its own record only, and the five adjoint builds all compile
# the file, so a stale one would compute J in the other units under the same name.
if [[ "$RUN_MODE" = tapAdj && "$cost_section_rec" = namelist && -f "$SETUP_DIR/code_tap/cost_atlantic_heat.F" ]]; then
  cost_units_rec=$(sed -n 's/^cost_units=//p' "$build_info" | sed 's/[[:space:]]*#.*$//')
  if grep -q 'tileTransport' "$SETUP_DIR/code_tap/cost_atlantic_heat.F"; then cost_units_src=Sv
  elif grep -q 'countV' "$SETUP_DIR/code_tap/cost_atlantic_heat.F"; then cost_units_src=tile_normalised
  else cost_units_src=""; fi
  if [[ -n "$cost_units_src" && "$cost_units_rec" != "$cost_units_src" ]]; then
    echo "ERROR: code_tap/cost_atlantic_heat.F computes J as cost_units=$cost_units_src, but $build_dir's"
    echo "       build_info.txt records cost_units=${cost_units_rec:-nothing}: the build is older than the source and"
    echo "       would report J in other units under the same run name. Rebuild with the build script."
    exit 1
  fi
  echo "cost units: J in $cost_units_rec (build record and source agree)"
fi
cost_token=""
if [[ "$RUN_MODE" = tapAdj && "$cost_section_rec" = namelist ]] && declare -F cost_section_token > /dev/null; then
  cost_src="$SETUP_DIR/$INPUT_DIR/data.cost"
  if [[ -n "$test_cases" && -f "$(dirname "$namelist_data")/data.cost_${test_cases##*/}" ]]; then
    cost_src="$(dirname "$namelist_data")/data.cost_${test_cases##*/}"
  fi
  jsec_eff=${IMPACTS_COST_JSEC:-$(sed -n 's/^[[:space:]]*cost_atl_jsec[[:space:]]*=[[:space:]]*\([0-9]*\).*/\1/ip' "$cost_src" | head -1)}
  jsec_eff=${jsec_eff:-$(sed -n 's/^cost_atl_jsec_default=\([0-9]*\).*/\1/p' "$build_info")}
  [[ "$jsec_eff" =~ ^[0-9]+$ ]] || { echo "ERROR: could not determine the cost section's row (cost_atl_jsec) for this run"; exit 1; }
  cost_token="_$(cost_section_token "$jsec_eff")"
  echo "cost section: row $jsec_eff, named ${cost_token#_} in the run directory"
fi
# Duration label: whole years as "<n>yr", otherwise "<n>d", so the run
# directory matches the scratch naming convention (DINO: 366-day years, SOMA: 360).
if (( duration_days % DAYS_PER_YEAR == 0 )); then
    dur_label="$(( duration_days / DAYS_PER_YEAR ))yr"
else
    dur_label="${duration_days}d"
fi
run_dir="$SCRATCH_ROOT/${SETUP_NAME}_outputs/runs/${RUNS_SUB}/${SETUP_NAME}_${run_token}_${dur_label}${suffix}${cost_token}_run$SLURM_JOB_ID"  # unique per job

# ========== STAGE THE RUN DIRECTORY ==========

# create run directory in scratch and move into it
mkdir -p "$run_dir"
cd "$run_dir"

# copy and link input files into run directory
# -maxdepth 1 -type f skips input*/variants/; a plain glob would try to
# copy that directory and abort the script under set -e.
find "$base_dir/$INPUT_DIR" -maxdepth 1 -type f -exec cp {} . \;
ln -s "$base_dir/input_binaries"/* .
if [[ "$RUN_MODE" = tapAdj ]]; then
  ln -s "$base_dir/input_adj_binaries"/* .
fi

# Replace data file correctly
rm -f data
cp "$namelist_data" data

# ---------- sibling overrides: a variant may replace more than just `data` ----------
# Any file beside the chosen namelist named <mitgcm-file>_<tag> is staged over
# <mitgcm-file>. That is what lets one variant change a package flag as well as
# the namelist -- DINO's grdchk_repair tags need data.pkg (useGrdchk=.TRUE.) and
# data.grdchk as well as data. Until 2026-08-28 only the data half was staged, and
# a KPP variant (deleted 2026-09-12) silently ran without KPP.
variant_tag="${test_cases##*/}"
if [[ -n "$variant_tag" ]]; then
  for extra in "$(dirname "$namelist_data")"/*_"$variant_tag"; do
    [[ -f "$extra" ]] || continue
    target="$(basename "$extra")"; target="${target%_$variant_tag}"
    [[ "$target" == data ]] && continue          # the namelist itself, already staged
    cp "$extra" "$target"
    echo "staged sibling override: $(basename "$extra") -> $target"
  done
fi

# The definition's own staging step, if any (the adjoint-viscosity submit
# script adds its lines to data.autodiff here).
if declare -F stage_extra > /dev/null; then
  stage_extra
fi

# ---------- the cost section override, into the STAGED data.cost ----------
# IMPACTS_COST_JSEC / IMPACTS_COST_KMAXDEPTH (checked above: adjoint, namelist-section
# build, whole numbers) replace the key's value if the staged file sets it, or add the
# key before the end of the COST_NML group if it does not. Asserted afterwards, as the
# time-stepping patches are: a sed that matched nothing would run another section under
# this run's name.
if [[ "$RUN_MODE" = tapAdj ]]; then
  set_cost_key() {   # <key> <value>: in ./data.cost
    local key=$1 val=$2
    if grep -qiE "^[[:space:]]*${key}[[:space:]]*=" data.cost; then
      sed -i -E "s|^([[:space:]]*${key}[[:space:]]*=)[^,]+|\1 ${val}|I" data.cost
    else
      awk -v key="$key" -v val="$val" '
        BEGIN { ingrp=0 }
        tolower($0) ~ /^[[:space:]]*&cost_nml/ { ingrp=1 }
        ingrp && /^[[:space:]]*(&|\/)[[:space:]]*$/ { printf "  %s = %s,\n", key, val; ingrp=0 }
        { print }' data.cost > data.cost.new && mv data.cost.new data.cost
    fi
    grep -qiE "^[[:space:]]*${key}[[:space:]]*=[[:space:]]*${val}," data.cost \
      || { echo "ERROR: ${key} not set to ${val} in the staged data.cost"; exit 1; }
    echo "staged data.cost: ${key} = ${val} (IMPACTS_${key#cost_atl_} override)"
  }
  [[ -z "${IMPACTS_COST_JSEC:-}" ]]      || set_cost_key cost_atl_jsec "$IMPACTS_COST_JSEC"
  [[ -z "${IMPACTS_COST_KMAXDEPTH:-}" ]] || set_cost_key cost_atl_kmaxdepth "$IMPACTS_COST_KMAXDEPTH"
  if [[ -n "$cost_token" ]]; then
    # the row the name was derived from must be the row the staged file sets (or the compiled default)
    jsec_staged=$(sed -n 's/^[[:space:]]*cost_atl_jsec[[:space:]]*=[[:space:]]*\([0-9]*\).*/\1/ip' data.cost | head -1)
    jsec_staged=${jsec_staged:-$(sed -n 's/^cost_atl_jsec_default=\([0-9]*\).*/\1/p' "$build_info")}
    [[ "$jsec_staged" = "$jsec_eff" ]] || { echo "ERROR: the run is named for row $jsec_eff but the staged data.cost gives row $jsec_staged"; exit 1; }
  fi
fi

# The setup's own check of the staged namelists, if scripts/setup_params.sh
# defines one (DINO: the adjoint-mode switches its adjoint requires).
if declare -F check_staged_namelists > /dev/null; then
  check_staged_namelists
fi

# ---------- adjoint-mode switches and the -nocheckpoint list ----------
# data.autodiff can flip a package flag between the sweeps (use<PKG>InAdMode=.FALSE. while
# data.pkg sets use<PKG>=.TRUE.; DINO's GM/Redi since 2026-09-11), swap the advection
# scheme inside the adjoint sweep (useApproxAdvectionInAdMode; DINO since 2026-09-10) and
# scale the viscosity files there (viscFacInAd). FORWARD_STEP applies the switches at the
# start of its reverse sweep, so they reach only what is recorded after that: a checkpointed
# routine's primal is re-run, recording, inside its _B routine, but a routine differentiated
# in split mode (-nocheckpoint) is recorded where its caller records -- before the switches
# when that is FORWARD_STEP or another such split routine. If one of those reads a switched
# variable the adjoint is neither the one nor the other (runs 31156/31157 of the DINO
# stability study split do_oceanic_phys under the GM flip and blew up; 31056 split dynamics
# under the viscosity boost). So a build with a -nocheckpoint list is accepted with a flip
# only if its build_info.txt records nocheckpoint_switch_free=yes, which the list builds'
# post_build_checks write from tools/tapenade_profiling/check_nocheckpoint_switches.py over
# the compiled sources (since 2026-09-12). The list is read from the tap_extra line alone,
# because other lines of a record may mention the option in prose.
if [[ "$RUN_MODE" = tapAdj && -f data.autodiff ]]; then
  flips=""
  for pkg in GMRedi KPP GGL90 SALT_PLUME SEAICE; do
    if [[ -f data.pkg ]] && grep -qiE "^[[:space:]]*use${pkg}[[:space:]]*=[[:space:]]*\.?t" data.pkg \
       && grep -qiE "^[[:space:]]*use${pkg}InAdMode[[:space:]]*=[[:space:]]*\.?f" data.autodiff; then
      flips="$flips use${pkg}InAdMode"
    fi
  done
  if grep -qiE '^[[:space:]]*useApproxAdvectionInAdMode[[:space:]]*=[[:space:]]*\.?t' data.autodiff; then
    flips="$flips useApproxAdvectionInAdMode"
  fi
  # viscFacAdj is viscFacInAd in the adjoint sweep and viscFacInFw otherwise (both default 1).
  autodiff_real() {
    awk -F= -v k="$1" 'tolower($1) ~ "^[[:space:]]*" tolower(k) "[[:space:]]*$" \
        { v = $2; gsub(/[,[:space:]]/, "", v); gsub(/[dD]/, "e", v); x = v + 0; set = 1 }
        END { print (set ? x : 1) }' data.autodiff
  }
  if [[ "$(autodiff_real viscFacInAd)" != "$(autodiff_real viscFacInFw)" ]]; then
    flips="$flips viscFacInAd"
  fi
  if [[ -n "$flips" && "$(sed -n 's/^tap_extra=//p' "$build_info")" == *-nocheckpoint* ]] \
     && ! grep -q '^nocheckpoint_switch_free=yes' "$build_info"; then
    echo "ERROR: data.autodiff switches between the sweeps ($flips ), but $build_dir was built with a"
    echo "       -nocheckpoint list its build_info.txt does not record as free of switched variables"
    echo "       (nocheckpoint_switch_free=yes), so the switch would act on part of the recomputation only."
    echo "       Rebuild with a switch-free list, or use a build that checkpoints every call (ckpAll)."
    exit 1
  fi
  # The replacement for the implicit vertical advection lives in gad_implicit_r.F, which the
  # vendored tree lacks: every adjoint build has the horizontal and explicit vertical one
  # (gad_advection.F in mods_tapenade_hooks/, since 2026-09-12), but only a build whose
  # compiled gad_implicit_r.f carries it records approx_advection_implicit_vertical=yes
  # (every DINO adjoint build since 2026-09-12, from code_tap/; from 2026-09-10 only the
  # approxAdv build, whose record does not have the line).
  if [[ "$flips" == *useApproxAdvectionInAdMode* ]] \
     && grep -qiE '^[[:space:]]*(temp|salt)ImplVertAdv[[:space:]]*=[[:space:]]*\.?t' data \
     && ! grep -q '^approx_advection_implicit_vertical=yes' "$build_info"; then
    echo "ERROR: data.autodiff sets useApproxAdvectionInAdMode and data advects tracers implicitly in"
    echo "       the vertical, but $build_dir's build_info.txt does not record"
    echo "       approx_advection_implicit_vertical=yes: its gad_implicit_r.F lacks the replacement, and the"
    echo "       adjoint would be approximate only in part. Rebuild (DINO: code_tap/gad_implicit_r.F)."
    exit 1
  fi
fi

# ---------- time stepping: patch the STAGED copy, not the tracked namelist ----------
# This runs here, after staging, so the repo is never written to. It matters for
# more than tidiness: this body executes on the compute node when the job
# STARTS, so a sed against $namelist_data would race any other job that happens
# to start around the same time, and each run would stage whichever value landed
# last while its run-directory name claimed its own.
#
# The duration first: days -> nTimeSteps (DINO, at DELTA_T) or endTime seconds
# (SOMA), whichever key this setup's namelist states its run length with.
total_seconds=$(awk -v d="$duration_days" 'BEGIN{printf "%.0f", d*86400}')
case "$DURATION_KEY" in
  nTimeSteps) dur_val=$(awk -v s="$total_seconds" -v dt="$DELTA_T" 'BEGIN{printf "%.0f", s/dt}') ;;
  endTime)    dur_val="${total_seconds}." ;;
  *) echo "ERROR: DURATION_KEY must be nTimeSteps or endTime, got '$DURATION_KEY'"; exit 1 ;;
esac
sed -i -E "s|^([[:space:]]*${DURATION_KEY}=)[^,]+|\1${dur_val}|g" data
# sed exits 0 when it matches nothing, which would leave the namelist's own
# value in place and run a different experiment silently. Assert instead.
grep -qE "^[[:space:]]*${DURATION_KEY}=${dur_val}," data \
  || { echo "ERROR: ${DURATION_KEY} not patched to ${dur_val} in staged data"; exit 1; }

# Then each frequency: <name>_days -> seconds, patching only the RHS value
# (keep commas/spaces). The names come from the definition's explicit
# TIME_PARAMS list. Do NOT go back to `compgen -v | grep '_days$'`: that also
# enumerates exported environment variables, so any *_days variable in the
# submitting shell would silently become a namelist key (sbatch exports the
# environment by default).
for name in "${TIME_PARAMS[@]}"; do
  var="${name}_days"
  days_val="${!var:-}"
  [[ -n "$days_val" ]] || { echo "ERROR: TIME_PARAMS lists ${name} but ${var} is not set"; exit 1; }
  secs=$(awk -v d="$days_val" 'BEGIN{printf "%.0f", d*86400}')
  newval="${secs}."
  sed -i -E "s|^([[:space:]]*${name}=)[^,]+|\1${newval}|g" data
  grep -qE "^[[:space:]]*${name}=${newval}," data \
    || { echo "ERROR: ${name} not patched to ${newval} in staged data"; exit 1; }
done

# >>> disable GMRedi and KPP if needed (comment out if you want to keep the default version) <<<
#sed -i -E "s|(useKPP[[:space:]]*=[[:space:]]*)\.TRUE\.|\1.FALSE.|" data.pkg
#sed -i -E "s|(useGMRedi[[:space:]]*=[[:space:]]*)\.TRUE\.|\1.FALSE.|" data.pkg

# copy MITgcm executable to run directory, with its build record so the run
# directory itself says which build (script, -tap_extra, commit) it ran
cp -p "$build_dir/$EXE" .
cp -p "$build_info" .

#----- pickups ---------------
# The definition owns these: nIter0 is baked into whichever data_<tag> the
# test case selects, and its stage_pickups links the matching pickup. DINO's
# adjoint definitions derive it from the staged nIter0 through link_pickup in
# scripts/setup_params.sh (since 2026-09-12); the others link a fixed one.
if declare -F stage_pickups > /dev/null; then
  stage_pickups
fi

# ========== RUN & TIMING ==========

# record start time
run_start_time=$(date +%s)
echo "Run started at: $(date)" > run_timing.txt

# run the model
if [[ "$PARALLEL" = mpi ]]; then
  $MPI_LAUNCHER $SLURM_NTASKS ./"$EXE" > "$MODEL_OUT" 2>&1
else
  ./"$EXE" > "$MODEL_OUT" 2>&1
fi

# record end time
run_end_time=$(date +%s)
echo "Run ended at:   $(date)" >> run_timing.txt

# calculate and append elapsed time
elapsed=$((run_end_time - run_start_time))
printf "Total runtime:  %02d:%02d:%02d (HH:MM:SS)\n" \
    $((elapsed/3600)) $(( (elapsed%3600)/60 )) $((elapsed%60)) >> run_timing.txt

# The definition's own epilogue, if any (the profiler run echoes its table).
if declare -F post_run > /dev/null; then
  post_run
fi
