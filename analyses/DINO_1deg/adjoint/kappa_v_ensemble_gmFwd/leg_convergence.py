#!/usr/bin/env python3
"""The stopping rule of the leg extension (2026-11-10): have the members' oceans stopped drifting?

    CAMPAIGN_NAME=kappa_v_ensemble_gmFwd_sec43N_Sv python leg_convergence.py [--window 5] [--factor 3] [--no-figure]

Background. At year 180, after ten years at their own kappa_v, the members were still adjusting: the transport the
cost measures drifted by 1.0-1.7 Sv per decade, 13-32 times the reference's own drift (make_figures.py leg_drift,
notes Section 7.2). The advisor meeting of 3 November 2026 decided to extend every leg by about 50 years before any
further adjoint; on 10 November the extension became a sequence of 50-year chunks, each member and the reference at
the same age, that stops when the rule below is met. A full equilibrium is out of reach by design: the basin's
2.5e17 m3 turn over once in about 1100 years at 7 Sv, and the diffusive time z^2/kappa_v to 1000 m is 2600 years at
the reference kappa_v and 42 000 years at a quarter of it, so the members adjust at paces a hundred times apart.
What the sensitivities need is the part of the state they live in, the upper kilometre, to stop changing.

The rule. For each member, the trend per decade over the last WINDOW years (default 5, whole years so the seasonal
cycle cancels) of
  JH_43N   the full-column meridional heat transport across 43 N in PW, the cost of the next campaign
           (cost_atlantic_heat.F with cost_atl_quantity='heat': theta on the southern face of the row,
           0.5 (theta_j + theta_{j-1}), times v dxG drF hFacS, summed over the row and all levels, times rho0 cp),
  JV       the volume transport the previous cost measured (campaign.jproxy: the campaign's row and depth), and
  T500     the volume-mean temperature above 500 m,
is compared with the reference's own drift: the same trend taken over the same window every year from year 150 to
the end of the spin-up 31203 (year 200), whose largest magnitude is the reference scale. A member has settled when
each of the three trends is within FACTOR (default 3) times its reference scale. The volume-mean temperature Tmean is
reported too but not used: it is the deep ocean's slow clock, and no member reaches equilibrium on it.

Inputs. The spin-up 31203 (campaign.SPINUP_JOB), the eight 10-year legs (campaign.LEG_JOB) and every extension chunk
listed in analysis/kappa_v_legs_extension/job_map.tsv (role starting 'forward leg extension'); per member the pieces
are concatenated by iteration. The monthly dynDiag records (THETA, SALT, VVEL) are reduced to the indices above and
cached per run in analysis/kappa_v_legs_extension/cache/series_<member>_<job>.csv, incrementally, so a rerun after a
new chunk reads only the new months. A record written in the last two minutes is left for the next run.

Outputs, under analysis/kappa_v_legs_extension/: stats/leg_convergence.csv (one row per member: last-year means,
trends, ratios to the reference scale, verdicts), stats/leg_convergence_reference.json (the reference scales and the
rule's parameters), figures/leg_convergence.png (the series from year 150 and the trends against kappa_v, with the
accepted band shaded). For the reference, the years the extension repeats (180-200) are also compared with the
spin-up's own months and the largest difference printed: a forward run reproduces the spin-up byte for byte, so this
should be zero.
"""
import argparse
import glob
import json
import re
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

import campaign as c

EXT = c.OUTPUTS / 'analysis' / 'kappa_v_legs_extension'
CACHE, STATS, FIGS = EXT / 'cache', EXT / 'stats', EXT / 'figures'
RHO0, CP = 1035.0, 3994.0                           # rhoConst (rhoNil of input_tap/data) and HeatCapacity_Cp's default
SECTIONS = {'25S': 73, '26N': 126, '43N': 147, '60N': 174}   # 0-based rows (Fortran jsec 74, 127, 148, 175)
RULE_INDICES = ('JH_43N', 'JV', 'T500')
REPORTED = ('Tmean', 'T500', 'Smean', 'JV', 'JH_43N', 'JH_26N', 'JH_60N', 'JH_25S', 'amoc43')
UNITS = {'Tmean': '°C', 'T500': '°C', 'Smean': 'g/kg', 'JV': 'Sv', 'JH_43N': 'PW', 'JH_26N': 'PW', 'JH_60N': 'PW',
         'JH_25S': 'PW', 'amoc43': 'Sv'}
REF_YEARS = (150.0, 200.0)                          # the spin-up's years over which its own drift is measured


