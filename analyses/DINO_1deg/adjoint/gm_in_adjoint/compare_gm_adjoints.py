#!/usr/bin/env python3
"""Compare DINO_1deg adjoint runs that differ in how GM/Redi enters the two sweeps.

Written 2026-09-11 for the GM test of input_tap/variants/stability_study/ (tags
from180yrPk_viscRef_ReMax2_gmFwd and _gmOn, against the live GM-free namelist).
For every run it reads the first 'global fc' line and the forward-sweep %MON
blocks of STDOUT.0000, the ADJ* dumps and the adxx_* gradients, and prints

  * fc of every run;
  * the forward-sweep monitor of every run against the reference run, at the
    last block of the forward sweep and as the largest relative difference;
  * per ADJ field and dump lead: the wet-point RMS of every run, and the pattern
    correlation and relative RMS difference, rms(run - ref) / rms(ref), of every
    run against the reference run;
  * the same for the adxx_* gradients, and the sum of adxx_diffkr (dJ/dkappa_v
    for a uniform kappa_v, the quantity the kappa finite differences check).

Precision and shape come from each .meta file (ADJ* float32, adxx_* float64).
The wet masks come from hFacC/hFacW/hFacS in --grid, a run directory holding them.

    python compare_gm_adjoints.py --grid <dir> --ref gmOn \\
        gmOn=<run dir> gmFwd=<run dir> gmOff=<run dir> [--leads 0,1,5,30] [--csv f]
"""
import argparse
import csv
import glob
import os
import re

import numpy as np

ADJ_FIELDS = [('ADJtheta', 'C'), ('ADJsalt', 'C'), ('ADJuvel', 'W'), ('ADJvvel', 'S'),
              ('ADJwvel', 'C'), ('ADJetan', 'C'), ('ADJdiffkr', 'C'), ('ADJqnet', 'C'),
              ('ADJempmr', 'C'), ('ADJtaux', 'W'), ('ADJtauy', 'S')]
ADXX_FIELDS = [('adxx_theta', 'C'), ('adxx_salt', 'C'), ('adxx_diffkr', 'C'),
               ('adxx_tauu', 'W'), ('adxx_tauv', 'S'), ('adxx_qnet', 'C'), ('adxx_empmr', 'C')]
MON_KEYS = ['dynstat_theta_mean', 'dynstat_theta_sd', 'dynstat_salt_mean', 'dynstat_salt_sd',
            'dynstat_uvel_max', 'dynstat_vvel_max', 'dynstat_wvel_max', 'dynstat_eta_sd',
            'ke_mean', 'ke_max']


def read_meta(path):
    with open(path) as f:
        txt = f.read()
    nd = int(re.search(r'nDims\s*=\s*\[\s*(\d+)', txt).group(1))
    dims = [int(v) for v in
            re.search(r'dimList\s*=\s*\[(.*?)\]', txt, re.S).group(1).replace(',', ' ').split()]
    prec = re.search(r"dataprec\s*=\s*\[\s*'(\w+)'", txt).group(1)
    nrec = int(re.search(r'nrecords\s*=\s*\[\s*(\d+)', txt).group(1))
    shape = [dims[3 * i] for i in range(nd)][::-1]
    if nrec > 1:
        shape = [nrec] + shape
    return nd, shape, {'float32': '>f4', 'float64': '>f8'}[prec]


def read_mds(base):
    nd, shape, dtype = read_meta(base + '.meta')
    return nd, np.fromfile(base + '.data', dtype=dtype).reshape(shape).astype(np.float64)


def nml(path, key):
    pat = re.compile(r'^\s*%s\s*=\s*([^,\s]+)' % key, re.I)
    val = None
    with open(path, errors='replace') as f:
        for line in f:
            if line.lstrip().startswith('#'):
                continue
            m = pat.match(line)
            if m:
                val = m.group(1)
    return val


