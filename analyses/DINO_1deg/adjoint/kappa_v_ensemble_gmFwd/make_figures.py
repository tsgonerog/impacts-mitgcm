#!/usr/bin/env python3
"""Figures (PNG) and animations (GIF) of the campaign, from the products of forward_state.py and
adjoint_products.py, into analysis/<campaign>/figures/ and animations/.

    python make_figures.py [--dev] all | <name> [<name> ...]

Conventions: signed sensitivities on a diverging map (cmocean balance, symmetric robust limits),
land grey, the cost section (campaign.SEC_NAME) drawn in ink; ADJ* dumps are shown in the order the adjoint
computes them, lead increasing. Colours for series follow the categorical slots of campaign.SERIES.
"""
import argparse
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

import campaign as c

DEV = False
FIG = {}


def figure(fn):
    FIG[fn.__name__] = fn
    return fn


def save(fig, name):
    p = c.FIGS / (name + '.png')
    fig.savefig(p)
    plt.close(fig)
    print('wrote', p)


def klev(depth_m):
    return int(np.abs(-c.grid()['RC'] - depth_m).argmin())


def section_line(ax):
    g = c.grid()
    ax.plot(g['XC'][c.JSEC], g['YC'][c.JSEC], color=c.INK, lw=1.2)


def sci(vmax):
    """Exponent for a colourbar: plot field / 10**e so ticks carry no offset text."""
    return int(np.floor(np.log10(vmax))) if vmax > 0 else 0


def map_panel(ax, f2d, title, vmax=None, cbar=True, units=''):
    g = c.grid()
    vmax = vmax or c.robust_sym(f2d)
    e = sci(vmax)
    pm = ax.pcolormesh(g['XC'], g['YC'], np.ma.masked_invalid(f2d) / 10.0 ** e, cmap=c.diverging_cmap(),
                       vmin=-vmax / 10.0 ** e, vmax=vmax / 10.0 ** e, shading='auto', rasterized=True)
    section_line(ax)
    ax.set_title(title, fontsize=8.5)
    ax.set_aspect('auto')
    ax.grid(False)
    ax.tick_params(labelsize=7.5)
    if cbar:
        cb = ax.figure.colorbar(pm, ax=ax, orientation='horizontal', pad=0.1, fraction=0.05, aspect=16)
        cb.ax.tick_params(labelsize=7)
        cb.set_label(('%s  ×1e%d' % (units, e)) if e else units, fontsize=7.5)
    return pm


def cbar_scaled(fig, mappable_fn, ax, f, units, **kw):
    """Draw with mappable_fn(scaled_field, vmax_scaled) and add a colourbar labelled with the exponent."""
    vm = c.robust_sym(f, kw.pop('p', 99.5))
    e = sci(vm)
    pm = mappable_fn(f / 10.0 ** e, vm / 10.0 ** e)
    cb = fig.colorbar(pm, ax=ax, pad=0.02, fraction=0.05)
    cb.ax.tick_params(labelsize=7.5)
    cb.set_label(('%s  ×1e%d' % (units, e)) if e else units, fontsize=8)
    return pm


def masked(f, var_mask):
    return np.where(var_mask, f, np.nan)


def fields(run):
    p = c.CACHE / ('fields_%s.npz' % run)
    return np.load(p) if p.exists() else None


def adxx(run):
    p = c.CACHE / ('adxx_%s.npz' % run)
    return np.load(p) if p.exists() else None


# ------------------------------------------------------------------ forward legs
@figure
def leg_indices_vs_kappa():
    df = pd.read_csv(c.CACHE / 'leg_series.csv')
    last = df[(df.run != 'spinup') & (df.iter > c.NITER0 - c.STEPS_PER_YEAR)]
    m = last.groupby('run')[['jproxy', c.SEC_AMOC, 'Tmean']].mean().reindex(c.RUN_ORDER)
    x = [c.FACTOR[r] for r in c.RUN_ORDER]
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.1))
    for ax, k, lab in zip(axs, ['jproxy', c.SEC_AMOC, 'Tmean'],
                          ['cost proxy J at %s (last year of the leg) [%s]' % (c.SEC_NAME, c.J_UNIT), 'overturning max above 1000 m at %s [Sv]' % c.SEC_NAME,
                           'volume-mean temperature [°C]']):
        ax.plot(x, m[k], '-o', color=c.SERIES[0], ms=5, mec=c.SURFACE, mew=1.5)
        ax.plot([1.0], [m.loc['REF', k]], 'o', color=c.INK, ms=6, mec=c.SURFACE, mew=1.5)
        ax.set_xscale('log', base=2)
        ax.set_xticks(x)
        ax.set_xticklabels(['%g' % v for v in x], fontsize=8)
        ax.set_xlabel('κ_v / 1.2e-5')
        ax.set_title(lab, fontsize=9.5)
    axs[0].annotate('reference', (1.0, m.loc['REF', 'jproxy']), xytext=(6, -12), textcoords='offset points', fontsize=8, color=c.INK2)
    save(fig, 'leg_indices_vs_kappa')


@figure
def leg_timeseries():
    df = pd.read_csv(c.CACHE / 'leg_series.csv')
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.2), sharex=True)
    for ax, k, lab in zip(axs, ['jproxy', c.SEC_AMOC], ['cost proxy J (30.5-d means) [%s]' % c.J_UNIT, 'overturning at %s [Sv]' % c.SEC_NAME]):
        for r in c.MEMBERS:
            s = df[df.run == r]
            ax.plot(s.year, s[k], color=c.AXIS_C, lw=0.9)
        for r, col in (('M1', c.SERIES[0]), ('M7', c.SERIES[1])):
            s = df[df.run == r]
            ax.plot(s.year, s[k], color=col, lw=1.4)
            ax.annotate('%s (%gx)' % (r, c.FACTOR[r]), (s.year.iloc[-1], s[k].iloc[-12:].mean()), xytext=(4, 0),
                        textcoords='offset points', fontsize=8, color=c.INK2, va='center')
        sp = df[df.run == 'spinup']
        ax.plot(sp.year, sp[k], color=c.INK, lw=1.2)
        s = df[df.run == 'REF']
        ax.plot(s.year, s[k], color=c.INK, lw=1.2)
        ax.annotate('reference', (s.year.iloc[-1], s[k].iloc[-12:].mean()), xytext=(4, 0), textcoords='offset points',
                    fontsize=8, color=c.INK2, va='center')
        ax.set_title(lab, fontsize=9.5)
        ax.set_xlabel('model year')
        ax.set_xlim(150, 181.6)
        ax.axvline(170, color=c.AXIS_C, lw=0.8)
    save(fig, 'leg_timeseries')


