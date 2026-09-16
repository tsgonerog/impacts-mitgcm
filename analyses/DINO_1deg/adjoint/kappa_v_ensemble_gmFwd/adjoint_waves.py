#!/usr/bin/env python3
"""Adjoint Kelvin and Rossby waves in the campaign's temperature sensitivity (2026-09-16).

    python adjoint_waves.py slices    # ADJtheta at 915 m, every dump of all eight adjoints -> cache/adjtheta_915m_<run>.npy
    python adjoint_waves.py measure   # arrival leads along the boundaries, crossing speeds, mode speeds
                                      #   -> stats/adjoint_waves.json
    python adjoint_waves.py plot      # figures/adjoint_waves.png

WHY THIS EXISTS. The slide deck describes the films in terms of adjoint Kelvin and adjoint Rossby waves. This
script measures, from the dumps themselves, which way the sensitivity travels and how fast, so that the
description is a reading of the data and not of a textbook.

WHICH WAY AN ADJOINT WAVE GOES. The adjoint is integrated backwards in time with the transpose of the forward
operator, so every wave of the forward model has an adjoint counterpart travelling the opposite way as the lead
grows. Forward coastal Kelvin waves keep the coast on their right in the northern hemisphere (south along a
western boundary, east along the equator, poleward along an eastern boundary) and on their left in the southern;
forward long Rossby waves carry information westward. Adjoint Kelvin waves therefore run north along the western
wall, south along the eastern wall, west along the equator and poleward along the western wall of both
hemispheres, and adjoint Rossby waves run east. Physically: the transport at 26 N is set by the density on the
two walls there, the eastern wall is fed by Kelvin waves from the equator, the equator by the western wall, and
the western wall by Rossby waves arriving from the interior -- so its sensitivity lies upstream along that chain.

WHAT IS MEASURED, at 915 m (the level of the deck's temperature film), for all eight adjoints:

* arrival leads along the waveguide -- the first lead at which |dJ/dtheta| exceeds ARRIVAL_FRAC of its largest
  value anywhere on the level -- on the eastern wall, the equator and the western wall;
* the crossing speed of the interior signal at several latitudes, from the lag that best correlates the
  per-lead-normalised Hovmoller at 40.5 W with that at 20.5 W (leads beyond 0.1 yr);
* for comparison, the first baroclinic gravity-wave speed c1 of the leg's own final-year stratification
  (cache/leg_final_profiles.npz; zonal mean of the interior columns; gsw N^2; rigid lid, flat bottom), the
  equatorial Kelvin speed c1 and the long Rossby speed beta c1^2 / f^2.
"""
from __future__ import annotations

import json
import sys

import numpy as np

import campaign as c

K915 = 24                      # 0-based level index of 915 m
ARRIVAL_FRAC = 0.01
OMEGA, A_EARTH = 7.292e-5, 6.371e6
ROSSBY_LATS = [35, 30, 25, 20, -20, -25, -30, -35]
EAST_WALL, WEST_WALL = slice(47, 50), slice(1, 4)     # the three wet columns next to each wall


def slice_path(run):
    return c.CACHE / ('adjtheta_915m_%s.npy' % run)


def slices():
    its = c.ITERS[::-1]                                  # lead increasing, as the adjoint wrote them
    for run in c.RUN_ORDER:
        p = slice_path(run)
        if p.exists():
            continue
        out = np.zeros((len(its), 198, 51), np.float32)
        for n, it in enumerate(its):
            out[n] = c.adj(c.ADJ_JOB[run], 'ADJtheta', it)[K915]
        np.save(p, out)
        print('wrote', p, flush=True)


def leads_days():
    return (c.NITER_END - c.ITERS[::-1]) / c.STEPS_PER_YEAR * 366.0


