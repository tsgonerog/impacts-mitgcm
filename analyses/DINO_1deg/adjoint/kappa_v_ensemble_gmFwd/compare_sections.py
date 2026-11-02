#!/usr/bin/env python3
"""The same adjoint experiments at four cost sections, compared: amplitude and pattern of the sensitivities
across latitude, and how each section's sensitivities depend on kappa_v (2026-10-20).

    python compare_sections.py table            # stats/sections_table.csv, stats/sections_summary.json
    python compare_sections.py figures [--deck D]   # figures/sections_*.png (+ copies into D, the deck's figures/)
    python compare_sections.py film [--deck D]  # animations/film_sections_theta.pdf/.gif (+ a copy into D)
    python compare_sections.py all [--deck D]

Reads the products of every campaign in campaign.SECTION_ORDER that has them (forward_state.py,
adjoint_products.py per campaign) and writes to analysis/cost_sections/ under campaign.OUTPUTS -- a
cross-campaign directory, as analysis/<campaign>/ is per campaign. A section whose campaign has not
finished is left out of every figure, so the script runs at any stage.

The four sections (the advisor's request of 2026-10-15; campaign.COST_SECTION): 25 S (jsec 74, 848 m), the
original 26 N (127, 982 m), 43 N (148, 848 m; the overturning maximum, production since 2026-10-13) and 60 N
(175, 982 m; subpolar). Every campaign differentiates the same eight states (the legs 31366-31373), so
anything that differs between the campaigns is the cost section.

What is compared, per section: the cost's own size and noise floor, J and dJ/dkappa_v across the ensemble,
the finite-difference checks, the amplitude of the temperature sensitivity against lead, the 791 m maps and
the control gradients of the reference adjoint (pattern correlations between sections), and the pattern
correlation of each member with its own reference (how much the kappa_v dependence of the patterns depends
on where the cost is). The film shows the column sum of the temperature sensitivity of the four reference
adjoints side by side, backwards in time.
"""
from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import campaign as c
import make_films as mf

OUT = c.OUTPUTS / 'analysis' / c.CROSS_DIR   # cost_sections (first generation) or cost_sections_Sv
FIGS, STATS, ANIMS = OUT / 'figures', OUT / 'stats', OUT / 'animations'
LEVEL_M = 791                      # the map level: the deck's temperature film's upper level (inside every section's band)
COLORS = c.SERIES + ['#7c4dff']    # four categorical slots: the suite's three plus a violet
LEADS = [30.0 / 366, 1.0, 5.0]
LEAD_LAB = {LEADS[0]: '30 d', 1.0: '1 yr', 5.0: '5 yr'}


# ---------------------------------------------------------------- the campaigns and their products
def short(name):
    return c.COST_SECTION[name]['sec_name']


def A(name):
    return c.OUTPUTS / 'analysis' / name


def jobs(name):
    """(ADJ, FD) job dicts of a campaign, as campaign.py derives them for the current one."""
    rows = c._job_map(name)
    adj = {('REF' if role.startswith('reference') else tag.split('/')[-1].split('_')[0]): j
           for j, role, tag in rows if role.startswith(('reference adjoint', 'member adjoint'))}
    fd = {(role.split()[-1] if role.split()[-1] != 'sweep' else tag.split('/')[-1].split('_')[0]): j
          for j, role, tag in rows if role.startswith('FD')}
    return adj, fd


def ready(name):
    """A campaign whose reference adjoint's products are cached (adjoint_products.py fields + tables)."""
    return (A(name) / 'cache' / 'fields_REF.npz').exists() and (A(name) / 'stats' / 'fc_gradient.csv').exists()


def sections():
    return [n for n in c.SECTION_ORDER if ready(n)]


def load(name, rel):
    p = A(name) / rel
    if not p.exists():
        return None
    if p.suffix == '.csv':
        return pd.read_csv(p)
    if p.suffix == '.json':
        return json.loads(p.read_text())
    return np.load(p)


def klev(depth_m):
    return int(np.abs(-c.grid()['RC'] - depth_m).argmin())


def colsum(a, m):
    return np.where(m.any(axis=0), np.where(m, a, 0.0).sum(axis=0), np.nan)


