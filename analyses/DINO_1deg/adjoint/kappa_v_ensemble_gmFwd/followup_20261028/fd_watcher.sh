#!/usr/bin/env bash
# Cancel each finite-difference run once its forward sweep has printed the cost; record the fc line.
# usage: FD_FC_LINES=<file> fd_watcher.sh <job id>...   (default ./fd_fc_lines.tsv)
OUT=${FD_FC_LINES:-./fd_fc_lines.tsv}
pending=("$@")
while ((${#pending[@]})); do
  still=()
  for j in "${pending[@]}"; do
    d=$(ls -d ${SCRATCH_ROOT:-/scratch2/$USER}/DINO_1deg_outputs/runs/adjoint/*_run$j 2>/dev/null | head -1)
    if [[ -n $d && -f $d/STDOUT.0000 ]] && line=$(grep -m1 'global fc' "$d/STDOUT.0000"); then
      scancel "$j"; echo -e "$j\t$(basename "$d")\t$line\t$(date -Is)" >> "$OUT"; echo "cancelled $j after fc: $line"
    elif squeue -h -j "$j" -o %t 2>/dev/null | grep -q .; then
      still+=("$j")
    else
      echo -e "$j\t$(basename "${d:-?}")\tENDED WITHOUT FC OR BEFORE WATCHER\t$(date -Is)" >> "$OUT"; echo "job $j no longer in the queue"
    fi
  done
  pending=("${still[@]}"); ((${#pending[@]})) && sleep 120
done
echo "watcher done"