def mode_speed(T, S, lat):
    """First baroclinic gravity-wave speed (m/s) of one T/S column on the model levels."""
    import gsw
    g = c.grid()
    zc, dz = g['RC'], g['DRF']
    ok = np.isfinite(T) & np.isfinite(S) & (S > 1)
    T, S, zc, dz = T[ok], S[ok], zc[ok], dz[ok]
    p = gsw.p_from_z(zc, lat)
    SA = gsw.SA_from_SP(S, p, -25.0, lat)
    CT = gsw.CT_from_pt(SA, T)
    N2 = np.maximum(gsw.Nsquared(SA, CT, p, lat)[0], 1e-8)
    dzc = -np.diff(zc)
    n = len(T)
    M = np.zeros((n, n))
    for k in range(n):
        if k > 0:
            a = 1.0 / (N2[k - 1] * dzc[k - 1])
            M[k, k] += a / dz[k]
            M[k, k - 1] -= a / dz[k]
        if k < n - 1:
            b = 1.0 / (N2[k] * dzc[k])
            M[k, k] += b / dz[k]
            M[k, k + 1] -= b / dz[k]
    ev = np.sort(np.linalg.eigvals(M).real)
    return float(1.0 / np.sqrt(ev[1]))                  # ev[0] is the barotropic mode, zero under a rigid lid


def column_speeds(run, lat0):
    g = c.grid()
    j = int(np.abs(g['lat'] - lat0).argmin())
    z = np.load(c.CACHE / 'leg_final_profiles.npz')
    T = z[run + '_T'][:, j - 1:j + 2, 15:36].mean(axis=(1, 2))
    S = z[run + '_S'][:, j - 1:j + 2, 15:36].mean(axis=(1, 2))
    c1 = mode_speed(T, S, float(g['lat'][j]))
    phi = np.deg2rad(g['lat'][j])
    f, beta = 2 * OMEGA * np.sin(phi), 2 * OMEGA * np.cos(phi) / A_EARTH
    return c1, (beta * c1 ** 2 / f ** 2 if abs(lat0) > 3 else np.nan)


def arrivals(A, lead):
    """First lead (d) above ARRIVAL_FRAC of the level's maximum, along the three waveguide segments."""
    g = c.grid()
    lat, lon = g['lat'], g['XC'][0]
    thr = ARRIVAL_FRAC * np.nanmax(np.abs(A))

    def first(series):
        idx = np.where(series > thr)[0]
        return float(lead[idx[0]]) if len(idx) else None

    E = np.abs(A[:, :, EAST_WALL]).max(axis=2)
    W = np.abs(A[:, :, WEST_WALL]).max(axis=2)
    jeq = [int(np.abs(lat - v).argmin()) for v in (-2, 2)]
    Q = np.abs(A[:, jeq[0]:jeq[1] + 1, :]).max(axis=1)
    pick = lambda L: int(np.abs(lat - L).argmin())
    return {
        'east_wall': {'%d' % L: first(E[:, pick(L)]) for L in (26, 20, 15, 10, 5, 0)},
        'equator': {'%.1f' % lon[i]: first(Q[:, i]) for i in range(1, 50, 6)},
        'west_wall_north': {'%d' % L: first(W[:, pick(L)]) for L in (26, 30, 35, 40, 45, 50)},
        'west_wall_south': {'%d' % L: first(W[:, pick(L)]) for L in (10, 0, -10, -20, -30)},
    }


def crossing_speed(A, lead, lat0):
    g = c.grid()
    lat, lon = g['lat'], g['XC'][0]
    j = int(np.abs(lat - lat0).argmin())
    H = A[:, j - 1:j + 2, :].mean(axis=1)
    H = H / (np.abs(H).max(axis=1, keepdims=True) + 1e-30)
    sel = lead > 0.1 * 366
    x1, x2 = int(np.abs(lon + 40.5).argmin()), int(np.abs(lon + 20.5).argmin())
    s1, s2 = H[sel, x1], H[sel, x2]
    best = (0, -2.0)
    for lag in range(1, 300):
        if len(s1) - lag < 60:
            break
        r = float(np.corrcoef(s1[:len(s1) - lag], s2[lag:])[0, 1])
        if r > best[1]:
            best = (lag, r)
    dist = np.deg2rad(lon[x2] - lon[x1]) * A_EARTH * np.cos(np.deg2rad(lat[j]))
    days = best[0] * 5.0
    return {'lag_days': days, 'r': round(best[1], 3), 'speed_m_s': round(dist / (days * 86400.0), 4)}