def ensure():
    for d in (FIGS, STATS, ANIMS):
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------- the streamfunction behind the sections
def psi_spinup():
    """psi(j, k) of the spin-up's last decade (years 190-200 of 31203), cached."""
    p = STATS / 'psi_spinup_last_decade.npz'
    if p.exists():
        return np.load(p)['psi']
    g = c.grid()
    files = sorted(glob.glob(str(c.run_dir(c.SPINUP_JOB) / 'dynDiag.*.data')))[-120:]
    v = np.mean([c.read_record(f[:-5], 'VVEL') for f in files], axis=0)
    P = c.overturning(v, g).T
    np.savez_compressed(p, psi=P, lat=g['lat'], rf=g['RF'])
    return P


def geometry():
    """One row per section: rows, latitudes, interface, psi of the spin-up there."""
    g = c.grid()
    P = psi_spinup()
    rows = []
    for name in c.SECTION_ORDER:
        cs = c.COST_SECTION[name]
        j, k = cs['jsec'], cs['kmax']
        rows.append(dict(campaign=name, section=cs['sec_name'], jsec=j + 1, kmaxdepth=k,
                         lat_centre=float(g['lat'][j]), lat_face=float(0.5 * (g['lat'][j - 1] + g['lat'][j])),
                         interface_m=float(-g['RF'][k]), psi_at_interface_sv=float(P[j, k - 1]),
                         psi_max_below_300m_sv=float(np.nanmax(np.where(-g['RF'][1:] > 300, P[j], np.nan))),
                         psi_interface_of_max_m=float(-g['RF'][int(np.nanargmax(np.where(-g['RF'][1:] > 300, P[j], -np.inf))) + 1]),
                         since=cs['since']))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- the table
def table(**_):
    ensure()
    g = c.grid()
    geo = geometry().set_index('campaign')
    rows, summary = [], {}
    for name in sections():
        adj, fd = jobs(name)
        fg = load(name, 'stats/fc_gradient.csv').set_index('run')
        nf = load(name, 'stats/noise_floor.json')
        fdc = load(name, 'stats/fd_checks.csv')
        ts = load(name, 'cache/adj_timeseries.csv')
        mm = load(name, 'cache/member_metrics.csv')
        ref = ts[(ts.run == 'REF') & (ts['var'] == 'ADJtheta')].sort_values('lead_yr')
        rms_at = lambda L, v='ADJtheta': float(ts[(ts.run == 'REF') & (ts['var'] == v)].iloc[(ts[(ts.run == 'REF') & (ts['var'] == v)].lead_yr - L).abs().argsort().iloc[0]].rms)
        kap = fdc[fdc.test.str.startswith('kappa')] if fdc is not None else pd.DataFrame()
        r = dict(geo.loc[name])
        r.update(campaign=name, ref_job=adj.get('REF'),
                 J_ref=float(fg.fc['REF']), sigma_monthly=float(nf['jproxy']['std_monthly']) if nf else np.nan,
                 J_over_sigma=float(fg.fc['REF'] / nf['jproxy']['std_monthly']) if nf else np.nan,
                 dJdkappa_ref=float(fg.G_dJdkappa_uniform['REF']),
                 dJdkappa_fd_err=float(kap.adjoint_rel_err.iloc[0]) if len(kap) else np.nan,
                 J_min_member=fg.fc.idxmin(), J_members_over_ref=', '.join('%.3f' % (fg.fc[m] / fg.fc['REF']) for m in c.RUN_ORDER if m in fg.index),
                 rms_ADJtheta_30d=rms_at(30 / 366.), rms_ADJtheta_1yr=rms_at(1.0), rms_ADJtheta_5yr=rms_at(5.0),
                 rms_ADJdiffkr_5yr=rms_at(5.0, 'ADJdiffkr'),
                 peak_lead_ADJtheta_yr=float(ref.lead_yr.iloc[ref.rms.values.argmax()]))
        if mm is not None:
            t1 = mm[(mm['var'] == 'ADJtheta') & mm.run.isin(c.MEMBERS)]
            t1 = t1.iloc[(t1.lead_yr - 1.0).abs().argsort()]
            t1 = t1[t1.lead_yr == t1.lead_yr.iloc[0]].set_index('run')['corr']
            d5 = mm[(mm['var'] == 'ADJdiffkr') & mm.run.isin(c.MEMBERS)]
            d5 = d5[d5.lead_yr == d5.lead_yr.max()].set_index('run')['corr']
            r.update(member_corr_ADJtheta_1yr=', '.join('%.2f' % t1[m] for m in c.MEMBERS if m in t1.index),
                     member_corr_ADJdiffkr_5yr=', '.join('%.2f' % d5[m] for m in c.MEMBERS if m in d5.index),
                     member_corr_ADJtheta_1yr_min=float(t1.min()), member_corr_ADJdiffkr_5yr_min=float(d5.min()))
        rows.append(r)
    df = pd.DataFrame(rows)
    # pattern correlations between the sections' reference adjoints
    names = sections()
    corr = {}
    if len(names) > 1:
        for var in ('adxx_theta', 'adxx_diffkr', 'adxx_qnet', 'adxx_fu', 'adxx_empmr'):
            m = c.mask(var)
            w = c.weights(var)[m]
            z = {n: load(n, 'cache/adxx_REF.npz')[var][m].astype(np.float64) for n in names}
            corr[var] = {a: {b: c.pattern_corr(z[a], z[b], w) for b in names} for a in names}
            corr[var + '_rms'] = {n: c.rms(z[n], w) for n in names}
        m = c.mask('ADJtheta')
        w = c.weights('ADJtheta')[m]
        for L in LEADS:
            z = {n: load(n, 'cache/fields_REF.npz')['ADJtheta_L%.3f' % L][m].astype(np.float64) for n in names}
            corr['ADJtheta_L%.3f' % L] = {a: {b: c.pattern_corr(z[a], z[b], w) for b in names} for a in names}
            corr['ADJtheta_L%.3f_rms' % L] = {n: c.rms(z[n], w) for n in names}
    df.to_csv(STATS / 'sections_table.csv', index=False)
    (STATS / 'sections_summary.json').write_text(json.dumps(
        dict(sections=names, table=df.to_dict(orient='records'), pattern_corr_between_sections=corr,
             level_m=LEVEL_M, note='pattern correlations are area/volume weighted over wet cells, between the reference '
                                   'adjoints of two campaigns (the same state, the same executable; only the cost differs)'),
        indent=1, default=float))
    with pd.option_context('display.width', 250, 'display.max_columns', 40):
        print(df.drop(columns=[k for k in df.columns if k.startswith('member_corr_ADJ') and not k.endswith('min')]).to_string())
    for k, v in corr.items():
        if not k.endswith('_rms'):
            print(k, pd.DataFrame(v).round(3).to_string())
    print('wrote', STATS / 'sections_table.csv')


