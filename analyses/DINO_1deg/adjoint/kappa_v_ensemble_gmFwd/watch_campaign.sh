#!/usr/bin/env bash
# Report state changes of the campaign's jobs (one line per change) and cancel each FD sweep once the model has
# printed its cost. Reads the job list from job_map.tsv. A job counts as ended only when squeue itself answered
# and no longer lists it, so a scheduler or filesystem hiccup is reported, not taken for an ending.
O=${SCRATCH_ROOT:-/scratch/$USER}/DINO_1deg_outputs
A=$O/analysis/kappa_v_ensemble_gmFwd
RE='^\(PID\.TID [0-9]{4}\.[0-9]{4}\) +global fc = +-?[0-9]\.[0-9]+E[-+][0-9]+'
mapfile -t ROWS < <(tail -n +2 "$A/job_map.tsv")
declare -A ROLE last fdone
for r in "${ROWS[@]}"; do IFS=$'\t' read -r j role _ <<<"$r"; ROLE[$j]=$role; done
while true; do
  if ! q=$(timeout 60 squeue -h -u "$USER" -o '%i %T' 2>/dev/null); then echo "squeue did not answer"; sleep 120; continue; fi
  if ! timeout 30 ls "$O/runs" >/dev/null 2>&1; then echo "scratch not readable"; sleep 120; continue; fi
  open=0
  for j in "${!ROLE[@]}"; do
    s=$(awk -v j="$j" '$1==j {print $2}' <<<"$q"); s=${s:-ENDED}
    [ "$s" != ENDED ] && open=$((open+1))
    if [[ "${ROLE[$j]}" == FD* && "${ROLE[$j]}" != *pickups* && -z "${fdone[$j]:-}" && "$s" == RUNNING ]]; then
      d=$(ls -d "$O"/runs/adjoint/*_run"$j" 2>/dev/null | head -1)
      line=$([ -n "$d" ] && grep -m1 -E "$RE" "$d/STDOUT.0000" 2>/dev/null)
      if [ -n "$line" ]; then
        v=$(sed -E 's/.*global fc = +//' <<<"$line")
        printf '%s\t%s\t%s\n' "$j" "$(basename "$d")" "$v" >> "$A/fd_fc_lines.tsv"
        scancel "$j"; fdone[$j]=1; echo "FD $j (${ROLE[$j]}): fc = $v, sweep cancelled"
      fi
    fi
    if [ "${last[$j]:-}" != "$s" ]; then
      [ "$s" != PENDING ] && [ "$s" != COMPLETING ] && echo "job $j (${ROLE[$j]}): $s"
      last[$j]=$s
    fi
  done
  [ "$open" -eq 0 ] && { echo "all campaign jobs have left the queue"; exit 0; }
  sleep 60
done