@figure
def leg_drift():
    """Whether the legs have settled when the adjoints start (year 180): the volume-mean temperature and the cost J
    (12-month running means of the monthly dynDiag; every leg continues the spin-up's years 150-170), and their
    trends over each leg's last three years against the reference's own three-year trends, taken every year from
    year 150 to 180 (the spin-up, then the REF leg, which reproduces it). Writes stats/leg_drift.csv and
    stats/leg_drift_reference.json."""
    from matplotlib.colors import LogNorm
    df = pd.read_csv(c.CACHE / 'leg_series.csv')
    sp = df[df.run == 'spinup'].sort_values('iter')
    depth = int(round(float(-np.asarray(c.grid()['RF']).ravel()[c.KMAX])))
    cm = c.sequential_cmap()
    norm = LogNorm(vmin=min(c.FACTOR.values()) / 1.5, vmax=max(c.FACTOR.values()))

    def colour(r):
        return c.INK if r == 'REF' else cm(norm(c.FACTOR[r]))

    def trend(s, col):          # per decade, over whole years (36 months), so the seasonal cycle cancels
        return float(np.polyfit(s.year.values, s[col].values, 1)[0] * 10)

    series = {r: pd.concat([sp, df[df.run == r]]).sort_values('iter') for r in c.RUN_ORDER}
    ref = series['REF']
    ref_tr = {k: [trend(ref.iloc[i:i + 36], k) for i in range(0, len(ref) - 35, 12)] for k in ('Tmean', 'jproxy')}
    rows = []
    for r in c.RUN_ORDER:
        leg = df[df.run == r].sort_values('iter')
        rows.append(dict(run=r, factor=c.FACTOR[r], kappa_v=1.2e-5 * c.FACTOR[r],
                         T_first_year=leg.Tmean.iloc[:12].mean(), T_last_year=leg.Tmean.iloc[-12:].mean(),
                         T_trend_last3yr_per_decade=trend(leg.iloc[-36:], 'Tmean'),
                         J_first_year=leg.jproxy.iloc[:12].mean(), J_last_year=leg.jproxy.iloc[-12:].mean(),
                         J_trend_last3yr_per_decade=trend(leg.iloc[-36:], 'jproxy')))
    tab = pd.DataFrame(rows)
    tab.to_csv(c.STATS / 'leg_drift.csv', index=False, float_format='%.5g')
    (c.STATS / 'leg_drift_reference.json').write_text(json.dumps(
        {k + '_3yr_trend_per_decade': dict(min=min(v), max=max(v), n=len(v), years='150-180') for k, v in ref_tr.items()},
        indent=1))

    fig = plt.figure(figsize=(6.4, 3.05))
    gs = fig.add_gridspec(2, 3, width_ratios=[1.2, 1.2, 0.95], left=0.07, right=0.985, top=0.75, bottom=0.15,
                          wspace=0.45, hspace=0.9)
    series_axes = [fig.add_subplot(gs[:, 0]), fig.add_subplot(gs[:, 1])]
    rate_axes = [fig.add_subplot(gs[0, 2]), fig.add_subplot(gs[1, 2])]
    titles = ['(a) volume-mean temperature [°C]', '(b) transport at %s, 0-%d m [Sv]' % (c.SEC_NAME, depth)]
    for ax, k, title in zip(series_axes, ('Tmean', 'jproxy'), titles):
        ax.axvspan(177, 180, color=c.GRID_C, alpha=0.6, lw=0, zorder=0)
        for x in (170, 180):
            ax.axvline(x, color=c.AXIS_C, lw=0.8, zorder=1)
        sm = sp.set_index('year')[k].rolling(12, center=True).mean()
        ax.plot(sm.index, sm.values, color=c.INK, lw=1.3, zorder=4)
        for r in c.RUN_ORDER:
            s = series[r].set_index('year')[k].rolling(12, center=True).mean()
            s = s[s.index >= 169.5]
            ax.plot(s.index, s.values, color=colour(r), lw=1.5 if r == 'REF' else 1.1, zorder=4 if r == 'REF' else 3)
        for r in ('M1', 'REF', 'M7'):
            s = series[r].set_index('year')[k].rolling(12, center=True).mean().dropna()
            ax.annotate('%gx' % c.FACTOR[r], (s.index[-1], s.values[-1]), xytext=(3, 0), textcoords='offset points',
                        fontsize=7, color=c.INK2, va='center')
        ax.set_xlim(150, 182.5)
        ax.set_xticks([150, 160, 170, 180])
        ax.set_xlabel('model year', fontsize=7.5)
        ax.tick_params(labelsize=7)
        ax.set_title(title, fontsize=7.8, loc='left')
    series_axes[0].text(169.6, 0.03, 'legs\nbranch', transform=series_axes[0].get_xaxis_transform(), fontsize=6.5,
                        color=c.MUTED, va='bottom', ha='right')
    for ax, k, unit, letter in zip(rate_axes, ('Tmean', 'jproxy'), ('°C', 'Sv'), 'cd'):
        col = 'T_trend_last3yr_per_decade' if k == 'Tmean' else 'J_trend_last3yr_per_decade'
        ax.axhline(0, color=c.MUTED, lw=0.6, zorder=1)
        ax.plot(tab.factor, tab[col], color=c.AXIS_C, lw=0.8, zorder=2)
        for _, row in tab.iterrows():
            ax.plot(row.factor, row[col], 'o', ms=4.2, color=colour(row.run), mec=c.SURFACE, mew=0.6, zorder=3)
        ax.set_xscale('log', base=2)
        ax.set_xticks([0.25, 1, 4, 16])
        ax.set_xticklabels(['0.25', '1', '4', '16'])
        ax.minorticks_off()
        ax.tick_params(labelsize=7)
        ax.set_title('(%s) trend at year 180 [%s/decade]' % (letter, unit), fontsize=7.8, loc='left')
    rate_axes[1].set_xlabel(r'$\kappa_v$ / reference', fontsize=7.5)
    fig.text(0.07, 0.985, 'Colour: $\\kappa_v$ from 0.25x (light) to 32x (dark); black: the reference (the spin-up to '
             'year 170, the REF leg after).\n(b) is the transport the cost J measures, computed month by month along '
             'the legs; J itself is its mean over the last 30 days of each adjoint run.\nShaded: each leg\'s last three '
             'years, over which the trends in (c) and (d) are taken. Every adjoint starts at year 180.', fontsize=7,
             color=c.INK2, va='top', linespacing=1.35)
    save(fig, 'leg_drift')


