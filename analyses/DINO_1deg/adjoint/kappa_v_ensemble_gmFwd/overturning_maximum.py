#!/usr/bin/env python3
"""Where the overturning cell peaks, and so where the cost section belongs (2026-10-13).

    python overturning_maximum.py            # -> stats/overturning_maximum.json (of the current campaign), and a table

The cost J (code_tap/cost_atlantic_heat.F) is the northward transport across one grid row, integrated from the
surface to one interface, averaged over the last 30 days of the window. Until 2026-10-13 that row was jsec = 127
(row centre 26.05 N) and the interface 982 m (kmaxdepth = 25) -- "the transport at 26 N" -- but the deck's own
depth-space overturning (slide 6 of references/dino_sensitivity_vs_mixing/slides) shows the cell cored well north
of that, which the advisor pointed out. This script locates the maximum of the depth-space streamfunction psi(y, z)
from the monthly dynDiag VVEL of the production spin-up 31203, the way the deck's figure is drawn (make_slide_figures.py
compute: cumulative transport from the surface, on the cell interfaces), restricted to the basin north of 20 N and
below 300 m so that the shallow wind-driven cells of the tropics do not count, and reports the row, the latitude of
the row's centre and of its southern face (the face the cost integrates across), the interface, and the value.

The answer, from the last decade of 31203 (years 190-200): row j = 147 (0-based; Fortran jsec = 148), centre 43.21 N,
southern face 42.84 N, interface 848.4 m (kmaxdepth = 24), psi = 7.37 Sv. The same row and interface hold in every
decade of the spin-up tested (100-110, 170-180, 180-190), in the reference leg 31366 (years 170-180 and its last
year) and in the reference adjoint's own window (31374, years 180-185): the maximum is a fixed feature of this
state. At 982 m the same row carries 7.11 Sv, 3.5 % less, so kmaxdepth moved with jsec. The members' maxima sit
elsewhere (M4-M6 in the far north, M7 at 35 N): the cost section is the reference state's, fixed for the ensemble.

The row convention: psi[j] here and vVel(i, jsec) in the Fortran are both the transport across the SOUTHERN face of
row j (0-based) = jsec - 1, so "the section at 43 N" names the row centre YC[147] = 43.21 N, as "26 N" named
YC[126] = 26.05 N, while the face itself is half a cell south.
"""
from __future__ import annotations

import glob
import json
import sys

import numpy as np

import campaign as c

LAT_MIN, DEPTH_MIN = 20.0, 300.0      # exclude the tropical cells: basin north of 20 N, below 300 m


def psi_mean(files):
    g = c.grid()
    v = np.mean([c.read_record(p[:-5], 'VVEL') for p in files], axis=0)
    return c.overturning(v, g).T                     # (j, k): transport above interface k+1 across the S face of row j


def locate(P):
    g = c.grid()
    lat, rf = g['lat'], g['RF']
    sel = (lat > LAT_MIN)[:, None] & (-rf[1:] > DEPTH_MIN)[None, :]
    M = np.where(sel, P, np.nan)
    j, k = np.unravel_index(int(np.nanargmax(M)), M.shape)
    return dict(j0=int(j), jsec_fortran=int(j) + 1, lat_centre=round(float(lat[j]), 3),
                lat_south_face=round(float(0.5 * (lat[j - 1] + lat[j])), 3),
                k0=int(k), kmaxdepth_fortran=int(k) + 1, interface_m=round(float(-rf[k + 1]), 1),
                psi_sv=round(float(M[j, k]), 4),
                psi_at_982m_sv=round(float(P[j, 24]), 4), psi_at_848m_sv=round(float(P[j, 23]), 4))


def main():
    c.ensure_dirs()
    g = c.grid()
    spin = sorted(glob.glob(str(c.run_dir(c.SPINUP_JOB) / 'dynDiag.*.data')))
    out = {'definition': 'maximum of the depth-space overturning streamfunction (cumulative northward transport '
                         'from the surface, on the cell interfaces) over rows north of %g N and interfaces below %g m, '
                         'from monthly dynDiag VVEL' % (LAT_MIN, DEPTH_MIN),
           'spinup_job': c.SPINUP_JOB, 'periods': {}}
    periods = {'31203 years 190-200 (the deck, slide 6)': spin[-120:],
               '31203 years 180-190': spin[-240:-120], '31203 years 170-180': spin[-360:-240],
               '31203 years 100-110': spin[1200:1320]}
    ref = sorted(glob.glob(str(c.run_dir(c.LEG_JOB['REF']) / 'dynDiag.*.data')))
    periods['REF leg %d years 170-180' % c.LEG_JOB['REF']] = ref
    periods['REF leg %d year 179-180' % c.LEG_JOB['REF']] = ref[-12:]
    adj = sorted(glob.glob(str(c.run_dir(c.ADJ_JOB['REF']) / 'dynDiag.*.data'))) if c.ADJ_JOB.get('REF') and c.run_dir(c.ADJ_JOB['REF']) else []
    if adj:
        periods['reference adjoint %d window, years 180-185' % c.ADJ_JOB['REF']] = adj
    for r in c.MEMBERS:
        f = sorted(glob.glob(str(c.run_dir(c.LEG_JOB[r]) / 'dynDiag.*.data')))
        periods['%s leg %d year 179-180 (%gx)' % (r, c.LEG_JOB[r], c.FACTOR[r])] = f[-12:]
    for name, files in periods.items():
        if not files:
            continue
        P = psi_mean(files)
        loc = locate(P)
        loc['n_months'] = len(files)
        loc['psi_row147_max_sv'] = round(float(np.nanmax(P[147])), 4)
        out['periods'][name] = loc
        print('%-52s n=%3d  j=%d (jsec %d) centre %6.2f N face %6.2f N  k=%d (%s m, kmaxdepth %d)  psi %.3f Sv  [row 147: %.3f]'
              % (name, len(files), loc['j0'], loc['jsec_fortran'], loc['lat_centre'], loc['lat_south_face'], loc['k0'],
                 loc['interface_m'], loc['kmaxdepth_fortran'], loc['psi_sv'], loc['psi_row147_max_sv']), flush=True)
    # the profile of the cell along its row and across latitude, for the record
    P = psi_mean(spin[-120:])
    j = out['periods']['31203 years 190-200 (the deck, slide 6)']['j0']
    out['chosen'] = dict(out['periods']['31203 years 190-200 (the deck, slide 6)'])
    out['row_profile_years_190_200'] = {'interface_m': [round(float(-v), 1) for v in g['RF'][1:]],
                                        'psi_sv': [round(float(v), 4) for v in P[j]]}
    out['latitude_profile_years_190_200'] = {'lat_centre': [round(float(v), 3) for v in g['lat'][120:198]],
                                             'psi_max_below_300m_sv': [round(float(np.nanmax(np.where(-g['RF'][1:] > DEPTH_MIN, P[jj], np.nan))), 4)
                                                                       for jj in range(120, 198)]}
    p = c.STATS / 'overturning_maximum.json'
    p.write_text(json.dumps(out, indent=1))
    print('wrote', p)


if __name__ == '__main__':
    main()
