#!/bin/bash
#
# Bit-compare two MITgcm adjoint run directories, optionally waiting for a job
# to finish first.
#
#   tools/compare_adj_runs.sh [options] <reference-run-dir> <new-run-dir>
#
# Options:
#   --wait <jobid>    poll squeue until that job leaves the queue, then compare.
#                     Requires TWO consecutive empty squeue results 60 s apart,
#                     so a transient squeue failure cannot be mistaken for
#                     "the job finished" and compare a half-written run.
#   --report <file>   where to write the report
#                     (default: <new-run-dir>/comparison_vs_<ref basename>.txt)
#   --no-report       print the report but write no file
#   --work <dir>      keep the intermediate listings here (default: a mktemp dir)
#   -h, --help        this message
#
# Exit status: 0 if the two runs are equivalent, 1 if not, 2 on a usage error.
#
# What it compares, in seven sections: job completion; the file inventory;
# every ADJ*/adxx* sensitivity field; every other common file; the cost
# function; the %MON monitor stream; then a verdict.
#
# Three differences are EXPECTED between a run with useGrdchk=.TRUE. and one
# with it .FALSE., and are classified rather than reported as failures:
#
#   data.pkg              the flag itself
#   output_tap_adj.txt    grdchk's ph-test / ph-grd chatter
#   xx_theta.effective.*  grdchk leaves its last probe's perturbation behind --
#                         exactly one element differing by exactly grdchk_eps
#
# The old run's grdchk also emits extra %MON lines after the main run, so the
# monitor comparison matches the new run's lines against the reference run's
# LEADING BLOCK of the same length rather than comparing wholesale.
#
# A difference in data.cost confined to comments and the cost_atl_* keys (the
# cost section, a namelist setting since 2026-10-20) is reported as CONFIG, like
# a differing build_info.txt key, and does not fail the verdict: whether the two
# runs measured the same section is printed for the reader to judge.
#
# A fourth difference is EXPECTED between two runs of the PROFILER build
# (profile) and is likewise classified rather than reported as a failure:
#
#   tapenade_profile.NNNN.txt   Tapenade's per-rank cost/benefit tables carry
#                               measured CPU seconds and are sorted by them, so
#                               the timings and the row order differ run to run.
#                               They are compared with the times masked and the
#                               rows sorted; the call sites, call counts, peak
#                               stack and memory gains left must match exactly,
#                               or the file counts as an unexpected difference.
#
# Deliberately no `set -e`: every check must run, and the report must be
# written even when an earlier one fails.
#
# Example -- schedule it to run when an adjoint job finishes (the job-chaining
# recipe in the project notes covers this pattern in full):
#
#   ADJ=$(../../../tools/submit.sh scripts/submit_tapAdj.sh --parsable | tail -1)
#   sbatch --parsable --dependency=afterany:$ADJ run_comparison.sh
#

JOB=""; REPORT=""; WORK=""; WRITE_REPORT=yes
while [ $# -gt 0 ]; do
    case "$1" in
        --wait)      JOB="$2"; shift 2 ;;
        --report)    REPORT="$2"; shift 2 ;;
        --no-report) WRITE_REPORT=no; shift ;;
        --work)      WORK="$2"; shift 2 ;;
        -h|--help)   sed -n '2,/^$/p' "$0" | sed 's/^# \?//'; exit 0 ;;
        -*)          echo "unknown option: $1" >&2; exit 2 ;;
        *)           break ;;
    esac
done

OLD="${1:-}"; NEW="${2:-}"
if [ -z "$OLD" ] || [ -z "$NEW" ]; then
    echo "usage: $(basename "$0") [options] <reference-run-dir> <new-run-dir>" >&2
    echo "       $(basename "$0") --help" >&2
    exit 2
fi
OLD="${OLD%/}"; NEW="${NEW%/}"
[ -d "$OLD" ] || { echo "no such reference run directory: $OLD" >&2; exit 2; }

WORK="${WORK:-$(mktemp -d)}"; mkdir -p "$WORK"
REPORT="${REPORT:-$NEW/comparison_vs_$(basename "$OLD").txt}"

# ---------- wait for the job, if asked ----------
if [ -n "$JOB" ]; then
    gone=0
    while [ "$gone" -lt 2 ]; do
        if squeue -h -j "$JOB" 2>/dev/null | grep -q .; then gone=0; sleep 120
        else gone=$((gone+1)); sleep 60; fi
    done
