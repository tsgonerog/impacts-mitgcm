#!/usr/bin/env bash
# Submit one campaign of the heat-transport generation (2026-11-11): the eight 5-yr adjoints and the finite-difference
# sweeps of ONE cost section, from the YEAR-330 states of the extended kappa_v legs.
#
#     CAMPAIGN_NAME=kappa_v_heat_sec43N ./submit_heat_campaign.sh
#
# What differs from submit_campaign.sh (the generations from the legs' year 180, 2026-09 to 2026-11-01):
#   - the cost is the full-column meridional heat transport (IMPACTS_COST_QUANTITY=heat, cost_atl_kmaxdepth=36 = Nr),
#     decided with the advisor on 2026-11-03: integrated top to bottom, it has no interface to choose and is defined
#     on every row (campaign.py, notes Section 3.4 and 7.2);
#   - the states are year 330 of every member and of the reference, the end of the third 50-year chunk of
#     analysis/kappa_v_legs_extension/ (runs 31982-31989), where six members have stopped drifting by the rule of
#     leg_convergence.py; the 32x member's volume transport still rises (0.5 Sv per decade, tied to its still-warming
#     deep ocean) and the 0.25x member's still eases down from its overshoot, both documented, neither waited for;
#   - eight northern rows 5-7 degrees apart (the latitude sweep of 2026-10-28 decorrelates over about 5 degrees north
#     of 43 N, 8-11 between 30 and 43 N, more to the south; the hemispheres are unrelated, so the south is left for a
#     later campaign): 20 N, 26 N, 32 N, 38 N, 43 N, 48 N, 54 N and 60 N; 26 N, 43 N and 60 N compare row by row with
#     the volume-transport generations;
#   - the reference adjoint runs from a tagged namelist too (kappa_v_ensemble/REF_ReMax2_gmFwd_approxAdv_from330yrPk),
#     and every namelist is the earlier one with nIter0 = 5797440 (year 330) -- the *_from330yrPk twins;
#   - the Theta pickups are perturbed copies of the reference's year-330 pickup, written once into
#     analysis/kappa_v_legs_extension/perturbed_pickups/ before the first campaign; the forcing files of the first
#     generation are reused (analysis/kappa_v_ensemble_gmFwd/perturbed_forcing/, named by absolute path in the
#     fd_checks namelists; they do not depend on the state).
#
# Per campaign: 8 adjoints (about 13 h each on 27 ranks) and 18 finite-difference sweeps (kappa_v +-10 %, the four
# forcing controls +-, the four Theta boxes +-; two more boxes at 60 N), each sweep cancelled by watch_campaign.sh once
# its forward sweep has printed the cost. The watcher is started detached at the end, logging into the campaign's
# analysis directory. The job map copies the extension's chunk-3 rows as the campaign's "forward leg" rows, so that
# campaign.py resolves the states (its LEG_JOB strips the _from280yrPk suffix).
set -euo pipefail
export SCRATCH_ROOT=${SCRATCH_ROOT:-/scratch2/$USER}
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP="$(cd "$HERE/../../../../MITgcm_c69m/mysetups/DINO_1deg" && pwd)"
O=$SCRATCH_ROOT/DINO_1deg_outputs
CAMPAIGN=${CAMPAIGN_NAME:?set CAMPAIGN_NAME to one of kappa_v_heat_sec20N 26N 32N 38N 43N 48N 54N 60N}
STATE=kappa_v_legs_extension                 # the campaign whose chunk-3 runs hold the year-330 states
S=$O/analysis/$STATE
A=$O/analysis/$CAMPAIGN
YEAR=330; IT=5797440; PKNAME=$(printf 'pickup.%010d' $IT); SUF=_from330yrPk
SUB=../../../tools/submit.sh
env | grep -q '^IMPACTS_' && { echo "unset the IMPACTS_* variables in this shell first"; exit 1; }
case "$CAMPAIGN" in                           # 1-based rows (campaign.py holds them 0-based); the centre latitude in the comment
  kappa_v_heat_sec20N) JSEC=120 ;;            # 19.6 N
  kappa_v_heat_sec26N) JSEC=127 ;;            # 26.0 N, the row of the September campaigns
  kappa_v_heat_sec32N) JSEC=134 ;;            # 32.2 N
  kappa_v_heat_sec38N) JSEC=141 ;;            # 37.9 N
  kappa_v_heat_sec43N) JSEC=148 ;;            # 43.2 N, the overturning maximum
  kappa_v_heat_sec48N) JSEC=155 ;;            # 48.1 N
  kappa_v_heat_sec54N) JSEC=164 ;;            # 53.8 N
  kappa_v_heat_sec60N) JSEC=175 ;;            # 59.8 N
  *) echo "campaign $CAMPAIGN is not a heat campaign of this script"; exit 1 ;;
