#!/usr/bin/env bash
# The submissions of 2026-10-28 (the follow-up runs of the meeting review), kept as the record of what was run and how.
# Not meant to be rerun as is: it submits 25 jobs (about 60 node-hours). Run with --really to submit.
#   swap:   the reference state (REF leg 31366, year 180) and the 32x state (M7 leg 31373), each with its own kappa_v
#           and with the other's in the adjoint (live input_tap/data or kappa_v_ensemble/M7_...), 30 d and 1 yr
#   fd:     the localised kappa_v check, input_tap/variants/fd_checks/data_diffkrBoxFD{p,m}_..., 5 yr, cancelled by
#           fd_watcher.sh once the forward sweep has printed the cost
#   ownmax: the 8x member (M5 leg 31371) with the cost at its own maximum, row 196 (68.8 N), 848 m, 5 yr
#   sweep:  fourteen 1-yr adjoints of the reference state with the cost at rows 69 ... 175 (30 S ... 60 N), 848 m,
#           in five dependency lanes
set -euo pipefail
[[ "${1:-}" == --really ]] || { sed -n '2,10p' "$0"; exit 2; }
SETUP=$(cd "$(dirname "$0")/../../../../../MITgcm_c69m/mysetups/DINO_1deg" && pwd); cd "$SETUP"
R=${SCRATCH_ROOT:-/scratch2/$USER}/DINO_1deg_outputs/runs/forward/kappa_v_ensemble_gmFwd
REF_LEG=$R/DINO_1deg_frd_10yr_REF_ReMax2_run31366; M7_LEG=$R/DINO_1deg_frd_10yr_M7_ReMax2_run31373; M5_LEG=$R/DINO_1deg_frd_10yr_M5_ReMax2_run31371
M7=kappa_v_ensemble/M7_ReMax2_gmFwd_approxAdv; M5=kappa_v_ensemble/M5_ReMax2_gmFwd_approxAdv
MAP=${JOB_MAP:-./job_map.tsv}; [[ -s $MAP ]] || echo -e "job\texperiment\tcase\tstate_pickup\tduration_d\tjsec\tkmax\tdepends" > "$MAP"
sub() {  # sub <experiment> <case or ""> <pickup dir> <days> <jsec or ""> <kmax or ""> [dependency job]
  local exp=$1 tc=$2 pk=$3 days=$4 js=$5 km=$6 dep=${7:-}; local extra="--mail-type=NONE"; [[ -n $dep ]] && extra="$extra --dependency=afterany:$dep"
  local -a ev=(IMPACTS_TEST_CASE="$tc" IMPACTS_PICKUP_RUN_DIR="$pk" IMPACTS_DURATION_DAYS="$days"); [[ -n $js ]] && ev+=(IMPACTS_COST_JSEC=$js IMPACTS_COST_KMAXDEPTH=$km)
  local out id; out=$(env "${ev[@]}" ../../../tools/submit.sh scripts/submit_tapAdj.sh $extra 2>&1 | tail -1); id=$(echo "$out" | grep -o '[0-9]\+$' || true)
  [[ -n $id ]] || { echo "SUBMIT FAILED: $out" >&2; exit 1; }
  echo -e "$id\t$exp\t${tc:-live}\t$(basename "$pk")\t$days\t${js:--}\t${km:--}\t${dep:--}" >> "$MAP"; echo "$id $exp" >&2; echo "$id"
}
for days in 30 366; do
  sub swap_REFstate_REFkappa_${days}d ""  "$REF_LEG" $days "" "" >/dev/null
  sub swap_REFstate_32xkappa_${days}d $M7 "$REF_LEG" $days "" "" >/dev/null
  sub swap_32xstate_REFkappa_${days}d ""  "$M7_LEG"  $days "" "" >/dev/null
  sub swap_32xstate_32xkappa_${days}d $M7 "$M7_LEG"  $days "" "" >/dev/null
done
for s in p m; do sub fd_diffkrBox_${s}10 fd_checks/diffkrBoxFD${s}_ReMax2_gmFwd_approxAdv "$REF_LEG" 1830 "" "" >/dev/null; done
sub ownmax_M5_jsec196 $M5 "$M5_LEG" 1830 196 24 >/dev/null
rows=(69 74 80 90 120 127 131 137 144 148 155 158 166 175); lanes=("" "" "" "" "")
for n in "${!rows[@]}"; do l=$((n % 5)); id=$(sub sweep_1yr_jsec${rows[$n]} "" "$REF_LEG" 366 ${rows[$n]} 24 "${lanes[$l]}"); lanes[$l]=$id; done
echo "submitted; job map: $MAP"
