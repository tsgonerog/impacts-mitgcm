#!/usr/bin/env python3
"""Figures of the follow-up runs of 2026-10-28/29, from the tables followup_analysis.py writes:

    python fig_followup.py swap     -> analysis/kappa_v_operator_vs_state/figures/fig_swap.png
    python fig_followup.py sweep    -> analysis/cost_section_sweep/figures/fig_sweep.png
    python fig_followup.py ownmax   -> analysis/cost_section_sweep/figures/fig_ownmax.png
"""
import csv
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ.setdefault('CAMPAIGN_NAME', 'kappa_v_ensemble_gmFwd_sec43N')
import numpy as np                 # noqa: E402
import matplotlib                  # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt    # noqa: E402
import campaign as c               # noqa: E402

c.setup_style()
AN = c.OUTPUTS / 'analysis'
SWAP = AN / 'kappa_v_operator_vs_state'
SWEEP = AN / 'cost_section_sweep'


def swap():
    rows = list(csv.DictReader(open(SWAP / 'swap_results.csv')))
    leads = sorted({(r['duration_d'], float(r['lead_d'])) for r in rows}, key=lambda t: (int(t[0]), t[1]))
    order = ['swap_REFstate_REFkappa', 'swap_REFstate_32xkappa', 'swap_32xstate_REFkappa', 'swap_32xstate_32xkappa']
    labels = ['reference state\nreference κ_v', 'reference state\n32× κ_v', '32× state\nreference κ_v', '32× state\n32× κ_v']
    fig, axs = plt.subplots(1, len(leads), figsize=(3.6 * len(leads) + 1, 4.0), sharey=True)
    axs = np.atleast_1d(axs)
    for ax, (d, L) in zip(axs, leads):
        ref = [r for r in rows if r['duration_d'] == d and float(r['lead_d']) == L and r['experiment'].startswith('swap_REFstate_REFkappa')][0]
        vals = []
        for o in order:
            r = [x for x in rows if x['duration_d'] == d and float(x['lead_d']) == L and x['experiment'].startswith(o)]
            vals.append(float(r[0]['rms']) / float(ref['rms']) if r else np.nan)
        ax.bar(range(4), vals, 0.62, color=[c.INK2, c.SERIES[0], c.SERIES[1], c.INK2])
        for i, v in enumerate(vals):
            ax.annotate('%.2f' % v, (i, v), xytext=(0, 4), textcoords='offset points', ha='center', fontsize=9, color=c.INK)
        ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=8); ax.axhline(1, color=c.AXIS_C, lw=0.8, ls='--')
        ax.set_title('%s-day adjoint, lead %.0f d' % (d, L), loc='left', fontsize=9.5)
    axs[0].set_ylabel('RMS of the temperature sensitivity / reference run')
    (SWAP / 'figures').mkdir(exist_ok=True)
    fig.tight_layout(); fig.savefig(SWAP / 'figures' / 'fig_swap.png'); print(SWAP / 'figures' / 'fig_swap.png')