# ---------------------------------------------------------------- indices of one monthly record
def heat_transport(v, th, g, jsec):
    """Full-column meridional heat transport across row jsec in PW, as the cost forms it."""
    area = g['DXG'][jsec][None, :] * g['DRF'][:, None] * g['hFacS'][:, jsec, :]
    tf = 0.5 * (th[:, jsec, :] + th[:, jsec - 1, :])
    return RHO0 * CP * 1e-15 * float((tf * v[:, jsec, :] * area).sum())


def indices(base):
    g = c.grid()
    v = c.read_record(base, 'VVEL')
    th = c.read_record(base, 'THETA')
    sa = c.read_record(base, 'SALT')
    it = int(re.search(r'\.(\d{10})$', str(base)).group(1))
    up = g['RC'] >= -500.0
    vol, volu = g['vol'], g['vol'][up]
    out = dict(iter=it, year=it / c.STEPS_PER_YEAR,
               Tmean=float((th * vol).sum() / vol.sum()), T500=float((th[up] * volu).sum() / volu.sum()),
               Smean=float((sa * vol).sum() / vol.sum()), JV=c.jproxy(v, g), amoc43=c.amoc_index(v, 43.0, g))
    for name, j in SECTIONS.items():
        out['JH_' + name] = heat_transport(v, th, g, j)
    return out


def series(run_dir, cache_file, procs=8):
    """The monthly indices of one run, from the cache plus whatever dynDiag records are new."""
    bases = sorted(p[:-5] for p in glob.glob(str(Path(run_dir) / 'dynDiag.*.data')))
    bases = [b for b in bases if time.time() - Path(b + '.data').stat().st_mtime > 120]   # not the one being written
    have = pd.read_csv(cache_file) if cache_file.exists() else pd.DataFrame(columns=['iter'])
    done = set(int(i) for i in have['iter'])
    new = [b for b in bases if int(b[-10:]) not in done]
    if new:
        c.grid()
        with Pool(procs) as pool:
            rows = pool.map(indices, new, chunksize=10)
        have = pd.concat([have, pd.DataFrame(rows)], ignore_index=True) if len(have) else pd.DataFrame(rows)
        have = have.sort_values('iter').reset_index(drop=True)
        have.to_csv(cache_file, index=False)
        print('  %s: %d new monthly records (now %d)' % (cache_file.name, len(new), len(have)))
    return have.sort_values('iter').reset_index(drop=True)


# ---------------------------------------------------------------- the runs
def extension_jobs():
    """{member: [(job, run_dir), ...]} from the extension's job map, in order of submission."""
    out = {}
    p = EXT / 'job_map.tsv'
    if not p.exists():
        return out
    for line in p.read_text().splitlines()[1:]:
        f = line.split('\t')
        if len(f) < 3 or not f[1].startswith('forward leg extension') or 'cancelled' in f[1]:
            continue
        job, tag = int(f[0]), f[2].split('/')[-1]
        member = tag.split('_')[0]
        d = c.run_dir(job)
        if d is None:
            print('  extension job %d (%s): no run directory yet' % (job, tag))
            continue
        out.setdefault(member, []).append((job, d))
    return out