@figure
def leg_temperature_change():
    z = np.load(c.CACHE / 'leg_final_profiles.npz')
    g = c.grid()
    wet = g['wetC']
    depth = -g['RC']

    def hmean(t):
        return np.array([np.nansum(np.where(wet[k], t[k], 0) * g['RAC']) / (wet[k] * g['RAC']).sum()
                         if wet[k].any() else np.nan for k in range(len(depth))])

    def zmean(t):
        n = wet.sum(axis=2)
        return np.where(n > 0, np.nansum(np.where(wet, t, 0), axis=2) / np.maximum(n, 1), np.nan)

    ref = hmean(z['REF_T'])
    D = np.array([hmean(z[r + '_T']) - ref for r in c.MEMBERS])
    fig = plt.figure(figsize=(11, 4.0))
    ax = fig.add_axes([0.06, 0.14, 0.20, 0.72])
    cax = fig.add_axes([0.27, 0.14, 0.010, 0.72])
    vmax = c.robust_sym(D, 100)
    pm = ax.pcolormesh(np.arange(len(c.MEMBERS)), depth, D.T, cmap=c.diverging_cmap(), vmin=-vmax, vmax=vmax, shading='auto')
    ax.set_yscale('symlog', linthresh=200)
    ax.invert_yaxis()
    ax.set_xticks(range(len(c.MEMBERS)))
    ax.set_xticklabels(['%gx' % c.FACTOR[r] for r in c.MEMBERS], fontsize=8)
    ax.set_ylabel('depth [m]')
    ax.set_title('horizontal-mean ΔT, year 180', fontsize=9.5)
    ax.grid(False)
    fig.colorbar(pm, cax=cax).set_label('K', fontsize=8)
    for i, r in enumerate(['M1', 'M7']):
        a = fig.add_axes([0.37 + i * 0.32, 0.14, 0.24, 0.72])
        ca = fig.add_axes([0.37 + i * 0.32 + 0.245, 0.14, 0.010, 0.72])
        dz = zmean(z[r + '_T']) - zmean(z['REF_T'])
        vm = c.robust_sym(dz, 99.5)
        p2 = a.pcolormesh(g['lat'], depth, np.ma.masked_invalid(dz), cmap=c.diverging_cmap(), vmin=-vm, vmax=vm, shading='auto')
        a.invert_yaxis()
        a.set_xlabel('latitude [°]')
        a.set_title('zonal-mean ΔT, %s (%gx) − reference' % (r, c.FACTOR[r]), fontsize=9.5)
        a.grid(False)
        fig.colorbar(p2, cax=ca).set_label('K', fontsize=8)
    save(fig, 'leg_temperature_change')


# ------------------------------------------------------------------ reference adjoint
@figure
def ref_rms_vs_lead():
    ts = pd.read_csv(c.CACHE / 'adj_timeseries.csv')
    prev_p = c.ANALYSIS / 'dev_cache' / 'adj_timeseries.csv'
    prev = pd.read_csv(prev_p) if prev_p.exists() and not DEV else None
    vars_ = ['ADJtheta', 'ADJsalt', 'ADJdiffkr', 'ADJqnet', 'ADJempmr', 'ADJtaux']
    units = dict(ADJtheta='per K', ADJsalt='per g/kg', ADJdiffkr='per m²/s', ADJqnet='per W/m²', ADJempmr='per kg/m²/s', ADJtaux='per N/m²')
    fig, axs = plt.subplots(2, 3, figsize=(10.5, 5.2), sharex=True)
    for ax, v in zip(axs.ravel(), vars_):
        s = ts[(ts.run == 'REF') & (ts['var'] == v)].sort_values('lead_yr')
        ax.plot(s.lead_yr, s.rms, color=c.SERIES[0], lw=1.6, label='reference adjoint')
        if prev is not None:
            q = prev[(prev.run == 'REF') & (prev['var'] == v)].sort_values('lead_yr')
            ax.plot(q.lead_yr, q.rms, color=c.MUTED, lw=1.1, label=('31237 (from 31205)' if c.UNITS == 'tile' else '%d (first generation, tile units)' % c.PREV_GMFWD_5YR_JOB))
        ax.set_yscale('log')
        ax.set_title('%s  RMS [dJ %s]' % (v, units[v]), fontsize=9)
    for ax in axs[1]:
        ax.set_xlabel('lead [yr]')
    if prev is not None:
        axs[0, 0].legend(loc='lower right')
    save(fig, 'ref_rms_vs_lead')


@figure
def ref_adxx_maps():
    z = adxx('REF')
    g = c.grid()
    panels = [('adxx_theta', 'Theta₀, col. sum', 'dJ/K'), ('adxx_salt', 'Salt₀, col. sum', 'dJ/(g/kg)'),
              ('adxx_diffkr', 'κ_v, col. sum', 'dJ/(m²/s)'), ('adxx_qnet', 'Qnet', 'dJ/(W/m²)'),
              ('adxx_qsw', 'Qsw', 'dJ/(W/m²)'), ('adxx_empmr', 'E−P−R', 'dJ/(kg/m²/s)'),
              ('adxx_fu', 'zonal stress', 'dJ/(N/m²)'), ('adxx_fv', 'meridional stress', 'dJ/(N/m²)')]
    fig, axs = plt.subplots(1, 8, figsize=(13.5, 5.6), sharey=True)
    for ax, (v, t, u) in zip(axs, panels):
        a = z[v]
        m = c.mask(v)
        f = np.where(m.any(axis=0), np.where(m, a, 0).sum(axis=0), np.nan) if a.ndim == 3 else np.where(m, a, np.nan)
        map_panel(ax, f, t, units=u)
    axs[0].set_ylabel('latitude [°]')
    fig.suptitle('Control gradients of J over the 5-yr window, reference adjoint (the %s cost section in black)' % c.SEC_NAME, fontsize=10.5, y=0.99)
    save(fig, 'ref_adxx_maps')


@figure
def ref_ADJtheta_depth_lead():
    z = fields('REF')
    depths = [100, 500, 1500]
    leads = [30.0 / 366, 1.0, 5.0]
    lead_lab = {leads[0]: '30 d', 1.0: '1 yr', 5.0: '5 yr'}
    fig, axs = plt.subplots(len(depths), len(leads), figsize=(7.2, 10.5), sharex=True, sharey=True)
    m = c.mask('ADJtheta')
    for i, dpt in enumerate(depths):
        k = klev(dpt)
        for j, L in enumerate(leads):
            f = np.where(m[k], z['ADJtheta_L%.3f' % L][k], np.nan)
            map_panel(axs[i, j], f, 'ADJtheta, %d m, lead %s' % (round(-c.grid()['RC'][k]), lead_lab[L]), units='dJ/K')
    fig.subplots_adjust(hspace=0.36)
    save(fig, 'ref_ADJtheta_depth_lead')


