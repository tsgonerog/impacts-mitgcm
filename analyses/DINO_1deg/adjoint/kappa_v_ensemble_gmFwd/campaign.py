"""Shared definitions for the κ_v ensemble under the current DINO configuration (2026-09-13).

Campaign `kappa_v_ensemble_gmFwd` (runs/{forward,adjoint}/kappa_v_ensemble_gmFwd/ and
analysis/kappa_v_ensemble_gmFwd/ under OUTPUTS), submitted by submit_campaign.sh as one dependency chain:

* a 170-yr spin-up from rest of the live input/data (reference viscosity files, viscAhReMax=2., scheme 33
  with explicit vertical advection, GM/Redi on); it replaces the production spin-up 31203, unreadable since
  /scratch2 failed on 2026-09-12; both trees were merged back into /scratch2 on 2026-09-15;
* forward legs, 10 yr from the spin-up's year 170, one per κ_v (input/variants/kappa_v_ensemble/
  data_<m>_ReMax2); the REF leg is the spin-up's own continuation to year 180;
* 5-yr adjoints (the approximate adjoint: GM/Redi in the forward sweep only, scheme 30 in the adjoint
  sweep) from year 180: the reference is the live input_tap/data from the REF leg, each member its own
  leg (input_tap/variants/kappa_v_ensemble/data_M<k>_ReMax2_gmFwd_approxAdv);
* finite-difference forward sweeps from the REF leg's year 180 (input_tap/variants/fd_checks/): κ_v ±10 %,
  Theta ±δ in three boxes of the pickup, and uniform perturbations of fu, fv, Qnet and E−P−R.

Job IDs come from job_map.tsv. The cost J (code_tap/cost_atlantic_heat.F) is the section transport index across
one grid row over the upper kmaxdepth levels, averaged over the final 30 d of the window and normalised per MPI tile.

FOUR CAMPAIGNS SHARE THIS SUITE (two since 2026-10-13, four since 2026-10-20), one per cost section, selected by the
CAMPAIGN_NAME environment variable. All four use the same legs 31366-31373, the same perturbed pickups and forcing
files (they belong to the state, not to the section); each has its own eight 5-yr adjoints and its own
finite-difference sweeps:

* `kappa_v_ensemble_gmFwd` (2026-09-13): the cost section at jsec = 127 (row centre 26.05 N), upper 25 levels (982 m);
  runs 31366-31398, analysed 2026-09-15.
* `kappa_v_ensemble_gmFwd_sec43N` (2026-10-13, the default): the section moved to the overturning maximum, jsec = 148
  (row centre 43.21 N, southern face 42.84 N), upper 24 levels (848 m) -- see overturning_maximum.py; runs 31553-31578.
* `kappa_v_ensemble_gmFwd_sec60N` (2026-10-20): the subpolar section the advisor asked for on 2026-10-15, near the
  OSNAP latitudes: jsec = 175 (row centre 59.77 N, the row nearest 60 N; southern face 59.52 N), upper 25 levels
  (982 m, the interface where psi peaks on that row: 6.04 Sv, 82 % of the 43 N maximum).
* `kappa_v_ensemble_gmFwd_sec25S` (2026-10-20): the Southern Hemisphere section, north of the Deacon cell:
  jsec = 74 (row centre 25.15 S, the row nearest 25 S; southern face 25.60 S), upper 24 levels (848 m: on that row
  psi falls monotonically from the Ekman layer and has no interior maximum, so the 43 N interface is kept, and the
  two costs differ in latitude only; psi there is 1.62 Sv).

The section is a data.cost setting since 2026-10-20 (cost_atl_jsec, cost_atl_kmaxdepth; a parameter statement in
code_tap/cost_atlantic_heat.F until then, so the first two campaigns each needed a build), which submit_campaign.sh
passes through IMPACTS_COST_JSEC / IMPACTS_COST_KMAXDEPTH; the run directories of the last two carry _sec60N / _sec25S.
Every campaign's job_map.tsv copies the leg rows of the first, so LEG_JOB resolves to the same run directories (filed
under runs/forward/kappa_v_ensemble_gmFwd/).

COST_SECTION below holds what differs; JSEC, KMAX, SEC_LAT and SEC_AMOC are the current campaign's. compare_sections.py
reads all four.

THE SECOND GENERATION, `*_Sv` (2026-11-01): the same four sections rerun after the cost routine was rewritten on
2026-10-29 (merged 2026-10-31): J is the row transport in Sverdrups, each tile's sum added without the tree's per-tile
wet-count normalisation, so every fc is 15 to 25 times the first generation's, depending on the row, and the middle third is no
longer weighted 6 % less. The same legs, pickups and forcing files; eight new 5-yr adjoints and the finite-difference
sweeps per section, filed under runs/adjoint/<campaign>/ and analysis/<campaign>/ beside the old ones, which stay as the
record. UNITS says which form a campaign's numbers are in ('tile' or 'Sv'), OLD_CAMPAIGN names the first-generation
campaign of the same section (its reference adjoint is PREV_GMFWD_5YR_JOB, so adjoint_products.py members/fields and
make_figures.py ref_vs_previous compare the two generations), jproxy follows the form, and the cross-section products of
the second generation go to analysis/cost_sections_Sv/ (CROSS_DIR).

ONE INTERFACE FOR EVERY SECTION (decided 2026-11-01, the same morning): the cost integrates to 848 m (24 levels) at
all four sections. 43 N and 25 S already did; 26 N and 60 N had used 982 m (25 levels), the interface where their own
cells peak, in the first generation and in the first submission of the second (campaigns `*_sec26N_Sv` and
`*_sec60N_Sv`, jobs 31748-31773 and 31800-31829, cancelled at the decision and deleted; their job maps and the cost
lines of their finite-difference sweeps are in logs/deleted_run_records/). Their Sverdrup campaigns at 848 m are
`*_sec26N_Sv848` and `*_sec60N_Sv848`, and the second generation the documents report is {25S_Sv, 26N_Sv848, 43N_Sv,
60N_Sv848} (SECTION_ORDER). A `_Sv848` campaign compares with the first generation of its section (old_campaign,
prev_5yr_job), which differs from it in units AND depth; the units effect alone is measured at 43 N and 25 S, where
the depth did not change.
"""
from __future__ import annotations