fi

rc=0

main() {
echo "======================================================================"
echo " Adjoint run comparison"
echo "   reference: $OLD"
echo "   new      : $NEW${JOB:+   (job $JOB)}"
echo " generated: $(date)"
echo "======================================================================"
echo

# ---------- 1. job completion ----------
echo "---------- 1. job completion ----------"
if [ -n "$JOB" ]; then
    sacct -j "$JOB" --format=JobID,JobName%24,State,ExitCode,Elapsed -n 2>&1 | head -4
    echo "  (sverdrup has accounting disabled; run_timing.txt below is the record)"
fi
if [ ! -d "$NEW" ]; then
    echo "FATAL: run directory $NEW does not exist. Nothing to compare."
    return 1
fi
echo "run_timing.txt:"; sed 's/^/  /' "$NEW/run_timing.txt" 2>/dev/null || echo "  (missing)"
# adjoint runs write output_tap_adj.txt, forward runs output.txt
out="$NEW/output_tap_adj.txt"; [ -f "$out" ] || out="$NEW/output.txt"
n_end=$(grep -ac 'NORMAL END' "$out" 2>/dev/null); n_end=${n_end:-0}
echo "NORMAL END count (one per rank; 27 for the MPI DINO adjoint): $n_end"
if [ "$n_end" -eq 0 ]; then
    echo "  *** WARNING: no NORMAL END - the run did not finish cleanly ***"
    tail -20 "$out" 2>/dev/null | sed 's/^/    /'
fi
echo

# ---------- 2. file inventory ----------
echo "---------- 2. file inventory ----------"
( cd "$OLD" && find . -maxdepth 1 -type f -printf '%P\n' | sort > "$WORK/old.txt" )
( cd "$NEW" && find . -maxdepth 1 -type f -printf '%P\n' | sort > "$WORK/new.txt" )
comm -12 "$WORK/old.txt" "$WORK/new.txt" > "$WORK/common.txt"
comm -23 "$WORK/old.txt" "$WORK/new.txt" > "$WORK/only_old.txt"
comm -13 "$WORK/old.txt" "$WORK/new.txt" > "$WORK/only_new.txt"
printf 'common: %s   only in reference: %s   only in new: %s\n' \
  "$(wc -l < "$WORK/common.txt")" "$(wc -l < "$WORK/only_old.txt")" "$(wc -l < "$WORK/only_new.txt")"
echo "only in the REFERENCE run:"; sed 's/^/    /' "$WORK/only_old.txt"
echo "only in the NEW run:";       sed 's/^/    /' "$WORK/only_new.txt"
echo

# ---------- 3. the sensitivities ----------
echo "---------- 3. sensitivity fields (ADJ* / adxx*), bit-comparison ----------"
grep -E '^(ADJ|adxx)' "$WORK/common.txt" > "$WORK/sens.txt"
: > "$WORK/sens_diff.txt"
same=0; diffc=0
while IFS= read -r f; do
    if cmp -s "$OLD/$f" "$NEW/$f"; then same=$((same+1))
    else diffc=$((diffc+1)); printf '%s\n' "$f" >> "$WORK/sens_diff.txt"; fi
done < "$WORK/sens.txt"
echo "compared : $(wc -l < "$WORK/sens.txt") files"
echo "           ADJ*.data  : $(grep -c '^ADJ.*\.data$'  "$WORK/sens.txt")"
echo "           adxx*.data : $(grep -c '^adxx.*\.data$' "$WORK/sens.txt")"
echo "identical: $same"
echo "differing: $diffc"
[ "$diffc" -gt 0 ] && { echo "differing files (first 60):"; head -60 "$WORK/sens_diff.txt" | sed 's/^/    /'; }
echo

# ---------- 4. everything else ----------
echo "---------- 4. all other common files ----------"
echo "(excluding STDOUT.*/STDERR.* (build date, node, grdchk section, timers),"
echo " the executable and run_timing.txt (wall clock); build_info.txt is compared"
echo " field by field just below, because parts of it must differ)"
grep -vE '^(ADJ|adxx)' "$WORK/common.txt" \
  | grep -vE '^(STDOUT\.|STDERR\.|mitgcmuv|run_timing\.txt$|build_info\.txt$)' > "$WORK/other.txt"
: > "$WORK/other_diff.txt"
osame=0; odiff=0
while IFS= read -r f; do
    if cmp -s "$OLD/$f" "$NEW/$f"; then osame=$((osame+1))
    else odiff=$((odiff+1)); printf '%s\n' "$f" >> "$WORK/other_diff.txt"; fi
done < "$WORK/other.txt"
echo "compared : $(wc -l < "$WORK/other.txt")"
echo "identical: $osame"
echo "differing: $odiff"
unexpected=0
if [ "$odiff" -gt 0 ]; then
    echo "differing files:"
    while IFS= read -r f; do
        case "$f" in
            data.pkg|output_tap_adj.txt|output.txt|xx_theta.effective.*)
                tag="[expected: grdchk]" ;;
            data.cost)
                # The cost section is a data.cost setting since 2026-10-20 (DINO: cost_atl_jsec,
                # cost_atl_kmaxdepth), so two runs may legitimately stage different files here --
                # of the same section (one wrote the keys, the other took the compiled defaults;
                # comments) or of different sections, which is a configuration difference, as a
                # differing build_info.txt key is below. Any other key differing stays unexpected.
                strip() { grep -vE '^[[:space:]]*(#|$)' "$1" | grep -viE '^[[:space:]]*cost_atl_'; }
                if diff <(strip "$OLD/$f") <(strip "$NEW/$f") > /dev/null 2>&1
                then tag="[CONFIG: the cost section (cost_atl_* keys and comments only)]"
                else tag="[UNEXPECTED: a key other than the cost section differs]"; unexpected=$((unexpected+1)); fi ;;
            tapenade_profile.*.txt)
                # the profiler's table: measured times masked, rows sorted --
                # what is left (call sites, counts, peak stack, memory) must match
                if diff <(sed -E 's/Time gain[ -]*[0-9.]+ s\./Time gain <t>/' "$OLD/$f" | sort) \
                        <(sed -E 's/Time gain[ -]*[0-9.]+ s\./Time gain <t>/' "$NEW/$f" | sort) > /dev/null 2>&1
                then tag="[expected: profiler timings]"
                else tag="[UNEXPECTED: profiler table differs beyond the measured times]"; unexpected=$((unexpected+1)); fi ;;
            *)  tag="[UNEXPECTED]"; unexpected=$((unexpected+1)) ;;
        esac
        echo "  --- $f  $tag"
        case "$f" in
          tapenade_profile.*.txt)
            echo "      $(diff "$OLD/$f" "$NEW/$f" 2>/dev/null | grep -c '^[<>]') raw lines differ; with measured times masked and rows sorted: $(diff <(sed -E 's/Time gain[ -]*[0-9.]+ s\./Time gain <t>/' "$OLD/$f" | sort) <(sed -E 's/Time gain[ -]*[0-9.]+ s\./Time gain <t>/' "$NEW/$f" | sort) 2>/dev/null | grep -c '^[<>]') lines" ;;
          xx_theta.effective.*.data)
            python3 -c "