@figure
def ref_ADJtheta_depth_lead_wide():
    """The same nine maps in one row, grouped by lead, for a 16:9 slide (2026-09-16): the 3x3 figure above is
    portrait and filled a third of the slide's width. One colour scale per map (its own 99th percentile, printed
    under it), so a single colourbar runs from -1 to +1 of that amplitude."""
    z = fields('REF')
    g = c.grid()
    depths = [100, 500, 1500]
    leads = [(30.0 / 366, '30 days before the end'), (1.0, '1 year before'), (5.0, '5 years before')]
    m = c.mask('ADJtheta')
    fig = plt.figure(figsize=(12.4, 4.3))
    gs = fig.add_gridspec(1, 12, width_ratios=[1, 1, 1, 0.22, 1, 1, 1, 0.22, 1, 1, 1, 0.12], wspace=0.08)
    col = 0
    for n, (L, lab) in enumerate(leads):
        axs = []
        for i, dpt in enumerate(depths):
            k = klev(dpt)
            ax = fig.add_subplot(gs[col])
            col += 1
            f = np.where(m[k], z['ADJtheta_L%.3f' % L][k], np.nan)
            vm = c.robust_sym(f)
            pm = ax.pcolormesh(g['XC'], g['YC'], np.ma.masked_invalid(f) / vm, cmap=c.diverging_cmap(), vmin=-1,
                               vmax=1, shading='auto', rasterized=True)
            section_line(ax)
            ax.set_title('%d m' % round(-g['RC'][k]), fontsize=9)
            ax.text(0.5, -0.035, '±%.1e' % vm, transform=ax.transAxes, ha='center', va='top', fontsize=7.5,
                    color=c.INK2)
            ax.set_xticks([-40, -20, 0])
            ax.tick_params(labelsize=7, labelbottom=False)
            ax.set_yticks([-60, -30, 0, 30, 60])
            if n or i:
                ax.tick_params(labelleft=False)
            ax.grid(False)
            axs.append(ax)
        col += 1
        bb0, bb1 = axs[0].get_position(), axs[-1].get_position()
        fig.text((bb0.x0 + bb1.x1) / 2, bb0.y1 + 0.085, lab, ha='center', va='bottom', fontsize=10.5, color=c.INK,
                 weight='bold')
    cax = fig.add_subplot(gs[-1])
    cb = fig.colorbar(pm, cax=cax, ticks=[-1, 0, 1])
    cb.set_label('dJ/dθ as a fraction of the amplitude under each map (dJ/K)', fontsize=8)
    cb.ax.tick_params(labelsize=7.5)
    save(fig, 'ref_ADJtheta_depth_lead_wide')


@figure
def ref_ADJtheta_zonal_section():
    z = fields('REF')
    g = c.grid()
    wet = g['wetC']
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.4), sharey=True)
    for ax, (L, lab) in zip(axs, [(30.0 / 366, '30 d'), (1.0, '1 yr'), (5.0, '5 yr')]):
        f = z['ADJtheta_L%.3f' % L]
        zm = np.where(wet.sum(axis=2) > 0, np.nansum(np.where(wet, f, 0), axis=2), np.nan)
        cbar_scaled(fig, lambda f, vm: ax.pcolormesh(g['lat'], -g['RC'], np.ma.masked_invalid(f), cmap=c.diverging_cmap(),
                                                      vmin=-vm, vmax=vm, shading='auto'), ax, zm, 'dJ/K')
        ax.axvline(g['lat'][c.JSEC], color=c.INK, lw=0.8)
        ax.set_title('zonal sum of ADJtheta, lead %s' % lab, fontsize=9.5)
        ax.set_xlabel('latitude [°]')
        ax.grid(False)
    axs[0].invert_yaxis()
    axs[0].set_ylabel('depth [m]')
    save(fig, 'ref_ADJtheta_zonal_section')


@figure
def ref_vs_previous():
    if c.PREV_GMFWD_5YR_JOB is None:
        print('ref_vs_previous: no earlier adjoint of this cost section; skipped')
        return
    mm = pd.read_csv(c.CACHE / 'member_metrics.csv')
    p = mm[mm.run == 'prev31237']
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.2), sharex=True)
    for v, col in zip(['ADJtheta', 'ADJdiffkr', 'ADJqnet'], [c.SERIES[0], c.SERIES[1], c.SERIES[2]]):
        s = p[p['var'] == v].sort_values('lead_yr')
        axs[0].plot(s.lead_yr, s['corr'], color=col, label=v)
        axs[1].plot(s.lead_yr, s['rms_ratio'], color=col, label=v)
    axs[0].set_title('pattern correlation, %d against the reference' % c.PREV_GMFWD_5YR_JOB, fontsize=9.5)
    axs[1].set_title('RMS ratio, %d / reference' % c.PREV_GMFWD_5YR_JOB, fontsize=9.5)
    axs[1].axhline(1, color=c.AXIS_C, lw=0.8)
    for a in axs:
        a.set_xlabel('lead [yr]')
    axs[0].legend(loc='lower left')
    save(fig, 'ref_vs_previous')


# ------------------------------------------------------------------ finite differences
def parent_stats(name):
    """A stats file of the campaign this one is compared with, c.CMP_CAMPAIGN (None when there is none): a
    first-generation section with the 26 N campaign of September whose legs it reuses, a second-generation one with
    the 26 N campaign of its own generation; the September campaign itself with the 2026-09-11 test."""
    par = c.CMP_CAMPAIGN
    p = c.OUTPUTS / 'analysis' / par / 'stats' / name if par else None
    return pd.read_csv(p) if p and p.exists() else None


def parent_stats_of(campaign, name):
    p = c.OUTPUTS / 'analysis' / campaign / 'stats' / name
    return pd.read_csv(p) if p.exists() else None


def cmp_ref_job():
    """The reference adjoint of the comparison campaign, from its job map."""
    return next(j for j, role, _ in c._job_map(c.CMP_CAMPAIGN) if role.startswith('reference adjoint'))


