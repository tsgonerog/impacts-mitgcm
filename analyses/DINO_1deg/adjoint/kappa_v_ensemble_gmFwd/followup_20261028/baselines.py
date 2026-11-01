#!/usr/bin/env python3
"""Interpolation baselines on the 32 five-year adjoints (4 sections x 8 kappa_v): can anything interpolate across
sections or along the kappa_v ladder? Nearest neighbour, linear interpolation in log kappa_v and a POD-ridge model,
leave-one-section-out and leave-one-kappa-out; targets the 5-yr initial-temperature gradient (adxx_theta), the
temperature sensitivity at one year of lead (ADJtheta) and the 5-yr kappa_v gradient (adxx_diffkr); metrics the
volume-weighted pattern correlation and the RMS ratio with the held-out adjoint.

    python baselines.py compute   -> analysis/cost_sections/baselines/baselines.csv (+ the summary on stdout)
    python baselines.py figure    -> analysis/cost_sections/baselines/fig_baselines.png

Reads the four campaigns' cache/ (adxx_<run>.npz, fields_<run>.npz) through campaign.py.
"""
import collections
import csv
import itertools
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
GEN = os.environ.get('FOLLOWUP_GEN', '')       # 'Sv': the second generation of the campaigns (2026-11-01)
SUF = ('_' + GEN) if GEN else ''
os.environ.setdefault('CAMPAIGN_NAME', 'kappa_v_ensemble_gmFwd_sec43N' + SUF)
import numpy as np        # noqa: E402
import campaign as c      # noqa: E402

AN = c.OUTPUTS / 'analysis'
OUT = AN / c.CROSS_DIR / 'baselines'           # cost_sections/ or cost_sections_Sv/
# the four campaigns of this generation, south to north (campaign.SECTION_ORDER), with the row-centre latitudes
_LAT = {'25 S': -25.15, '26 N': 26.05, '43 N': 43.21, '60 N': 59.77}
SECS = [(c.COST_SECTION[n]['sec_name'], n, _LAT[c.COST_SECTION[n]['sec_name']]) for n in c.SECTION_ORDER]
RUNS = c.RUN_ORDER
LK = np.log2([c.FACTOR[r] for r in RUNS])
TARGETS = [('adxx_theta', 'initial-temperature gradient (5 yr)'), ('ADJtheta_1yr', 'temperature sensitivity, 1 yr lead'),
           ('adxx_diffkr', 'κ_v gradient (5 yr)')]


def load(camp, run, target):
    if target in ('adxx_theta', 'adxx_diffkr'):
        a = np.load(AN / camp / 'cache' / ('adxx_%s.npz' % run))[target]
    else:
        a = np.load(AN / camp / 'cache' / ('fields_%s.npz' % run))['ADJtheta_L1.000']
    return a[c.grid()['wetC']]


def pod_ridge(Xtr, ftr, Xte, sw, r=None, lam=1e-2):
    """Xtr (n, N) training fields, ftr (n, p) features, Xte (m, p): volume-weighted POD + ridge on the coefficients."""
    mu = Xtr.mean(axis=0); Y = (Xtr - mu) * sw
    U, S, Vt = np.linalg.svd(Y, full_matrices=False)
    r = r or min(len(Xtr) - 1, 12)
    coef = U[:, :r] * S[:r]
    F = np.c_[np.ones(len(ftr)), ftr]; Fte = np.c_[np.ones(len(Xte)), Xte]
    B = np.linalg.solve(F.T @ F + lam * np.eye(F.shape[1]), F.T @ coef)
    return (Fte @ B) @ Vt[:r] / sw + mu