# ---------------------------------------------------------------- figures
FIG = {}


def figure(fn):
    FIG[fn.__name__] = fn
    return fn


def save(fig, name):
    p = FIGS / (name + '.png')
    fig.savefig(p)
    plt.close(fig)
    print('wrote', p)


@figure
def sections_on_psi():
    """The depth-space overturning of the spin-up's last decade with the four sections drawn as what they are:
    the integral across one row's southern face from the surface to one interface."""
    import cmocean
    g = c.grid()
    P = psi_spinup()
    geo = geometry()
    lat, rf = g['lat'], g['RF']
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    lev = np.arange(-12, 12.1, 1.0)
    cf = ax.contourf(lat, rf[1:], P.T, levels=lev, cmap=cmocean.cm.balance, extend='both')   # rf is negative (depth down)
    ax.contour(lat, rf[1:], P.T, levels=lev, colors='k', linewidths=0.25, alpha=0.5)
    for i, r in geo.iterrows():
        col = COLORS[i]
        ax.plot([r.lat_face, r.lat_face], [0, -r.interface_m], color=col, lw=2.6, solid_capstyle='butt')
        ax.plot([r.lat_face], [-r.interface_m], 'o', color=col, ms=6, mec='white', mew=1.2)
        ax.annotate('%s\n%d m, %.1f Sv' % (r.section, round(r.interface_m), r.psi_at_interface_sv),
                    (r.lat_face, -r.interface_m), xytext=(0, -14 - 34 * (i % 2)), textcoords='offset points', ha='center',
                    va='top', fontsize=8, color=col, weight='bold',
                    bbox=dict(fc=c.SURFACE, ec='none', alpha=0.75, pad=1.5))
    cb = fig.colorbar(cf, ax=ax, pad=0.02)
    cb.set_label('overturning streamfunction [Sv]')
    ax.set_xlabel('latitude')
    ax.set_ylabel('depth [m]')
    ax.set_ylim(-4000, 0)
    ax.set_xlim(lat.min(), lat.max())
    ax.set_title('The four cost sections on the overturning of the spin-up 31203, years 190-200\n'
                 '(each cost: the transport across one row, from the surface to the marked interface)', fontsize=9.5)
    ax.grid(False)
    save(fig, 'sections_on_psi')