@figure
def fd_checks():
    df = pd.read_csv(c.STATS / 'fd_checks.csv')
    sigma = json.loads((c.STATS / 'noise_floor.json').read_text())['jproxy']['std_monthly']
    # the kappa_v check and the Theta boxes, in the order of the file; a check without signal (below) is drawn
    # hollow with its sigma counts instead of a ratio
    rows = df[~df.test.str.contains('everywhere')].reset_index(drop=True)
    names = [t.replace('Theta +%g K, ' % a, 'Theta, ') if t.startswith('Theta') else t
             for t, a in zip(rows.test, [float(t.split('+')[1].split(' ')[0]) if t.startswith('Theta') else 0 for t in rows.test])]
    ratio = (rows.adjoint / rows.fd_central).values
    # a check has signal when its central difference clears the noise floor and its two one-sided differences agree
    # (one_sided_spread < 1: |fd_plus - fd_minus| below |fd_central|); deepN at 43 N fails both, fv and qnet the second
    signal = ((np.abs(rows.fd_central) >= sigma) & (rows.one_sided_spread < 1.0)).values
    par = parent_stats('fd_checks.csv')
    if par is not None:        # the same checks of the parent campaign (26 N section, 2026-09): its own adjoint/FD, by test name
        pr = par.set_index('test')
        prev = [float(pr.adjoint[t] / pr.fd_central[t]) if t in pr.index else np.nan for t in rows.test]
        prev_label = '%s: adjoint %d vs FD, same legs' % (c.CMP_LABEL, cmp_ref_job())
    else:
        prev_map = {  # 2026-09-11 GM test (fd_summary.md): adjoint 31237 against finite differences of the GM model
            'kappa': -2.4511e3 / -2.0012e3, '40-50 N': -4.4259e-3 / -5.5797e-3, '0-10 N': 5.0309e-3 / 4.8365e-3, '40-60 S': 3.7552e-3 / 2.5825e-3}
        prev = [next((v for k, v in prev_map.items() if k in t), np.nan) for t in rows.test]
        prev_label = '2026-09-11: adjoint 31237 vs FD, from 31205'
    y = np.arange(len(rows))[::-1]
    fig, ax = plt.subplots(figsize=(7.5, 0.55 * len(rows) + 0.8))
    ax.axvline(1.0, color=c.AXIS_C, lw=1)
    ax.plot(prev, y, 'o', color=c.SERIES[1], ms=7, mec=c.SURFACE, mew=1.5, label=prev_label)
    ax.plot(np.where(signal, ratio, np.nan), y, 'o', color=c.SERIES[0], ms=8, mec=c.SURFACE, mew=1.5,
            label='this campaign (%s section): reference adjoint vs FD, from the reference leg %d' % (c.SEC_NAME, c.LEG_JOB['REF']))
    ax.plot(np.where(signal, np.nan, 1.0), y, 'o', color=c.SURFACE, ms=8, mec=c.SERIES[0], mew=1.5,
            label='no signal: the measured response is at the noise floor, or its two one-sided differences disagree')
    for yy, v, ok, fdc, adj in zip(y, ratio, signal, rows.fd_central, rows.adjoint):
        if ok:
            ax.annotate('%+.0f %%' % (100 * (v - 1)), (v, yy), xytext=(0, 7), textcoords='offset points', ha='center', fontsize=8, color=c.INK2)
        else:
            ax.annotate('FD %.1f σ, adjoint %.1f σ' % (fdc / sigma, adj / sigma), (1.0, yy), xytext=(0, 7),
                        textcoords='offset points', ha='center', fontsize=8, color=c.INK2)
    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=8.5)
    ax.set_xlabel('adjoint prediction / central finite difference')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.22 - 0.4 / len(rows)), ncol=1, fontsize=8)
    save(fig, 'fd_checks')


@figure
def fd_forcing():
    df = pd.read_csv(c.STATS / 'fd_checks.csv')
    f = df[df.test.str.contains('everywhere')].reset_index(drop=True)
    y = np.arange(len(f))[::-1]
    fig, ax = plt.subplots(figsize=(7.5, 2.8))
    ax.axvline(0, color=c.AXIS_C, lw=0.8)
    lim = 1.15 * max(np.abs(f.fd_central).max(), np.abs(f.adjoint).max())
    for yy, (_, r) in zip(y, f.iterrows()):
        ax.plot([r.fd_central, r.adjoint], [yy, yy], color=c.AXIS_C, lw=1.2, zorder=1)
    ax.plot(f.fd_central, y, 'o', color=c.INK, ms=7, mec=c.SURFACE, mew=1.5, label='central finite difference')
    ax.plot(f.adjoint, y, 'o', color=c.SERIES[0], ms=7, mec=c.SURFACE, mew=1.5, label='adjoint prediction')
    ax.set_xscale('symlog', linthresh=max(1e-5, 0.02 * lim))
    ax.set_yticks(y)
    ax.set_yticklabels([t.replace(' everywhere', '') for t in f.test], fontsize=8)
    ax.set_xlabel('ΔJ for the perturbation')
    ax.legend(fontsize=8, loc='upper center', bbox_to_anchor=(0.5, -0.3), ncol=2)
    save(fig, 'fd_forcing')