def sweep():
    rows = sorted(list(csv.DictReader(open(SWEEP / 'sweep_results.csv'))), key=lambda r: float(r['lat']))
    lat = np.array([float(r['lat']) for r in rows])
    M = np.loadtxt(SWEEP / 'sweep_corr_1yr.csv', delimiter=',')
    fig, ax = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw=dict(width_ratios=[1.05, 1]))
    im = ax[0].imshow(M, cmap=c.sequential_cmap(), vmin=0, vmax=1, origin='lower')
    labels = ['%.0f %s' % (abs(l), 'N' if l > 0 else 'S') for l in lat]
    ax[0].set_xticks(range(len(lat))); ax[0].set_xticklabels(labels, rotation=90, fontsize=8)
    ax[0].set_yticks(range(len(lat))); ax[0].set_yticklabels(labels, fontsize=8)
    for a in range(len(lat)):
        for b in range(len(lat)):
            if abs(a - b) == 1:
                ax[0].text(b, a, '%.2f' % M[a, b], ha='center', va='center', fontsize=6.5, color=c.INK if M[a, b] < 0.6 else '#ffffff')
    ax[0].grid(False); ax[0].set_title('temperature sensitivity at one year of lead: correlation between sections', loc='left', fontsize=9.5)
    cb = fig.colorbar(im, ax=ax[0], shrink=0.85, pad=0.02); cb.set_label('pattern correlation')
    mids, c30, c1 = [], [], []
    for r in rows:
        if r.get('corr_1yr_next'):
            mids.append(float(r['lat']) + 0.5 * float(r['dlat'])); c30.append(float(r['corr_30d_next'])); c1.append(float(r['corr_1yr_next']))
    ax[1].plot(mids, c1, '-o', color=c.SERIES[0], ms=5, label='one year of lead')
    ax[1].plot(mids, c30, '-o', color=c.SERIES[1], ms=5, label='30 days of lead')
    ax[1].axhline(0, color=c.AXIS_C, lw=0.8); ax[1].axhline(0.5, color=c.GRID_C, lw=0.8, ls='--'); ax[1].axvline(0, color=c.GRID_C, lw=0.8)
    ax[1].set_ylim(-0.7, 1.02); ax[1].set_xlabel('latitude midway between the two neighbouring sections')
    ax[1].set_ylabel('pattern correlation of neighbouring sections')
    ax[1].set_title('neighbouring sections, about 5° apart (30° across the equator)', loc='left', fontsize=9.5); ax[1].legend(loc='lower right', fontsize=8)
    (SWEEP / 'figures').mkdir(exist_ok=True)
    fig.tight_layout(); fig.savefig(SWEEP / 'figures' / 'fig_sweep.png'); print(SWEEP / 'figures' / 'fig_sweep.png')


def ownmax():
    g = c.grid(); lat = g['lat']; lon = g['XC'][0, :]
    d = np.load(SWEEP / 'ownmax_1yr_fields.npz'); r = json.load(open(SWEEP / 'ownmax_result.json'))
    own_job = [x['job'] for x in csv.DictReader(open(SWEEP / 'job_map.tsv'), delimiter='\t') if x['experiment'].startswith('ownmax')][0]
    fig, ax = plt.subplots(1, 2, figsize=(8.5, 6.2), sharey=True)
    panels = (('fixed', 'cost at the fixed section, 43 N (run %d)' % c.ADJ_JOB['M5'], 147),
              ('own', "cost at the member's own maximum, 69 N (run %s)" % own_job, 195))
    for a, (k, title, row) in zip(ax, panels):
        f = np.ma.masked_where(~g['wetC'][0], d[k]); v = c.robust_sym(f.compressed(), 99.5)
        a.pcolormesh(lon, lat, f, cmap=c.diverging_cmap(), vmin=-v, vmax=v, shading='auto')
        a.axhline(lat[row] - 0.37, color='#0b0b0b', lw=1.2); a.set_title(title, loc='left', fontsize=9); a.set_xlabel('longitude'); a.grid(False)
        a.text(0.02, 0.02, 'scale ±%.1e' % v, transform=a.transAxes, fontsize=8, color=c.INK2)
    ax[0].set_ylabel('latitude')
    fig.suptitle('8× member: column sum of the temperature sensitivity at one year of lead (pattern correlation %.2f)'
                 % r['leads']['366']['corr_colsum'], fontsize=10, x=0.01, ha='left')
    (SWEEP / 'figures').mkdir(exist_ok=True)
    fig.tight_layout(); fig.savefig(SWEEP / 'figures' / 'fig_ownmax.png'); print(SWEEP / 'figures' / 'fig_ownmax.png')


if __name__ == '__main__':
    {'swap': swap, 'sweep': sweep, 'ownmax': ownmax}[sys.argv[1]]()