@figure
def sections_J_gradient():
    names = sections()
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 3.6))
    for i, n in enumerate(names):
        col = COLORS[c.SECTION_ORDER.index(n)]
        fg = load(n, 'stats/fc_gradient.csv').sort_values('factor')
        axs[0].plot(fg.factor, fg.fc, '-o', color=col, ms=4.5, mec=c.SURFACE, mew=1.2, label=short(n))
        ref = float(fg.set_index('run').fc['REF'])
        axs[1].plot(fg.factor, fg.fc / ref, '-o', color=col, ms=4.5, mec=c.SURFACE, mew=1.2, label=short(n))
        axs[2].plot(fg.factor, fg.G_dJdkappa_uniform, '-o', color=col, ms=4.5, mec=c.SURFACE, mew=1.2, label='adjoint, ' + short(n))
        fd = load(n, 'stats/fd_checks.csv')
        kap = fd[fd.test.str.startswith('kappa')] if fd is not None else []
        if len(kap):
            axs[2].plot([1.0], [kap.fd_central.iloc[0] / (0.1 * c.KAPPA0)], 'D', color=col, ms=6, mec=c.INK, mew=0.8)
    axs[2].axhline(0, color=c.AXIS_C, lw=0.8)
    axs[2].set_yscale('symlog', linthresh=300 * c.J_SCALE)
    xs = sorted(c.FACTOR.values())
    for ax in axs:
        ax.set_xscale('log', base=2)
        ax.set_xticks(xs)
        ax.set_xticklabels(['%g' % v for v in xs])
        ax.set_xlabel('κ_v / 1.2e-5')
    axs[0].set_ylabel('J over the 5-yr window (fc)')
    axs[0].set_title('the cost at each section', fontsize=9.5)
    axs[1].set_ylabel('J / J(reference κ_v)')
    axs[1].set_title('the same, relative to each section\'s reference', fontsize=9.5)
    axs[2].set_ylabel('dJ/dκ_v [per m²/s]')
    axs[2].set_title('the adjoint gradient (◆ central finite difference, ±10 %)', fontsize=9.5)
    axs[0].legend(fontsize=8, title='cost section', title_fontsize=8)
    fig.tight_layout()
    save(fig, 'sections_J_gradient')


@figure
def sections_amplitude_vs_lead():
    names = sections()
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 3.5))
    for v, ax in zip(('ADJtheta', 'ADJdiffkr', 'ADJqnet'), axs):
        for n in names:
            ts = load(n, 'cache/adj_timeseries.csv')
            s = ts[(ts.run == 'REF') & (ts['var'] == v)].sort_values('lead_yr')
            ax.plot(s.lead_yr, s.rms, color=COLORS[c.SECTION_ORDER.index(n)], lw=1.6, label=short(n))
        ax.set_yscale('log')
        ax.set_xlabel('lead [yr]')
        ax.set_ylabel('RMS %s over wet cells' % v)
        ax.set_title({'ADJtheta': 'temperature sensitivity (an adjoint state: set at lead 0, decays backwards)',
                      'ADJdiffkr': 'κ_v sensitivity (a running total: grows backwards)',
                      'ADJqnet': 'heat-flux sensitivity (a running total)'}[v], fontsize=8.5)
    axs[0].legend(fontsize=8, title='cost section', title_fontsize=8)
    fig.tight_layout()
    save(fig, 'sections_amplitude_vs_lead')