def trend_per_decade(df, col, window_years):
    """Slope per decade of col over the last window_years whole years of df (None if too short)."""
    n = int(round(window_years * 12))
    if len(df) < n:
        return None
    w = df.iloc[-n:]
    return float(np.polyfit(w.year.values, w[col].values, 1)[0] * 10)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--window', type=float, default=5.0, help='years over which each trend is taken (default 5)')
    ap.add_argument('--factor', type=float, default=3.0, help='accepted multiple of the reference drift (default 3)')
    ap.add_argument('--no-figure', action='store_true')
    ap.add_argument('--procs', type=int, default=8)
    a = ap.parse_args()
    for d in (CACHE, STATS, FIGS):
        d.mkdir(parents=True, exist_ok=True)

    print('spin-up %d' % c.SPINUP_JOB)
    sp = series(c.run_dir(c.SPINUP_JOB), CACHE / ('series_spinup_%d.csv' % c.SPINUP_JOB), a.procs)
    ext = extension_jobs()
    pieces, member_series = {}, {}
    for r in c.RUN_ORDER:
        parts = [sp[sp.iter <= c.LEG_NITER0]]
        print('leg %s: %d' % (r, c.LEG_JOB[r]))
        leg = series(c.run_dir(c.LEG_JOB[r]), CACHE / ('series_%s_%d.csv' % (r, c.LEG_JOB[r])), a.procs)
        parts.append(leg)
        covered = [(float(leg.year.min()), float(leg.year.max()), c.LEG_JOB[r])]
        for job, d in ext.get(r, []):
            print('extension %s: %d (%s)' % (r, job, d.name))
            e = series(d, CACHE / ('series_%s_%d.csv' % (r, job)), a.procs)
            if len(e):
                parts.append(e)
                covered.append((float(e.year.min()), float(e.year.max()), job))
        s = pd.concat(parts, ignore_index=True).drop_duplicates('iter', keep='last').sort_values('iter')
        member_series[r] = s.reset_index(drop=True)
        pieces[r] = covered

    # the reference's own drift: the spin-up over REF_YEARS, every year, same window
    ref = sp[(sp.year > REF_YEARS[0] - 1e-6) & (sp.year <= REF_YEARS[1] + 1e-6)].reset_index(drop=True)
    n = int(round(a.window * 12))
    ref_tr = {k: [float(np.polyfit(ref.year.values[i:i + n], ref[k].values[i:i + n], 1)[0] * 10)
                  for i in range(0, len(ref) - n + 1, 12)] for k in REPORTED}
    scale = {k: max(abs(x) for x in v) for k, v in ref_tr.items()}

    rows = []
    for r in c.RUN_ORDER:
        s = member_series[r]
        last = s[s.iter > c.LEG_NITER0]                 # the member's own years (leg + extension)
        row = dict(run=r, factor=c.FACTOR[r], kappa_v=c.KAPPA0 * c.FACTOR[r],
                   first_year=float(last.year.min()), last_year=float(last.year.max()),
                   n_years_own=len(last) / 12.0, jobs=' '.join(str(j) for _, _, j in pieces[r]))
        for k in REPORTED:
            row['%s_last_year' % k] = float(last[k].iloc[-12:].mean())
            tr = trend_per_decade(last, k, a.window)
            row['%s_trend_per_decade' % k] = tr
            row['%s_ratio_to_ref' % k] = None if tr is None or scale[k] == 0 else abs(tr) / scale[k]
        ok = [row['%s_ratio_to_ref' % k] is not None and row['%s_ratio_to_ref' % k] <= a.factor for k in RULE_INDICES]
        for k, o in zip(RULE_INDICES, ok):
            row['settled_%s' % k] = bool(o)
        row['settled'] = all(ok)
        rows.append(row)
    tab = pd.DataFrame(rows)
    tab.to_csv(STATS / 'leg_convergence.csv', index=False, float_format='%.6g')
    (STATS / 'leg_convergence_reference.json').write_text(json.dumps(dict(
        rule=dict(window_years=a.window, factor=a.factor, indices=list(RULE_INDICES),
                  reference_years=list(REF_YEARS), spinup_job=c.SPINUP_JOB,
                  statement='a member has settled when |trend over the last window| <= factor * max |reference trend| '
                            'for each of the indices, the reference trends taken over the same window every year '
                            'between the reference years of the spin-up'),
        reference_scale_per_decade=scale,
        reference_trends_per_decade={k: dict(min=min(v), max=max(v), n=len(v)) for k, v in ref_tr.items()},
        units=UNITS), indent=1))

    # the reference extension against the spin-up's own months (years 180-200): a free reproducibility check
    for job, d in ext.get('REF', []):
        e = pd.read_csv(CACHE / ('series_REF_%d.csv' % job))
        both = e.merge(sp, on='iter', suffixes=('_ext', '_sp'))
        if len(both):
            dmax = max(float(np.abs(both[k + '_ext'] - both[k + '_sp']).max()) for k in ('Tmean', 'JV', 'JH_43N'))
            print('REF extension %d against the spin-up over %d shared months: largest difference in Tmean, JV, JH_43N'
                  ' = %.3g (zero means byte-identical output)' % (job, len(both), dmax))

    # the report
    print('\nreference drift, spin-up years %g-%g, %g-yr windows (per decade): ' % (*REF_YEARS, a.window)
          + ', '.join('%s %+.3g..%+.3g' % (k, min(v), max(v)) for k, v in ref_tr.items() if k in RULE_INDICES + ('Tmean',)))
    print('rule: |trend| <= %g x reference scale for %s\n' % (a.factor, ', '.join(RULE_INDICES)))
    hdr = '%-4s %6s %9s  ' % ('run', 'kappa', 'years') + ''.join('%22s' % k for k in RULE_INDICES + ('Tmean',)) + '  verdict'
    print(hdr)
    for _, row in tab.iterrows():
        cells = ''
        for k in RULE_INDICES + ('Tmean',):
            tr, ra = row['%s_trend_per_decade' % k], row['%s_ratio_to_ref' % k]
            cells += '%22s' % ('--' if tr is None else '%+.3g %s (%.0fx)' % (tr, UNITS[k], ra))
        print('%-4s %6gx %4.0f-%-4.0f  %s  %s' % (row.run, row.factor, row.first_year, row.last_year, cells,
                                                   'settled' if row.settled else 'drifting'))

    if not a.no_figure:
        figure(member_series, sp, tab, scale, a)