import numpy as np
a=np.fromfile('$OLD/$f',dtype='>f8'); b=np.fromfile('$NEW/$f',dtype='>f8')
nz=np.nonzero(a-b)[0]
print(f'      elements differing: {nz.size} of {a.size}')
if nz.size: print(f'      magnitudes: {sorted(set(np.round(a[nz]-b[nz],12)))[:5]}  (expect one value == grdchk_eps)')
" 2>/dev/null || echo "      (numpy check unavailable)" ;;
          data.cost)
            echo "      ref: $(grep -iE '^[[:space:]]*cost_atl_' "$OLD/$f" | tr -s ' ' | tr '\n' ' ')"
            echo "      new: $(grep -iE '^[[:space:]]*cost_atl_' "$NEW/$f" | tr -s ' ' | tr '\n' ' ')"
            echo "      (a run without the keys measured the build's compiled section: its build_info.txt says which)" ;;
          *) diff "$OLD/$f" "$NEW/$f" 2>/dev/null | head -14 | sed 's/^/      /' ;;
        esac
    done < "$WORK/other_diff.txt"
    echo "unexpected differences among them: $unexpected"
fi
echo

# ---- build_info.txt, field by field ---------------------------------------
# A whole-file cmp is useless here: build_info.txt records both WHAT was built
# and WHEN/FROM WHAT it was built, and the second group cannot match across two
# builds -- the build date is baked in, so no two builds are ever byte-identical.
# Blanket-ignoring the file would throw away the first group, which is exactly
# what tells you whether the two runs are the same configuration at all. So the
# keys are split:
#
#   provenance    expected to differ; says nothing about the configuration
#   configuration defines what was built; a difference is reported loudly but
#                 does NOT fail the verdict, because "different build, identical
#                 output" is a real and wanted result -- it is what the
#                 checkpointing study (ckpAll vs nocheckpoint) sets out to show.
#
# Keys absent on one side are reported as such rather than skipped: exe_md5 was
# only added on 2026-09-03, so any comparison against an older run hits this.
BI_PROVENANCE=" built exe_md5 git_commit git_modified_tracked_files invoked_as "