def _maps_grid(names, panels, fname, title, units):
    """rows = sections (south to north), columns = panels [(label, fn(name) -> 2-D field)], each map on its own
    symmetric scale (99.5th percentile, printed under it)."""
    g = c.grid()
    nr, nc = len(names), len(panels)
    fig, axs = plt.subplots(nr, nc, figsize=(2.3 * nc + 0.6, 3.1 * nr), squeeze=False, sharex=True, sharey=True)
    for i, n in enumerate(names):
        for j, (lab, fn) in enumerate(panels):
            ax = axs[i, j]
            f = fn(n)
            vm = c.robust_sym(f, 99.5)
            pm = ax.pcolormesh(g['XC'], g['YC'], np.ma.masked_invalid(f) / vm, cmap=c.diverging_cmap(), vmin=-1, vmax=1,
                               shading='auto', rasterized=True)
            jj = c.COST_SECTION[n]['jsec']
            ax.plot(g['XC'][jj], g['YC'][jj], color=c.INK, lw=1.1)
            if i == 0:
                ax.set_title(lab, fontsize=9)
            if j == 0:
                ax.set_ylabel('cost at %s' % short(n), fontsize=9.5, color=COLORS[c.SECTION_ORDER.index(n)], weight='bold')
            ax.text(0.98, 0.02, '±%.1e' % vm, transform=ax.transAxes, ha='right', va='bottom', fontsize=7, color=c.INK2,
                    bbox=dict(fc=c.SURFACE, ec='none', alpha=0.8, pad=1))
            ax.set_xticks([-40, -20, 0])
            ax.set_yticks([-60, -30, 0, 30, 60])
            ax.tick_params(labelsize=7)
            ax.grid(False)
    cb = fig.colorbar(pm, ax=axs, shrink=0.5, pad=0.015, ticks=[-1, 0, 1])
    cb.set_label('fraction of the amplitude printed in each map (%s)' % units, fontsize=8)
    fig.suptitle(title, fontsize=10, y=0.995)
    save(fig, fname)


@figure
def sections_ADJtheta_maps():
    k = klev(LEVEL_M)
    m = c.mask('ADJtheta')
    panels = [('lead %s, %d m' % (LEAD_LAB[L], round(-c.grid()['RC'][k])),
               (lambda n, L=L: np.where(m[k], load(n, 'cache/fields_REF.npz')['ADJtheta_L%.3f' % L][k], np.nan)))
              for L in LEADS]
    panels.append(('lead 5 yr, column sum', lambda n: colsum(load(n, 'cache/fields_REF.npz')['ADJtheta_L5.000'], m)))
    _maps_grid(sections(), panels, 'sections_ADJtheta_maps',
               'Temperature sensitivity of the reference adjoint at the four sections (each map on its own scale)', 'dJ/K')


@figure
def sections_adxx_maps():
    k = klev(LEVEL_M)
    g = c.grid()
    mC = c.mask('adxx_theta')
    panels = [('dJ/dθ(t=0), %d m' % round(-g['RC'][k]), lambda n: np.where(mC[k], load(n, 'cache/adxx_REF.npz')['adxx_theta'][k], np.nan)),
              ('dJ/dκ_v, column sum', lambda n: colsum(load(n, 'cache/adxx_REF.npz')['adxx_diffkr'], mC)),
              ('dJ/dQnet (5-yr total)', lambda n: np.where(c.mask('adxx_qnet'), load(n, 'cache/adxx_REF.npz')['adxx_qnet'], np.nan)),
              ('dJ/dτ_x (5-yr total)', lambda n: np.where(c.mask('adxx_fu'), load(n, 'cache/adxx_REF.npz')['adxx_fu'], np.nan)),
              ('dJ/d(E−P−R) (5-yr total)', lambda n: np.where(c.mask('adxx_empmr'), load(n, 'cache/adxx_REF.npz')['adxx_empmr'], np.nan))]
    _maps_grid(sections(), panels, 'sections_adxx_maps',
               'Control gradients over the 5-yr window, reference adjoint, four sections (each map on its own scale)', 'per unit of the control')


