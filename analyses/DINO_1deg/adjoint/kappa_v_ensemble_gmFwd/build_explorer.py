#!/usr/bin/env python3
"""The interactive depth-level explorer for the campaign's adjoint sensitivities.

    python build_explorer.py                      # -> analysis/<campaign>/explorer/
    python build_explorer.py --stride 12 --member-stride 24
    python build_explorer.py --out /some/where

WHY THIS EXISTS. A film has to choose a depth level, and the deck's films choose two (make_films.py
says which and why). Every other level of every three-dimensional dump is here: one page with a
variable selector, a depth slider over all 36 levels plus the column sum, a time slider that plays,
and a choice of colour scaling. Two datasets share the controls -- the reference adjoint's twelve
ADJ* dumps, and ADJtheta and ADJdiffkr for all eight kappa_v members side by side.

HOW THE DATA GETS INTO A WEB PAGE. Not as pre-rendered images: 12 variables x 37 levels x 31 frames
would be 13 000 PNGs. Each (dataset, variable) is instead ONE PNG used as a container -- a greyscale
image tiled (time down, level across), one pixel per grid cell, the field quantised to 0..254 about
127 with 255 reserved for land. The page decodes it once, and colours a 51x198 tile on a canvas
whenever the viewer moves a slider, so changing depth or time costs nothing. The physical value of a
pixel is (q - 127)/127 * scale, and the scales -- one per (frame, level), the 99.8th percentile of
|field| over the wet cells of that slice -- are in manifest.json, so the page can label a colourbar
in the dump's own units and can switch between per-slice scaling (the pattern at a level where the
amplitude is small) and one scale for the whole variable (amplitudes comparable across depth).

The tiled layout matters: the obvious `(nt*nz*ny, nx)` image is 220 968 pixels tall and browsers
refuse anything over 32 767 in a dimension, so the levels go across instead -- 1836 x 6138 for a
31-frame, 37-level variable, 2.4 MB of PNG.

SERVING IT. Published as a claude.ai artifact the page just works. From a local copy it needs a
server, because a browser taints a canvas drawn from a `file://` image and then refuses to read the
pixels back; `explorer/serve.sh` starts one on port 8765.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

import campaign as c
import make_films as f

LAND = 255          # the quantised value reserved for a dry cell
ZERO = 127          # the quantised value of zero
TEMPLATE = Path(__file__).resolve().parent / 'explorer_template.html'
EXPLORER_VARS_MEMBER = f.MEMBER_VARS      # ADJtheta, ADJdiffkr

# make_films.py's units are LaTeX, for the film captions; a web page wants its own.
UNITS_HTML = {
    'ADJtheta': 'dJ / K', 'ADJsalt': 'dJ / (g kg\u207b\u00b9)',
    'ADJdiffkr': 'dJ / (m\u00b2 s\u207b\u00b9)',
    'ADJuvel': 'dJ / (m s\u207b\u00b9)', 'ADJvvel': 'dJ / (m s\u207b\u00b9)',
    'ADJwvel': 'dJ / (m s\u207b\u00b9)', 'ADJetan': 'dJ / m',
    'ADJqnet': 'dJ / (W m\u207b\u00b2)', 'ADJqsw': 'dJ / (W m\u207b\u00b2)',
    'ADJempmr': 'dJ / (kg m\u207b\u00b2 s\u207b\u00b9)',
    'ADJtaux': 'dJ / (N m\u207b\u00b2)', 'ADJtauy': 'dJ / (N m\u207b\u00b2)',
}


def _cmap_table():
    """256 RGB triples of the same diverging map the figures use, for the page's canvas."""
    cm = c.diverging_cmap()
    return [[int(round(255 * v)) for v in cm(i / 255.0)[:3]] for i in range(256)]


def _tiles(run_dir, var, its, three):
    """(payload (nt*ny, nlev*nx) uint8, scale (nt, nlev) float32, level labels).

    Level `nz` of a three-dimensional variable is the mass-weighted column sum, the quantity the
    still maps and the ensemble panel films show; it is carried as one more tile so the slider can
    reach it without the page having to add 36 numbers itself.
    """
    g = c.grid()
    m = c.mask(var)
    nz = g['RC'].size if three else 1
    nlev = nz + 1 if three else 1
    ny, nx = g['YC'].shape
    wcol = m.any(axis=0) if three else m
    q = np.full((len(its) * ny, nlev * nx), LAND, np.uint8)
    sc = np.zeros((len(its), nlev), np.float32)
    for n, it in enumerate(its):
        a = c.read_mds(c.dump_base(run_dir, var, it), np.float32).astype(np.float64)
        slices = ([(k, a[k], m[k]) for k in range(nz)] +
                  [(nz, np.where(m, a, 0.0).sum(axis=0), wcol)]) if three else [(0, a, m)]
        for k, fld, w in slices:
            if not w.any():
                continue
            v = np.abs(fld[w])
            s = float(np.percentile(v, 99.8)) or float(v.max())
            sc[n, k] = s
            tile = np.full((ny, nx), LAND, np.uint8)
            tile[w] = (np.clip(np.round(fld[w] / s * 127.0) + ZERO, 0, 254).astype(np.uint8)
                       if s > 0 else ZERO)
            q[n * ny:(n + 1) * ny, k * nx:(k + 1) * nx] = tile
    labels = ([('%d m' % round(-g['RC'][k])) for k in range(nz)] + ['column sum']) if three \
        else ['surface']
    return q, sc, labels