bi_keys() { sed -n 's/^\([A-Za-z_][A-Za-z0-9_]*\)=.*/\1/p' "$1" 2>/dev/null | sort -u; }
# trailing "# ..." comments are stripped: a reworded comment is not a config change
bi_val()  { sed -n "s/^$2=//p" "$1" 2>/dev/null | head -1             | sed -e 's/[[:space:]]*#.*$//' -e 's/[[:space:]]*$//'; }

echo "build_info.txt (field by field):"
if [ ! -f "$OLD/build_info.txt" ] || [ ! -f "$NEW/build_info.txt" ]; then
    bi_config_diff=-1
    echo "  not present in both runs — no build record to compare"
    [ -f "$OLD/build_info.txt" ] || echo "    reference has none (builds before 2026-09-02 wrote no record)"
    [ -f "$NEW/build_info.txt" ] || echo "    new run has none"
elif cmp -s "$OLD/build_info.txt" "$NEW/build_info.txt"; then
    bi_config_diff=0
    echo "  byte-identical — same build, same executable"
else
    bi_config_diff=0; bi_prov_diff=0
    for k in $( { bi_keys "$OLD/build_info.txt"; bi_keys "$NEW/build_info.txt"; } | sort -u ); do
        vo=$(bi_val "$OLD/build_info.txt" "$k"); vn=$(bi_val "$NEW/build_info.txt" "$k")
        [ "$vo" = "$vn" ] && continue
        case "$BI_PROVENANCE" in
            *" $k "*) bi_prov_diff=$((bi_prov_diff+1)); continue ;;
        esac
        bi_config_diff=$((bi_config_diff+1))
        printf '  CONFIG  %-24s ref: %s\n' "$k" "${vo:-(absent)}"
        printf '          %-24s new: %s\n' "" "${vn:-(absent)}"
    done
    if [ "$bi_config_diff" -eq 0 ]; then
        echo "  $bi_prov_diff provenance field(s) differ (build date, commit, exe_md5) — expected;"
        echo "  every configuration field matches, so this is the same build configuration"
    else
        echo "  -> the two runs came from DIFFERENT build configurations (above)."
        echo "     Not a fault by itself: identical output across configurations is the"
        echo "     point of a checkpointing or toolchain comparison. But read the"
        echo "     sensitivity verdict knowing that is what was compared."
    fi
fi
echo

# ---------- 5. cost function ----------
echo "---------- 5. cost function ----------"
# An MPI run's rank 0 writes fc and the %MON stream to STDOUT.0000; a serial
# run (SOMA's adjoint) has no STDOUT.* at all and writes both to
# output_tap_adj.txt. Read whichever the run has (2026-09-05; before that a
# serial run always compared as NOT CLEAN with an empty fc).
mon_of() { if [ -f "$1/STDOUT.0000" ]; then echo "$1/STDOUT.0000"; else echo "$1/output_tap_adj.txt"; fi; }
echo "(read from $(basename "$(mon_of "$NEW")"))"
fl_old=$(grep -a 'global fc' "$(mon_of "$OLD")" 2>/dev/null | head -1)
fl_new=$(grep -a 'global fc' "$(mon_of "$NEW")" 2>/dev/null | head -1)
echo "reference: $fl_old"
echo "new      : $fl_new"
fc_old=$(printf '%s' "$fl_old" | grep -oE '[-0-9.]+E[+-][0-9]+')
fc_new=$(printf '%s' "$fl_new" | grep -oE '[-0-9.]+E[+-][0-9]+')
if [ -n "$fc_old" ] && [ "$fc_old" = "$fc_new" ]; then
    echo "  -> IDENTICAL to all printed digits ($fc_new)"
