#!/usr/bin/env python3
"""Write a copy of an MITgcm pickup with one 3-D field perturbed in a box.

Written 2026-09-11 for the GM test (stability_study *_ReMax2_gmFwd): a
finite-difference check of the initial-temperature sensitivity adxx_theta in a
region the adjoints disagree on. The copy goes into its own directory, which
IMPACTS_PICKUP_RUN_DIR then points the adjoint submit script at; the source
pickup is only read.

    python perturb_pickup.py --src <run dir> --iter 3162240 --field Theta \\
        --box k0:k1,j0:j1,i0:i1 --amp 0.1 --grid <dir with hFacC> --out <new dir> \\
        [--adxx gmFwd=<adxx_theta base> --adxx gmOff=<adxx_theta base>]

The box is 0-based and end-exclusive, (k, j, i) as in the MDS arrays; only wet
cells (hFacC > 0) are changed. With --adxx it prints, per adjoint, the first-order
cost change sum(adxx_theta * delta) that the perturbed run is to be compared with.
"""
import argparse
import os
import re

import numpy as np


def read_meta_text(path):
    with open(path) as f:
        return f.read()


def meta_info(txt):
    dims = [int(v) for v in re.search(r'dimList\s*=\s*\[(.*?)\]', txt, re.S).group(1).replace(',', ' ').split()]
    nd = int(re.search(r'nDims\s*=\s*\[\s*(\d+)', txt).group(1))
    prec = re.search(r"dataprec\s*=\s*\[\s*'(\w+)'", txt).group(1)
    nrec = int(re.search(r'nrecords\s*=\s*\[\s*(\d+)', txt).group(1))
    m = re.search(r'fldList\s*=\s*\{(.*?)\}', txt, re.S)
    flds = [s.strip() for s in re.findall(r"'([^']*)'", m.group(1))] if m else []
    return [dims[3 * i] for i in range(nd)][::-1], {'float32': '>f4', 'float64': '>f8'}[prec], nrec, flds


def read_mds(base):
    shape, dtype, nrec, _ = meta_info(read_meta_text(base + '.meta'))
    return np.fromfile(base + '.data', dtype=dtype).reshape(([nrec] if nrec > 1 else []) + shape)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--src', required=True, help='run directory holding the pickup')
    ap.add_argument('--iter', type=int, required=True)
    ap.add_argument('--field', default='Theta')
    ap.add_argument('--box', required=True, help='k0:k1,j0:j1,i0:i1 (0-based, end-exclusive)')
    ap.add_argument('--amp', type=float, required=True, help='added value in the wet cells of the box')
    ap.add_argument('--grid', required=True, help='directory holding hFacC')
    ap.add_argument('--out', required=True, help='new directory for the perturbed pickup')
    ap.add_argument('--nz', type=int, default=36, help='levels of a 3-D pickup field')
    ap.add_argument('--adxx', action='append', default=[], help='label=adxx_theta base path (no .data)')
    args = ap.parse_args()

    base = os.path.join(args.src, 'pickup.%010d' % args.iter)
    txt = read_meta_text(base + '.meta')
    shape2d, dtype, nrec, flds = meta_info(txt)
    two_d = {'EtaN', 'dEtaHdt', 'EtaH'}
    offsets, r = {}, 0
    for f in flds:
        n = 1 if f in two_d else args.nz
        offsets[f] = (r, n)
        r += n
    if r != nrec:
        raise SystemExit('field layout (%d records) does not match nrecords=%d' % (r, nrec))
    r0, n = offsets[args.field]
    if n != args.nz:
        raise SystemExit('%s is not a 3-D field' % args.field)

    data = np.fromfile(base + '.data', dtype=dtype).reshape([nrec] + shape2d)
    (k0, k1), (j0, j1), (i0, i1) = [tuple(int(v) for v in s.split(':')) for s in args.box.split(',')]
    wet = read_mds(os.path.join(args.grid, 'hFacC')) > 0
    delta = np.zeros([args.nz] + shape2d)
    delta[k0:k1, j0:j1, i0:i1] = args.amp
    delta *= wet
    before = data[r0:r0 + n].copy()
    data[r0:r0 + n] = before + delta.astype(data.dtype)

    os.makedirs(args.out, exist_ok=False)
    out = os.path.join(args.out, 'pickup.%010d' % args.iter)
    data.astype(dtype).tofile(out + '.data')
    with open(out + '.meta', 'w') as f:
        f.write(txt)
    with open(os.path.join(args.out, 'README.txt'), 'w') as f:
        f.write('Copy of %s.data with %s += %g in the wet cells of box (k,j,i) %s (%d cells); '
                'every other record byte-identical. Written by '
                'analyses/DINO_1deg/adjoint/gm_in_adjoint/perturb_pickup.py.\n'
                % (base, args.field, args.amp, args.box, int((delta != 0).sum())))

    check = np.fromfile(out + '.data', dtype=dtype).reshape([nrec] + shape2d)
    changed = np.flatnonzero((check != np.fromfile(base + '.data', dtype=dtype).reshape([nrec] + shape2d)).any(axis=(1, 2)))
    print('wrote %s: %d wet cells changed, records changed %s..%s (field %s spans %d..%d)'
          % (out, int((delta != 0).sum()), changed.min() if changed.size else '-',
             changed.max() if changed.size else '-', args.field, r0, r0 + n - 1))
    for spec in args.adxx:
        label, path = spec.split('=', 1)
        a = read_mds(path).astype(np.float64)
        print('  predicted dJ[%s] = sum(adxx_theta * delta) = %.4e' % (label, float((a * delta).sum())))


if __name__ == '__main__':
    main()