import glob
import os
import re
from pathlib import Path

import numpy as np

OUTPUTS = Path(os.environ.get('CAMPAIGN_OUTPUTS', '/scratch2/tshahriar/DINO_1deg_outputs'))  # the campaign's runs, moved back 2026-09-15
EARLIER_OUTPUTS = Path('/scratch/tshahriar/DINO_1deg_outputs')                               # the tree it ran in while /scratch2 was down
# Which campaign this suite reads: CAMPAIGN_NAME in the environment, the 43 N rerun by default (see the module docstring).
COST_SECTION = {   # jsec is 0-based here (the Fortran row is jsec + 1); kmax the number of levels from the surface
    # first generation: the cost in the tree's per-tile-normalised form (units='tile'), runs up to 2026-10-28
    'kappa_v_ensemble_gmFwd': dict(jsec=126, kmax=25, sec_name='26 N', sec_amoc='amoc26', since='2026-09-13',
                                   prev_5yr_job=31237, legs_from=None, units='tile', old_campaign=None),
    'kappa_v_ensemble_gmFwd_sec43N': dict(jsec=147, kmax=24, sec_name='43 N', sec_amoc='amoc43', since='2026-10-13',
                                          prev_5yr_job=None, legs_from='kappa_v_ensemble_gmFwd', units='tile', old_campaign=None),
    'kappa_v_ensemble_gmFwd_sec60N': dict(jsec=174, kmax=25, sec_name='60 N', sec_amoc='amoc60', since='2026-10-20',
                                          prev_5yr_job=None, legs_from='kappa_v_ensemble_gmFwd', units='tile', old_campaign=None),
    'kappa_v_ensemble_gmFwd_sec25S': dict(jsec=73, kmax=24, sec_name='25 S', sec_amoc='amoc25S', since='2026-10-20',
                                          prev_5yr_job=None, legs_from='kappa_v_ensemble_gmFwd', units='tile', old_campaign=None),
    # second generation (2026-11-01): the cost as the row transport in Sverdrups; prev_5yr_job is the first
    # generation's reference adjoint of the same section, so the two generations are compared by the suite itself
    'kappa_v_ensemble_gmFwd_sec43N_Sv': dict(jsec=147, kmax=24, sec_name='43 N', sec_amoc='amoc43', since='2026-11-01',
                                             prev_5yr_job=31553, legs_from='kappa_v_ensemble_gmFwd', units='Sv',
                                             old_campaign='kappa_v_ensemble_gmFwd_sec43N'),
    'kappa_v_ensemble_gmFwd_sec25S_Sv': dict(jsec=73, kmax=24, sec_name='25 S', sec_amoc='amoc25S', since='2026-11-01',
                                             prev_5yr_job=31647, legs_from='kappa_v_ensemble_gmFwd', units='Sv',
                                             old_campaign='kappa_v_ensemble_gmFwd_sec25S'),
    # the one-interface decision of 2026-11-01: 26 N and 60 N at 848 m (24 levels); the 982 m *_Sv submissions of the
    # same morning were cancelled, so these compare with the first generation (units and depth together)
    'kappa_v_ensemble_gmFwd_sec26N_Sv848': dict(jsec=126, kmax=24, sec_name='26 N', sec_amoc='amoc26', since='2026-11-01',
                                                prev_5yr_job=31374, legs_from='kappa_v_ensemble_gmFwd', units='Sv',
                                                old_campaign='kappa_v_ensemble_gmFwd'),
    'kappa_v_ensemble_gmFwd_sec60N_Sv848': dict(jsec=174, kmax=24, sec_name='60 N', sec_amoc='amoc60', since='2026-11-01',
                                                prev_5yr_job=31621, legs_from='kappa_v_ensemble_gmFwd', units='Sv',
                                                old_campaign='kappa_v_ensemble_gmFwd_sec60N'),
}
CAMPAIGN = os.environ.get('CAMPAIGN_NAME', 'kappa_v_ensemble_gmFwd_sec43N')
if CAMPAIGN not in COST_SECTION:
    raise SystemExit('CAMPAIGN_NAME=%s is not one of %s' % (CAMPAIGN, sorted(COST_SECTION)))