def compute():
    g = c.grid(); wet = g['wetC']; w = g['vol'][wet]; w = w / w.sum(); sw = np.sqrt(w)

    def corr(a, b):
        a = a - (w * a).sum(); b = b - (w * b).sum()
        return float((w * a * b).sum() / np.sqrt((w * a * a).sum() * (w * b * b).sum()))

    def rmsr(a, b):
        return float(np.sqrt((w * a * a).sum() / (w * b * b).sum()))

    rows = []
    for target, _ in TARGETS:
        fields = {(s[0], r): load(s[1], r, target) for s in SECS for r in RUNS}
        for sname, camp, lat in SECS:                       # leave-one-kappa-out at a fixed section
            for i, r in enumerate(RUNS):
                truth = fields[(sname, r)]
                nb = [j for j in range(len(RUNS)) if j != i]
                near = min(nb, key=lambda j: abs(LK[j] - LK[i]))
                nn = fields[(sname, RUNS[near])]
                lo = [j for j in nb if LK[j] < LK[i]]; hi = [j for j in nb if LK[j] > LK[i]]
                if lo and hi:
                    jl, jh = max(lo), min(hi); t = (LK[i] - LK[jl]) / (LK[jh] - LK[jl])
                    lin = (1 - t) * fields[(sname, RUNS[jl])] + t * fields[(sname, RUNS[jh])]
                else:
                    lin = nn
                Xtr = np.array([fields[(sname, RUNS[j])] for j in nb]); ftr = np.c_[LK[nb], LK[nb] ** 2]
                pod = pod_ridge(Xtr, ftr, np.c_[[LK[i]], [LK[i] ** 2]], sw, r=4)[0]
                for name, p in (('nearest kappa', nn), ('linear in log kappa', lin), ('POD-ridge (kappa)', pod)):
                    rows.append(dict(target=target, split='leave-one-kappa-out', section=sname, held_out=r, model=name,
                                     corr=corr(p, truth), rms_ratio=rmsr(p, truth)))
        for sname, camp, lat in SECS:                       # leave-one-section-out at a fixed kappa
            others = [s for s in SECS if s[0] != sname]
            near = min(others, key=lambda s: abs(s[2] - lat))[0]
            Xtr = np.array([fields[(o[0], r)] for o in others for r in RUNS])
            ftr = np.array([[LK[k], LK[k] ** 2, o[2] / 60.0, (o[2] / 60.0) ** 2, LK[k] * o[2] / 60.0] for o in others for k in range(len(RUNS))])
            fte = np.array([[LK[k], LK[k] ** 2, lat / 60.0, (lat / 60.0) ** 2, LK[k] * lat / 60.0] for k in range(len(RUNS))])
            pod = pod_ridge(Xtr, ftr, fte, sw, r=10)
            for k, r in enumerate(RUNS):
                truth = fields[(sname, r)]
                for name, p in (('nearest section (%s)' % near, fields[(near, r)]), ('POD-ridge (kappa, latitude)', pod[k])):
                    rows.append(dict(target=target, split='leave-one-section-out', section=sname, held_out=r, model=name,
                                     corr=corr(p, truth), rms_ratio=rmsr(p, truth)))
        print(target, 'done', flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / 'baselines.csv', 'w') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
    summ = collections.defaultdict(list)
    for r in rows:
        summ[(r['target'], r['split'], r['model'].split(' (')[0])].append(r['corr'])
    print('\nmedian (min-max) pattern correlation of prediction with truth')
    for k in sorted(summ):
        v = np.array(summ[k]); print('%-14s %-22s %-22s %.2f (%.2f-%.2f) n=%d' % (k[0], k[1], k[2], np.median(v), v.min(), v.max(), len(v)))
    print('\nleave-one-section-out by section (nearest section), median over kappa')
    for t, _ in TARGETS:
        for s in SECS:
            v = [r['corr'] for r in rows if r['target'] == t and r['split'] == 'leave-one-section-out' and r['section'] == s[0] and r['model'].startswith('nearest')]
            print('  %-13s %s %.2f' % (t, s[0], np.median(v)))


def figure():
    rows = list(csv.DictReader(open(OUT / 'baselines.csv')))
    import matplotlib
    matplotlib.use('Agg'); import matplotlib.pyplot as plt
    c.setup_style()
    secs = [s[0] for s in SECS]
    fig, ax = plt.subplots(1, 2, figsize=(11, 4.2))
    x = np.arange(len(RUNS))
    for (t, lbl), col in zip(TARGETS, c.SERIES):
        lin = [np.median([float(r['corr']) for r in rows if r['target'] == t and r['split'] == 'leave-one-kappa-out'
                          and r['held_out'] == m and r['model'].startswith('linear')]) for m in RUNS]
        ax[0].plot(x, lin, '-o', color=col, ms=5, label=lbl)
    ax[0].set_xticks(x); ax[0].set_xticklabels(['¼', '½', '1', '2', '4', '8', '16', '32']); ax[0].set_xlabel('held-out κ_v (multiple of the reference)')
    ax[0].set_ylabel('pattern correlation with the held-out adjoint'); ax[0].set_ylim(0, 1.02)
    ax[0].set_title('along κ_v: linear interpolation in log κ_v, median over sections', loc='left', fontsize=9.5); ax[0].legend(loc='lower left', fontsize=8)
    xb = np.arange(len(secs)); wdt = 0.26
    for i, ((t, lbl), col) in enumerate(zip(TARGETS, c.SERIES)):
        nn = [np.median([float(r['corr']) for r in rows if r['target'] == t and r['split'] == 'leave-one-section-out'
                         and r['section'] == s and r['model'].startswith('nearest')]) for s in secs]
        ax[1].bar(xb + (i - 1) * wdt, nn, wdt - 0.03, color=col, label=lbl)
    ax[1].axhline(0, color=c.AXIS_C, lw=0.8); ax[1].set_xticks(xb); ax[1].set_xticklabels(secs)
    ax[1].set_xlabel('held-out section (predicted from the nearest other section)'); ax[1].set_ylim(-0.1, 1.02)
    ax[1].set_title('across sections: nearest section at the same κ_v, median over κ_v', loc='left', fontsize=9.5); ax[1].legend(loc='upper left', fontsize=8)
    fig.tight_layout(); fig.savefig(OUT / 'fig_baselines.png'); print(OUT / 'fig_baselines.png')


if __name__ == '__main__':
    {'compute': compute, 'figure': figure}[sys.argv[1]]()
