#!/usr/bin/env python3
"""Regenerate DINO's lateral-viscosity binaries from the grid file.

DINO (Kamm et al. 2025, GMD 18, 8091) sets its 1-degree Laplacian viscosity
with NEMO's ``nn_ahm_ijk_t = 20`` law, A_h = U_v * dx / 2, with
``rn_Uv = 0.27`` m/s (the DINO ``EXPREF/namelist_cfg``). ``dino_viscAhD.bin``
is that law on this setup's Mercator grid: dxC from
``input_binaries/tile001.mitgrid``, the same value in every level. The
production ``_2p00`` file is the same field times 2, i.e. U_v = 0.54 m/s;
the other ``_<f>p<ff>`` files are the field times f.ff.

MITgcm has no namelist parameter for a viscosity that is *linear* in the
grid spacing -- ``viscAhGrid`` is quadratic in it (``viscAhGrid*L^2/(4 deltaT)``,
``pkg/mom_common/mom_calc_visc.F``), ``viscAhReMax`` uses the local speed --
so the law stays a ``PARM05`` file, and this script is its recipe.

Bitwise: the original files were built from the model's float32 ``DXC``
output (``writeBinaryPrec=32``) in float32 arithmetic and written as
float64. The same sequence here, starting from the float64 grid file cast to
float32, reproduces ``dino_viscAhD.bin`` and ``dino_viscAhD_2p00.bin`` byte
for byte (checked 2026-09-09; the float64 route differs by up to 1.6e-3
m^2/s, i.e. one float32 ulp). ``--check`` compares against an existing file
instead of writing.

    scripts/gen_viscAhD.py --factor 1 --check          # dino_viscAhD.bin
    scripts/gen_viscAhD.py --factor 2 --check          # dino_viscAhD_2p00.bin
    scripts/gen_viscAhD.py --factor 3 --out input_binaries/dino_viscAhD_3p00.bin

The file names follow ``analyses/README.md``: ``<f>p<ff>`` reads ``f.ff``.
"""
import argparse
import os
import sys

import numpy as np

SETUP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NX, NY, NR = 51, 198, 36            # code/SIZE.h: sNx*nPx, sNy*nPy, Nr
MITGRID_FIELDS = ['XC', 'YC', 'DXF', 'DYF', 'RAC', 'XG', 'YG', 'DXV', 'DYU',
                  'RAZ', 'DXC', 'DYC', 'RAW', 'RAS', 'DXG', 'DYG']


def default_name(factor):
    if factor == 1:
        return 'dino_viscAhD.bin'
    return 'dino_viscAhD_%dp%02d.bin' % (int(factor), round((factor - int(factor)) * 100))


def build(mitgrid, uv, factor):
    g = np.fromfile(mitgrid, dtype='>f8')
    n = (NX + 1) * (NY + 1)
    if g.size != len(MITGRID_FIELDS) * n:
        sys.exit('%s: %d values, expected %d' % (mitgrid, g.size, len(MITGRID_FIELDS) * n))
    dxc = g.reshape((len(MITGRID_FIELDS), NY + 1, NX + 1))[MITGRID_FIELDS.index('DXC')][:NY, :NX]
    # the original recipe: float32 dxC, float32 arithmetic (numpy keeps the
    # array's float32 for a Python scalar), then float64 for the file
    visc32 = dxc.astype('f4') * uv / 2.0
    field = visc32.astype('f8') * float(factor)          # (NY, NX)
    return np.ascontiguousarray(np.broadcast_to(field[None, :, :], (NR, NY, NX)))


def main():
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    p.add_argument('--mitgrid', default=os.path.join(SETUP, 'input_binaries', 'tile001.mitgrid'))
    p.add_argument('--uv', type=float, default=0.27, help='velocity scale U_v [m/s] (DINO rn_Uv)')
    p.add_argument('--factor', type=float, default=1.0, help='multiply the reference field by this')
    p.add_argument('--out', help='output file (default input_binaries/<name for --factor>)')
    p.add_argument('--check', action='store_true', help='compare with --out instead of writing')
    p.add_argument('--force', action='store_true', help='overwrite an existing --out')
    a = p.parse_args()
    out = a.out or os.path.join(SETUP, 'input_binaries', default_name(a.factor))
    field = build(a.mitgrid, a.uv, a.factor)
    print('A_h = %g * dxC * %g / 2: min %.6f max %.6f m^2/s, %d values'
          % (a.factor, a.uv, field.min(), field.max(), field.size))
    if a.check:
        if not os.path.exists(out):
            sys.exit('--check: %s does not exist' % out)
        have = np.fromfile(out, dtype='>f8')
        if have.size != field.size:
            sys.exit('%s: %d values, expected %d' % (out, have.size, field.size))
        same = np.array_equal(have, field.ravel())
        print('%s: %s' % (out, 'IDENTICAL' if same else 'DIFFERS, max|diff| = %.3e'
                          % np.abs(have - field.ravel()).max()))
        sys.exit(0 if same else 1)
    if os.path.exists(out) and not a.force:
        sys.exit('%s exists; use --check to compare or --force to overwrite' % out)
    field.astype('>f8').tofile(out)
    print('wrote %s (%d bytes)' % (out, os.path.getsize(out)))


if __name__ == '__main__':
    main()
