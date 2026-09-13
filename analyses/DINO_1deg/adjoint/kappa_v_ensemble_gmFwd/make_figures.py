#!/usr/bin/env python3
"""Figures (PNG) and animations (GIF) of the campaign, from the products of forward_state.py and
adjoint_products.py, into analysis/<campaign>/figures/ and animations/.

    python make_figures.py [--dev] all | <name> [<name> ...]

Conventions: signed sensitivities on a diverging map (cmocean balance, symmetric robust limits),
land grey, the 26 N cost section drawn in ink; ADJ* dumps are shown in the order the adjoint
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
        cb = ax.figure.colorbar(pm, ax=ax, orientation='horizontal', pad=0.07, fraction=0.05, aspect=16)
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
    last = df[(df.run != 'spinup31203') & (df.iter > c.NITER0 - c.STEPS_PER_YEAR)]
    m = last.groupby('run')[['jproxy', 'amoc26', 'Tmean']].mean().reindex(c.RUN_ORDER)
    x = [c.FACTOR[r] for r in c.RUN_ORDER]
    fig, axs = plt.subplots(1, 3, figsize=(10.5, 3.1))
    for ax, k, lab in zip(axs, ['jproxy', 'amoc26', 'Tmean'],
                          ['cost proxy J at 26 N (last year of the leg)', 'overturning max above 1000 m at 26 N [Sv]',
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
    for ax, k, lab in zip(axs, ['jproxy', 'amoc26'], ['cost proxy J (30.5-d means)', 'overturning at 26 N [Sv]']):
        for r in c.MEMBERS:
            s = df[df.run == r]
            ax.plot(s.year, s[k], color=c.AXIS_C, lw=0.9)
        for r, col in (('M1', c.SERIES[0]), ('M7', c.SERIES[1])):
            s = df[df.run == r]
            ax.plot(s.year, s[k], color=col, lw=1.4)
            ax.annotate('%s (%gx)' % (r, c.FACTOR[r]), (s.year.iloc[-1], s[k].iloc[-12:].mean()), xytext=(4, 0),
                        textcoords='offset points', fontsize=8, color=c.INK2, va='center')
        sp = df[df.run == 'spinup31203']
        ax.plot(sp.year, sp[k], color=c.INK, lw=1.2)
        s = df[df.run == 'REF']
        ax.plot(s.year, s[k], color=c.INK, lw=0.8, ls=(0, (1, 1.5)))
        ax.annotate('reference', (sp.year.iloc[-1], sp[k].iloc[-12:].mean()), xytext=(4, 0), textcoords='offset points',
                    fontsize=8, color=c.INK2, va='center')
        ax.set_title(lab, fontsize=9.5)
        ax.set_xlabel('model year')
        ax.set_xlim(170, 181.6)
    save(fig, 'leg_timeseries')


@figure
def leg_temperature_change():
    z = np.load(c.CACHE / 'leg_final_profiles.npz')
    g = c.grid()
    wet = g['wetC']
    depth = -g['RC']

    def hmean(t):
        return np.array([np.nansum(np.where(wet[k], t[k], 0) * g['RAC']) / (wet[k] * g['RAC']).sum()
                         if wet[k].any() else np.nan for k in range(len(depth))])

    ref = hmean(z['REF_T'])
    D = np.array([hmean(z[r + '_T']) - ref for r in c.MEMBERS])
    fig = plt.figure(figsize=(10.5, 3.9))
    ax = fig.add_axes([0.06, 0.14, 0.26, 0.74])
    vmax = c.robust_sym(D, 100)
    pm = ax.pcolormesh(np.arange(len(c.MEMBERS)), depth, D.T, cmap=c.diverging_cmap(), vmin=-vmax, vmax=vmax, shading='auto')
    ax.set_yscale('symlog', linthresh=200)
    ax.invert_yaxis()
    ax.set_xticks(range(len(c.MEMBERS)))
    ax.set_xticklabels(['%gx' % c.FACTOR[r] for r in c.MEMBERS], fontsize=8)
    ax.set_ylabel('depth [m]')
    ax.set_title('horizontal-mean ΔT vs reference, year 180 [K]', fontsize=9.5)
    ax.grid(False)
    fig.colorbar(pm, ax=ax, pad=0.02, fraction=0.06)
    for i, r in enumerate(['M1', 'M7']):
        a = fig.add_axes([0.42 + i * 0.29, 0.14, 0.24, 0.74])
        zm = lambda t: np.where(wet.sum(axis=2) > 0, np.nansum(np.where(wet, t, 0), axis=2) / np.maximum(wet.sum(axis=2), 1), np.nan)
        dz = zm(z[r + '_T']) - zm(z['REF_T'])
        vm = c.robust_sym(dz, 99.5)
        p2 = a.pcolormesh(g['lat'], depth, np.ma.masked_invalid(dz), cmap=c.diverging_cmap(), vmin=-vm, vmax=vm, shading='auto')
        a.invert_yaxis()
        a.set_xlabel('latitude [°]')
        a.set_title('zonal-mean ΔT, %s (%gx) − reference [K]' % (r, c.FACTOR[r]), fontsize=9.5)
        a.grid(False)
        fig.colorbar(p2, ax=a, pad=0.02, fraction=0.06)
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
        ax.plot(s.lead_yr, s.rms, color=c.SERIES[0], lw=1.6, label='reference (from 31203)')
        if prev is not None:
            q = prev[(prev.run == 'REF') & (prev['var'] == v)].sort_values('lead_yr')
            ax.plot(q.lead_yr, q.rms, color=c.MUTED, lw=1.1, label='31237 (from 31205)')
        ax.set_yscale('log')
        ax.set_title('%s  RMS [dJ %s]' % (v, units[v]), fontsize=9)
    for ax in axs[1]:
        ax.set_xlabel('lead before the end of the cost window [yr]')
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
    fig.suptitle('Control gradients of J over the 5-yr window, reference adjoint (the 26 N cost section in black)', fontsize=10.5, y=0.99)
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
    save(fig, 'ref_ADJtheta_depth_lead')


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
    mm = pd.read_csv(c.CACHE / 'member_metrics.csv')
    p = mm[mm.run == 'prev31237']
    fig, axs = plt.subplots(1, 2, figsize=(10.5, 3.2), sharex=True)
    for v, col in zip(['ADJtheta', 'ADJdiffkr', 'ADJqnet'], [c.SERIES[0], c.SERIES[1], c.SERIES[2]]):
        s = p[p['var'] == v].sort_values('lead_yr')
        axs[0].plot(s.lead_yr, s['corr'], color=col, label=v)
        axs[1].plot(s.lead_yr, s['rms_ratio'], color=col, label=v)
    axs[0].set_title('pattern correlation, 31237 against the reference', fontsize=9.5)
    axs[1].set_title('RMS ratio, 31237 / reference', fontsize=9.5)
    axs[1].axhline(1, color=c.AXIS_C, lw=0.8)
    for a in axs:
        a.set_xlabel('lead [yr]')
    axs[0].legend(loc='lower left')
    save(fig, 'ref_vs_previous')


# ------------------------------------------------------------------ finite differences
@figure
def fd_checks():
    df = pd.read_csv(c.STATS / 'fd_checks.csv')
    prev = {  # 2026-09-11 GM test (fd_summary.md): adjoint 31237 against finite differences of the GM model
        'kappa': -2.4511e3 / -2.0012e3, 'deepN': -4.4259e-3 / -5.5797e-3, 'midTrop': 5.0309e-3 / 4.8365e-3, 'soUpper': 3.7552e-3 / 2.5825e-3}
    names = ['kappa_v ±10 %', 'Theta, 40–50 N below 1500 m', 'Theta, 0–10 N 500–1500 m', 'Theta, 40–60 S 0–500 m']
    keys = ['kappa', 'deepN', 'midTrop', 'soUpper']
    new = (df.adjoint / df.fd_central).values
    y = np.arange(len(names))[::-1]
    fig, ax = plt.subplots(figsize=(7.5, 2.9))
    ax.axvline(1.0, color=c.AXIS_C, lw=1)
    ax.plot([prev[k] for k in keys], y, 'o', color=c.SERIES[1], ms=7, mec=c.SURFACE, mew=1.5,
            label='2026-09-11: adjoint 31237 vs FD, from 31205')
    ax.plot(new[:len(names)], y[:len(new)], 'o', color=c.SERIES[0], ms=8, mec=c.SURFACE, mew=1.5,
            label='this campaign: reference adjoint vs FD, from 31203')
    for yy, v in zip(y, new):
        ax.annotate('%+.0f %%' % (100 * (v - 1)), (v, yy), xytext=(0, 7), textcoords='offset points', ha='center', fontsize=8, color=c.INK2)
    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.set_xlabel('adjoint prediction / central finite difference')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.28), ncol=1)
    save(fig, 'fd_checks')


# ------------------------------------------------------------------ ensemble
@figure
def fc_vs_kappa():
    fg = pd.read_csv(c.STATS / 'fc_gradient.csv')
    old = json.loads((c.STATS / 'previous_campaigns.json').read_text())
    nf = json.loads((c.STATS / 'noise_floor.json').read_text())
    sig = nf['jproxy']['std_monthly']
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ref = float(fg[fg.run == 'REF'].fc.iloc[0])
    ax.axhspan(ref - 2 * sig, ref + 2 * sig, color=c.SERIES[0], alpha=0.10, lw=0)
    series = [('this campaign (GM forward sweep, from 31203)', fg.factor, fg.fc, c.SERIES[0]),
              ('2026-09-10 (GM-free adjoint, legs from 30983)', old['gmFree_ReMax2_2026_09_10']['factor'], old['gmFree_ReMax2_2026_09_10']['fc'], c.SERIES[1]),
              ('2026-08 (2x viscosity, GM-free adjoint)', old['visc2x_2026_08']['factor'], old['visc2x_2026_08']['fc'], c.SERIES[2])]
    for lab, x, yv, col in series:
        o = np.argsort(x)
        ax.plot(np.array(x)[o], np.array(yv)[o], '-o', color=col, ms=5, mec=c.SURFACE, mew=1.5, label=lab)
    ax.set_xscale('log', base=2)
    xs = sorted(c.FACTOR.values())
    ax.set_xticks(xs)
    ax.set_xticklabels(['%g' % v for v in xs])
    ax.set_xlabel('κ_v / 1.2e-5')
    ax.set_ylabel('J (fc) over the 5-yr window')
    ax.annotate('±2σ internal variability of J', (0.26, ref + 2 * sig), xytext=(2, 3), textcoords='offset points', fontsize=8, color=c.INK2)
    ax.legend(loc='upper center', fontsize=8)
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
    old = json.loads((c.STATS / 'previous_campaigns.json').read_text())
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
                label='central FD, κ_v ±10 % from 31203')
    o = old['gmFree_ReMax2_2026_09_10']
    ax.plot(o['factor'], o['G'], '-', color=c.MUTED, lw=1, label='adjoint, 2026-09-10 GM-free ensemble')
    ax.set_xscale('log', base=2)
    ax.set_yscale('symlog', linthresh=1e3)
    xs = sorted(c.FACTOR.values())
    ax.set_xticks(xs)
    ax.set_xticklabels(['%g' % v for v in xs])
    ax.set_xlabel('κ_v / 1.2e-5')
    ax.set_ylabel('dJ/dκ_v [per m²/s]')
    ax.legend(fontsize=7.5, loc='lower right')
    save(fig, 'kappa_gradient')


@figure
def dJ_decomposition():
    d = pd.read_csv(c.STATS / 'dJ_decomposition.csv')
    nf = json.loads((c.STATS / 'noise_floor.json').read_text())
    sig = nf['jproxy']['std_monthly']
    x = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.axhspan(-2 * sig, 2 * sig, color=c.MUTED, alpha=0.12, lw=0)
    ax.axhline(0, color=c.AXIS_C, lw=0.8)
    ax.plot(x, d.dJ_measured, 'o', color=c.INK, ms=7, mec=c.SURFACE, mew=1.5, label='measured ΔJ = J(member) − J(reference)')
    ax.plot(x, d.dJ_kappa_refgrad, 's', color=c.SERIES[0], ms=6, mec=c.SURFACE, mew=1.5, label='adjoint: reference gradient × Δκ_v')
    ax.plot(x, d.dJ_predicted_refgrad_plus_state, '^', color=c.SERIES[1], ms=6, mec=c.SURFACE, mew=1.5,
            label='adjoint: κ_v term + year-180 Theta/Salt change term')
    ax.set_xticks(x)
    ax.set_xticklabels(['%s %gx' % (r, f) for r, f in zip(d.run, d.factor)], fontsize=8)
    ax.set_yscale('symlog', linthresh=0.02)
    ax.set_ylabel('ΔJ')
    ax.legend(fontsize=7.5, loc='upper left')
    ax.annotate('±2σ', (len(d) - 0.6, 2 * sig), fontsize=8, color=c.INK2)
    save(fig, 'dJ_decomposition')


@figure
def member_adxx_maps():
    g = c.grid()
    runs = ['M2', 'REF', 'M3', 'M5', 'M7']
    vars_ = [('adxx_diffkr', 'κ_v (column sum)'), ('adxx_qnet', 'Qnet')]
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
            map_panel(axs[i, j], col(z[v]), '%s, %s' % (t, c.LABEL[r]), vmax=vmax)
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
        ax.plot(q.lead_yr, q.corr_with_5yr, color=col, lw=1.6)
        ax.annotate(v, (q.lead_yr.iloc[len(q) // 3], q.corr_with_5yr.iloc[len(q) // 3]), xytext=(4, 6),
                    textcoords='offset points', fontsize=8, color=c.INK2)
    ax.set_ylim(-0.1, 1.02)
    ax.set_xlabel('lead [yr]')
    ax.set_title('pattern correlation with the 5-yr accumulation', fontsize=9.5)
    ax2 = fig.add_axes([0.53, 0.16, 0.44, 0.72])
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
    ax2.set_yticklabels(names, fontsize=8.5)
    ax2.set_xlim(min(0, min(vals) - 0.1), 1.0)
    ax2.set_xlabel('rank correlation with |∂J/∂κ_v| within each level, mean over the upper 25')
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