_CS = COST_SECTION[CAMPAIGN]
UNITS = _CS['units']                           # 'tile' (first generation) or 'Sv' (second)
OLD_CAMPAIGN = _CS['old_campaign']             # the first-generation campaign of the same section, for a *_Sv campaign
J_UNIT = 'Sv' if UNITS == 'Sv' else 'tile units'   # what fc is in, for axis labels
J_SCALE = 16.6 if UNITS == 'Sv' else 1.0           # for limits and thresholds written in the first generation's units
# south to north, for the cross-section comparison: the four campaigns of this campaign's generation
SECTION_ORDER = (['kappa_v_ensemble_gmFwd_sec25S_Sv', 'kappa_v_ensemble_gmFwd_sec26N_Sv848', 'kappa_v_ensemble_gmFwd_sec43N_Sv',
                  'kappa_v_ensemble_gmFwd_sec60N_Sv848'] if UNITS == 'Sv' else
                 ['kappa_v_ensemble_gmFwd_sec25S', 'kappa_v_ensemble_gmFwd', 'kappa_v_ensemble_gmFwd_sec43N',
                  'kappa_v_ensemble_gmFwd_sec60N'])
CROSS_DIR = 'cost_sections_Sv' if UNITS == 'Sv' else 'cost_sections'   # analysis/<CROSS_DIR>/: the sections compared
ANALYSIS = OUTPUTS / 'analysis' / CAMPAIGN
CACHE = ANALYSIS / 'cache'
STATS = ANALYSIS / 'stats'
FIGS = ANALYSIS / 'figures'
ANIMS = ANALYSIS / 'animations'
# The perturbed pickups and forcing files of the finite-difference sweeps belong to the state they perturb (the
# reference leg's year 180), not to a cost section, so a campaign that reuses another's legs reuses those too.
SHARED_INPUTS = OUTPUTS / 'analysis' / (_CS['legs_from'] or CAMPAIGN)
PICKUPS = SHARED_INPUTS / 'perturbed_pickups'
PERTURBED_FORCING = SHARED_INPUTS / 'perturbed_forcing'
PREVIOUS = Path(__file__).resolve().parent / 'previous_campaigns_reference.json'   # numbers of the earlier campaigns

