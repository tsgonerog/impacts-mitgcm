#!/usr/bin/env python3
"""Three figures of the kappa_v ensemble drawn for the meeting review of 2026-10-28, for the campaign CAMPAIGN_NAME
(default the 43 N one), into analysis/<campaign>/figures/:

    fig_line_plot.png          J after ten years at each kappa_v, and dJ/dkappa_v from the adjoint (sum of the field),
                               from the slope of J between neighbouring members, and from the central finite difference
    fig_amplitude_by_lead.png  each member's ADJtheta amplitude relative to the reference against lead, and the sum of
                               the field against lead (needs stats/theta_sum_vs_rms_by_member.json from
                               member_diagnostics.py sums)
    fig_psi_members.png        each member's overturning in its last leg year with the fixed cost box and its own maximum

    python page_figures.py [line|amplitude|psi|all]
"""
import collections
import csv
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ.setdefault('CAMPAIGN_NAME', 'kappa_v_ensemble_gmFwd_sec43N')
import numpy as np                                        # noqa: E402
import matplotlib                                         # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                           # noqa: E402
from matplotlib.colors import LinearSegmentedColormap     # noqa: E402
import campaign as c                                      # noqa: E402

c.setup_style()
FACT = [0.25, 0.5, 1, 2, 4, 8, 16, 32]
RUNS = c.RUN_ORDER
LBL = {r: ('reference (1×)' if r == 'REF' else '%g×' % c.FACTOR[r]) for r in RUNS}
_ramp = LinearSegmentedColormap.from_list('r', ['#9ec5f4', '#3987e5', '#0d366b'])
COL = {r: _ramp(i / 6.0) for i, r in enumerate(c.MEMBERS)}; COL['REF'] = '#0b0b0b'


def xlog2(ax):
    ax.set_xscale('log', base=2); ax.set_xticks(FACT); ax.set_xticklabels(['¼', '½', '1', '2', '4', '8', '16', '32'])
    ax.set_xlabel('κ_v as a multiple of the reference (1.2e-5 m²/s)'); ax.minorticks_off()


def end_labels(ax, pts, min_gap):
    """pts: (x, y, text, colour); labels at the right end, pushed apart vertically by at least min_gap."""
    pts = sorted(pts, key=lambda t: t[1]); ys = [t[1] for t in pts]
    for i in range(1, len(ys)):
        if ys[i] - ys[i - 1] < min_gap:
            ys[i] = ys[i - 1] + min_gap
    for (x, y, txt, col), yy in zip(pts, ys):
        ax.annotate(txt, (x, yy), xytext=(6, 0), textcoords='offset points', color=col, fontsize=8.5, va='center')


def line():
    fg = list(csv.DictReader(open(c.STATS / 'fc_gradient.csv')))
    kap = np.array([float(r['kappa']) for r in fg]); J = np.array([float(r['fc']) for r in fg]); G = np.array([float(r['G_dJdkappa_uniform']) for r in fg])
    fd = list(csv.DictReader(open(c.STATS / 'fd_checks.csv')))[0]
    fd_slope = float(fd['fd_central']) / (0.1 * c.KAPPA0)
    sec = (J[1:] - J[:-1]) / (kap[1:] - kap[:-1]); xs = np.sqrt(np.array(FACT[1:]) * np.array(FACT[:-1]))
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    ax[0].plot(FACT, J, '-o', color=c.SERIES[0], ms=5)
    ax[0].plot([1], [J[2]], 'o', color='#0b0b0b', ms=6); ax[0].annotate('reference', (1, J[2]), xytext=(8, -14), textcoords='offset points', color=c.INK2, fontsize=9)
    ax[0].set_ylabel('J: 30-day mean transport through the %s box (fc)' % c.SEC_NAME); xlog2(ax[0]); ax[0].set_title('the cost against the mixing', loc='left')
    ax[1].plot(FACT, G, '-o', color=c.SERIES[0], ms=5, label='adjoint: ∂J/∂κ_v at fixed state (sum of the map)')
    ax[1].plot(xs, sec, 's', color=c.SERIES[1], ms=6, label='slope of J between neighbours (includes the 10-yr adjustment)')
    ax[1].plot([1], [fd_slope], 'D', color='#0b0b0b', ms=7, label='finite difference at the reference, κ_v ±10 %')
    ax[1].axhline(0, color=c.AXIS_C, lw=0.8); ax[1].set_yscale('symlog', linthresh=200 * c.J_SCALE); ax[1].set_yticks([v * (10 if c.UNITS == 'Sv' else 1) for v in [-10000, -1000, 0, 1000]])
    ax[1].set_ylabel('dJ/dκ_v  [per m² s⁻¹]'); xlog2(ax[1]); ax[1].set_title('the gradient against the mixing', loc='left'); ax[1].legend(loc='upper left', fontsize=8)
    fig.tight_layout(); fig.savefig(c.FIGS / 'fig_line_plot.png'); plt.close(fig); print(c.FIGS / 'fig_line_plot.png')