def measure():
    lead = leads_days()
    out = {'level_m': 915, 'arrival_frac_of_level_max': ARRIVAL_FRAC,
           'note': 'arrival: first lead (d) at which |ADJtheta| at 915 m exceeds the fraction of its largest value on '
                   'the level; crossing: lag of best correlation between 40.5 W and 20.5 W; c1: first baroclinic '
                   'gravity-wave speed of the leg\'s final-year stratification; rossby_theory: beta c1^2/f^2',
           'runs': {}}
    for run in c.RUN_ORDER:
        A = np.load(slice_path(run))
        r = {'factor': c.FACTOR[run], 'job': c.ADJ_JOB[run], 'arrival_days': arrivals(A, lead)}
        eq = r['arrival_days']['equator']
        vals = [v for v in eq.values() if v is not None]
        keys = [float(k) for k, v in eq.items() if v is not None]
        if len(vals) > 2:
            p = np.polyfit(np.array(vals) * 86400.0, np.deg2rad(np.array(keys)) * A_EARTH, 1)
            r['equator_front_speed_m_s'] = round(float(p[0]), 3)       # negative: westward
        r['c1_equator_m_s'] = round(column_speeds(run, 0.5)[0], 3)
        r['crossing'] = {}
        for L in ROSSBY_LATS:
            cs = crossing_speed(A, lead, L)
            c1, cr = column_speeds(run, L)
            cs.update({'c1_m_s': round(c1, 3), 'rossby_theory_m_s': round(cr, 4)})
            r['crossing']['%d' % L] = cs
        out['runs'][run] = r
        print(run, json.dumps(r['arrival_days']['east_wall']), r.get('equator_front_speed_m_s'),
              r['c1_equator_m_s'], {k: (v['speed_m_s'], v['rossby_theory_m_s']) for k, v in r['crossing'].items()},
              flush=True)
    (c.STATS / 'adjoint_waves.json').write_text(json.dumps(out, indent=1))
    print('wrote', c.STATS / 'adjoint_waves.json')