# ---------------------------------------------------------------- runs
KAPPA0 = 1.2e-5
FACTOR = dict(M1=0.25, M2=0.5, REF=1.0, M3=2.0, M4=4.0, M5=8.0, M6=16.0, M7=32.0)
RUN_ORDER = ['M1', 'M2', 'REF', 'M3', 'M4', 'M5', 'M6', 'M7']
MEMBERS = [r for r in RUN_ORDER if r != 'REF']
PREV_GMFWD_5YR_JOB = _CS['prev_5yr_job']  # 26 N campaign: 31237, the 2026-09-11 adjoint of the same cost from the deleted leg 31205's
                                          # year 180; None for the 43 N campaign, whose cost no earlier adjoint measured
THETA_BOXES = {   # (k0, k1, j0, j1, i0, i1), 0-based end-exclusive, as in perturb_pickup.py
    'deepN': dict(box=(28, 36, 143, 157, 0, 51), amp=0.016, what='40-50 N, below 1500 m'),
    'midTrop': dict(box=(20, 28, 99, 110, 0, 51), amp=0.035, what='0-10 N, 500-1500 m'),
    'soUpper': dict(box=(0, 20, 24, 56, 0, 51), amp=0.5, what='40-60 S, 0-500 m'),
    # 2026-10-14, for the 43 N cost: the deepN box sits right under the new section and moves J by only 4e-5 (the noise
    # floor; the 43 N adjoint predicts +1.2e-4), so a deep box NORTH of the section, where the 43 N adjoint predicts
    # +5.1e-3 for the same amplitude, was added and run as one more pair of sweeps (jobs in job_map.tsv, deepNN_p/m).
    'deepNN': dict(box=(28, 36, 150, 175, 0, 51), amp=0.016, what='45-60 N, below 1500 m'),
    # 2026-10-21, for the 60 N and 25 S costs: with the amplitudes above, no check at 60 N and only two at 25 S (the
    # zonal stress and soUpper) clear twice those costs' monthly noise (1.8e-3 and 1.9e-3), so one pair of boxes per
    # section was added where its reference adjoint predicts about 5 sigma: for 60 N the subpolar deep water
    # (55-68 N below 1500 m, +-0.05 K) and the thermocline just north of the section (56-64 N, 300-1000 m, +-0.10 K);
    # for 25 S the South Atlantic thermocline (35-10 S, 300-1000 m, +-0.06 K) and deep water (35-10 S below 1500 m,
    # +-0.10 K). Run for those two campaigns only (jobs in their job_map.tsv); pickups beside the others.
    'subpolarDeep': dict(box=(28, 36, 165, 194, 0, 51), amp=0.05, what='55-68 N, below 1500 m'),
    'secN60': dict(box=(16, 26, 167, 184, 0, 51), amp=0.10, what='56-64 N, 300-1000 m'),
    'sAtlThermo': dict(box=(16, 26, 62, 90, 0, 51), amp=0.06, what='35-10 S, 300-1000 m'),
    'sAtlDeep': dict(box=(28, 36, 62, 90, 0, 51), amp=0.10, what='35-10 S, below 1500 m'),
}
FORCING_TESTS = {   # control: (adxx file, amplitude, unit, what) -- files in analysis/<campaign>/perturbed_forcing/
    'fu': ('adxx_fu', 0.005, 'N/m2', 'zonal surface stress'),
    'fv': ('adxx_fv', 2e-8, 'N/m2', 'meridional surface stress'),
    'qnet': ('adxx_qnet', 0.003, 'W/m2', 'net surface heat flux'),
    'empmr': ('adxx_empmr', 3e-9, 'kg/m2/s', 'freshwater flux E-P-R'),
}