def build(out=None, stride=12, member_stride=24):
    g = c.grid()
    out = Path(out or (c.ANALYSIS / 'explorer'))
    (out / 'data').mkdir(parents=True, exist_ok=True)
    its = c.ITERS[::stride]
    mits = c.ITERS[::member_stride]
    man = {
        'built': __import__('datetime').date.today().isoformat(),
        'campaign': c.CAMPAIGN,
        'grid': {'nx': int(g['XC'].shape[1]), 'ny': int(g['YC'].shape[0]),
                 'lon': [round(float(v), 3) for v in g['XC'][0, :]],
                 'lat': [round(float(v), 3) for v in g['YC'][:, 0]],
                 'depth': [round(float(-v), 1) for v in g['RC']],
                 'jsec': int(c.JSEC), 'kcost': int(c.KMAX),
                 'lat_sec': round(float(g['YC'][c.JSEC, 0]), 2)},
        'cmap': _cmap_table(),
        'datasets': {},
    }
    total = 0

    # ---- the reference adjoint: every ADJ* dump ------------------------------------------------
    d = c.run_dir(c.ADJ_JOB['REF'])
    ref = {'label': 'reference adjoint, run %d' % c.ADJ_JOB['REF'],
           'note': 'the live input_tap/data adjoint, 5 years from the year-180 state of the '
                   'reference leg; %d frames %d days apart' % (len(its), 5 * stride),
           'leads': [round(float(v), 3) for v in c.lead_years(its)],
           'panels': 'single', 'vars': {}}
    for var in f.INFO:
        three = var in c.ADJ_3D
        what, _latex_units = f.INFO[var]
        kind, peak, ratio = f.kind_of(var)
        q, sc, labels = _tiles(d, var, its, three)
        name = 'data/reference_%s.png' % var
        Image.fromarray(q, 'L').save(out / name, format='PNG', optimize=True)
        total += (out / name).stat().st_size
        ref['vars'][var] = {
            'label': what, 'units': UNITS_HTML[var],
            'file': name, 'nlev': len(labels), 'levels': labels,
            'scale': [[float('%.4g' % v) for v in row] for row in sc],
            'kind': kind, 'film_levels': [int(k) for k in f.levels_of(var)] if three else [],
            'three': bool(three),
        }
        print('  reference %-10s %s  %.2f MB' % (var, str(q.shape), (out / name).stat().st_size / 1e6), flush=True)
    man['datasets']['reference'] = ref

    # ---- the ensemble: two variables, all eight members ----------------------------------------
    ens = {'label': 'the \u03ba\u1d65 ensemble, runs %d\u2013%d' % (c.ADJ_JOB['M1'], c.ADJ_JOB['M7']),
           'note': 'all eight members at once, each its own 5-year adjoint from its own 10-year '
                   'leg; %d frames %d days apart' % (len(mits), 5 * member_stride),
           'leads': [round(float(v), 3) for v in c.lead_years(mits)],
           'panels': 'members',
           'members': [{'run': r, 'factor': c.FACTOR[r], 'job': c.ADJ_JOB[r], 'label': c.LABEL[r]}
                       for r in c.RUN_ORDER],
           'vars': {}}
    for var in EXPLORER_VARS_MEMBER:
        what, _latex_units = f.INFO[var]
        kind, _p, _r = f.kind_of(var)
        entry = {'label': what, 'units': UNITS_HTML[var], 'files': {}, 'scale': {},
                 'kind': kind, 'three': True,
                 'film_levels': [int(k) for k in f.levels_of(var)]}
        for r in c.RUN_ORDER:
            q, sc, labels = _tiles(c.run_dir(c.ADJ_JOB[r]), var, mits, True)
            name = 'data/%s_%s.png' % (r, var)
            Image.fromarray(q, 'L').save(out / name, format='PNG', optimize=True)
            total += (out / name).stat().st_size
            entry['files'][r] = name
            entry['scale'][r] = [[float('%.4g' % v) for v in row] for row in sc]
            entry['nlev'], entry['levels'] = len(labels), labels
            print('  member %-4s %-10s %.2f MB' % (r, var, (out / name).stat().st_size / 1e6), flush=True)
        ens['vars'][var] = entry
    man['datasets']['ensemble'] = ens

    (out / 'manifest.json').write_text(json.dumps(man, separators=(',', ':')))
    html = TEMPLATE.read_text().replace('/*MANIFEST*/null', json.dumps(man, separators=(',', ':')))
    (out / 'index.html').write_text(html)
    (out / 'serve.sh').write_text(
        '#!/usr/bin/env bash\n'
        '# A browser refuses to read the pixels back out of a canvas drawn from a file:// image, so\n'
        '# this page needs a server even locally. Then open http://localhost:8765/\n'
        'cd "$(dirname "${BASH_SOURCE[0]}")" && exec python3 -m http.server 8765\n')
    (out / 'serve.sh').chmod(0o750)
    print('\nwrote %s  (%d payloads, %.1f MB of data, index.html %.2f MB)'
          % (out, len(list((out / "data").glob("*.png"))), total / 1e6,
             (out / 'index.html').stat().st_size / 1e6))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=None)
    ap.add_argument('--stride', type=int, default=12, help='dumps between frames, reference (5 d each)')
    ap.add_argument('--member-stride', type=int, default=24, help='dumps between frames, members')
    a = ap.parse_args()
    c.setup_style()
    c.ensure_dirs()
    build(a.out, a.stride, a.member_stride)