esac
KMAX=36                                       # the whole column: the heat transport, not its upper branch
BI=$SETUP/build_tapAdj_ckpAll/build_info.txt
grep -q '^cost_section=namelist' "$BI" 2>/dev/null || { echo "build_tapAdj_ckpAll does not record cost_section=namelist: rebuild first"; exit 1; }
grep -q '^cost_quantities=volume,heat' "$BI" || { echo "build_tapAdj_ckpAll does not record cost_quantities=volume,heat: rebuild from main first"; exit 1; }
export IMPACTS_COST_JSEC=$JSEC IMPACTS_COST_KMAXDEPTH=$KMAX IMPACTS_COST_QUANTITY=heat
echo "campaign $CAMPAIGN: heat transport across row $JSEC, $KMAX levels, from the year-$YEAR states"

# the states: the chunk-3 rows of the extension's job map
[ -f "$S/job_map.tsv" ] || { echo "no job map at $S/job_map.tsv"; exit 1; }
declare -A ST
while IFS=$'\t' read -r j role tag pk dep; do
  [ "$role" = "forward leg extension yr 280-330" ] || continue
  t=${tag##*/}; t=${t%%_*}
  ST[$t]=$j
done < <(tail -n +2 "$S/job_map.tsv")
for t in REF M1 M2 M3 M4 M5 M6 M7; do [ -n "${ST[$t]:-}" ] || { echo "no chunk-3 row for $t in $S/job_map.tsv"; exit 1; }; done
statedir() { local d; for d in "$O"/runs/forward/*/DINO_1deg_frd_50yr_${1}_ReMax2_from280yrPk_run${ST[$1]} "$O"/runs/forward/DINO_1deg_frd_50yr_${1}_ReMax2_from280yrPk_run${ST[$1]}; do
              [ -d "$d" ] && { echo "$d"; return 0; }; done; echo "state directory of $1 (job ${ST[$1]}) not found under $O/runs/forward" >&2; return 1; }
REF_DIR=$(statedir REF) || exit 1
for t in REF M1 M2 M3 M4 M5 M6 M7; do d=$(statedir $t) || exit 1; [ -f "$d/$PKNAME.data" ] || { echo "$t: $PKNAME missing in $d"; exit 1; }; done
PK=$S/perturbed_pickups
THETA_BOXES="deepN_p deepN_m midTrop_p midTrop_m soUpper_p soUpper_m deepNN_p deepNN_m"
case "$CAMPAIGN" in *sec60N*) THETA_BOXES="$THETA_BOXES subpolarDeep_p subpolarDeep_m secN60_p secN60_m" ;; esac
for n in $THETA_BOXES; do [ -f "$PK/$n/$PKNAME.data" ] || { echo "perturbed pickup missing: $PK/$n/$PKNAME (make_perturbed_pickups_yr330.sh)"; exit 1; }; done
[ -f "$O/analysis/kappa_v_ensemble_gmFwd/perturbed_forcing/empmr_m.bin" ] || { echo "the perturbed forcing files are missing"; exit 1; }

mkdir -p "$A"
cd "$SETUP"
MAP=$A/job_map.tsv
[ -f "$MAP" ] && mv "$MAP" "$MAP.$(date +%Y%m%d_%H%M%S)"
printf 'job\trole\ttag\tpickup_from\tdepends_on\n' > "$MAP"
jid() { tail -1 | grep -oE '^[0-9]+'; }
row() { printf '%s\t%s\t%s\t%s\t%s\n' "$@" >> "$MAP"; }
while IFS=$'\t' read -r j role tag pk dep; do
  [ "$role" = "forward leg extension yr 280-330" ] && row "$j" "forward leg (year-$YEAR state: chunk 3 of $STATE)" "$tag" "$pk" "$dep"
done < <(tail -n +2 "$S/job_map.tsv")

j=$(IMPACTS_TEST_CASE=kappa_v_ensemble/REF_ReMax2_gmFwd_approxAdv$SUF IMPACTS_PICKUP_RUN_DIR=$REF_DIR \
    $SUB scripts/submit_tapAdj.sh --parsable --mail-type=END | jid)
row "$j" "reference adjoint 5 yr" "kappa_v_ensemble/REF_ReMax2_gmFwd_approxAdv$SUF" "REF state ${ST[REF]} yr $YEAR" "-"
for k in 1 2 3 4 5 6 7; do
  j=$(IMPACTS_TEST_CASE=kappa_v_ensemble/M${k}_ReMax2_gmFwd_approxAdv$SUF IMPACTS_PICKUP_RUN_DIR=$(statedir M$k) \
      $SUB scripts/submit_tapAdj.sh --parsable --mail-type=END | jid)
  row "$j" "member adjoint 5 yr" "kappa_v_ensemble/M${k}_ReMax2_gmFwd_approxAdv$SUF" "M$k state ${ST[M$k]} yr $YEAR" "-"
done
for t in REFp10 REFm10; do
  j=$(IMPACTS_TEST_CASE=fd_checks/${t}_ReMax2_gmFwd_approxAdv$SUF IMPACTS_PICKUP_RUN_DIR=$REF_DIR \
      $SUB scripts/submit_tapAdj.sh --parsable --mail-type=NONE | jid)
  row "$j" "FD kappa sweep" "fd_checks/${t}_ReMax2_gmFwd_approxAdv$SUF" "REF state ${ST[REF]} yr $YEAR" "-"
done
for ctl in fu fv qnet empmr; do for t in p m; do
  j=$(IMPACTS_TEST_CASE=fd_checks/${ctl}FD${t}_ReMax2_gmFwd_approxAdv$SUF IMPACTS_PICKUP_RUN_DIR=$REF_DIR \
      $SUB scripts/submit_tapAdj.sh --parsable --mail-type=NONE | jid)
  row "$j" "FD forcing sweep ${ctl}_$t" "fd_checks/${ctl}FD${t}_ReMax2_gmFwd_approxAdv$SUF" "REF state ${ST[REF]} yr $YEAR" "-"
done; done
for n in $THETA_BOXES; do
  j=$(IMPACTS_TEST_CASE=fd_checks/thetaPatchFD_ReMax2_gmFwd_approxAdv$SUF IMPACTS_PICKUP_RUN_DIR=$PK/$n \
      $SUB scripts/submit_tapAdj.sh --parsable --mail-type=NONE | jid)
  row "$j" "FD theta sweep $n" "fd_checks/thetaPatchFD_ReMax2_gmFwd_approxAdv$SUF" "REF state yr $YEAR + $n (of $STATE)" "-"
done
column -t -s $'\t' "$MAP"

# the watcher, detached from this shell: cancels each FD sweep once its cost is printed, logs state changes
LOG=$A/watch_$(date +%Y%m%d_%H%M).log
nohup setsid env CAMPAIGN_NAME=$CAMPAIGN SCRATCH_ROOT=$SCRATCH_ROOT bash "$HERE/watch_campaign.sh" > "$LOG" 2>&1 < /dev/null &
echo "watcher started (pid $!), log $LOG"