def _job_map(campaign=None):
    """Rows of analysis/<campaign>/job_map.tsv written by submit_campaign.sh: (job, role, tag)."""
    p = OUTPUTS / 'analysis' / (campaign or CAMPAIGN) / 'job_map.tsv'
    rows = []
    if p.exists():
        for line in p.read_text().splitlines()[1:]:
            f = line.split('\t')
            if len(f) >= 3 and 'cancelled' not in f[1]:
                rows.append((int(f[0]), f[1], f[2]))
    return rows


_MAP = _job_map()
# A campaign that reuses another's legs (legs_from) reads them from that campaign's job map until its own map
# exists -- submit_campaign.sh copies the leg rows into the new map, so afterwards both agree.
if _CS['legs_from'] and not any(role == 'forward leg' for _, role, _ in _MAP):
    _MAP += [(j, role, tag) for j, role, tag in _job_map(_CS['legs_from']) if role.startswith(('spin-up', 'forward leg'))]
# The campaign was submitted with its own 170-year spin-up, 31329, whose last 61 days were rerun as 31365
# (job_map.tsv keeps both rows as the record of what ran). Every output file of the two was byte-identical
# to the production spin-up 31203's first 170 years, so they were deleted on 2026-09-16, 31365's year-170
# pickup was moved into 31203 and the legs' pickup links repointed there. The spin-up is 31203; it runs on
# to year 200, so anything that means "the spin-up up to the legs' start" must stop at LEG_NITER0 itself.
SPINUP_JOB = 31203
SPINUP_END_JOB = None     # was 31365, the rerun last 61 days; deleted with 31329
LEG_JOB = {tag.split('/')[-1].replace('_ReMax2', ''): j for j, role, tag in _MAP if role.startswith('forward leg')}
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
    # (not Path.with_suffix: on 'ADJempr.0003162240' it would replace the iteration, not append '.data', so the
    # second spelling was never found -- the 2026-10-13 runs are the first here that write ADJempr.*)
    for prefix in DUMP_FILE_ALIASES.get(var, (var,)):
        base = Path(d) / ('%s.%010d' % (prefix, it))
        if Path(str(base) + '.data').exists():
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
# JSEC is the 0-based row whose SOUTHERN face the compiled cost integrates VVEL across (Fortran jsec = JSEC + 1); KMAX the
# number of levels from the surface (Fortran kmaxdepth). 126 / 25 for the 26 N campaign, 147 / 24 for the 43 N rerun.
JSEC, KMAX, SNX, NTILE = _CS['jsec'], _CS['kmax'], 17, 3
SEC_NAME = _CS['sec_name']                   # how the section is named in titles: '26 N' / '43 N' / '60 N' / '25 S' (the row centre, rounded)
SEC_AMOC = _CS['sec_amoc']                   # the forward_state.py column holding the overturning maximum at the section's row
AMOC_INDEX_LATS = {'amoc26': 26.0, 'amoc43': 43.2, 'amoc60': 59.8, 'amoc25S': -25.2}   # the overturning index columns
                                                      # forward_state.py writes (nearest row); at 25 S the maximum above
                                                      # 1000 m is the Ekman layer's, not an AMOC cell (jproxy is the cost)


def sec_lat():
    """Latitude (deg N) of the section row's centre, from the grid."""
    return float(grid()['lat'][JSEC])



def jproxy(v, g=None):
    """The compiled cost formula applied to a meridional-velocity field v (k, j, i), upper KMAX
    levels, row JSEC: for a 'Sv' campaign the row transport in Sverdrups (the rewritten routine of
    2026-10-29), for a 'tile' campaign the tree's per-tile wet-face normalisation. With a 30.5-d
    mean v it is a proxy of fc, which averages the final 30 d."""
    g = g or grid()
    msk = g['hFacS'][:, JSEC, :] > 0
    dxg = g['DXG'][JSEC, :]
    vs = v[:, JSEC, :]
    if UNITS == 'Sv':
        return 1e-6 * float((vs[:KMAX] * dxg[None, :] * g['DRF'][:KMAX, None] * g['hFacS'][:KMAX, JSEC, :]).sum())
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
    """max of psi above 1000 m at the row nearest lat0 (the deck's AMOC index; the row centre names the latitude)."""
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
