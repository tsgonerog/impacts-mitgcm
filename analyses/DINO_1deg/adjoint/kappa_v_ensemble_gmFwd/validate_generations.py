#!/usr/bin/env python3
"""The second generation of the kappa_v campaigns (the cost in Sverdrups, 2026-11-01) against the first (the tree's
per-tile-normalised cost): what changed, section by section and member by member.

    CAMPAIGN_NAME=kappa_v_ensemble_gmFwd_sec43N_Sv python validate_generations.py [--sections 43N,60N] [--self-test]

Reads, for every second-generation campaign in campaign.SECTION_ORDER whose products exist, its own products and
those of the first-generation campaign of the same section (campaign.COST_SECTION[...]['old_campaign']):
stats/fc_gradient.csv, fd_checks.csv, noise_floor.json, dJ_decomposition.csv and the cached fields (cache/fields_*.npz,
adxx_*.npz). Writes analysis/<CROSS_DIR>/validation_vs_tile/: generations_table.csv (one row per section and member),
generations_fd.csv (the finite-difference checks side by side), generations_summary.json, fig_generations.png and a
README.md with the table and the reading of it. --self-test compares each first-generation campaign with itself (every
ratio 1, every correlation 1), to exercise the code paths before the new runs exist.

What it found first at 43 N (2026-11-01): fc_new / fc_old is close to 16.6 but not constant (16, 17 and 16 wet cells per
tile, so the factor depends on how the transport splits across the tiles), dJ/dkappa_v scales by a different factor, and
the fields are NOT a rescaling: the expectation written here before the rerun, correlations above 0.999, was wrong, having
been read off a 5-day comparison. The per-tile weights leave a net sensitivity at the two tile seams of the cost row
(i=17|18, 34|35), which the adjoint carries away from them, so the difference grows with lead. seam_share_<lead> measures
it: the share, in the eight columns around the seams, of the squared difference between the new field and the best
rescaling of the old one, on the rows within 6 of the cost row. At 26 N and 60 N the first generation also integrated to
982 m, so there the comparison carries the change of depth as well.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import campaign as c

LEADS = {'30 d': 30.0 / 366, '1 yr': 1.0, '5 yr': 5.0}
SEAM_COLUMNS = [15, 16, 17, 18, 32, 33, 34, 35]   # 0-based: the columns around the tile seams i=17|18 and 34|35
FIELDS = ['ADJtheta', 'ADJsalt', 'ADJdiffkr', 'ADJqnet', 'ADJempmr']
ADXX = ['adxx_theta', 'adxx_salt', 'adxx_diffkr', 'adxx_qnet', 'adxx_empmr', 'adxx_qsw', 'adxx_fu', 'adxx_fv']


def A(name):
    return c.OUTPUTS / 'analysis' / name


def corr_rms(a, b, w):
    """Pattern correlation of a against b, and RMS ratio a/b, both weighted by w (the suite's conventions)."""
    r = c.rms(b, w)
    return c.pattern_corr(a, b, w), (c.rms(a, w) / r if r > 0 else np.nan)


def seam_share(new, old, jsec):
    """(share of the difference in the seam columns near the cost row, the same share of the new field, RMS difference /
    RMS new), the difference being new minus the volume-weighted best rescaling of old."""
    g = c.grid(); wet = g['wetC']; w = g['vol'] * wet
    a, b = np.where(wet, new, 0.0).astype(np.float64), np.where(wet, old, 0.0).astype(np.float64)
    d = a - (w * a * b).sum() / (w * b * b).sum() * b
    rows = slice(max(jsec - 6, 0), jsec + 7)

    def share(x):
        z = (w * x * x)[:, rows, :].sum(axis=(0, 1))
        return float(z[SEAM_COLUMNS].sum() / z.sum())
    return share(d), share(a), float(np.sqrt((w * d * d).sum() / (w * a * a).sum()))


def ls_ratio(a, b):
    m = (a != 0) | (b != 0)
    den = float(b[m] @ b[m])
    return float(a[m] @ b[m]) / den if den else np.nan


def compare(new, old, out):
    rows, fdrows = [], []
    fg_n = pd.read_csv(A(new) / 'stats' / 'fc_gradient.csv').set_index('run')
    fg_o = pd.read_csv(A(old) / 'stats' / 'fc_gradient.csv').set_index('run')
    nf_n = json.loads((A(new) / 'stats' / 'noise_floor.json').read_text())['jproxy']
    nf_o = json.loads((A(old) / 'stats' / 'noise_floor.json').read_text())['jproxy']
    dec_n = pd.read_csv(A(new) / 'stats' / 'dJ_decomposition.csv').set_index('run') if (A(new) / 'stats' / 'dJ_decomposition.csv').exists() else None
    dec_o = pd.read_csv(A(old) / 'stats' / 'dJ_decomposition.csv').set_index('run') if (A(old) / 'stats' / 'dJ_decomposition.csv').exists() else None
    sec = c.COST_SECTION[new]['sec_name']
    for r in c.RUN_ORDER:
        if r not in fg_n.index or r not in fg_o.index:
            continue
        row = dict(section=sec, run=r, factor=c.FACTOR[r], fc_old=fg_o.fc[r], fc_new=fg_n.fc[r], fc_ratio=fg_n.fc[r] / fg_o.fc[r],
                   dJdk_old=fg_o.G_dJdkappa_uniform[r], dJdk_new=fg_n.G_dJdkappa_uniform[r],
                   dJdk_ratio=fg_n.G_dJdkappa_uniform[r] / fg_o.G_dJdkappa_uniform[r])
        fn, fo = np.load(A(new) / 'cache' / ('fields_%s.npz' % r)), np.load(A(old) / 'cache' / ('fields_%s.npz' % r))
        for v in FIELDS:
            w = c.weights(v)
            for lab, L in LEADS.items():
                k = '%s_L%.3f' % (v, L)
                if k in fn and k in fo:
                    cc, rr = corr_rms(fn[k], fo[k], w)
                    row['%s_corr_%s' % (v, lab.replace(' ', ''))] = cc
                    row['%s_rmsratio_%s' % (v, lab.replace(' ', ''))] = rr
                    if v == 'ADJtheta':
                        tag = lab.replace(' ', '')
                        row['seam_share_%s' % tag], row['seam_share_of_new_%s' % tag], row['diff_rms_over_new_%s' % tag] = seam_share(
                            fn[k], fo[k], c.COST_SECTION[new]['jsec'])
        xn, xo = np.load(A(new) / 'cache' / ('adxx_%s.npz' % r)), np.load(A(old) / 'cache' / ('adxx_%s.npz' % r))
        for v in ADXX:
            if v in xn and v in xo:
                m = c.mask(v)
                a, b = xn[v][m], xo[v][m]
                row['%s_corr' % v] = c.pattern_corr(a, b)
                row['%s_lsratio' % v] = ls_ratio(a, b)
        if dec_n is not None and dec_o is not None and r in dec_n.index and r in dec_o.index:
            for k in ('corr_adxx_theta', 'corr_adxx_diffkr', 'corr_adxx_qnet'):
                row['member_vs_ref_%s_old' % k[5:]] = dec_o[k][r]
                row['member_vs_ref_%s_new' % k[5:]] = dec_n[k][r]
        rows.append(row)
    # the finite-difference checks, test by test
    fd_n = pd.read_csv(A(new) / 'stats' / 'fd_checks.csv') if (A(new) / 'stats' / 'fd_checks.csv').exists() else pd.DataFrame()
    fd_o = pd.read_csv(A(old) / 'stats' / 'fd_checks.csv') if (A(old) / 'stats' / 'fd_checks.csv').exists() else pd.DataFrame()
    if len(fd_n) and len(fd_o):
        m = fd_n.merge(fd_o, on='test', suffixes=('_new', '_old'))
        for _, q in m.iterrows():
            fdrows.append(dict(section=sec, test=q.test, fd_central_old=q.fd_central_old, fd_central_new=q.fd_central_new,
                               fd_ratio=q.fd_central_new / q.fd_central_old if q.fd_central_old else np.nan,
                               adjoint_old=q.adjoint_old, adjoint_new=q.adjoint_new,
                               adjoint_ratio=q.adjoint_new / q.adjoint_old if q.adjoint_old else np.nan,
                               rel_err_old=q.adjoint_rel_err_old, rel_err_new=q.adjoint_rel_err_new,
                               spread_old=q.get('one_sided_spread_old', np.nan), spread_new=q.get('one_sided_spread_new', np.nan)))
    summary = dict(section=sec, new=new, old=old,
                   noise_floor_old=nf_o['std_monthly'], noise_floor_new=nf_n['std_monthly'],
                   noise_floor_ratio=nf_n['std_monthly'] / nf_o['std_monthly'],
                   jproxy_mean_old=nf_o['mean'], jproxy_mean_new=nf_n['mean'],
                   fc_ratio_min=min(r['fc_ratio'] for r in rows), fc_ratio_max=max(r['fc_ratio'] for r in rows),
                   dJdk_ratio_min=min(r['dJdk_ratio'] for r in rows), dJdk_ratio_max=max(r['dJdk_ratio'] for r in rows),
                   ADJtheta_corr_5yr_min=min(r.get('ADJtheta_corr_5yr', np.nan) for r in rows),
                   adxx_diffkr_corr_min=min(r.get('adxx_diffkr_corr', np.nan) for r in rows))
    return rows, fdrows, summary


def figure(df, fd, summ, out):
    secs = [s['section'] for s in summ]
    fig, axs = plt.subplots(2, 2, figsize=(11, 7.2))
    ax = axs[0, 0]
    for s in secs:
        q = df[df.section == s]
        ax.plot(q.factor, q.fc_ratio, 'o-', label=s)
    ax.set_xscale('log'); ax.set_xlabel('κ_v / reference'); ax.set_ylabel('fc, second / first generation')
    ax.set_title('cost: ratio of the two forms (16.6 if the row transport were split evenly over the tiles)', fontsize=9)
    ax.legend(fontsize=8)
    ax = axs[0, 1]
    for s in secs:
        q = df[df.section == s]
        for lab, mk in zip(['30d', '1yr', '5yr'], ['^', 's', 'o']):
            col = 'ADJtheta_corr_%s' % lab
            if col in q:
                ax.plot(q.factor, q[col], marker=mk, ls='-', label='%s, %s' % (s, lab))
    ax.set_xscale('log'); ax.set_xlabel('κ_v / reference'); ax.set_ylabel('pattern correlation')
    ax.set_title('ADJtheta, second against first generation, by lead', fontsize=9); ax.legend(fontsize=6.5, ncol=2)
    ax = axs[1, 0]
    for s in secs:
        q = df[df.section == s]
        cols = [v + '_corr' for v in ADXX if v + '_corr' in q]
        ax.plot(range(len(cols)), [q[k].mean() for k in cols], 'o-', label=s)
    ax.set_xticks(range(len(cols))); ax.set_xticklabels([k[5:-5] for k in cols], rotation=30, fontsize=8)
    ax.set_ylabel('pattern correlation (mean over members)'); ax.set_title('control gradients, second against first generation', fontsize=9)
    ax.legend(fontsize=8)
    ax = axs[1, 1]
    if len(fd):
        for s in secs:
            q = fd[fd.section == s]
            ax.scatter(q.rel_err_old * 100, q.rel_err_new * 100, label=s, s=22)
        lim = np.nanmax(np.abs(np.r_[fd.rel_err_old, fd.rel_err_new].astype(float))) * 100
        lim = min(max(lim * 1.1, 1), 60)
        ax.plot([-lim, lim], [-lim, lim], color='0.6', lw=0.8); ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim)
        ax.set_xlabel('adjoint vs finite difference, first generation [%]'); ax.set_ylabel('second generation [%]')
        ax.set_title('finite-difference checks (the surface-flux failures lie outside the frame)', fontsize=9)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / 'fig_generations.png', dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--self-test', action='store_true', help='compare each first-generation campaign with itself')
    ap.add_argument('--sections', default='', help='comma-separated section tokens to restrict to, e.g. 43N,60N')
    ap.add_argument('--campaigns', default='', help='comma-separated campaign names to compare (each with its old_campaign); default campaign.SECTION_ORDER')
    ap.add_argument('--out', default='', help='output subdirectory under analysis/<CROSS_DIR>/ (default validation_vs_tile)')
    a = ap.parse_args()
    out = c.OUTPUTS / 'analysis' / c.CROSS_DIR / (a.out or ('validation_selftest' if a.self_test else 'validation_vs_tile'))
    out.mkdir(parents=True, exist_ok=True)
    want = [s.strip() for s in a.sections.split(',') if s.strip()]
    names = [s.strip() for s in a.campaigns.split(',') if s.strip()] or c.SECTION_ORDER
    rows, fdrows, summ = [], [], []
    for name in names:
        old = name if a.self_test else c.COST_SECTION[name]['old_campaign']
        if old is None or (want and not any(w in name for w in want)):
            continue
        if not (A(name) / 'stats' / 'fc_gradient.csv').exists() or not (A(old) / 'stats' / 'fc_gradient.csv').exists():
            print('skipped (no products yet):', name)
            continue
        r, f, s = compare(name, old, out)
        rows += r; fdrows += f; summ.append(s)
        print('%s: fc ratio %.3f..%.3f, dJ/dk ratio %.3f..%.3f, noise ratio %.3f, min ADJtheta corr 5 yr %.4f' % (
            s['section'], s['fc_ratio_min'], s['fc_ratio_max'], s['dJdk_ratio_min'], s['dJdk_ratio_max'],
            s['noise_floor_ratio'], s['ADJtheta_corr_5yr_min']))
    if not rows:
        print('nothing to compare'); return
    df, fd = pd.DataFrame(rows), pd.DataFrame(fdrows)
    df.to_csv(out / 'generations_table.csv', index=False)
    fd.to_csv(out / 'generations_fd.csv', index=False)
    (out / 'generations_summary.json').write_text(json.dumps(summ, indent=1, default=float))
    figure(df, fd, summ, out)
    cols = ['section', 'run', 'fc_old', 'fc_new', 'fc_ratio', 'dJdk_old', 'dJdk_new', 'dJdk_ratio', 'ADJtheta_corr_30d',
            'ADJtheta_corr_1yr', 'ADJtheta_corr_5yr', 'adxx_theta_corr', 'adxx_diffkr_corr', 'adxx_qnet_corr', 'adxx_fu_corr',
            'seam_share_30d', 'seam_share_of_new_30d', 'diff_rms_over_new_30d', 'diff_rms_over_new_1yr', 'diff_rms_over_new_5yr']
    cols = [k for k in cols if k in df]
    md = ['# The second generation (cost in Sverdrups) against the first (per-tile normalised)', '',
          'Written by validate_generations.py on %s. One row per section and member; ratios are second / first.' % pd.Timestamp.today().date(), '',
          df[cols].to_markdown(index=False, floatfmt='.4g'), '', '## Noise floors (sigma of the monthly cost proxy of the spin-up)', '',
          pd.DataFrame(summ)[['section', 'noise_floor_old', 'noise_floor_new', 'noise_floor_ratio']].to_markdown(index=False, floatfmt='.4g'), '']
    if len(fd):
        md += ['## Finite-difference checks, test by test', '',
               fd[['section', 'test', 'fd_central_old', 'fd_central_new', 'fd_ratio', 'adjoint_ratio', 'rel_err_old', 'rel_err_new']].to_markdown(index=False, floatfmt='.4g'), '']
    (out / 'README.md').write_text('\n'.join(md))
    print('written to', out)


if __name__ == '__main__':
    main()
