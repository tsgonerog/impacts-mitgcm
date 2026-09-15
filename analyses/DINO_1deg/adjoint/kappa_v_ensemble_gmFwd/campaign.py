"""Shared definitions for the κ_v ensemble under the current DINO configuration (2026-09-13).

Campaign `kappa_v_ensemble_gmFwd` (runs/{forward,adjoint}/kappa_v_ensemble_gmFwd/ and
analysis/kappa_v_ensemble_gmFwd/ under OUTPUTS), submitted by submit_campaign.sh as one dependency chain:

* a 170-yr spin-up from rest of the live input/data (reference viscosity files, viscAhReMax=2., scheme 33
  with explicit vertical advection, GM/Redi on); it replaces the production spin-up 31203, unreadable since
  /scratch2 failed on 2026-09-12;
* forward legs, 10 yr from the spin-up's year 170, one per κ_v (input/variants/kappa_v_ensemble/
  data_<m>_ReMax2); the REF leg is the spin-up's own continuation to year 180;
* 5-yr adjoints (the approximate adjoint: GM/Redi in the forward sweep only, scheme 30 in the adjoint
  sweep) from year 180: the reference is the live input_tap/data from the REF leg, each member its own
  leg (input_tap/variants/kappa_v_ensemble/data_M<k>_ReMax2_gmFwd_approxAdv);
* finite-difference forward sweeps from the REF leg's year 180 (input_tap/variants/fd_checks/): κ_v ±10 %,
  Theta ±δ in three boxes of the pickup, and uniform perturbations of fu, fv, Qnet and E−P−R.

Job IDs come from job_map.tsv. The cost J (code_tap/cost_atlantic_heat.F) is the section transport index
at 26 N over the upper 25 levels, averaged over the final 30 d of the window and normalised per MPI tile.
"""
from __future__ import annotations

import glob
import os
import re
from pathlib import Path

import numpy as np

OUTPUTS = Path(os.environ.get('CAMPAIGN_OUTPUTS', '/scratch/tshahriar/DINO_1deg_outputs'))   # /scratch2 was down from 2026-09-12 18:45
EARLIER_OUTPUTS = Path('/scratch2/tshahriar/DINO_1deg_outputs')                              # where the earlier campaigns' runs are
CAMPAIGN = 'kappa_v_ensemble_gmFwd'
ANALYSIS = OUTPUTS / 'analysis' / CAMPAIGN
CACHE = ANALYSIS / 'cache'
STATS = ANALYSIS / 'stats'
FIGS = ANALYSIS / 'figures'
ANIMS = ANALYSIS / 'animations'
PICKUPS = ANALYSIS / 'perturbed_pickups'
PREVIOUS = Path(__file__).resolve().parent / 'previous_campaigns_reference.json'   # numbers of the earlier campaigns

# ---------------------------------------------------------------- runs
KAPPA0 = 1.2e-5
FACTOR = dict(M1=0.25, M2=0.5, REF=1.0, M3=2.0, M4=4.0, M5=8.0, M6=16.0, M7=32.0)
RUN_ORDER = ['M1', 'M2', 'REF', 'M3', 'M4', 'M5', 'M6', 'M7']
MEMBERS = [r for r in RUN_ORDER if r != 'REF']
PREV_GMFWD_5YR_JOB = 31237  # 2026-09-11: the same adjoint from the deleted REF_ReMax2 leg 31205's year 180 (on /scratch2)
THETA_BOXES = {   # (k0, k1, j0, j1, i0, i1), 0-based end-exclusive, as in perturb_pickup.py
    'deepN': dict(box=(28, 36, 143, 157, 0, 51), amp=0.016, what='40-50 N, below 1500 m'),
    'midTrop': dict(box=(20, 28, 99, 110, 0, 51), amp=0.035, what='0-10 N, 500-1500 m'),
    'soUpper': dict(box=(0, 20, 24, 56, 0, 51), amp=0.5, what='40-60 S, 0-500 m'),
}
FORCING_TESTS = {   # control: (adxx file, amplitude, unit, what) -- files in analysis/<campaign>/perturbed_forcing/
    'fu': ('adxx_fu', 0.005, 'N/m2', 'zonal surface stress'),
    'fv': ('adxx_fv', 2e-8, 'N/m2', 'meridional surface stress'),
    'qnet': ('adxx_qnet', 0.003, 'W/m2', 'net surface heat flux'),
    'empmr': ('adxx_empmr', 3e-9, 'kg/m2/s', 'freshwater flux E-P-R'),
}


