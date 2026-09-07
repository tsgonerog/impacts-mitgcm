#!/usr/bin/env bash
#
# Pre-push sanity check for this repository.
#
# Reports the things that routinely dirty the tree here without anyone
# authoring a change, and the things that silently rot. Read-only: it never
# edits, stages, or pushes anything.
#
#     ./tools/pre_push_check.sh
#
# Exit status is 1 if something would actually break a push or a run, 0
# otherwise. Warnings are informational and do not affect the exit status.
#
set -uo pipefail
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

red=$'\033[31m'; yel=$'\033[33m'; grn=$'\033[32m'; dim=$'\033[2m'; off=$'\033[0m'
fail=0
ok()   { printf "  ${grn}ok${off}    %s\n" "$1"; }
warn() { printf "  ${yel}note${off}  %s\n" "$1"; }
bad()  { printf "  ${red}FAIL${off}  %s\n" "$1"; fail=1; }

echo "── notebook output filter ───────────────────────────────────────────"
if [[ -n "$(git config --get filter.nbstrip.clean || true)" ]]; then
    ok "nbstrip active — outputs are stripped on commit"
else
    bad "nbstrip NOT installed; notebooks would be committed with full outputs"
    printf "        ${dim}run ./analyses/tools/install_git_filters.sh${off}\n"
fi

if ( source tools/machine_env.sh >/dev/null 2>&1 ); then
    m=$( source tools/machine_env.sh >/dev/null 2>&1; echo "$MACHINE" )
    ok "machine profile resolves (MACHINE=$m)"
else
    bad "tools/machine_env.sh does not source cleanly"
fi

echo
echo "── side effects you did not author ──────────────────────────────────"
# Submit scripts used to sed -i the tracked namelist, so submitting a job edited
# the repo. They now patch the staged copy in the run directory instead, so a
# modified namelist here should only ever be one you edited by hand.
#
# The pathspec is scoped to */mysetups/*/ deliberately: git pathspec wildcards
# match '/', so a bare '*/input*/data*' also sweeps in ~900 files from the
# vendored MITgcm verification tree. 00_archive/ is excluded because it mirrors
# the live directory names and no submit script can reach it.
nl=$(git diff --name-only HEAD -- '*/mysetups/*/input*/data*' ':(exclude)*/00_archive/*' 2>/dev/null)
if [[ -n "$nl" ]]; then
    warn "namelist modified — if you did not edit this by hand, a submit script did"
    warn "(which should now be impossible; investigate rather than just committing):"
    printf "        %s\n" $nl
else
    ok "no namelist churn from a submitted job"
fi

echo
echo "── derived output leaking into the repo ─────────────────────────────"
imgs=$(git diff --cached --name-only --diff-filter=A 2>/dev/null | grep -E '^analyses/.*\.(png|jpg|gif|html)$' || true)
if [[ -n "$imgs" ]]; then
    bad "figures/animations staged under analyses/ — these belong on scratch:"
    printf "        %s\n" $imgs
else
    ok "no images staged under analyses/"
fi

big=$(git diff --cached --name-only --diff-filter=ACM 2>/dev/null | while read -r f; do
        [[ -f "$f" ]] || continue
        sz=$(git cat-file -s "$(git rev-parse ":$f" 2>/dev/null)" 2>/dev/null || echo 0)
        (( sz > 10485760 )) && printf "%s (%s MB)\n" "$f" "$((sz/1048576))"
      done)
if [[ -n "$big" ]]; then
    warn "staged blobs over 10 MB (GitHub hard-fails at 100 MB):"
    printf "        %s\n" "$big"
else
    ok "no oversized blobs staged"
fi

echo
echo "── Tapenade hooks directory ─────────────────────────────────────────"
# MITgcm_c69m/mods_tapenade_hooks/ is both the -mods directory every adjoint
# build uses and the upstream proposal; its own script checks that every file
# is new to the tree or a tree file plus added lines, and that patches/ is
# what the files give against the vendored tree.
if out=$(MITgcm_c69m/mods_tapenade_hooks/check_against_tree.sh --check 2>&1); then
    ok "mods_tapenade_hooks keeps the shape of an upstream contribution; patches/ current"
else
    bad "mods_tapenade_hooks/check_against_tree.sh --check failed:"
    printf "%s\n" "$out" | grep 'FAIL' | sed 's/^/       /'
    printf "        ${dim}run MITgcm_c69m/mods_tapenade_hooks/check_against_tree.sh to regenerate patches/${off}\n"
fi

echo
echo "── notebook scratch paths ───────────────────────────────────────────"
python3 - <<'PY'
import json, glob, re, os, sys
missing = {}
for p in sorted(glob.glob('analyses/**/*.ipynb', recursive=True)):
    if '.ipynb_checkpoints' in p:
        continue
    try:
        nb = json.load(open(p))
    except Exception:
        continue
    src = '\n'.join(''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code')
    # notebooks build run_dir from string literals split across lines
    j = re.sub(r'"\s*\n\s*"', '', src)
    j = re.sub(r"'\s*\n\s*'", '', j)
    for x in {y.rstrip('/') for y in re.findall(r'/scratch\d*/[^\s"\'),\]]+', j)}:
        if not os.path.exists(x):
            missing.setdefault(p, []).append(x)
total = sum(len(v) for v in missing.values())
if not total:
    print("  \033[32mok\033[0m    every scratch path referenced by a notebook exists")
else:
    print(f"  \033[33mnote\033[0m  {total} scratch path(s) do not resolve "
          f"in {len(missing)} notebook(s):")
    for f, xs in sorted(missing.items())[:6]:
        print(f"        {f.split('analyses/')[-1]}")
        for x in xs[:3]:
            print(f"          {x}")
PY

echo
if (( fail )); then
    printf "${red}Not ready to push.${off} Fix the FAIL lines above.\n"
else
    printf "${grn}Ready to push.${off}  git push origin main\n"
fi
exit $fail
