#!/usr/bin/env bash
#
# check_against_tree.sh -- verify that this directory keeps the shape of an
# upstream contribution, and derive the patch series from it.
#
#     ./check_against_tree.sh            verify, then (re)write patches/
#     ./check_against_tree.sh --check    verify, and fail if patches/ is stale
#                                        (this is what tools/pre_push_check.sh runs)
#     ./check_against_tree.sh --tree=DIR check against another MITgcm tree
#                                        (a newer checkpoint, before rebasing)
#
# What "the shape of an upstream contribution" means here:
#
#   * every file in this directory is either NEW to the tree, or a copy of a
#     tree file with lines ADDED and none removed -- with two declared
#     exceptions: stubs_tap_adj.F, where the five ADEXCH_* stubs are replaced
#     by implementations, and dummy_tap.F, where the four unreachable
#     DUMMY_IN_STEPPING_B/_D and DUMMY_FOR_ETAN_B/_D stubs are removed;
#   * a file that has become identical to its tree counterpart is reported
#     as "landed upstream": delete it here;
#   * the patch series in patches/ is exactly what these files give against
#     the vendored tree, and applies to it (git apply --check).
#
# The mapping below is the single statement of where each file goes in the
# tree; README.md repeats it in words. Keep the two in step.
#
# Exit status 1 on any failure. Writes only inside patches/, and only without
# --check.

set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
TREE="$HERE/../MITgcm"
MODE=write
for arg in "$@"; do
    case "$arg" in
        --check)   MODE=check ;;
        --tree=*)  TREE="${arg#--tree=}" ;;
        -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
        *) echo "unknown argument: $arg" >&2; exit 2 ;;
    esac
done
TREE="$(cd "$TREE" && pwd)" || { echo "FAIL  no MITgcm tree at $TREE" >&2; exit 1; }

# file here | destination in the tree | kind | patch number
#   new       : the tree has no such file
#   add       : tree file plus added lines, nothing removed
#   replace   : tree file with lines removed as well (a declared exception)
MAP=(
    "stubs_tap_adj.F         pkg/tapenade/stubs_tap_adj.F          replace 0001"
    "forward_step.F          model/src/forward_step.F              add     0002"
    "integr_continuity.F     model/src/integr_continuity.F         add     0002"
    "flow_tap                tools/TAP_support/flow_tap            add     0002"
    "dummy_tap.F             pkg/tapenade/dummy_tap.F              replace 0002"
    "dummy_in_stepping_tap.F pkg/tapenade/dummy_in_stepping_tap.F  new     0002"
    "tapenade_ad_diff.list   pkg/tapenade/tapenade_ad_diff.list    new     0002"
)
PATCH_TITLE_0001="Implement the ADEXCH adjoint halo exchanges of pkg/tapenade"
PATCH_TITLE_0002="Tapenade output hooks: ADJ*/G_J* dumps and adjoint-mode switches"

fail=0
ok()   { printf '  ok    %s\n' "$1"; }
bad()  { printf '  FAIL  %s\n' "$1"; fail=1; }
note() { printf '  note  %s\n' "$1"; }

echo "mods_tapenade_hooks against $TREE"

# ---- every file here is mapped, every mapped file is here ----------------
declare -A MAPPED
for entry in "${MAP[@]}"; do
    set -- $entry
    MAPPED[$1]=1
    [ -f "$HERE/$1" ] || bad "$1 is in the mapping but not in this directory"