def _job_map():
    """Rows of analysis/<campaign>/job_map.tsv written by submit_campaign.sh: (job, role, tag)."""
    p = OUTPUTS / 'analysis' / CAMPAIGN / 'job_map.tsv'
    rows = []
    if p.exists():
        for line in p.read_text().splitlines()[1:]:
            f = line.split('\t')
            if len(f) >= 3 and 'cancelled' not in f[1]:
                rows.append((int(f[0]), f[1], f[2]))
    return rows


_MAP = _job_map()
SPINUP_JOB = next((j for j, role, _ in _MAP if role.startswith('spin-up 170')), None)
SPINUP_END_JOB = next((j for j, role, _ in _MAP if role.startswith('spin-up end')), None)   # the rerun last 61 days, if any
LEG_JOB = {tag.split('/')[-1].replace('_ReMax2', ''): j for j, role, tag in _MAP if role == 'forward leg'}
ADJ_JOB = {('REF' if role.startswith('reference') else tag.split('/')[-1].split('_')[0]): j
           for j, role, tag in _MAP if role.startswith(('reference adjoint', 'member adjoint'))}
FD_JOB = {(role.split()[-1] if role.split()[-1] != 'sweep' else tag.split('/')[-1].split('_')[0]): j
          for j, role, tag in _MAP if role.startswith('FD')}
LABEL = {r: ('reference (1x)' if r == 'REF' else '%s (%gx)' % (r, FACTOR[r])) for r in RUN_ORDER}


def run_dir(job):
    """The run directory of a job, wherever it is filed under runs/ (this campaign's tree first)."""
    if job is None:
        return None
    for root in (OUTPUTS, EARLIER_OUTPUTS):
        for pat in ('runs/*/*_run%d', 'runs/*/*/*_run%d'):
            try:
                hits = glob.glob(str(root / (pat % job)))
            except OSError:
                hits = []
            if hits:
                return Path(hits[0])
    return None


# ---------------------------------------------------------------- time axis of the adjoint window
DT = 1800.0
STEPS_PER_YEAR = 48 * 366
NITER0 = 3162240                 # year 180
NSTEPS = 87840                   # 5 yr
NITER_END = NITER0 + NSTEPS      # year 185
DUMP_STRIDE = 240                # adjDumpFreq = 5 d
ITERS = np.arange(NITER0, NITER_END, DUMP_STRIDE)   # 366 ADJ* dumps (ADJetan also at NITER_END)
LEG_NITER0 = 2986560             # year 170


def lead_years(it):
    """Years before the end of the cost window: 5 at the window start, the full accumulation."""
    return (NITER_END - np.asarray(it)) / STEPS_PER_YEAR


def nearest_iter(lead_yr):
    return int(ITERS[np.abs(lead_years(ITERS) - lead_yr).argmin()])


# ---------------------------------------------------------------- MDS I/O
def read_meta(path):
    txt = Path(path).read_text()
    nd = int(re.search(r'nDims\s*=\s*\[\s*(\d+)', txt).group(1))
    dims = [int(v) for v in re.search(r'dimList\s*=\s*\[(.*?)\]', txt, re.S).group(1).replace(',', ' ').split()]
    prec = re.search(r"dataprec\s*=\s*\[\s*'(\w+)'", txt).group(1)
    nrec = int(re.search(r'nrecords\s*=\s*\[\s*(\d+)', txt).group(1))
    m = re.search(r'fldList\s*=\s*\{(.*?)\}', txt, re.S)
    flds = [s.strip() for s in re.findall(r"'([^']*)'", m.group(1))] if m else []
    shape = [dims[3 * i] for i in range(nd)][::-1]
    return shape, {'float32': '>f4', 'float64': '>f8'}[prec], nrec, flds


def read_mds(base, dtype=np.float64):
    """<base>.data as (k, j, i) or (j, i), or (nrec, ...) when nrec > 1."""
    shape, fdt, nrec, _ = read_meta(str(base) + '.meta')
    a = np.fromfile(str(base) + '.data', dtype=fdt)
    return a.reshape(([nrec] if nrec > 1 else []) + shape).astype(dtype)


def read_record(base, field, nz=36):
    """One field of a multi-record diagnostics file, by name, via a memory map."""
    shape, fdt, nrec, flds = read_meta(str(base) + '.meta')
    names = [f.strip() for f in flds]
    k = names.index(field)
    mm = np.memmap(str(base) + '.data', dtype=fdt, mode='r', shape=tuple([nrec] + shape))
    out = np.asarray(mm[k], np.float64)
    del mm
    return out


FC_RE = re.compile(r'^\(PID\.TID [0-9]{4}\.[0-9]{4}\) +global fc = +(-?[0-9]\.[0-9]+E[-+][0-9]+)')