@figure
def sections_pattern_corr():
    s = json.loads((STATS / 'sections_summary.json').read_text())
    names = s['sections']
    keys = [('ADJtheta_L%.3f' % LEADS[0], 'ADJtheta, lead 30 d'), ('ADJtheta_L1.000', 'ADJtheta, lead 1 yr'),
            ('ADJtheta_L5.000', 'ADJtheta, lead 5 yr'), ('adxx_theta', 'dJ/dθ(t=0)'), ('adxx_diffkr', 'dJ/dκ_v'),
            ('adxx_qnet', 'dJ/dQnet'), ('adxx_fu', 'dJ/dτ_x'), ('adxx_empmr', 'dJ/d(E−P−R)')]
    keys = [(k, l) for k, l in keys if k in s['pattern_corr_between_sections']]
    fig, axs = plt.subplots(1, len(keys), figsize=(2.3 * len(keys) + 0.6, 2.9), squeeze=False)
    labs = [short(n) for n in names]
    for ax, (k, lab) in zip(axs[0], keys):
        M = np.array([[s['pattern_corr_between_sections'][k][a][b] for b in names] for a in names])
        ax.imshow(M, cmap=c.sequential_cmap(), vmin=-1, vmax=1)
        for i in range(len(names)):
            for j in range(len(names)):
                ax.text(j, i, '%.2f' % M[i, j], ha='center', va='center', fontsize=7.5,
                        color=c.SURFACE if M[i, j] > 0.55 else c.INK)
        ax.set_xticks(range(len(names)))
        ax.set_xticklabels(labs, fontsize=7.5)
        ax.set_yticks(range(len(names)))
        ax.set_yticklabels(labs if ax is axs[0, 0] else [], fontsize=7.5)
        ax.set_title(lab, fontsize=8.5)
        ax.grid(False)
    fig.suptitle('Pattern correlation between the reference adjoints of two sections (same state, same executable, only the cost differs)',
                 fontsize=9.5, y=1.02)
    fig.tight_layout()
    save(fig, 'sections_pattern_corr')


@figure
def sections_kappa_dependence():
    names = sections()
    fig, axs = plt.subplots(1, 3, figsize=(12.5, 3.5))
    xs = [c.FACTOR[m] for m in c.MEMBERS]
    for n in names:
        col = COLORS[c.SECTION_ORDER.index(n)]
        mm = load(n, 'cache/member_metrics.csv')
        ts = load(n, 'cache/adj_timeseries.csv')
        if mm is None:
            continue
        t1 = mm[(mm['var'] == 'ADJtheta') & mm.run.isin(c.MEMBERS)]
        L1 = t1.lead_yr.iloc[(t1.lead_yr - 1.0).abs().argsort().iloc[0]]
        t1 = t1[t1.lead_yr == L1].set_index('run')['corr'].reindex(c.MEMBERS)
        d5 = mm[(mm['var'] == 'ADJdiffkr') & mm.run.isin(c.MEMBERS)]
        d5 = d5[d5.lead_yr == d5.lead_yr.max()].set_index('run')['corr'].reindex(c.MEMBERS)
        axs[0].plot(xs, t1.values, '-o', color=col, ms=4.5, mec=c.SURFACE, mew=1.2, label=short(n))
        axs[1].plot(xs, d5.values, '-o', color=col, ms=4.5, mec=c.SURFACE, mew=1.2, label=short(n))
        amp = []
        for m in c.MEMBERS:
            sm = ts[(ts.run == m) & (ts['var'] == 'ADJtheta')]
            sr = ts[(ts.run == 'REF') & (ts['var'] == 'ADJtheta')]
            amp.append(float(sm[sm.lead_yr == sm.lead_yr.max()].rms.iloc[0] / sr[sr.lead_yr == sr.lead_yr.max()].rms.iloc[0]))
        axs[2].plot(xs, amp, '-o', color=col, ms=4.5, mec=c.SURFACE, mew=1.2, label=short(n))
    for ax in axs:
        ax.set_xscale('log', base=2)
        ax.set_xticks(xs)
        ax.set_xticklabels(['%g' % v for v in xs])
        ax.set_xlabel('κ_v / 1.2e-5')
    axs[0].set_ylim(0, 1)
    axs[1].set_ylim(0, 1)
    axs[0].set_ylabel('pattern correlation with the section\'s reference')
    axs[0].set_title('temperature sensitivity, lead 1 yr', fontsize=9.5)
    axs[1].set_title('κ_v sensitivity, lead 5 yr', fontsize=9.5)
    axs[2].set_ylabel('RMS ADJtheta at 5 yr, member / reference')
    axs[2].set_title('amplitude at 5 yr lead, relative to the reference', fontsize=9.5)
    axs[2].axhline(1, color=c.AXIS_C, lw=0.8)
    axs[0].legend(fontsize=8, title='cost section', title_fontsize=8)
    fig.tight_layout()
    save(fig, 'sections_kappa_dependence')


