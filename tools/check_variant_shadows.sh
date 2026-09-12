#!/usr/bin/env bash
#
# check_variant_shadows.sh -- the setup-local copies of MITgcm tree files must
# say which tree file they were derived from, and fail loudly when it changes.
#
# A variant directory (MITgcm_c69m/mysetups/<setup>/code_tap/variants/<name>/),
# the profiler's tools/tapenade_profiling/mods_profile/ and a setup's code_tap/
# itself hold whole copies of tree files with a few lines changed, compiled
# through genmake2 -mods in place of the tree's. Nothing in a build compares them
# with the tree, so after a checkpoint upgrade they would silently carry the old
# checkpoint's text into the executable. Each such directory keeps a TREE_BASE.txt:
#
#     <file>   <path under MITgcm_c69m/MITgcm>   <git blob of that tree file>
#     <file>   -   <origin, free text>           (not a tree file; not checked)
#
# naming, for every copy, the tree file and the blob it was derived from (or
# last reviewed against). The check:
#
#   * every Fortran, header or C source in the directory is listed (in a setup's
#     code_tap/, which also holds its own headers, only the listed files count);
#   * every listed tree file exists and still has the recorded blob -- if not, the
#     tree changed under the copy: re-derive it, then record the blob with --record;
#   * no copy is identical to its tree file (dead weight, or landed upstream).
#
# A variant directory with sources but no TREE_BASE.txt fails; code_tap/ without one is skipped.
#
#     tools/check_variant_shadows.sh               check against the vendored tree
#     tools/check_variant_shadows.sh --tree=DIR    check against another tree (a
#                                                  newer checkpoint, before upgrading)
#     tools/check_variant_shadows.sh --record DIR  rewrite the blobs in
#                                                  DIR/TREE_BASE.txt from the tree,
#                                                  after re-deriving the copies in DIR
#
# Exit status 1 on any failure. tools/pre_push_check.sh runs the check form.

set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TREE="$REPO/MITgcm_c69m/MITgcm"
RECORD=""
while [ $# -gt 0 ]; do
    case "$1" in
        --tree=*)  TREE="${1#--tree=}" ;;
        --record)  RECORD="${2:?--record needs a directory}"; shift ;;
        -h|--help) sed -n '2,36p' "$0"; exit 0 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
    shift
done
TREE="$(cd "$TREE" 2>/dev/null && pwd)" || { echo "FAIL  no MITgcm tree at $TREE" >&2; exit 1; }

# ---- --record: rewrite one manifest's blobs from the tree ------------------
if [ -n "$RECORD" ]; then
    m="$(cd "$RECORD" && pwd)/TREE_BASE.txt"
    [ -f "$m" ] || { echo "FAIL  no TREE_BASE.txt in $RECORD" >&2; exit 1; }
    tmp=$(mktemp)
    while IFS= read -r line; do
        read -r f path rest <<< "$line"
        if [ -n "${f:-}" ] && [ "${f:0:1}" != "#" ] && [ "${path:-}" != "-" ]; then
            [ -f "$TREE/$path" ] || { echo "FAIL  $path is not in $TREE" >&2; rm -f "$tmp"; exit 1; }
            printf '%-30s %-45s %s\n' "$f" "$path" "$(git hash-object "$TREE/$path")"
        else
            printf '%s\n' "$line"
        fi
    done < "$m" > "$tmp"
    mv "$tmp" "$m"
    echo "recorded the blobs of $TREE in ${m#$REPO/}"
    exit 0
fi

# ---- check ------------------------------------------------------------------
fail=0
ok()  { printf '  ok    %s\n' "$1"; }
bad() { printf '  FAIL  %s\n' "$1"; fail=1; }

echo "setup-local copies of tree files against $TREE"
for d in "$REPO"/MITgcm_c69m/mysetups/*/code_tap/ "$REPO"/MITgcm_c69m/mysetups/*/code_tap/variants/*/ "$REPO"/tools/tapenade_profiling/mods_profile/; do
    [ -d "$d" ] || continue
    d=${d%/}; rel=${d#$REPO/}
    # A setup's code_tap/ also holds its own headers and new files, so it is checked only
    # where it keeps a TREE_BASE.txt, and only for the files listed there.
    partial=0; [[ "$rel" == */code_tap ]] && partial=1
    srcs=$(cd "$d" && ls -1 -- *.F *.F90 *.h *.c *.flow 2>/dev/null)
    if [ ! -f "$d/TREE_BASE.txt" ]; then
        [ "$partial" -eq 0 ] && [ -n "$srcs" ] && bad "$rel: holds sources ($(echo $srcs)) but no TREE_BASE.txt"
        continue
    fi
    unset listed; declare -A listed=()
    while read -r f path rest; do
        case "${f:-}" in ''|\#*) continue ;; esac
        listed[$f]=1
        if [ ! -f "$d/$f" ]; then bad "$rel/$f: listed in TREE_BASE.txt but not in the directory"; continue; fi
        if [ "$path" = "-" ]; then ok "$rel/$f: not a tree file (${rest})"; continue; fi
        rec=${rest%% *}
        if [ ! -f "$TREE/$path" ]; then bad "$rel/$f: the tree has no $path"; continue; fi
        now=$(git hash-object "$TREE/$path")
        if [ "$now" != "$rec" ]; then
            bad "$rel/$f: $path changed since this copy was derived (blob ${rec:0:9} -> ${now:0:9}); re-derive the copy, then --record $rel"
        elif cmp -s "$d/$f" "$TREE/$path"; then
            bad "$rel/$f: identical to $path; delete the copy"
        else
            ok "$rel/$f: derived from $path at blob ${rec:0:9}, still current"
        fi
    done < "$d/TREE_BASE.txt"
    if [ "$partial" -eq 0 ]; then
        for f in $srcs; do
            [ -n "${listed[$f]:-}" ] || bad "$rel/$f: not listed in TREE_BASE.txt"
        done
    fi
done

echo
if [ "$fail" -eq 0 ]; then
    echo "OK: every setup-local copy names a tree file that has not changed under it."
else
    echo "FAIL: see above." >&2
fi
exit $fail
