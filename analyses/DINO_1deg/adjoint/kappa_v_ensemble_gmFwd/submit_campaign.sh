#!/usr/bin/env bash
# Submit a kappa_v ensemble campaign as one dependency chain.
#
# TWO MODES (since 2026-10-13):
#
#   CAMPAIGN_LEGS_FROM=<campaign>   (the default, kappa_v_ensemble_gmFwd): reuse that campaign's spin-up, legs,
#       perturbed pickups and forcing files, and submit only the eight 5-yr adjoints and the sixteen
#       finite-difference sweeps -- the rerun of 2026-10-13 with the cost section moved to the overturning
#       maximum (43 N; code_tap/cost_atlantic_heat.F, overturning_maximum.py). The leg rows are copied into the new
#       job_map.tsv so campaign.py resolves the same leg directories. No dependencies: the legs have finished.
#   CAMPAIGN_LEGS_FROM=  (empty): the full chain below, as run on 2026-09-13.
#
# CAMPAIGN_NAME names the campaign (analysis/<name>/job_map.tsv; the 43 N rerun by default, see campaign.py).
#
# The full chain, as submitted on /scratch on 2026-09-13 (/scratch2, which holds the production spin-up 31203, had
# failed on 2026-09-12 at 18:45):
#
#   spin-up   170 yr from rest, the live input/data                              (about 27 h)
#   legs      REF_ReMax2 and M1-M7_ReMax2, 10 yr from the spin-up's year 170       after the spin-up
#   adjoints  reference 5 yr, the live input_tap/data, from the REF leg's year 180  after the REF leg
#             members M1-M7 from their own legs' year 180                          after each leg
#   FD        kappa_v +-10 % and the forcing sweeps from the REF leg's year 180    after the REF leg
#             Theta boxes from perturbed copies of that pickup                     after the pickup job
#
# The REF leg continues the spin-up from year 170 with the same settings, so the reference adjoint starts from the
# spin-up's year-180 state. Writes analysis/kappa_v_ensemble_gmFwd/job_map.tsv. watch_campaign.sh cancels the FD
# sweeps once they print their cost.
set -euo pipefail
export SCRATCH_ROOT=${SCRATCH_ROOT:-/scratch2/$USER}   # /scratch/$USER while /scratch2 was down, 2026-09-12 to 2026-09-15
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP="$(cd "$HERE/../../../../MITgcm_c69m/mysetups/DINO_1deg" && pwd)"
O=$SCRATCH_ROOT/DINO_1deg_outputs
CAMPAIGN=${CAMPAIGN_NAME:-kappa_v_ensemble_gmFwd_sec43N}
LEGS_FROM=${CAMPAIGN_LEGS_FROM-kappa_v_ensemble_gmFwd}     # empty (CAMPAIGN_LEGS_FROM=) submits the spin-up and the legs too
A=$O/analysis/$CAMPAIGN
SHARED=$O/analysis/${LEGS_FROM:-$CAMPAIGN}                   # perturbed pickups and forcing files: the state's, not the section's
SUB=../../../tools/submit.sh
env | grep -q '^IMPACTS_' && { echo "unset the IMPACTS_* variables in this shell first"; exit 1; }
[ -z "${CAMPAIGN_SPINUP_JOB:-}" ] || [ -n "${CAMPAIGN_SPINUP_DIR:-}" ] || { echo "CAMPAIGN_SPINUP_JOB needs CAMPAIGN_SPINUP_DIR"; exit 1; }
[ -f "$SHARED/perturbed_forcing/empmr_m.bin" ] || { echo "perturbed forcing files missing in $SHARED/perturbed_forcing"; exit 1; }
# The cost section is compiled in: refuse to submit a campaign named for a section the executable does not carry.
case "$CAMPAIGN" in
  *_sec43N) want_jsec=148 ;;
  kappa_v_ensemble_gmFwd) want_jsec=127 ;;
  *) want_jsec= ;;