@figure
def sections_fd_checks():
    names = sections()
    tests = []
    data = {}
    for n in names:
        fd = load(n, 'stats/fd_checks.csv')
        nf = load(n, 'stats/noise_floor.json')
        if fd is None:
            continue
        sig = nf['jproxy']['std_monthly'] if nf else 0.0
        for _, r in fd.iterrows():
            # one bar group per perturbation; a Theta box keeps its place in the label, since two boxes can share an amplitude
            t = (r.test.replace(' everywhere', '').replace(' +', ' ±').replace('surface stress', 'stress').replace('surface heat flux', 'heat flux')
                 .replace('freshwater flux E-P-R', 'E−P−R').replace(' below 1500 m', ' >1500 m').replace('kappa_v', 'κ_v'))
            if t.startswith('Theta'):
                t = t.replace('Theta ', 'θ ').replace(', ', '\n')
            if t not in tests:
                tests.append(t)
            data[(n, t)] = (float(r.adjoint_rel_err), abs(float(r.fd_central)) >= 2 * sig)
    fig, ax = plt.subplots(figsize=(12.5, 4.2))
    w = 0.8 / max(1, len(names))
    for i, n in enumerate(names):
        col = COLORS[c.SECTION_ORDER.index(n)]
        for j, t in enumerate(tests):
            if (n, t) not in data:
                continue
            e, ok = data[(n, t)]
            y = np.clip(e, -3, 3)
            ax.bar(j + (i - (len(names) - 1) / 2) * w, y, w * 0.92, color=col if ok else c.SURFACE, edgecolor=col, lw=1.2,
                   label=short(n) if j == 0 else None)
            if abs(e) > 3:   # off the scale: the ratio adjoint/FD, written along the bar
                ax.text(j + (i - (len(names) - 1) / 2) * w, np.sign(e) * 0.15, '×%.0f' % (1 + e),
                        ha='center', va='bottom' if e > 0 else 'top', fontsize=6.5, color=c.INK, rotation=90)
    ax.axhline(0, color=c.AXIS_C, lw=0.8)
    ax.set_xticks(range(len(tests)))
    ax.set_xticklabels(tests, fontsize=7, rotation=25, ha='right')
    ax.set_ylabel('adjoint / finite difference − 1')
    ax.set_ylim(-3.3, 3.3)
    ax.set_title('Finite-difference checks of the reference adjoint at each section (hollow: the finite difference is below 2σ '
                 'of the cost\'s monthly noise, so the check has no signal there)', fontsize=9)
    ax.legend(fontsize=8, title='cost section', title_fontsize=8, ncol=len(names), loc='upper left')
    fig.tight_layout()
    save(fig, 'sections_fd_checks')


@figure
def sections_jproxy_spinup():
    """The cost proxy of the spin-up at the four sections: what each cost measures through 170 years, and its noise."""
    names = [n for n in c.SECTION_ORDER if (A(n) / 'cache' / 'spinup_series.csv').exists()]
    fig, axs = plt.subplots(1, 2, figsize=(11, 3.4), gridspec_kw=dict(width_ratios=[3, 1.2]))
    for n in names:
        col = COLORS[c.SECTION_ORDER.index(n)]
        sp = load(n, 'cache/spinup_series.csv')
        axs[0].plot(sp.year, sp.jproxy, color=col, lw=0.9, label=short(n))
        nf = load(n, 'stats/noise_floor.json')
        if nf:
            axs[1].bar(short(n), nf['jproxy']['std_monthly'], color=col)
    axs[0].set_xlabel('year of the spin-up 31203')
    axs[0].set_ylabel('cost proxy J (30.5-d means) [%s]' % c.J_UNIT)
    axs[0].set_title('the cost formula applied to the spin-up\'s monthly velocity, four sections', fontsize=9.5)
    axs[0].legend(fontsize=8, ncol=4)
    axs[1].set_ylabel('σ of monthly J, years 100-170, detrended')
    axs[1].set_title('the noise floor of each cost', fontsize=9.5)
    fig.tight_layout()
    save(fig, 'sections_jproxy_spinup')