def first_fc(d):
    """The cost printed at the end of the forward sweep (None if not yet printed)."""
    p = Path(d) / 'STDOUT.0000'
    if not p.exists():
        return None
    with open(p, errors='replace') as f:
        for line in f:
            m = FC_RE.match(line)
            if m:
                return float(m.group(1))
    return None


# ---------------------------------------------------------------- grid
_GRID = {}


def grid(d=None):
    if _GRID:
        return _GRID
    d = Path(d or run_dir(SPINUP_JOB))
    g = {n: np.squeeze(read_mds(d / n)) for n in
         ('XC', 'YC', 'XG', 'YG', 'RAC', 'RAW', 'RAS', 'DXG', 'DYG', 'Depth',
          'hFacC', 'hFacW', 'hFacS', 'DRF', 'RC', 'RF')}
    g['DRF'] = np.atleast_1d(g['DRF'])
    g['RC'] = np.atleast_1d(g['RC'])
    for p in 'CWS':
        g['wet' + p] = g['hFac' + p] > 0
    g['vol'] = g['RAC'][None] * g['hFacC'] * g['DRF'][:, None, None]
    g['lat'] = g['YC'][:, 0]
    _GRID.update(g)
    return g


# ---------------------------------------------------------------- variables
ADJ_3D = {'ADJtheta': 'C', 'ADJsalt': 'C', 'ADJdiffkr': 'C', 'ADJuvel': 'W', 'ADJvvel': 'S', 'ADJwvel': 'C'}
ADJ_2D = {'ADJqnet': 'C', 'ADJqsw': 'C', 'ADJempmr': 'C', 'ADJtaux': 'W', 'ADJtauy': 'S', 'ADJetan': 'C'}
ADJ_VARS = {**ADJ_3D, **ADJ_2D}
ADXX_3D = {'adxx_theta': 'C', 'adxx_salt': 'C', 'adxx_diffkr': 'C'}
ADXX_2D = {'adxx_qnet': 'C', 'adxx_empmr': 'C', 'adxx_qsw': 'C', 'adxx_fu': 'W', 'adxx_fv': 'S'}
ADXX_VARS = {**ADXX_3D, **ADXX_2D}
CONTROL_INFO = {   # unit of the control, a plausible perturbation scale for the ranking, its label
    'adxx_theta': ('K', 0.1, 'initial temperature'),
    'adxx_salt': ('g/kg', 0.01, 'initial salinity'),
    'adxx_diffkr': ('m2/s', 1.2e-6, 'vertical diffusivity (10 % of 1.2e-5)'),
    'adxx_qnet': ('W/m2', 1.0, 'net surface heat flux'),
    'adxx_qsw': ('W/m2', 1.0, 'shortwave heat flux'),
    'adxx_empmr': ('kg/m2/s', 3.2e-6, 'freshwater flux E-P-R (0.1 m/yr)'),
    'adxx_fu': ('N/m2', 0.01, 'zonal surface stress'),
    'adxx_fv': ('N/m2', 0.01, 'meridional surface stress'),
}


def mask(var):
    g = grid()
    pt = {**ADJ_VARS, **ADXX_VARS}[var]
    w = g['wet' + pt]
    return w if var in ADJ_3D or var in ADXX_3D else w[0]


def weights(var):
    g = grid()
    pt = {**ADJ_VARS, **ADXX_VARS}[var]
    ra = g[{'C': 'RAC', 'W': 'RAW', 'S': 'RAS'}[pt]]
    if var in ADJ_3D or var in ADXX_3D:
        return ra[None] * g['hFac' + pt] * g['DRF'][:, None, None]
    return ra * g['wet' + pt][0]


# The freshwater-flux dump was written as ADJempmr.* until 2026-09-14 and as
# ADJempr.* (the TAF spelling, taken over when mods_tapenade_hooks was
# re-synced from the upstream branch) from then on; runs of either vintage are
# read through dump_base, which keeps 'ADJempmr' as the field's name.
DUMP_FILE_ALIASES = {'ADJempmr': ('ADJempmr', 'ADJempr')}


def dump_base(d, var, it):
    """path stem <run dir>/<prefix>.<it> of a dump, whichever prefix the run wrote"""
    for prefix in DUMP_FILE_ALIASES.get(var, (var,)):
        base = Path(d) / ('%s.%010d' % (prefix, it))
        if base.with_suffix('.data').exists():
            return base
    return Path(d) / ('%s.%010d' % (var, it))


def adj(job, var, it):
    return read_mds(dump_base(run_dir(job), var, it))


def adxx(job, var):
    return read_mds(run_dir(job) / ('%s.0000000000' % var))