esac
have_jsec=$(sed -n 's/^cost_section_jsec=\([0-9]*\).*/\1/p' "$SETUP/build_tapAdj_ckpAll/build_info.txt" 2>/dev/null || true)
[ -z "$want_jsec" ] || [ "$have_jsec" = "$want_jsec" ] || { echo "build_tapAdj_ckpAll records cost_section_jsec=${have_jsec:-none}; campaign $CAMPAIGN needs $want_jsec -- rebuild first"; exit 1; }
mkdir -p "$A"
cd "$SETUP"
MAP=$A/job_map.tsv
[ -f "$MAP" ] && mv "$MAP" "$MAP.$(date +%Y%m%d_%H%M%S)"
printf 'job\trole\ttag\tpickup_from\tdepends_on\n' > "$MAP"
jid() { tail -1 | grep -oE '^[0-9]+'; }
row() { printf '%s\t%s\t%s\t%s\t%s\n' "$@" >> "$MAP"; }

if [ -n "$LEGS_FROM" ]; then
  # ---- reuse mode: the legs, the perturbed pickups and the forcing files of another campaign ----
  OLDMAP=$O/analysis/$LEGS_FROM/job_map.tsv
  [ -f "$OLDMAP" ] || { echo "no job map at $OLDMAP"; exit 1; }
  declare -A LEG
  while IFS=$'\t' read -r j role tag pk dep; do
    case "$role" in
      spin-up*) row "$j" "$role" "$tag" "$pk" "$dep" ;;                       # the record of the shared state
      "forward leg") t=${tag##*/}; t=${t%_ReMax2}; LEG[$t]=$j; row "$j" "$role (shared with $LEGS_FROM)" "$tag" "$pk" "$dep" ;;
    esac
  done < <(tail -n +2 "$OLDMAP")
  [ -n "${LEG[REF]:-}" ] && [ -n "${LEG[M7]:-}" ] || { echo "leg rows missing in $OLDMAP"; exit 1; }
  # (a plain loop, not `ls | head`: under set -e a failing command substitution ends the script without a word)
  legdir() { local d; for d in "$O"/runs/forward/*/DINO_1deg_frd_10yr_${1}_ReMax2_run${LEG[$1]} "$O"/runs/forward/DINO_1deg_frd_10yr_${1}_ReMax2_run${LEG[$1]}; do
               [ -d "$d" ] && { echo "$d"; return 0; }; done; echo "leg directory of $1 (job ${LEG[$1]}) not found under $O/runs/forward" >&2; return 1; }
  REF_DIR=$(legdir REF) || exit 1
  [ -f "$REF_DIR/pickup.0003162240.data" ] || { echo "REF leg's year-180 pickup missing in $REF_DIR"; exit 1; }
  for k in 1 2 3 4 5 6 7; do legdir M$k >/dev/null || exit 1; done
  PK=$SHARED/perturbed_pickups
  for n in deepN_p deepN_m midTrop_p midTrop_m soUpper_p soUpper_m; do
    [ -f "$PK/$n/pickup.0003162240.data" ] || { echo "perturbed pickup missing: $PK/$n"; exit 1; }
  done

  j=$(IMPACTS_PICKUP_RUN_DIR=$REF_DIR $SUB scripts/submit_tapAdj.sh --parsable | jid)
  row "$j" "reference adjoint 5 yr" "(live input_tap/data)" "REF leg ${LEG[REF]} yr 180" "-"
  for k in 1 2 3 4 5 6 7; do
    l=${LEG[M$k]}
    j=$(IMPACTS_TEST_CASE=kappa_v_ensemble/M${k}_ReMax2_gmFwd_approxAdv IMPACTS_PICKUP_RUN_DIR=$(legdir M$k) \
        $SUB scripts/submit_tapAdj.sh --parsable | jid)
    row "$j" "member adjoint 5 yr" "kappa_v_ensemble/M${k}_ReMax2_gmFwd_approxAdv" "leg $l yr 180" "-"
  done
  for t in REFp10 REFm10; do
    j=$(IMPACTS_TEST_CASE=fd_checks/${t}_ReMax2_gmFwd_approxAdv IMPACTS_PICKUP_RUN_DIR=$REF_DIR \
        $SUB scripts/submit_tapAdj.sh --parsable --mail-type=NONE | jid)
    row "$j" "FD kappa sweep" "fd_checks/${t}_ReMax2_gmFwd_approxAdv" "REF leg ${LEG[REF]} yr 180" "-"
  done
  for ctl in fu fv qnet empmr; do for t in p m; do
    j=$(IMPACTS_TEST_CASE=fd_checks/${ctl}FD${t}_ReMax2_gmFwd_approxAdv IMPACTS_PICKUP_RUN_DIR=$REF_DIR \
        $SUB scripts/submit_tapAdj.sh --parsable --mail-type=NONE | jid)
    row "$j" "FD forcing sweep ${ctl}_$t" "fd_checks/${ctl}FD${t}_ReMax2_gmFwd_approxAdv" "REF leg ${LEG[REF]} yr 180" "-"
  done; done
  for n in deepN_p deepN_m midTrop_p midTrop_m soUpper_p soUpper_m; do
    j=$(IMPACTS_TEST_CASE=fd_checks/thetaPatchFD_ReMax2_gmFwd_approxAdv IMPACTS_PICKUP_RUN_DIR=$PK/$n \
        $SUB scripts/submit_tapAdj.sh --parsable --mail-type=NONE | jid)
    row "$j" "FD theta sweep $n" "fd_checks/thetaPatchFD_ReMax2_gmFwd_approxAdv" "REF leg yr 180 + $n (of $LEGS_FROM)" "-"
  done
  column -t -s $'\t' "$MAP"
  exit 0
fi

# CAMPAIGN_SPINUP_JOB and CAMPAIGN_SPINUP_DIR, when set, chain the campaign on an existing (or queued) run that holds
# the year-170 pickup instead of submitting the spin-up (2026-09-14: the last 61 days of 31329, rerun). Both 31329 and
# 31365 were deleted on 2026-09-16 as byte-identical to 31203's first 170 years: a rerun would chain on
#   CAMPAIGN_SPINUP_JOB=31203 CAMPAIGN_SPINUP_DIR=<31203's run directory>
# and the two job_map rows below, which record what ran in 2026-09, would not apply.
if [ -n "${CAMPAIGN_SPINUP_JOB:-}" ]; then
  SPIN=$CAMPAIGN_SPINUP_JOB
  SPIN_DIR=$CAMPAIGN_SPINUP_DIR
  row 31329 "spin-up 170 yr (final pickup not written)" "(live input/data)" "rest" "-"
  row "$SPIN" "spin-up end, last 61 d" "kappa_v_ensemble/spinupEnd_ReMax2" "31329 pickup 2983632" "-"
else
  SPIN=$(IMPACTS_DURATION_DAYS=62220 $SUB scripts/submit_frd.sh --parsable | jid)
  SPIN_DIR=$O/runs/forward/DINO_1deg_frd_170yr_from_rest_viscRef_ReMax2_run$SPIN
  row "$SPIN" "spin-up 170 yr" "(live input/data)" "rest" "-"
fi

declare -A LEG
for t in REF M1 M2 M3 M4 M5 M6 M7; do
  LEG[$t]=$(IMPACTS_TEST_CASE=kappa_v_ensemble/${t}_ReMax2 IMPACTS_PICKUP_RUN_DIR=$SPIN_DIR \
            $SUB scripts/submit_frd.sh --parsable --dependency=afterok:$SPIN | jid)
  row "${LEG[$t]}" "forward leg" "kappa_v_ensemble/${t}_ReMax2" "spin-up $SPIN yr 170" "$SPIN"
done
REF_DIR=$O/runs/forward/DINO_1deg_frd_10yr_REF_ReMax2_run${LEG[REF]}

j=$(IMPACTS_PICKUP_RUN_DIR=$REF_DIR $SUB scripts/submit_tapAdj.sh --parsable --dependency=afterok:${LEG[REF]} | jid)
row "$j" "reference adjoint 5 yr" "(live input_tap/data)" "REF leg ${LEG[REF]} yr 180" "${LEG[REF]}"
for k in 1 2 3 4 5 6 7; do
  l=${LEG[M$k]}
  j=$(IMPACTS_TEST_CASE=kappa_v_ensemble/M${k}_ReMax2_gmFwd_approxAdv IMPACTS_PICKUP_RUN_DIR=$O/runs/forward/DINO_1deg_frd_10yr_M${k}_ReMax2_run$l \
      $SUB scripts/submit_tapAdj.sh --parsable --dependency=afterok:$l | jid)
  row "$j" "member adjoint 5 yr" "kappa_v_ensemble/M${k}_ReMax2_gmFwd_approxAdv" "leg $l yr 180" "$l"
done

for t in REFp10 REFm10; do
  j=$(IMPACTS_TEST_CASE=fd_checks/${t}_ReMax2_gmFwd_approxAdv IMPACTS_PICKUP_RUN_DIR=$REF_DIR \
      $SUB scripts/submit_tapAdj.sh --parsable --mail-type=NONE --dependency=afterok:${LEG[REF]} | jid)
  row "$j" "FD kappa sweep" "fd_checks/${t}_ReMax2_gmFwd_approxAdv" "REF leg ${LEG[REF]} yr 180" "${LEG[REF]}"
done
for ctl in fu fv qnet empmr; do for t in p m; do
  j=$(IMPACTS_TEST_CASE=fd_checks/${ctl}FD${t}_ReMax2_gmFwd_approxAdv IMPACTS_PICKUP_RUN_DIR=$REF_DIR \
      $SUB scripts/submit_tapAdj.sh --parsable --mail-type=NONE --dependency=afterok:${LEG[REF]} | jid)
  row "$j" "FD forcing sweep ${ctl}_$t" "fd_checks/${ctl}FD${t}_ReMax2_gmFwd_approxAdv" "REF leg ${LEG[REF]} yr 180" "${LEG[REF]}"
done; done

# the perturbed pickups can only be written once the REF leg has written its year-180 pickup
PK=$A/perturbed_pickups
PERT=$(sbatch --parsable --export=ALL -N 1 -n 1 -t 00:30:00 -J DINO_perturb_pickups -o logs/%x.%j.out --mail-type=NONE \
  --dependency=afterok:${LEG[REF]} --wrap "set -e; rm -rf $PK; mkdir -p $PK
    for spec in 'deepN 28:36,143:157,0:51 0.016' 'midTrop 20:28,99:110,0:51 0.035' 'soUpper 0:20,24:56,0:51 0.5'; do
      set -- \$spec
      python3 $HERE/../gm_in_adjoint/perturb_pickup.py --src $REF_DIR --iter 3162240 --field Theta --box \$2 --amp \$3 --grid $REF_DIR --out $PK/\$1_p
      python3 $HERE/../gm_in_adjoint/perturb_pickup.py --src $REF_DIR --iter 3162240 --field Theta --box \$2 --amp -\$3 --grid $REF_DIR --out $PK/\$1_m
    done" | tail -1)
row "$PERT" "perturbed pickups" "(perturb_pickup.py)" "REF leg ${LEG[REF]} yr 180" "${LEG[REF]}"
for n in deepN_p deepN_m midTrop_p midTrop_m soUpper_p soUpper_m; do
  j=$(IMPACTS_TEST_CASE=fd_checks/thetaPatchFD_ReMax2_gmFwd_approxAdv IMPACTS_PICKUP_RUN_DIR=$PK/$n \
      $SUB scripts/submit_tapAdj.sh --parsable --mail-type=NONE --dependency=afterok:$PERT | jid)
  row "$j" "FD theta sweep $n" "fd_checks/thetaPatchFD_ReMax2_gmFwd_approxAdv" "REF leg yr 180 + $n" "$PERT"
done
column -t -s $'\t' "$MAP"