def run_info(d):
    data = os.path.join(d, 'data')
    dt = nml(data, 'deltaT') or nml(data, 'deltaTClock') or '1800.'
    return int(nml(data, 'nIter0')), int(nml(data, 'nTimeSteps')), float(dt.replace('D', 'E'))


def first_fc(d):
    for name in ('STDOUT.0000', 'output_tap_adj.txt'):
        p = os.path.join(d, name)
        if os.path.exists(p):
            with open(p, errors='replace') as f:
                for line in f:
                    if 'global fc' in line:
                        return line.split('=', 1)[1].strip()
    return None


def forward_mon(d):
    """%MON blocks of the first forward sweep: stop when time_tsnumber stops increasing."""
    blocks, last = [], None
    with open(os.path.join(d, 'STDOUT.0000'), errors='replace') as f:
        for line in f:
            if 'global fc' in line:
                break
            if '%MON' not in line:
                continue
            m = re.search(r'%MON\s+(\S+)\s*=\s*(\S+)', line)
            if not m:
                continue
            key, val = m.group(1), m.group(2)
            if key == 'time_tsnumber':
                n = int(val)
                if last is not None and n <= last:
                    break
                last = n
                blocks.append({'time_tsnumber': n})
            elif blocks:
                try:
                    blocks[-1][key] = float(val.replace('D', 'E'))
                except ValueError:
                    pass
    return blocks


def rms(a, w):
    x = a[w]
    return float(np.sqrt((x * x).mean())) if np.isfinite(x).all() else float('inf')


def compare(a, b, w):
    x, y = a[w], b[w]
    if not (np.isfinite(x).all() and np.isfinite(y).all()):
        return float('nan'), float('nan')
    xc, yc = x - x.mean(), y - y.mean()
    den = np.sqrt((xc * xc).sum() * (yc * yc).sum())
    corr = float((xc * yc).sum() / den) if den > 0 else float('nan')
    ry = np.sqrt((y * y).mean())
    rel = float(np.sqrt(((x - y) ** 2).mean()) / ry) if ry > 0 else float('nan')
    return corr, rel


def mask_for(masks, point, nd, shape):
    return np.broadcast_to(masks[point] if nd == 3 else masks[point][0], shape)