done
for f in "$HERE"/*; do
    b=$(basename "$f")
    [ -f "$f" ] || continue
    case "$b" in README.md|check_against_tree.sh) continue ;; esac
    [ -n "${MAPPED[$b]:-}" ] || bad "$b is not in the mapping (add it to MAP in $(basename "$0") and to README.md)"
done

# ---- shape of each file -----------------------------------------------------
for entry in "${MAP[@]}"; do
    set -- $entry
    f=$1; dest=$2; kind=$3
    [ -f "$HERE/$f" ] || continue
    case "$kind" in
        new)
            if [ -e "$TREE/$dest" ]; then
                bad "$f: the tree already has $dest; it is not new any more"
            else
                ok "$f: new file for $dest ($(wc -l < "$HERE/$f") lines)"
            fi ;;
        add|replace)
            if [ ! -f "$TREE/$dest" ]; then
                bad "$f: no $dest in the tree to shadow"; continue
            fi
            added=$(diff "$TREE/$dest" "$HERE/$f" | grep -c '^>')
            removed=$(diff "$TREE/$dest" "$HERE/$f" | grep -c '^<')
            if [ "$added" -eq 0 ] && [ "$removed" -eq 0 ]; then
                bad "$f: identical to $dest -- landed upstream? delete it here"
            elif [ "$kind" = add ] && [ "$removed" -gt 0 ]; then
                bad "$f: removes $removed line(s) of $dest; only additions are allowed"
                diff "$TREE/$dest" "$HERE/$f" | grep '^<' | head -5 | sed 's/^/          /'
            elif [ "$kind" = add ]; then
                ok "$f: $dest plus $added added lines, nothing removed"
            else
                ok "$f: $dest with $added added, $removed removed (a declared exception: tree stubs replaced or removed)"
            fi ;;
    esac
done

# The flow declarations must not already be in the tree's file (a second
# copy would be harmless to Tapenade but means the block has landed).
if [ -f "$TREE/tools/TAP_support/flow_tap" ] && grep -q '^subroutine dummy_in_stepping_xyz_rl:' "$TREE/tools/TAP_support/flow_tap"; then
    bad "the tree's flow_tap already declares the hook externals"
fi

# ---- the patch series -------------------------------------------------------
gen_patches() {   # $1 = output directory
    local out=$1 entry f dest kind num
    mkdir -p "$out"
    for num in 0001 0002; do
        local title; eval "title=\$PATCH_TITLE_$num"
        local file="$out/$num-$(echo "$title" | tr 'A-Z' 'a-z' | tr -c 'a-z0-9\n' '-' | sed 's/-*$//; s/--*/-/g').patch"
        {
            echo "Subject: [PATCH] $title"
            echo
            echo "Generated from MITgcm_c69m/mods_tapenade_hooks/ against the tree at"
            echo "MITgcm_c69m/MITgcm (checkpoint69m) by check_against_tree.sh."
            echo "Apply from the tree's root with: git apply -p1 $(basename "$file")"
            echo
            for entry in "${MAP[@]}"; do
                set -- $entry
                f=$1; dest=$2; kind=$3
                [ "$4" = "$num" ] || continue
                [ -f "$HERE/$f" ] || continue
                if [ "$kind" = new ]; then
                    diff -u --label /dev/null --label "b/$dest" /dev/null "$HERE/$f"
                else
                    diff -u --label "a/$dest" --label "b/$dest" "$TREE/$dest" "$HERE/$f"
                fi
            done
        } > "$file"
    done
}

if [ "$MODE" = write ]; then
    rm -f "$HERE"/patches/*.patch
    gen_patches "$HERE/patches"
    ok "patches/ rewritten: $(ls "$HERE"/patches/*.patch | xargs -n1 basename | tr '\n' ' ')"
else
    tmp=$(mktemp -d)
    gen_patches "$tmp"
    if diff -qr "$tmp" "$HERE/patches" > /dev/null 2>&1; then
        ok "patches/ is current"
    else
        bad "patches/ is stale: run $(basename "$0") without --check to regenerate it"
        diff -qr "$tmp" "$HERE/patches" | sed 's/^/          /'
    fi
    rm -rf "$tmp"
fi

# The series must apply to the vendored tree (the repository is the git
# checkout the tree lives in). Read-only: --check applies nothing.
if [ -d "$REPO/.git" ] && [ "$TREE" = "$(cd "$HERE/../MITgcm" && pwd)" ]; then
    if git -C "$REPO" apply --check -p1 --directory=MITgcm_c69m/MITgcm "$HERE"/patches/*.patch 2> "$HERE/.apply_check.err"; then
        ok "patches/ apply cleanly to the vendored tree (git apply --check)"
    else
        bad "patches/ do not apply to the vendored tree:"
        sed 's/^/          /' "$HERE/.apply_check.err"
    fi
    rm -f "$HERE/.apply_check.err"
else
    note "not the vendored tree, or not in a git checkout: git apply --check skipped"
fi

echo
if [ "$fail" -eq 0 ]; then
    echo "OK: mods_tapenade_hooks has the shape of an upstream contribution."
else
    echo "FAIL: see above." >&2
fi
exit $fail