# ---------------------------------------------------------------- metrics
def rms(a, w=None):
    a = np.asarray(a, np.float64)
    fin = np.isfinite(a)
    if w is None:
        return float(np.sqrt(np.mean(a[fin] ** 2))) if fin.any() else np.nan
    w = np.asarray(w, np.float64)
    return float(np.sqrt((w[fin] * a[fin] ** 2).sum() / w[fin].sum())) if fin.any() else np.nan


def pattern_corr(a, r, w=None):
    a, r = np.asarray(a, np.float64), np.asarray(r, np.float64)
    ok = np.isfinite(a) & np.isfinite(r)
    a, r = a[ok], r[ok]
    w = np.ones_like(a) if w is None else np.asarray(w, np.float64)[ok]
    sw = w.sum()
    a = a - (w * a).sum() / sw
    r = r - (w * r).sum() / sw
    den = np.sqrt((w * a * a).sum() * (w * r * r).sum())
    return float((w * a * r).sum() / den) if den > 0 else np.nan


# ---------------------------------------------------------------- cost proxy at the section
JSEC, KMAX, SNX, NTILE = 126, 25, 17, 3


def jproxy(v, g=None):
    """The compiled cost formula applied to a meridional-velocity field v (k, j, i): per-tile
    wet-face normalisation, upper KMAX levels, row JSEC. With a 30.5-d mean v it is a proxy of
    fc, which averages the final 30 d."""
    g = g or grid()
    msk = g['hFacS'][:, JSEC, :] > 0
    dxg = g['DXG'][JSEC, :]
    vs = v[:, JSEC, :]
    tot = 0.0
    for t in range(NTILE):
        sl = slice(SNX * t, SNX * (t + 1))
        m = msk[:KMAX, sl]
        cnt = m.sum(axis=1).astype(np.float64)
        tr = (vs[:KMAX, sl] * dxg[None, sl] * m).sum(axis=1)
        ok = cnt > 0
        tot += (tr[ok] * g['DRF'][:KMAX][ok] / cnt[ok]).sum()
    return 1e-6 * tot


def overturning(v, g=None):
    """Depth-space overturning streamfunction psi(k, j) in Sv, integrated from the surface."""
    g = g or grid()
    tr = (v * g['DXG'][None] * g['DRF'][:, None, None] * g['hFacS']).sum(axis=2) / 1e6
    return np.cumsum(tr, axis=0)


def amoc_index(v, lat0=26.0, g=None):
    g = g or grid()
    psi = overturning(v, g)
    j = int(np.abs(g['lat'] - lat0).argmin())
    up = g['RC'] >= -1000
    return float(np.nanmax(psi[up, j]))


# ---------------------------------------------------------------- figure style (dataviz tokens)
INK, INK2, MUTED, GRID_C, AXIS_C, SURFACE = '#0b0b0b', '#52514e', '#898781', '#e1e0d9', '#c3c2b7', '#fcfcfb'
SERIES = ['#2a78d6', '#eb6834', '#1baf7a']     # categorical slots 1-3 (validated all-pairs, light)
BLUE_RAMP = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
LAND = '#d9d8d2'


def setup_style():
    import matplotlib as mpl
    mpl.rcParams.update({
        'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
        'figure.dpi': 110, 'savefig.dpi': 170, 'savefig.bbox': 'tight',
        'font.family': 'DejaVu Sans', 'font.size': 9.5, 'axes.titlesize': 10.5, 'axes.labelsize': 9.5,
        'text.color': INK, 'axes.labelcolor': INK2, 'xtick.color': MUTED, 'ytick.color': MUTED,
        'xtick.labelcolor': INK2, 'ytick.labelcolor': INK2,
        'axes.edgecolor': AXIS_C, 'axes.linewidth': 0.8, 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': True, 'grid.color': GRID_C, 'grid.linewidth': 0.6, 'grid.linestyle': '-',
        'axes.axisbelow': True, 'lines.linewidth': 1.6, 'lines.solid_capstyle': 'round',
        'legend.frameon': False, 'legend.fontsize': 8.5, 'image.interpolation': 'nearest',
    })


def diverging_cmap():
    import cmocean
    cm = cmocean.cm.balance.copy()
    cm.set_bad(LAND)
    return cm


def sequential_cmap():
    from matplotlib.colors import LinearSegmentedColormap
    cm = LinearSegmentedColormap.from_list('blue_ramp', BLUE_RAMP)
    cm.set_bad(LAND)
    return cm


def robust_sym(a, p=99.0):
    a = np.abs(np.asarray(a)[np.isfinite(a)])
    if a.size == 0:
        return 1.0
    v = float(np.percentile(a, p))
    return v if v > 0 else (float(a.max()) or 1.0)


def ensure_dirs():
    for d in (CACHE, STATS, FIGS, ANIMS):
        d.mkdir(parents=True, exist_ok=True)