def table(title, labels, ref, others, rows_out, field, entries):
    """entries: list of (lead or '', iteration, {label: array}, nd, point)."""
    print('\n== %s   (wet RMS; corr and rel. RMS difference against %s)' % (title, ref))
    head = ' %8s' % 'lead_d' + ''.join(' %11s' % ('rms[%s]' % l) for l in labels)
    head += ''.join(' %10s %9s' % ('corr[%s]' % o, 'rel[%s]' % o) for o in others)
    print(head)
    for lead, it, arrs, w in entries:
        line = ' %8s' % (('%.2f' % lead) if lead != '' else '-')
        r = {l: (rms(arrs[l], w) if l in arrs else float('nan')) for l in labels}
        line += ''.join(' %11.3e' % r[l] for l in labels)
        for o in others:
            c, rel = compare(arrs[o], arrs[ref], w) if (o in arrs and ref in arrs) else (float('nan'),) * 2
            line += ' %10.4f %9.3f' % (c, rel)
            rows_out.append([field, lead, it, o, r[o], c, rel])
        rows_out.append([field, lead, it, ref, r[ref], '', ''])
        print(line)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--grid', required=True, help='directory holding hFacC/W/S .data/.meta')
    ap.add_argument('--ref', required=True, help='label of the reference run')
    ap.add_argument('--leads', default='', help='comma-separated lead days to print (default: every dump)')
    ap.add_argument('--fields', default='', help='comma-separated ADJ fields (default: all)')
    ap.add_argument('--csv', help='write every number printed to this CSV file')
    ap.add_argument('runs', nargs='+', help='label=run_directory')
    args = ap.parse_args()

    runs = dict(r.split('=', 1) for r in args.runs)
    labels, ref = list(runs), args.ref
    others = [l for l in labels if l != ref]
    masks = {p: read_mds(os.path.join(args.grid, 'hFac' + p))[1] > 0 for p in 'CWS'}
    rows = []

    print('== fc (first global fc line)')
    for l in labels:
        print('  %-10s %s' % (l, first_fc(runs[l])))

    print('\n== forward sweep %%MON against %s: value at the last common block, and max |rel. diff| over the sweep' % ref)
    mons = {l: forward_mon(runs[l]) for l in labels}
    common = set(b['time_tsnumber'] for b in mons[ref])
    for l in others:
        common &= set(b['time_tsnumber'] for b in mons[l])
    if common:
        last = max(common)
        byts = {l: {b['time_tsnumber']: b for b in mons[l]} for l in labels}
        print('  last common time_tsnumber %d (%d common blocks)' % (last, len(common)))
        for k in MON_KEYS:
            if k not in byts[ref][last]:
                continue
            v0 = byts[ref][last][k]
            line = '  %-20s %s=%.6e' % (k, ref, v0)
            for o in others:
                v = byts[o][last].get(k, float('nan'))
                mx = max(abs(byts[o][n].get(k, np.nan) - byts[ref][n].get(k, np.nan))
                         / max(abs(byts[ref][n].get(k, np.nan)), 1e-30) for n in common)
                line += '   %s-%s=%+.3e (rel %+.2e, max rel %.2e)' % (o, ref, v - v0, (v - v0) / max(abs(v0), 1e-30), mx)
                rows.append(['MON_' + k, '', last, o, v, v - v0, mx])
            print(line)

    it0, nts, dt = run_info(runs[ref])
    iend = it0 + nts
    lead_of = lambda it: (iend - it) * dt / 86400.0
    iters = sorted(int(re.search(r'\.(\d{10})\.data$', p).group(1))
                   for p in glob.glob(os.path.join(runs[ref], 'ADJtheta.*.data')))
    if args.leads:
        sel = sorted({min(iters, key=lambda it: abs(lead_of(it) - float(w))) for w in args.leads.split(',')},
                     reverse=True)
    else:
        sel = sorted(iters, reverse=True)
    wanted = set(args.fields.split(',')) if args.fields else None

    for name, point in ADJ_FIELDS:
        if wanted and name not in wanted:
            continue
        entries = []
        for it in sel:
            arrs, nd, shape = {}, None, None
            for l in labels:
                base = os.path.join(runs[l], '%s.%010d' % (name, it))
                if os.path.exists(base + '.data'):
                    nd, arrs[l] = read_mds(base)
                    shape = arrs[l].shape
            if ref in arrs:
                entries.append((lead_of(it), it, arrs, mask_for(masks, point, nd, shape)))
        if entries:
            table(name, labels, ref, others, rows, name, entries)

    for name, point in ADXX_FIELDS:
        arrs, nd, shape = {}, None, None
        for l in labels:
            base = os.path.join(runs[l], '%s.0000000000' % name)
            if os.path.exists(base + '.data'):
                nd, arrs[l] = read_mds(base)
                shape = arrs[l].shape
        if ref in arrs:
            table(name, labels, ref, others, rows, name, [('', 0, arrs, mask_for(masks, point, nd, shape))])
            if name == 'adxx_diffkr':
                for l in labels:
                    if l in arrs:
                        s = float(arrs[l].sum())
                        print('  sum(adxx_diffkr)[%s] = %.4e' % (l, s))
                        rows.append(['sum_adxx_diffkr', '', 0, l, s, '', ''])

    if args.csv:
        with open(args.csv, 'w', newline='') as f:
            wr = csv.writer(f)
            wr.writerow(['field', 'lead_days', 'iteration', 'run', 'value_or_rms', 'corr_or_diff', 'rel_or_maxrel'])
            wr.writerows(rows)
        print('\nwrote %s' % args.csv)


if __name__ == '__main__':
    main()