def figures(names=None, deck=None, **_):
    ensure()
    if not (STATS / 'sections_summary.json').exists():
        table()
    for k, fn in FIG.items():
        if names is None or k in names:
            fn()
            if deck:
                import shutil
                Path(deck).mkdir(parents=True, exist_ok=True)
                shutil.copy2(FIGS / (k + '.png'), Path(deck) / (k + '.png'))
                print('  copied to', Path(deck) / (k + '.png'))


# ---------------------------------------------------------------- the four-section film
def film(stride=12, deck=None, **_):
    """The column sum of the temperature sensitivity of the four reference adjoints, side by side, backwards in
    time (the convention of the deck's eight-member film: one fixed scale for every panel and frame)."""
    ensure()
    names = sections()
    g = c.grid()
    m = c.mask('ADJtheta')
    its = c.ITERS[::stride][::-1]
    cols = {}
    for n in names:
        adj, _ = jobs(n)
        d = c.run_dir(adj['REF'])
        cols[n] = np.array([colsum(c.read_mds(c.dump_base(d, 'ADJtheta', it), np.float32).astype(np.float64), m) for it in its])
    vmax = c.robust_sym(np.array([cols[n] for n in names]), 99.5)
    e = int(np.floor(np.log10(vmax))) if vmax > 0 else 0
    mf.c.ANIMS = ANIMS          # Film writes into campaign.ANIMS: point it at the cross-section directory
    fl = mf.Film('sections_theta', [deck] if deck else [])
    for i, it in enumerate(its):
        L = float(c.lead_years(it))
        fig, axs = plt.subplots(1, len(names), figsize=(2.3 * len(names) + 0.8, 4.4), squeeze=False, sharey=True)
        fig.subplots_adjust(top=0.80, bottom=0.08, left=0.05, right=0.90, wspace=0.12)
        for ax, n in zip(axs[0], names):
            pm = ax.pcolormesh(g['XC'], g['YC'], np.ma.masked_invalid(cols[n][i]) / 10.0 ** e, cmap=c.diverging_cmap(),
                               vmin=-vmax / 10.0 ** e, vmax=vmax / 10.0 ** e, shading='auto', rasterized=True)
            jj = c.COST_SECTION[n]['jsec']
            ax.plot(g['XC'][jj], g['YC'][jj], color=c.INK, lw=1.0)
            ax.set_title('cost at %s' % short(n), fontsize=9.5, color=COLORS[c.SECTION_ORDER.index(n)], weight='bold')
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
        fig.suptitle('column sum of the sensitivity of $J$ to temperature, reference $\\kappa_v$, one cost section per panel\n'
                     'lead %4.2f yr before the end of the cost window' % L, fontsize=10.5, y=0.985)
        cb = fig.colorbar(pm, ax=axs[0], shrink=0.8, pad=0.015)
        cb.set_label(('dJ / K m  $\\times10^{%d}$' % e) if e else 'dJ / K m', fontsize=8.5)
        cb.ax.tick_params(labelsize=7.5)
        fl.add(fig)
    fl.close()
    (ANIMS / 'films_index.tsv').write_text('film\truns\tvariable\twhat\tpanels\tframes\tstride_days\tlead_yr\tscale\tunits\n'
                                           + '\t'.join(['film_sections_theta', ', '.join('%s %d' % (short(n), jobs(n)[0]['REF']) for n in names),
                                                        'ADJtheta', 'temperature, the reference adjoint of each cost section', 'column sum',
                                                        str(len(its)), str(5 * stride), '%.2f-%.2f' % (float(c.lead_years(its[0])), float(c.lead_years(its[-1]))),
                                                        'fixed, 99.5th pct = %.3e' % vmax, 'dJ/K m']) + '\n')


STEPS = {'table': table, 'figures': figures, 'film': film}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('steps', nargs='+', help="table | figures [names] | film | all")
    ap.add_argument('--deck', default=None, help='copy the film into this directory (the deck\'s figures/)')
    ap.add_argument('--stride', type=int, default=12, help='dumps between film frames (a dump is 5 d)')
    a = ap.parse_args()
    steps = ['table', 'figures', 'film'] if a.steps == ['all'] else a.steps
    if steps[0] == 'figures' and len(steps) > 1:
        figures(names=steps[1:], deck=a.deck)
    else:
        for s in steps:
            STEPS[s](stride=a.stride, deck=a.deck)
