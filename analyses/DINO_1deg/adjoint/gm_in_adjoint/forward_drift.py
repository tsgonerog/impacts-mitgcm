#!/usr/bin/env python3
"""Forward-sweep drift between two DINO_1deg runs, from their monthly dynDiag output.

Written 2026-09-11 for the GM test of input_tap/variants/stability_study/
(*_ReMax2_gmFwd): the adjoint's forward sweep with GM/Redi on, the model of the
spin-up and the forward legs, against the production adjoint's GM-free forward
sweep from the same pickup. For the dynDiag records the two runs share it prints
the overturning indices of forward_legs.ipynb (maximum above 1000 m of the
depth-space streamfunction at the rows nearest 26, 41 and 55 N, its maximum at
3 S, its minimum), the volume-mean temperature, and the wet-point RMS and the
largest zonal-mean differences of THETA and SALT.

    python forward_drift.py --grid <dir> [--leg <run dir>] [--every 6] [--csv f] \\
        A=<run dir> B=<run dir>

--leg prints the same indices for the last record of another run (the forward
leg that wrote the pickup), as the state both sweeps start from.
"""
import argparse
import csv
import glob
import os
import re

import numpy as np

STEPS_PER_YEAR = 48 * 366


def read_meta(path):
    with open(path) as f:
        txt = f.read()
    nd = int(re.search(r'nDims\s*=\s*\[\s*(\d+)', txt).group(1))
    dims = [int(v) for v in
            re.search(r'dimList\s*=\s*\[(.*?)\]', txt, re.S).group(1).replace(',', ' ').split()]
    prec = re.search(r"dataprec\s*=\s*\[\s*'(\w+)'", txt).group(1)
    nrec = int(re.search(r'nrecords\s*=\s*\[\s*(\d+)', txt).group(1))
    m = re.search(r'fldList\s*=\s*\{(.*?)\}', txt, re.S)
    flds = [s.strip() for s in re.findall(r"'([^']*)'", m.group(1))] if m else []
    shape = [dims[3 * i] for i in range(nd)][::-1]
    return ([nrec] if nrec > 1 else []) + shape, {'float32': '>f4', 'float64': '>f8'}[prec], flds


def read_mds(base):
    shape, dtype, flds = read_meta(base + '.meta')
    a = np.fromfile(base + '.data', dtype=dtype)
    if a.size != int(np.prod(shape)):          # still being written
        return None, flds
    return a.reshape(shape).astype(np.float64), flds


def load_grid(d):
    g = lambda n: read_mds(os.path.join(d, n))[0]
    hfc, hfs = g('hFacC'), g('hFacS')
    drf, rc = g('DRF').ravel(), g('RC').ravel()
    return dict(hfc=hfc, hfs=hfs, drf=drf, rc=rc, dxg=g('DXG'), lat=g('YC')[:, 0],
                wet=hfc > 0, vol=hfc * drf[:, None, None] * g('RAC')[None])


def diag_iters(d):
    return sorted(int(re.search(r'\.(\d{10})\.data$', p).group(1))
                  for p in glob.glob(os.path.join(d, 'dynDiag.*.data')))


def load_rec(d, it):
    a, flds = read_mds(os.path.join(d, 'dynDiag.%010d' % it))
    if a is None:
        return None
    return {k: a[flds.index(k)] for k in ('THETA', 'SALT', 'VVEL')}


def indices(rec, g):
    tr = (rec['VVEL'] * g['dxg'][None] * g['drf'][:, None, None] * g['hfs']).sum(axis=2) / 1e6
    psi = np.cumsum(tr, axis=0)                 # (k, j): transport above the bottom of cell k
    up, lat = g['rc'] >= -1000, g['lat']
    out = {'amoc%d' % lp: float(np.nanmax(psi[up, int(np.abs(lat - lp).argmin())])) for lp in (26, 41, 55)}
    out['trop_max'] = float(np.nanmax(psi[:, int(np.abs(lat + 3).argmin())]))
    out['psi_min'] = float(np.nanmin(psi))
    out['Tmean'] = float((rec['THETA'] * g['vol']).sum() / g['vol'].sum())
    return out


def zonal_mean(f, wet):
    n = wet.sum(axis=2)
    with np.errstate(invalid='ignore', divide='ignore'):
        return np.where(n > 0, (f * wet).sum(axis=2) / np.maximum(n, 1), np.nan)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--grid', required=True, help='directory holding hFacC/S, DRF, RC, DXG, YC, RAC')
    ap.add_argument('--leg', help='run whose last dynDiag record is printed as the starting state')
    ap.add_argument('--every', type=int, default=1, help='print every n-th common record (the last is always printed)')
    ap.add_argument('--csv', help='write the table to this CSV file')
    ap.add_argument('runs', nargs=2, help='label=run_directory (two runs)')
    args = ap.parse_args()

    (la, da), (lb, db) = (r.split('=', 1) for r in args.runs)
    g = load_grid(args.grid)
    wet = g['wet']
    keys = ['amoc26', 'amoc41', 'amoc55', 'trop_max', 'psi_min', 'Tmean']

    if args.leg:
        its = diag_iters(args.leg)
        s = indices(load_rec(args.leg, its[-1]), g)
        print('starting state, last record of %s (iteration %d):' % (os.path.basename(args.leg.rstrip('/')), its[-1]))
        print('  ' + '  '.join('%s=%.3f' % (k, s[k]) for k in keys))

    common = sorted(set(diag_iters(da)) & set(diag_iters(db)))
    if not common:
        print('no common dynDiag records yet')
        return
    sel = common[::max(args.every, 1)]
    if sel[-1] != common[-1]:
        sel.append(common[-1])
    it0 = common[0] - 1464                      # first record closes the first 30.5-day average

    cols = ['year'] + ['%s_%s' % (k, l) for k in keys for l in (la, lb)] + ['rms_dT', 'rms_dS', 'max_zm_dT', 'max_zm_dS']
    print('\n%6s ' % 'year' + ' '.join('%9s' % c[:9] for c in cols[1:]))
    rows = []
    for it in sel:
        A, B = load_rec(da, it), load_rec(db, it)
        if A is None or B is None:
            continue
        sa, sb = indices(A, g), indices(B, g)
        dT, dS = A['THETA'] - B['THETA'], A['SALT'] - B['SALT']
        row = [(it - it0) / STEPS_PER_YEAR]
        for k in keys:
            row += [sa[k], sb[k]]
        row += [float(np.sqrt((dT[wet] ** 2).mean())), float(np.sqrt((dS[wet] ** 2).mean())),
                float(np.nanmax(np.abs(zonal_mean(A['THETA'], wet) - zonal_mean(B['THETA'], wet)))),
                float(np.nanmax(np.abs(zonal_mean(A['SALT'], wet) - zonal_mean(B['SALT'], wet))))]
        rows.append(row)
        print('%6.2f ' % row[0] + ' '.join('%9.3f' % v if abs(v) >= 1e-2 else '%9.2e' % v for v in row[1:]))

    if args.csv:
        with open(args.csv, 'w', newline='') as f:
            wr = csv.writer(f)
            wr.writerow(cols)
            wr.writerows(rows)
        print('\nwrote %s' % args.csv)


if __name__ == '__main__':
    main()