def plot():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    g = c.grid()
    lat, lon = g['lat'], g['XC'][0]
    lead = leads_days()
    A = np.load(slice_path('REF'))
    amax = np.nanmax(np.abs(A))
    nt = int(np.searchsorted(lead, 150.0)) + 1

    # the waveguide south of the section, unrolled: eastern wall 26 N -> equator, equator east -> west,
    # western wall equator -> 40 S; distance in 1000 km
    je = [j for j in range(int(np.abs(lat - 26.5).argmin()), int(np.abs(lat).argmin()) - 1, -1)]
    jeq = [int(np.abs(lat - v).argmin()) for v in (-2, 2)]
    jw = [j for j in range(int(np.abs(lat).argmin()), int(np.abs(lat + 40).argmin()) - 1, -1)]
    dy = g['DYG'][:, 25]
    seg_e = np.abs(A[:nt][:, je, EAST_WALL]).max(axis=2)
    seg_q = np.abs(A[:nt, jeq[0]:jeq[1] + 1, 49:0:-1]).max(axis=1)
    seg_w = np.abs(A[:nt][:, jw, WEST_WALL]).max(axis=2)
    d_e = np.cumsum([dy[j] for j in je]) / 1e6
    d_q = d_e[-1] + np.cumsum(g['DXG'][int(np.abs(lat).argmin()), 49:0:-1]) / 1e6
    d_w = d_q[-1] + np.cumsum([dy[j] for j in jw]) / 1e6
    dist = np.concatenate([d_e, d_q, d_w])
    guide = np.concatenate([seg_e, seg_q, seg_w], axis=1)

    jn = list(range(int(np.abs(lat - 26.5).argmin()), int(np.abs(lat - 60).argmin()) + 1))
    north = np.abs(A[:nt][:, jn, WEST_WALL]).max(axis=2)

    fig = plt.figure(figsize=(12.6, 3.9))
    gs = fig.add_gridspec(1, 6, width_ratios=[2.3, 1.0, 0.07, 0.62, 1.35, 1.35], wspace=0.10)
    lv = dict(vmin=-3, vmax=0, cmap='magma_r', shading='auto', rasterized=True)

    ax = fig.add_subplot(gs[0])
    pm = ax.pcolormesh(dist, lead[:nt], np.log10(guide / amax + 1e-12), **lv)
    for b in (d_e[-1], d_q[-1]):
        ax.axvline(b, color='w', lw=1.0)
    top = ax.secondary_xaxis('top')
    top.set_xticks([d_e[-1] / 2, (d_e[-1] + d_q[-1]) / 2, (d_q[-1] + d_w[-1]) / 2])
    top.set_xticklabels(['eastern wall\n26°N to equator', 'equator\n0° to 50°W',
                         'western wall\nequator to 40°S'], fontsize=7.5)
    top.tick_params(length=0)
    c1 = column_speeds('REF', 0.5)[0]
    t0 = 5.0
    ax.plot([0, dist[-1]], [t0, t0 + dist[-1] * 1e6 / c1 / 86400.0], color='#2a78d6', lw=1.3, ls='--')
    ax.text(dist[-1] * 0.45, 12, 'dashes: first-mode speed\nc$_1$ = %.1f m/s, from the\nleg\'s own stratification' % c1,
            color='#2a78d6', fontsize=8, ha='left', va='bottom')
    ax.set_xlabel('distance from 26°N along the path [1000 km]')
    ax.set_ylabel('lead [days]')
    ax.set_title('adjoint Kelvin waves, south of the section', fontsize=9.5, pad=24)
    ax.grid(False)

    ax = fig.add_subplot(gs[1], sharey=fig.axes[0])
    ax.pcolormesh(lat[jn], lead[:nt], np.log10(north / amax + 1e-12), **lv)
    ax.set_xlabel('latitude [°N]')
    ax.set_title('... and north of it', fontsize=9.5, pad=24)
    ax.tick_params(labelleft=False)
    ax.grid(False)
    cax = fig.add_subplot(gs[2])
    cb = fig.colorbar(pm, cax=cax)
    cb.set_label('log$_{10}$ of |dJ/d$\\theta$| over its maximum', fontsize=8)

    for n, L in enumerate((25, -25)):
        ax = fig.add_subplot(gs[4 + n])
        j = int(np.abs(lat - L).argmin())
        H = A[:, j - 1:j + 2, 1:50].mean(axis=1)
        H = H / (np.abs(H).max(axis=1, keepdims=True) + 1e-30)
        ax.pcolormesh(lon[1:50], lead / 366.0, H, cmap=c.diverging_cmap(), vmin=-1, vmax=1, shading='auto',
                      rasterized=True)
        cr = column_speeds('REF', L)[1]
        deg_per_yr = cr * 366 * 86400 / (np.deg2rad(1.0) * A_EARTH * np.cos(np.deg2rad(lat[j])))
        for t0 in (0.2, 2.2):
            tt = np.array([t0, 5.0])
            ax.plot(-50 + deg_per_yr * (tt - t0), tt, color=c.INK, lw=1.0, ls='--')
        ax.set_xlim(-50, 0)
        ax.set_ylim(0, 5)
        ax.set_xlabel('longitude')
        if n == 0:
            ax.set_ylabel('lead [yr]')
        else:
            ax.tick_params(labelleft=False)
        ax.set_title('adjoint Rossby waves, %d°%s' % (abs(L), 'N' if L > 0 else 'S'), fontsize=9.5, pad=24)
        ax.text(-1, 0.15, 'dashes: long Rossby\nspeed, %.1f cm/s' % (100 * cr), fontsize=7.5, color=c.INK, ha='right',
                va='bottom', bbox=dict(boxstyle='square,pad=0.2', fc=c.SURFACE, ec='none', alpha=0.9))
        ax.grid(False)
    p = c.FIGS / 'adjoint_waves.png'
    fig.savefig(p)
    print('wrote', p)


STEPS = {'slices': slices, 'measure': measure, 'plot': plot}

if __name__ == '__main__':
    c.setup_style()
    c.ensure_dirs()
    for s in (sys.argv[1:] or ['slices', 'measure', 'plot']):
        STEPS[s]()
