#!/usr/bin/env python3
"""File the campaign's run directories under runs/{forward,adjoint}/kappa_v_ensemble_gmFwd/.

    python file_runs.py            # dry run: prints what would move
    python file_runs.py --apply

Refuses while any of the campaign's jobs is still queued or running. After moving, the pickup links of
the member adjoints (which point at their legs by absolute path) are relinked to the legs' new place.
"""
import os
import subprocess
import sys
from pathlib import Path

import campaign as c


def main(apply):
    jobs = list(c.LEG_JOB.values()) + list(c.ADJ_JOB.values()) + list(c.FD_JOB.values())
    q = subprocess.run(['squeue', '-h', '-u', os.environ['USER'], '-o', '%i'], capture_output=True, text=True).stdout.split()
    busy = sorted(set(map(int, q)) & set(jobs))
    if busy:
        sys.exit('still queued or running: %s' % busy)
    moves = []
    for j in c.LEG_JOB.values():
        d = c.run_dir(j)
        if d and d.parent.name != c.CAMPAIGN:
            moves.append((d, c.OUTPUTS / 'runs' / 'forward' / c.CAMPAIGN / d.name))
    for j in list(c.ADJ_JOB.values()) + list(c.FD_JOB.values()):
        d = c.run_dir(j)
        if d and d.parent.name != c.CAMPAIGN:
            moves.append((d, c.OUTPUTS / 'runs' / 'adjoint' / c.CAMPAIGN / d.name))
    for a, b in moves:
        print(('move ' if apply else 'would move ') + '%s -> %s' % (a, b.parent))
        if apply:
            b.parent.mkdir(parents=True, exist_ok=True)
            a.rename(b)
    if not apply:
        return
    old_legs = {str(a): str(b) for a, b in moves if '/forward/' in str(b)}
    for j in c.ADJ_JOB.values():
        d = c.run_dir(j)
        for lk in d.glob('pickup.*'):
            if lk.is_symlink():
                tgt = os.readlink(lk)
                for oa, ob in old_legs.items():
                    if tgt.startswith(oa + '/'):
                        lk.unlink()
                        lk.symlink_to(ob + tgt[len(oa):])
                        print('relinked', lk, '->', ob + tgt[len(oa):])


if __name__ == '__main__':
    main('--apply' in sys.argv)