def figure(member_series, sp, tab, scale, a):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    c.setup_style()
    cm = c.sequential_cmap()
    norm = LogNorm(vmin=min(c.FACTOR.values()) / 1.5, vmax=max(c.FACTOR.values()))

    def colour(r):
        return c.INK if r == 'REF' else cm(norm(c.FACTOR[r]))

    keys = ('Tmean', 'T500', 'JV', 'JH_43N')
    titles = ('(a) volume-mean temperature [°C]', '(b) temperature above 500 m [°C]',
              '(c) transport at %s, upper %d levels [Sv]' % (c.SEC_NAME, c.KMAX), '(d) heat transport across 43 N, full column [PW]')
    x_end = max(float(s.year.max()) for s in member_series.values()) + 2
    fig, axs = plt.subplots(2, 4, figsize=(11.5, 5.4))
    fig.subplots_adjust(left=0.05, right=0.99, top=0.88, bottom=0.09, wspace=0.32, hspace=0.5)
    for ax, k, title in zip(axs[0], keys, titles):
        sm = sp.set_index('year')[k].rolling(12, center=True).mean()
        ax.plot(sm.index, sm.values, color=c.INK, lw=1.2, zorder=4)
        for r in c.RUN_ORDER:
            s = member_series[r].set_index('year')[k].rolling(12, center=True).mean()
            s = s[s.index >= 169.5]
            ax.plot(s.index, s.values, color=colour(r), lw=1.5 if r == 'REF' else 1.0, zorder=4 if r == 'REF' else 3)
        for r in ('M1', 'REF', 'M7'):
            s = member_series[r].set_index('year')[k].rolling(12, center=True).mean().dropna()
            ax.annotate('%gx' % c.FACTOR[r], (s.index[-1], s.values[-1]), xytext=(3, 0), textcoords='offset points',
                        fontsize=7, color=c.INK2, va='center')
        for x in (170, 180):
            ax.axvline(x, color=c.AXIS_C, lw=0.7, zorder=1)
        ax.set_xlim(150, x_end)
        ax.set_xlabel('model year', fontsize=7.5)
        ax.tick_params(labelsize=7)
        ax.set_title(title, fontsize=8, loc='left')
    for ax, k, letter in zip(axs[1], keys, 'efgh'):
        col = '%s_trend_per_decade' % k
        band = a.factor * scale[k]
        ax.axhspan(-band, band, color=c.GRID_C, alpha=0.7, lw=0, zorder=0)
        ax.axhline(0, color=c.MUTED, lw=0.6, zorder=1)
        ok = tab[col].notna()
        ax.plot(tab.factor[ok], tab[col][ok], color=c.AXIS_C, lw=0.8, zorder=2)
        for _, row in tab[ok].iterrows():
            ax.plot(row.factor, row[col], 'o', ms=4.5, color=colour(row.run), mec=c.SURFACE, mew=0.6, zorder=3)
        ax.set_xscale('log', base=2)
        ax.set_xticks([0.25, 1, 4, 16])
        ax.set_xticklabels(['0.25', '1', '4', '16'])
        ax.minorticks_off()
        ax.tick_params(labelsize=7)
        ax.set_xlabel(r'$\kappa_v$ / reference', fontsize=7.5)
        ax.set_title('(%s) trend over the last %g yr [%s/decade]' % (letter, a.window, UNITS[k]), fontsize=8, loc='left')
    years = sorted(set(int(round(r.last_year)) for _, r in tab.iterrows()))
    fig.text(0.05, 0.975, 'Top: 12-month running means along the spin-up (black to year 170), the legs and their extensions; '
             'colour from 0.25x (light) to 32x (dark), the reference black.\nBottom: the trend over each member\'s last '
             '%g years at year %s; the band is %g times the largest %g-year trend of the spin-up itself between years '
             '%g and %g. Settled: %s.' % (a.window, '/'.join(str(y) for y in years), a.factor, a.window, *REF_YEARS,
                                          ', '.join(tab.run[tab.settled]) or 'none'),
             fontsize=7.2, color=c.INK2, va='top', linespacing=1.4)
    p = FIGS / 'leg_convergence.png'
    fig.savefig(p, dpi=170)
    plt.close(fig)
    print('wrote', p)


if __name__ == '__main__':
    sys.exit(main())