# ------------------------------------------------------------------ ensemble
@figure
def fc_vs_kappa():
    fg = pd.read_csv(c.STATS / 'fc_gradient.csv')
    old = json.loads((c.STATS / 'previous_campaigns.json').read_text())
    nf = json.loads((c.STATS / 'noise_floor.json').read_text())
    sig = nf['jproxy']['std_monthly']
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ref = float(fg[fg.run == 'REF'].fc.iloc[0])
    par = parent_stats('fc_gradient.csv')
    earlier = [('2026-09-10 (GM-free adjoint, legs from 30983)', old['gmFree_ReMax2_2026_09_10']['factor'], old['gmFree_ReMax2_2026_09_10']['fc'], c.SERIES[1]),
               ('2026-08 (2x viscosity, GM-free adjoint)', old['visc2x_2026_08']['factor'], old['visc2x_2026_08']['fc'], c.SERIES[2])]
    if par is None:
        series = [('this campaign (GM/Redi in the forward sweep, legs from the new spin-up)', fg.factor, fg.fc, c.SERIES[0])] + earlier
        for lab, x, yv, col in series:
            o = np.argsort(x)
            ax.plot(np.array(x)[o], np.array(yv)[o], '-o', color=col, ms=5, mec=c.SURFACE, mew=1.5, label=lab)
        ax.set_ylabel('J (fc) over the 5-yr window [%s]' % c.J_UNIT)
        ax.legend(loc='upper center', fontsize=8)
    elif c.UNITS != 'Sv' or not c.CMP_SAME_UNITS:
        # this campaign measures another section than every earlier one, so the earlier curves go on a second
        # axis: their shape against kappa_v is what is compared, not their level
        o = np.argsort(fg.factor.values)
        ax.plot(fg.factor.values[o], fg.fc.values[o], '-o', color=c.SERIES[0], ms=6, mec=c.SURFACE, mew=1.5,
                label='this campaign: the %s section (left axis)' % c.SEC_NAME)
        ax.set_ylabel('J at %s (fc) over the 5-yr window [%s]' % (c.SEC_NAME, c.J_UNIT), color=c.SERIES[0])
        ax2 = ax.twinx()
        ax2.grid(False)
        ax2.spines['right'].set_visible(True)
        for lab, x, yv, col in [('2026-09 campaign: the 26 N section, same legs', par.factor, par.fc, c.SERIES[1])] + \
                               [(e[0] + ', 26 N', e[1], e[2], e[3]) for e in earlier]:
            oo = np.argsort(np.array(x))
            ax2.plot(np.array(x)[oo], np.array(yv)[oo], '--o', color=col, ms=4, mec=c.SURFACE, mew=1.2, lw=1.1,
                     alpha=0.85, label=lab + ' (right axis)')
        ax2.set_ylabel('J at 26 N, the earlier campaigns [tile units]', color=c.SERIES[1])
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc='upper center', fontsize=7.5)
    else:
        # second generation: this section and the 26 N section of the same generation share the left axis (Sverdrups,
        # 848 m); the earlier 26 N campaigns, in the cost's first form and to 982 m, keep the right axis, where only
        # their shape against kappa_v is compared
        old26 = parent_stats_of('kappa_v_ensemble_gmFwd', 'fc_gradient.csv')
        for lab, d, col, ms in [('%s, this campaign' % c.SEC_NAME, fg, c.SERIES[0], 6),
                                ('26 N, Sv, 848 m, same legs', par, c.INK, 5)]:
            o = np.argsort(d.factor.values)
            ax.plot(d.factor.values[o], d.fc.values[o], '-o', color=col, ms=ms, mec=c.SURFACE, mew=1.5, label=lab + ' (left)')
        ax.set_ylabel('J over the 5-yr window [Sv]')
        ax2 = ax.twinx()
        ax2.grid(False)
        ax2.spines['right'].set_visible(True)
        rows = ([('2026-09, same legs', old26.factor, old26.fc, c.SERIES[1])] if old26 is not None else []) + \
               [('2026-09-10, GM-free adjoint', earlier[0][1], earlier[0][2], c.MUTED),
                ('2026-08, 2x viscosity', earlier[1][1], earlier[1][2], earlier[1][3])]
        for lab, x, yv, col in rows:
            oo = np.argsort(np.array(x))
            ax2.plot(np.array(x)[oo], np.array(yv)[oo], '--o', color=col, ms=4, mec=c.SURFACE, mew=1.2, lw=1.1,
                     alpha=0.85, label=lab + ', 26 N, earlier form (right)')
        ax2.set_ylabel('J at 26 N to 982 m, earlier form [tile units]', color=c.MUTED)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc='upper center', bbox_to_anchor=(0.5, -0.17), ncol=2, fontsize=7.5,
                  columnspacing=1.2, handlelength=1.8)
    ax.set_xscale('log', base=2)
    xs = sorted(c.FACTOR.values())
    ax.set_xticks(xs)
    ax.set_xticklabels(['%g' % v for v in xs])
    ax.set_xlabel('κ_v / 1.2e-5')
    save(fig, 'fc_vs_kappa')


@figure
def member_stability():
    ts = pd.read_csv(c.CACHE / 'adj_timeseries.csv')
    fig, axs = plt.subplots(2, 4, figsize=(11, 5.0), sharex=True, sharey=True)
    ref = ts[(ts.run == 'REF') & (ts['var'] == 'ADJtheta')].sort_values('lead_yr')
    for ax, r in zip(axs.ravel(), c.MEMBERS + ['REF']):
        s = ts[(ts.run == r) & (ts['var'] == 'ADJtheta')].sort_values('lead_yr')
        ax.plot(ref.lead_yr, ref.rms, color=c.AXIS_C, lw=1.2)
        if r != 'REF':
            ax.plot(s.lead_yr, s.rms, color=c.SERIES[0], lw=1.5)
            bad = s[(s.finite_frac < 1)]
            if len(bad):
                ax.axvline(bad.lead_yr.min(), color=c.SERIES[1], lw=1)
        else:
            ax.plot(s.lead_yr, s.rms, color=c.INK, lw=1.5)
        ax.set_yscale('log')
        ax.set_title(c.LABEL[r], fontsize=9.5)
    for ax in axs[1]:
        ax.set_xlabel('lead [yr]')
    axs[0, 0].set_ylabel('RMS ADJtheta [dJ/K]')
    axs[1, 0].set_ylabel('RMS ADJtheta [dJ/K]')
    fig.suptitle('Does each member\'s adjoint stay bounded? (grey: the reference in every panel)', fontsize=10.5, y=1.0)
    save(fig, 'member_stability')


@figure
def member_pattern_corr():
    mm = pd.read_csv(c.CACHE / 'member_metrics.csv')
    vars_ = ['ADJtheta', 'ADJdiffkr', 'ADJqnet', 'ADJtaux']
    fig, axs = plt.subplots(1, len(vars_), figsize=(11, 3.2), sharey=True)
    for ax, v in zip(axs, vars_):
        piv = mm[(mm['var'] == v) & mm.run.isin(c.MEMBERS)].pivot(index='run', columns='lead_yr', values='corr').reindex(c.MEMBERS)
        pm = ax.pcolormesh(piv.columns.values, np.arange(len(c.MEMBERS)), piv.values, cmap=c.sequential_cmap(),
                           vmin=0, vmax=1, shading='auto')
        ax.set_title(v, fontsize=9.5)
        ax.set_xlabel('lead [yr]')
        ax.grid(False)
    axs[0].set_yticks(range(len(c.MEMBERS)))
    axs[0].set_yticklabels(['%s %gx' % (r, c.FACTOR[r]) for r in c.MEMBERS])
    cb = fig.colorbar(pm, ax=axs, pad=0.01, fraction=0.02)
    cb.set_label('pattern correlation with the reference')
    save(fig, 'member_pattern_corr')