def amplitude():
    mm = [r for r in csv.DictReader(open(c.CACHE / 'member_metrics.csv')) if r['var'] == 'ADJtheta']
    by = collections.defaultdict(list)
    for r in mm:
        by[r['run']].append((float(r['lead_yr']), float(r['rms_ratio'])))
    sums = json.load(open(c.STATS / 'theta_sum_vs_rms_by_member.json'))
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2)); pts0 = []; pts1 = []
    for r in c.MEMBERS:
        d = np.array(sorted(by[r])); ok = d[:, 0] >= 0.08
        ax[0].plot(d[ok, 0], d[ok, 1], color=COL[r], lw=1.6); pts0.append((d[ok, 0][-1], d[ok, 1][-1], LBL[r], COL[r]))
    ax[0].axhline(1, color=c.AXIS_C, lw=0.8, ls='--'); ax[0].set_xscale('log'); ax[0].set_xticks([0.1, 0.3, 1, 3, 5]); ax[0].set_xticklabels(['0.1', '0.3', '1', '3', '5'])
    ax[0].set_xlim(0.075, 7.5); ax[0].set_xlabel('lead: years before the end of the cost window'); ax[0].set_ylabel('RMS of the temperature sensitivity, member / reference')
    ax[0].set_title('amplitude relative to the reference, by lead', loc='left'); ax[0].minorticks_off()
    for r in RUNS:
        L = sorted(float(k) for k in sums[r]); y = [sums[r]['%.3f' % k]['sum_cell'] for k in L]
        ax[1].plot(L, y, '-o', color=COL[r], ms=4, lw=1.6); pts1.append((L[-1], y[-1], LBL[r], COL[r]))
    end_labels(ax[0], pts0, 0.07); end_labels(ax[1], pts1, 0.0075)
    ax[1].set_xscale('log'); ax[1].set_xticks([0.1, 0.3, 1, 3, 5]); ax[1].set_xticklabels(['0.1', '0.3', '1', '3', '5']); ax[1].set_xlim(0.075, 7.5); ax[1].minorticks_off()
    ax[1].set_xlabel('lead: years before the end of the cost window'); ax[1].set_ylabel('sum of the map: dJ per +1 K everywhere')
    ax[1].set_title('the sum of the map (response to +1 K everywhere), by lead', loc='left')
    fig.tight_layout(); fig.savefig(c.FIGS / 'fig_amplitude_by_lead.png'); plt.close(fig); print(c.FIGS / 'fig_amplitude_by_lead.png')


def psi():
    import cmocean
    g = c.grid(); lat = g['lat']; zb = g['RF'][1:37]                # psi[k, j] sits at the bottom interface of level k
    prof = np.load(str(c.CACHE / 'leg_final_profiles.npz'))
    JSEC, KB = c.JSEC, c.KMAX - 1
    north = lat > 20; deep = zb < -300
    fig, axs = plt.subplots(2, 4, figsize=(13, 7.2), sharex=True, sharey=True)
    for a, r in zip(axs.ravel(), RUNS):
        p = prof[r + '_psi']
        cf = a.contourf(lat, zb, p, levels=np.linspace(-12, 12, 25), cmap=cmocean.cm.balance, extend='both')
        a.contour(lat, zb, p, levels=[2, 4, 6, 8, 10], colors='#0b0b0b', linewidths=0.4, alpha=0.5)
        sub = np.where(north[None, :] & deep[:, None], p, -np.inf); k, j = np.unravel_index(np.argmax(sub), sub.shape)
        own, box = p[k, j], p[KB, JSEC]
        a.plot([lat[JSEC] - 0.37] * 2, [0, zb[KB]], color='#1baf7a', lw=2.2); a.plot(lat[JSEC] - 0.37, zb[KB], 'o', color='#1baf7a', ms=5)
        a.plot(lat[j], zb[k], 'o', mfc='none', mec='#0b0b0b', ms=8, mew=1.4)
        a.set_title('%s  box %.1f Sv (%.0f %% of max)\nmax %.1f Sv at %.0f N, %.0f m' % (
            '1× (reference)' if r == 'REF' else LBL[r], box, 100 * box / own, own, lat[j], -zb[k]), fontsize=8.3, loc='left')
        a.set_xlim(-10, 72); a.set_ylim(-3000, 0); a.grid(False)
    for a in axs[1]:
        a.set_xlabel('latitude')
    for a in axs[:, 0]:
        a.set_ylabel('depth [m]')
    fig.suptitle("Each member's overturning in its last leg year (Sv). Green: the fixed cost box (%s, upper %.0f m); circle: that member's own maximum"
                 % (c.SEC_NAME, -g['RF'][c.KMAX]), fontsize=10, x=0.01, ha='left')
    cb = fig.colorbar(cf, ax=axs, shrink=0.8, pad=0.01); cb.set_label('overturning streamfunction [Sv]')
    fig.savefig(c.FIGS / 'fig_psi_members.png'); plt.close(fig); print(c.FIGS / 'fig_psi_members.png')


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    for name, fn in (('line', line), ('amplitude', amplitude), ('psi', psi)):
        if what in (name, 'all'):
            fn()
