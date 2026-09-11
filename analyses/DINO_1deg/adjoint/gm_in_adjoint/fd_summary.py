#!/usr/bin/env python3
"""Finite-difference checks of the GM test: every adjoint against both models.

Written 2026-09-11 for the GM test of input_tap/variants/stability_study/. Two
models are checked: the GM model (GM/Redi on, the forward model of the spin-up and
the forward legs) and the GM-free model of the production adjoint. For each, the
cost J is taken from the first 'global fc' line of forward sweeps that were
cancelled once it was printed:

  * kappa_v +/-10 % (1.2e-6 m2/s): dJ/dkappa_v, against sum(adxx_diffkr);
  * Theta +/-delta in three boxes of the year-180 pickup (perturb_pickup.py):
    the cost change for +delta, against sum(adxx_theta * delta), delta read back
    from the perturbed pickups themselves.

The adjoints are the 5-yr gmFwd run (GM in the forward sweep only) and the
production adjoint (GM-free in both sweeps). An adjoint whose adxx files are not
complete yet is reported as pending.

    python fd_summary.py [--md out.md]
"""
import argparse
import glob
import os

import numpy as np

SCRATCH = '/scratch2/tshahriar/DINO_1deg_outputs'
SRC_PICKUP = SCRATCH + '/runs/forward/kappa_v_ensemble_ReMax2_approxAdv/DINO_1deg_frd_10yr_REF_ReMax2_run31205'
PICKUPS = SCRATCH + '/analysis/gm_in_adjoint/perturbed_pickups'
ITER = 3162240
DKAPPA = 1.2e-6
NX, NY, NZ = 51, 198, 36
THETA_RECORDS = slice(72, 108)                 # Theta in the pickup field list (perturb_pickup.py)

MODELS = {'GM': 31237, 'GM-free': 31206}       # J0: first fc of the unperturbed 5-yr run
KAPPA = {'GM': (31238, 31239), 'GM-free': (31231, 31232)}
PATCHES = {'deepN': {'GM': (31241, 31242), 'GM-free': (31247, 31248), 'what': '40-50 N, below 1500 m'},
           'midTrop': {'GM': (31243, 31244), 'GM-free': (31249, 31250), 'what': '0-10 N, 500-1500 m'},
           'soUpper': {'GM': (31245, 31246), 'GM-free': (31251, 31252), 'what': '40-60 S, 0-500 m'}}
ADJOINTS = [('gmFwd 31237', 31237), ('production 31206', 31206)]


def run_dir(jobid):
    hits = glob.glob('%s/runs/adjoint/*_run%d' % (SCRATCH, jobid)) + \
        glob.glob('%s/runs/adjoint/*/*_run%d' % (SCRATCH, jobid))
    if len(hits) != 1:
        raise SystemExit('run %d: %d directories found' % (jobid, len(hits)))
    return hits[0]


def fc(jobid):
    with open(os.path.join(run_dir(jobid), 'STDOUT.0000'), errors='replace') as f:
        for line in f:
            if 'global fc' in line:
                return float(line.split('=', 1)[1])
    raise SystemExit('run %d: no global fc line' % jobid)


def adxx(jobid, name):
    """The gradient, or None while the run is unfinished: adxx_* files are written
    as zeros when the run starts, and run_timing.txt gains 'Total runtime' only at
    the end."""
    d = run_dir(jobid)
    p = os.path.join(d, '%s.0000000000.data' % name)
    timing = os.path.join(d, 'run_timing.txt')
    done = os.path.exists(timing) and 'Total runtime' in open(timing).read()
    if not (done and os.path.exists(p) and os.path.getsize(p) == 8 * NX * NY * NZ):
        return None
    return np.fromfile(p, '>f8').reshape(NZ, NY, NX)


def pickup_theta(d):
    return np.fromfile(os.path.join(d, 'pickup.%010d.data' % ITER), '>f8').reshape(-1, NY, NX)[THETA_RECORDS]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--md', help='also write the tables as Markdown to this file')
    args = ap.parse_args()

    j0 = {m: fc(r) for m, r in MODELS.items()}
    theta0 = pickup_theta(SRC_PICKUP)
    tests = []                                  # (name, description, {model: (central, fwd, bwd)}, pert)

    fd = {}
    for m, (rp, rm) in KAPPA.items():
        jp, jm = fc(rp), fc(rm)
        fd[m] = ((jp - jm) / (2 * DKAPPA), (jp - j0[m]) / DKAPPA, (j0[m] - jm) / DKAPPA)
    tests.append(('kappa_v', 'uniform kappa_v, dJ/dkappa_v', fd, None))

    for name, spec in PATCHES.items():
        fd = {}
        for m in ('GM', 'GM-free'):
            rp, rm = spec[m]
            jp, jm = fc(rp), fc(rm)
            fd[m] = ((jp - jm) / 2, jp - j0[m], j0[m] - jm)
        delta = pickup_theta(os.path.join(PICKUPS, name + '_p')) - theta0
        amp = float(np.abs(delta).max())
        tests.append((name, 'Theta +%.3g K, %s, cost change' % (amp, spec['what']), fd, delta))

    lines = ['J0: GM %.9f, GM-free %.9f' % (j0['GM'], j0['GM-free']), '']
    head = '| test | GM model FD | GM-free model FD | ' + ' | '.join('%s (vs GM, vs GM-free)' % a for a, _ in ADJOINTS) + ' |'
    lines += [head, '|' + ' --- |' * (3 + len(ADJOINTS))]
    for name, desc, fd, delta in tests:
        row = '| %s: %s | %.4e (one-sided %.1f %% apart) | %.4e (%.1f %%) |' % (
            name, desc, fd['GM'][0], 100 * abs(fd['GM'][1] - fd['GM'][2]) / abs(fd['GM'][0]),
            fd['GM-free'][0], 100 * abs(fd['GM-free'][1] - fd['GM-free'][2]) / abs(fd['GM-free'][0]))
        for _, r in ADJOINTS:
            a = adxx(r, 'adxx_diffkr' if delta is None else 'adxx_theta')
            if a is None:
                row += ' pending |'
                continue
            pred = float(a.sum()) if delta is None else float((a * delta).sum())
            row += ' %.4e (%+.0f %%, %+.0f %%) |' % (pred, 100 * (pred / fd['GM'][0] - 1), 100 * (pred / fd['GM-free'][0] - 1))
        lines.append(row)
    text = '\n'.join(lines)
    print(text)
    if args.md:
        with open(args.md, 'w') as f:
            f.write(text + '\n')
        print('\nwrote %s' % args.md)


if __name__ == '__main__':
    main()