@figure
def kappa_gradient():
    fg = pd.read_csv(c.STATS / 'fc_gradient.csv').sort_values('factor')
    fd = pd.read_csv(c.STATS / 'fd_checks.csv')
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.axhline(0, color=c.AXIS_C, lw=0.8)
    ax.plot(fg.factor, fg.G_dJdkappa_uniform, '-o', color=c.SERIES[0], ms=5, mec=c.SURFACE, mew=1.5,
            label='adjoint, each run: Σ adxx_diffkr (this campaign)')
    k = fg.kappa.values
    sec = np.diff(fg.fc.values) / np.diff(k)
    xm = np.sqrt(fg.factor.values[:-1] * fg.factor.values[1:])
    ax.plot(xm, sec, 's', color=c.SERIES[1], ms=6, mec=c.SURFACE, mew=1.5, label='secant of J between neighbouring members (includes the 10-yr adjustment)')
    kap = fd[fd.test.str.startswith('kappa')]
    if len(kap):
        ax.plot([1.0], [kap.fd_central.iloc[0] / (0.1 * c.KAPPA0)], 'D', color=c.INK, ms=6, mec=c.SURFACE, mew=1.5,
                label='central finite difference, κ_v ±10 % at the reference')
    ax.set_xscale('log', base=2)
    ax.set_yscale('symlog', linthresh=300 * c.J_SCALE)
    ax.set_ylim(-2.5e4 * c.J_SCALE, 3e3 * c.J_SCALE)   # the limits were set for the first generation's units
    xs = sorted(c.FACTOR.values())
    ax.set_xticks(xs)
    ax.set_xticklabels(['%g' % v for v in xs])
    ax.set_xlabel('κ_v / 1.2e-5')
    ax.set_ylabel('dJ/dκ_v [per m²/s]')
    ax.legend(fontsize=7.5, loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=1)
    save(fig, 'kappa_gradient')


@figure
def dJ_decomposition():
    d = pd.read_csv(c.STATS / 'dJ_decomposition.csv')
    nf = json.loads((c.STATS / 'noise_floor.json').read_text())
    sig = nf['jproxy']['std_monthly']
    x = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.axhline(0, color=c.AXIS_C, lw=0.8)
    ax.plot(x, d.dJ_measured, 'o', color=c.INK, ms=7, mec=c.SURFACE, mew=1.5, label='measured ΔJ = J(member) − J(reference)')
    ax.plot(x, d.dJ_kappa_refgrad, 's', color=c.SERIES[0], ms=6, mec=c.SURFACE, mew=1.5, label='adjoint: reference gradient × Δκ_v')
    ax.plot(x, d.dJ_predicted_refgrad_plus_state, '^', color=c.SERIES[1], ms=6, mec=c.SURFACE, mew=1.5,
            label='adjoint: κ_v term + year-180 Theta/Salt change term')
    ax.set_xticks(x)
    ax.set_xticklabels(['%s %gx' % (r, f) for r, f in zip(d.run, d.factor)], fontsize=8)
    ax.set_yscale('symlog', linthresh=0.02 * c.J_SCALE)
    cols = ['dJ_measured', 'dJ_kappa_refgrad', 'dJ_predicted_refgrad_plus_state']
    ax.set_ylim(1.6 * float(d[cols].min().min()), 1.6 * float(d[cols].max().max()))
    ax.set_ylabel('ΔJ')
    ax.legend(fontsize=7.5, loc='upper center', bbox_to_anchor=(0.5, -0.16), ncol=1)
    save(fig, 'dJ_decomposition')


@figure
def member_adxx_maps():
    g = c.grid()
    runs = ['M2', 'REF', 'M3', 'M5', 'M7']
    vars_ = [('adxx_diffkr', '∂J/∂κ_v, column sum'), ('adxx_qnet', '∂J/∂Qnet')]
    fig, axs = plt.subplots(len(vars_), len(runs), figsize=(10.5, 9.5), sharex=True, sharey=True)
    for i, (v, t) in enumerate(vars_):
        ref = adxx('REF')[v]
        m = c.mask(v)
        col = lambda a: np.where(m.any(axis=0), np.where(m, a, 0).sum(axis=0), np.nan) if a.ndim == 3 else np.where(m, a, np.nan)
        vmax = c.robust_sym(col(ref))
        for j, r in enumerate(runs):
            z = adxx(r)
            if z is None:
                axs[i, j].set_visible(False)
                continue
            map_panel(axs[i, j], col(z[v]), c.LABEL[r] if i == 0 else '', vmax=vmax)
        axs[i, 0].set_ylabel(t, fontsize=9)
    save(fig, 'member_adxx_maps')


@figure
def control_ranking():
    rk = pd.read_csv(c.STATS / 'control_ranking.csv').iloc[::-1]
    y = np.arange(len(rk))
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.axvline(1, color=c.AXIS_C, lw=1)
    ax.axvline(2, color=c.AXIS_C, lw=1)
    ax.plot(rk.dJ_signmatched_over_sigma, y, 'o', color=c.SERIES[0], ms=7, mec=c.SURFACE, mew=1.5,
            label='largest response: perturbation of that size at every cell, sign-matched')
    ax.plot(rk.dJ_uniform_over_sigma, y, 'o', mfc=c.SURFACE, mec=c.SERIES[1], mew=1.6, ms=7,
            label='uniform perturbation of that size')
    ax.set_xscale('log')
    ax.set_yticks(y)
    ax.set_yticklabels(['%s (%g %s)' % (w.split(' (')[0], s, u) for w, s, u in zip(rk.what, rk.scale, rk.unit)], fontsize=8)
    ax.set_xlabel('|ΔJ| / σ(J), internal variability of the monthly cost')
    ax.legend(fontsize=7.5, loc='upper center', bbox_to_anchor=(0.45, -0.2))
    save(fig, 'control_ranking')


# ------------------------------------------------------------------ surrogate target structure
@figure
def target_structure():
    ld = pd.read_csv(c.CACHE / 'lead_decorrelation.csv')
    ts = json.loads((c.STATS / 'target_structure.json').read_text())
    fig = plt.figure(figsize=(11, 3.4))
    ax = fig.add_axes([0.06, 0.16, 0.36, 0.72])
    for v, col in (('ADJdiffkr', c.SERIES[0]), ('ADJtheta', c.SERIES[1])):
        q = ld[ld['var'] == v].sort_values('lead_yr')
        ax.plot(q.lead_yr, q.corr_with_5yr, color=col, lw=1.6, label=v)
    ax.set_ylim(-0.1, 1.02)
    ax.legend(loc='upper left', fontsize=8)
    ax.set_xlabel('lead [yr]')
    ax.set_title('pattern correlation with the same field at 5-yr lead', fontsize=9.5)
    ax2 = fig.add_axes([0.60, 0.16, 0.37, 0.72])
    lp = ts['local_predictors']
    names = list(lp)
    vals = [lp[n].get('spearman_abs_within_levels', lp[n].get('spearman_abs', np.nan)) for n in names]
    y = np.arange(len(names))[::-1]
    ax2.axvline(0, color=c.AXIS_C, lw=0.8)
    ax2.barh(y, vals, height=0.42, color=c.SERIES[0])
    for yy, v in zip(y, vals):
        ax2.annotate('%.2f' % v, (v, yy), xytext=(4 if v >= 0 else -4, 0), textcoords='offset points',
                     ha='left' if v >= 0 else 'right', va='center', fontsize=8, color=c.INK2)
    ax2.set_yticks(y)
    short = {'|dT/dz|': '|∂T/∂z|', '|dS/dz|': '|∂S/∂z|', '|drho/dz| (N^2 proxy)': '|∂ρ/∂z|',
             'adjoint identity (window-mean state)': 'adjoint identity'}
    ax2.set_yticklabels([short.get(n, n) for n in names], fontsize=8.5)
    ax2.set_xlim(min(0, min(vals) - 0.1), 1.0)
    ax2.set_xlabel('rank correlation with |∂J/∂κ_v| within levels (mean of the upper 25)')
    ax2.set_title('what predicts the target locally?', fontsize=9.5)
    save(fig, 'target_structure')