else
    echo "  -> DIFFER  (reference='$fc_old'  new='$fc_new')"
fi
echo "(later 'global fc' lines in a grdchk run are its perturbed forward"
echo " integrations; only the first is the reference cost)"
echo

# ---------- 6. monitor stream ----------
echo "---------- 6. monitor output ----------"
grep -a '%MON' "$(mon_of "$OLD")" > "$WORK/mon_old.txt" 2>/dev/null
grep -a '%MON' "$(mon_of "$NEW")" > "$WORK/mon_new.txt" 2>/dev/null
n_mold=$(wc -l < "$WORK/mon_old.txt"); n_mnew=$(wc -l < "$WORK/mon_new.txt")
echo "%MON lines: reference=$n_mold  new=$n_mnew"
mon_verdict="n/a"
if [ "$n_mnew" -gt 0 ] && [ "$n_mold" -ge "$n_mnew" ]; then
    head -n "$n_mnew" "$WORK/mon_old.txt" > "$WORK/mon_old_head.txt"
    if cmp -s "$WORK/mon_old_head.txt" "$WORK/mon_new.txt"; then
        echo "  -> the new run's $n_mnew lines are BYTE-IDENTICAL to the reference's first $n_mnew"
        mon_verdict="identical"
    else
        echo "  -> monitor streams DIFFER; first 40 differing lines:"
        diff "$WORK/mon_old_head.txt" "$WORK/mon_new.txt" | head -40 | sed 's/^/      /'
        mon_verdict="differ"
    fi
elif [ "$n_mnew" -gt "$n_mold" ]; then
    echo "  -> the new run has MORE monitor lines than the reference; not comparable this way"
    mon_verdict="differ"
fi
echo

# ---------- 7. verdict ----------
echo "---------- 7. verdict ----------"
if [ "$n_end" -gt 0 ] && [ "$diffc" -eq 0 ] && [ "$unexpected" -eq 0 ] \
   && [ "$mon_verdict" != "differ" ] && [ -n "$fc_old" ] && [ "$fc_old" = "$fc_new" ]; then
    echo "EQUIVALENT: all $same sensitivity fields are bit-identical to the reference,"
    echo "the cost function matches to every printed digit, and the monitor stream"
    echo "matches byte for byte. Any remaining differences are the known"
    echo "consequences of running without grdchk."
    if [ "${bi_config_diff:-0}" -gt 0 ]; then
        echo
        echo "Note: the two runs came from DIFFERENT build configurations"
        echo "($bi_config_diff field(s) in build_info.txt; see section 4). Identical"
        echo "output across them is the result, not an oversight."
    elif [ "${bi_config_diff:-0}" -lt 0 ]; then
        echo
        echo "Note: no build record in one or both runs, so the build configurations"
        echo "could not be confirmed to match (see section 4)."
    fi
    return 0
else
    echo "NOT CLEAN - review the sections above:"
    echo "  NORMAL END ranks         : $n_end (expect one per rank)"
    echo "  differing sensitivities  : $diffc (expect 0)"
    echo "  unexpected other diffs   : $unexpected (expect 0)"
    echo "  cost function            : reference=$fc_old new=$fc_new"
    echo "  monitor stream           : $mon_verdict (expect identical)"
    if [ "${bi_config_diff:-0}" -gt 0 ]; then
        echo "  build configuration      : DIFFERS in $bi_config_diff field(s) (see section 4)"
    elif [ "${bi_config_diff:-0}" -lt 0 ]; then
        echo "  build configuration      : unconfirmed (no build record in one or both)"
    else
        echo "  build configuration      : same (provenance fields aside)"
    fi
    return 1
fi
}

main > "$WORK/report.txt" 2>&1
rc=$?
echo "Full listings kept in $WORK/" >> "$WORK/report.txt"
if [ "$WRITE_REPORT" = yes ]; then
    cp "$WORK/report.txt" "$REPORT" 2>/dev/null \
      && echo "Report written to $REPORT" >> "$WORK/report.txt"
fi
cat "$WORK/report.txt"
exit $rc