@figure
def identity_map():
    g = c.grid()
    t = adxx('REF')['adxx_diffkr']
    i = np.load(c.CACHE / 'identity_REF.npz')['identity']
    m = c.mask('adxx_diffkr')
    col = lambda a: np.where(m.any(axis=0), np.where(m, a, 0).sum(axis=0), np.nan)
    fig, axs = plt.subplots(1, 2, figsize=(5.6, 5.6), sharey=True)
    vm = c.robust_sym(col(t))
    map_panel(axs[0], col(t), 'adxx_diffkr (adjoint)', vmax=vm, units='dJ/(m²/s)')
    map_panel(axs[1], col(i), '−Σ ∂zλ·∂z(T,S) Δt', vmax=c.robust_sym(col(i)), units='dJ/(m²/s)')
    axs[0].set_ylabel('latitude [°]')
    save(fig, 'identity_map')


# ------------------------------------------------------------------ animations
def gif(frames, path, ms=110):
    pal = [f.convert('P', palette=Image.ADAPTIVE, colors=160) for f in frames]
    pal[0].save(path, save_all=True, append_images=pal[1:], duration=ms, loop=0, optimize=True)
    frames[-1].save(str(path)[:-4] + '_still.png')      # the last frame (longest lead), for reduced motion
    print('wrote', path, '%.1f MB' % (Path(path).stat().st_size / 1e6))


def render(fig, dpi=78):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, facecolor=c.SURFACE)
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert('RGB')


@figure
def anim_ref_ADJtheta():
    g = c.grid()
    d = c.run_dir(c.PREV_GMFWD_5YR_JOB if DEV else c.ADJ_JOB['REF'])
    ts = pd.read_csv(c.CACHE / 'adj_timeseries.csv')
    ts = ts[(ts.run == 'REF') & (ts['var'] == 'ADJtheta')].sort_values('lead_yr')
    ks = [klev(300), klev(1500)]
    m = c.mask('ADJtheta')
    iters = c.ITERS[::-4]          # every 20 d, lead increasing
    frames = []
    for it in iters:
        a = c.read_mds(d / ('ADJtheta.%010d' % it), np.float32)
        fig = plt.figure(figsize=(7.6, 5.4))
        for n, k in enumerate(ks):
            ax = fig.add_axes([0.05 + n * 0.3, 0.1, 0.25, 0.78])
            f = np.where(m[k], a[k], np.nan)
            vm = c.robust_sym(f)
            ax.pcolormesh(g['XC'], g['YC'], np.ma.masked_invalid(f / vm), cmap=c.diverging_cmap(), vmin=-1, vmax=1, shading='auto')
            section_line(ax)
            ax.set_title('ADJtheta at %d m' % round(-g['RC'][k]), fontsize=9.5)
            ax.grid(False)
            ax.tick_params(labelsize=7)
        ax = fig.add_axes([0.7, 0.55, 0.27, 0.3])
        ax.plot(ts.lead_yr, ts.rms, color=c.SERIES[0], lw=1.3)
        L = float(c.lead_years(it))
        ax.plot([L], [np.interp(L, ts.lead_yr, ts.rms)], 'o', color=c.INK, ms=5)
        ax.set_yscale('log')
        ax.set_title('RMS ADJtheta [dJ/K]', fontsize=8.5)
        ax.set_xlabel('lead [yr]', fontsize=8)
        ax.tick_params(labelsize=7)
        fig.text(0.7, 0.4, 'lead %.2f yr\n(%d d before the\nend of the window)' % (L, round(L * 366)), fontsize=10, color=c.INK)
        fig.text(0.7, 0.14, 'Each map is scaled by its own\n99th percentile of |ADJtheta|;\nthe panel above gives the amplitude.',
                 fontsize=7.5, color=c.INK2)
        frames.append(render(fig))
    gif(frames, c.ANIMS / 'ref_ADJtheta_lead.gif')


@figure
def anim_members_ADJdiffkr():
    g = c.grid()
    m = c.mask('ADJdiffkr')
    runs = c.RUN_ORDER
    dirs = {r: c.run_dir(c.ADJ_JOB[r]) for r in runs}
    iters = c.ITERS[::-6]          # every 30 d
    frames = []
    for it in iters:
        fig = plt.figure(figsize=(10.4, 4.6))
        for n, r in enumerate(runs):
            ax = fig.add_axes([0.02 + n * 0.122, 0.08, 0.11, 0.78])
            a = c.read_mds(dirs[r] / ('ADJdiffkr.%010d' % it), np.float32)
            f = np.where(m.any(axis=0), np.where(m, a, 0).sum(axis=0), np.nan)
            vm = c.robust_sym(f)
            ax.pcolormesh(g['XC'], g['YC'], np.ma.masked_invalid(f / vm), cmap=c.diverging_cmap(), vmin=-1, vmax=1, shading='auto')
            section_line(ax)
            ax.set_title(c.LABEL[r], fontsize=8.5)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
        L = float(c.lead_years(it))
        fig.text(0.02, 0.93, 'Column sum of ADJdiffkr, each panel scaled by its own 99th percentile · lead %.2f yr' % L, fontsize=10, color=c.INK)
        frames.append(render(fig, dpi=72))
    gif(frames, c.ANIMS / 'members_ADJdiffkr_lead.gif', ms=160)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dev', action='store_true')
    ap.add_argument('names', nargs='+')
    a = ap.parse_args()
    c.setup_style()
    c.ensure_dirs()
    if a.dev:
        DEV = True
        c.CACHE = c.ANALYSIS / 'dev_cache'
        c.STATS = c.ANALYSIS / 'dev_stats'
        c.FIGS = c.ANALYSIS / 'dev_figures'
        c.ANIMS = c.ANALYSIS / 'dev_figures'
        c.FIGS.mkdir(parents=True, exist_ok=True)
    names = list(FIG) if a.names == ['all'] else a.names
    for n in names:
        try:
            FIG[n]()
        except Exception as e:      # a figure whose inputs are not there yet is skipped, loudly
            print('SKIPPED %s: %s: %s' % (n, type(e).__name__, e))
