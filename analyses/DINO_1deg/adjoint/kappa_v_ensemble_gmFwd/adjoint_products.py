#!/usr/bin/env python3
"""Adjoint side of the campaign: statistics, fields and tables the figures and the page read.

    python adjoint_products.py [--dev] step [step ...]

steps
  verify      stats/run_verification.csv: completion, fc, runtime and output counts of every run
  timeseries  cache/adj_timeseries.csv: wet-cell RMS (volume/area weighted), max|.| and finite
              fraction of every ADJ* dump of every adjoint
  members     cache/member_metrics.csv: pattern correlation and RMS ratio of each member's dumps
              against the reference's, every second dump; also 31237 against the reference
  fields      cache/fields_<run>.npz: ADJ* fields at leads 5, 2, 1, 0.25 yr and 30 d;
              cache/adxx_<run>.npz: the eight control gradients
  tables      stats/fc_gradient.csv, stats/control_ranking.csv, stats/dJ_decomposition.csv,
              stats/previous_campaigns.json
  fd          stats/fd_checks.csv from analysis/<campaign>/fd_fc_lines.tsv
--dev uses 31237 as the only adjoint (the reference) to exercise the code paths.
"""
import argparse
import json
import re
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import pandas as pd

import campaign as c

LEADS = [5.0, 2.0, 1.0, 0.25, 30.0 / 366]
F3 = ['ADJtheta', 'ADJsalt', 'ADJdiffkr']
F2 = ['ADJqnet', 'ADJempmr', 'ADJtaux', 'ADJtauy', 'ADJetan']
ADJ = dict(c.ADJ_JOB)


def load32(d, var, it):
    return c.read_mds(Path(d) / ('%s.%010d' % (var, it)), np.float32)


def verify():
    rows = []
    groups = [('leg', r, j) for r, j in c.LEG_JOB.items()] + [('adjoint', r, j) for r, j in ADJ.items()] + \
             [('fd', k, j) for k, j in c.FD_JOB.items()]
    for kind, lab, job in groups:
        d = c.run_dir(job)
        row = dict(kind=kind, label=lab, job=job, run_dir=d.name if d else None)
        if d is None:
            rows.append(row)
            continue
        out = (d / 'STDOUT.0000').read_text(errors='replace') if (d / 'STDOUT.0000').exists() else ''
        row['ended_normally'] = 'Execution ended Normally' in out
        rt = d / 'run_timing.txt'
        m = re.search(r'Total runtime:\s*(\S+)', rt.read_text()) if rt.exists() else None
        row['runtime'] = m.group(1) if m else None
        errs = [p for p in d.glob('STDERR.*') if p.stat().st_size and re.search(r'(?i)error|nan', p.read_text(errors='replace'))]
        row['stderr_files_with_error_or_nan'] = len(errs)
        if kind == 'leg':
            row['final_pickup'] = (d / ('pickup.%010d.data' % c.NITER0)).exists()
            row['dynDiag_records'] = len(list(d.glob('dynDiag.*.data')))
        else:
            row['fc'] = c.first_fc(d)
            if kind == 'adjoint':
                row['ADJ_dumps_per_field'] = min(len(list(d.glob('%s.*.data' % v))) for v in c.ADJ_VARS if v != 'ADJetan')
                row['ADJetan_dumps'] = len(list(d.glob('ADJetan.*.data')))
                row['adxx_files'] = sum((d / ('%s.0000000000.data' % v)).exists() for v in c.ADXX_VARS)
                mon = re.findall(r'%MON ad_\w+\s*=\s*(\S+)', out)
                row['adjoint_monitor_nonfinite'] = sum(1 for x in mon if not re.match(r'^-?[0-9.]+E[-+][0-9]+$', x))
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(c.STATS / 'run_verification.csv', index=False)
    print(df.to_string())


def _ts_worker(args):
    lab, job, var = args
    m = c.mask(var)
    w = c.weights(var)[m]
    d = c.run_dir(job)
    rows = []
    for it in c.ITERS:
        a = load32(d, var, it)[m].astype(np.float64)
        fin = np.isfinite(a)
        rows.append((lab, var, int(it), float(c.lead_years(it)), c.rms(a, w),
                     float(np.abs(a[fin]).max()) if fin.any() else np.nan, float(fin.mean())))
    return rows


def timeseries():
    tasks = [(lab, job, v) for lab, job in ADJ.items() for v in c.ADJ_VARS]
    c.grid()
    with Pool(6) as p:
        out = p.map(_ts_worker, tasks, chunksize=1)
    df = pd.DataFrame([r for rows in out for r in rows],
                      columns=['run', 'var', 'iter', 'lead_yr', 'rms', 'maxabs', 'finite_frac'])
    df.to_csv(c.CACHE / 'adj_timeseries.csv', index=False)
    print('timeseries:', len(df), 'rows')


def _mm_worker(args):
    lab, job, refjob, var = args
    m = c.mask(var)
    w = c.weights(var)[m]
    d, dr = c.run_dir(job), c.run_dir(refjob)
    rows = []
    for it in c.ITERS[::2]:
        a = load32(d, var, it)[m].astype(np.float64)
        r = load32(dr, var, it)[m].astype(np.float64)
        rr = c.rms(r, w)
        rows.append((lab, var, int(it), float(c.lead_years(it)), c.pattern_corr(a, r, w),
                     c.rms(a, w) / rr if rr > 0 else np.nan))
    return rows


def members():
    others = {k: v for k, v in ADJ.items() if k != 'REF'}
    others['prev31237'] = c.PREV_GMFWD_5YR_JOB
    tasks = [(lab, job, ADJ['REF'], v) for lab, job in others.items() for v in c.ADJ_VARS
             if c.run_dir(job) and job != ADJ['REF']]
    c.grid()
    with Pool(6) as p:
        out = p.map(_mm_worker, tasks, chunksize=1)
    df = pd.DataFrame([r for rows in out for r in rows],
                      columns=['run', 'var', 'iter', 'lead_yr', 'corr', 'rms_ratio'])
    df.to_csv(c.CACHE / 'member_metrics.csv', index=False)
    print('member metrics:', len(df), 'rows')


def fields():
    runs = dict(ADJ)
    if c.run_dir(c.PREV_GMFWD_5YR_JOB):
        runs['prev31237'] = c.PREV_GMFWD_5YR_JOB
    for lab, job in runs.items():
        d = c.run_dir(job)
        out = {}
        for L in LEADS:
            it = c.nearest_iter(L)
            for v in F3 + F2:
                out['%s_L%.3f' % (v, L)] = load32(d, v, it)
        np.savez_compressed(c.CACHE / ('fields_%s.npz' % lab), **out)
        np.savez_compressed(c.CACHE / ('adxx_%s.npz' % lab), **{v: c.adxx(job, v) for v in c.ADXX_VARS
                                                                if (d / ('%s.0000000000.data' % v)).exists()})
        print('fields cached for', lab)


def tables():
    g = c.grid()
    nf = json.loads((c.STATS / 'noise_floor.json').read_text())
    sigma = nf['jproxy']['std_monthly']
    rows = []
    for r in c.RUN_ORDER:
        if r not in ADJ:
            continue
        d = c.run_dir(ADJ[r])
        z = np.load(c.CACHE / ('adxx_%s.npz' % r))
        rows.append(dict(run=r, factor=c.FACTOR[r], kappa=c.KAPPA0 * c.FACTOR[r], fc=c.first_fc(d),
                         G_dJdkappa_uniform=float(z['adxx_diffkr'][g['wetC']].sum())))
    fg = pd.DataFrame(rows)
    fg.to_csv(c.STATS / 'fc_gradient.csv', index=False)
    print(fg.to_string())

    # control ranking for the reference: response to a uniform perturbation of plausible size, and the
    # largest response to a perturbation of that size at every cell (sign-matched)
    z = np.load(c.CACHE / 'adxx_REF.npz')
    rank = []
    for v, (unit, s, what) in c.CONTROL_INFO.items():
        a = z[v][c.mask(v)]
        rank.append(dict(control=v, what=what, unit=unit, scale=s, sum_adxx=float(a.sum()),
                         dJ_uniform=float(s * a.sum()), dJ_signmatched=float(s * np.abs(a).sum()),
                         dJ_uniform_over_sigma=float(abs(s * a.sum()) / sigma),
                         dJ_signmatched_over_sigma=float(s * np.abs(a).sum() / sigma)))
    pd.DataFrame(rank).to_csv(c.STATS / 'control_ranking.csv', index=False)
    print(pd.DataFrame(rank).to_string())

    # member Delta J against the adjoint prediction: the kappa term and the initial-state term
    if len(ADJ) > 1:
        ref_leg = c.run_dir(c.LEG_JOB['REF'])      # the spin-up's continuation to year 180
        pk = 'pickup.%010d' % c.NITER0

        def state(d):
            a = c.read_mds(Path(d) / pk)
            return a[72:108], a[108:144]      # Theta, Salt records

        th0, s0 = state(ref_leg)
        dec = []
        fc_ref = fg.set_index('run').fc['REF']
        G = fg.set_index('run').G_dJdkappa_uniform
        for r in c.MEMBERS:
            if r not in ADJ:
                continue
            zm = np.load(c.CACHE / ('adxx_%s.npz' % r))
            dk = c.KAPPA0 * (c.FACTOR[r] - 1.0)
            th, s = state(c.run_dir(c.LEG_JOB[r]))
            wet = g['wetC']
            st_T = float((z['adxx_theta'] * (th - th0))[wet].sum())
            st_S = float((z['adxx_salt'] * (s - s0))[wet].sum())
            dec.append(dict(run=r, factor=c.FACTOR[r], dJ_measured=fg.set_index('run').fc[r] - fc_ref,
                            dJ_kappa_refgrad=G['REF'] * dk, dJ_kappa_membergrad=G[r] * dk,
                            dJ_kappa_mean=0.5 * (G['REF'] + G[r]) * dk,
                            dJ_state_theta=st_T, dJ_state_salt=st_S,
                            dJ_predicted_refgrad_plus_state=G['REF'] * dk + st_T + st_S,
                            corr_adxx_theta=c.pattern_corr(zm['adxx_theta'][wet], z['adxx_theta'][wet]),
                            corr_adxx_diffkr=c.pattern_corr(zm['adxx_diffkr'][wet], z['adxx_diffkr'][wet]),
                            corr_adxx_qnet=c.pattern_corr(zm['adxx_qnet'][wet[0]], z['adxx_qnet'][wet[0]])))
        pd.DataFrame(dec).to_csv(c.STATS / 'dJ_decomposition.csv', index=False)
        print(pd.DataFrame(dec).to_string())

    # the earlier campaigns, for the comparison figures (numbers kept in the suite, see previous_campaigns_reference.json)
    ref = json.loads(c.PREVIOUS.read_text())
    old = {'visc2x_2026_08': ref['visc2x_2026_08'], 'gmFree_ReMax2_2026_09_10': ref['gmFree_ReMax2_2026_09_10'],
           'gm_test_2026_09_11': ref['gm_test_2026_09_11']}
    (c.STATS / 'previous_campaigns.json').write_text(json.dumps(old, indent=1))


def fd():
    g = c.grid()
    tsv = c.ANALYSIS / 'fd_fc_lines.tsv'
    got = {int(l.split('\t')[0]): float(l.split('\t')[2]) for l in tsv.read_text().splitlines() if l.strip()}
    inv = {j: k for k, j in c.FD_JOB.items()}
    J = {inv[j]: v for j, v in got.items() if j in inv}
    z = np.load(c.CACHE / 'adxx_REF.npz')
    J0 = c.first_fc(c.run_dir(ADJ['REF']))
    rows = []
    dk = 0.1 * c.KAPPA0
    if 'REFp10' in J and 'REFm10' in J:
        pred = float(z['adxx_diffkr'][g['wetC']].sum()) * dk
        fdc = 0.5 * (J['REFp10'] - J['REFm10'])
        rows.append(dict(test='kappa_v +10 %', J_plus=J['REFp10'], J_minus=J['REFm10'], J0=J0, fd_central=fdc,
                         fd_plus=J['REFp10'] - J0, fd_minus=J0 - J['REFm10'], adjoint=pred,
                         adjoint_rel_err=(pred - fdc) / abs(fdc)))
    for name, spec in c.THETA_BOXES.items():
        if name + '_p' in J and name + '_m' in J:
            k0, k1, j0, j1, i0, i1 = spec['box']
            delta = np.zeros_like(z['adxx_theta'])
            delta[k0:k1, j0:j1, i0:i1] = spec['amp']
            delta *= g['wetC']
            pred = float((z['adxx_theta'] * delta).sum())
            fdc = 0.5 * (J[name + '_p'] - J[name + '_m'])
            rows.append(dict(test='Theta +%g K, %s' % (spec['amp'], spec['what']), J_plus=J[name + '_p'],
                             J_minus=J[name + '_m'], J0=J0, fd_central=fdc, fd_plus=J[name + '_p'] - J0,
                             fd_minus=J0 - J[name + '_m'], adjoint=pred, adjoint_rel_err=(pred - fdc) / abs(fdc)))
    for ctl, (v, amp, unit, what) in c.FORCING_TESTS.items():
        if ctl + '_p' in J and ctl + '_m' in J:
            pred = float(z[v][c.mask(v)].sum()) * amp
            fdc = 0.5 * (J[ctl + '_p'] - J[ctl + '_m'])
            rows.append(dict(test='%s +%g %s everywhere' % (what, amp, unit), J_plus=J[ctl + '_p'], J_minus=J[ctl + '_m'],
                             J0=J0, fd_central=fdc, fd_plus=J[ctl + '_p'] - J0, fd_minus=J0 - J[ctl + '_m'],
                             adjoint=pred, adjoint_rel_err=(pred - fdc) / abs(fdc) if fdc else np.nan))
    df = pd.DataFrame(rows)
    if len(df):   # how far the two one-sided differences disagree, relative to the central one: >1 means noise
        df['one_sided_spread'] = (df.fd_plus - df.fd_minus).abs() / df.fd_central.abs()
    df.to_csv(c.STATS / 'fd_checks.csv', index=False)
    print(df.to_string())


def structure():
    """Properties of the primary surrogate target, dJ/dkappa_v, in the reference adjoint:
    dynamic range and concentration at several leads, decorrelation with lead, and how well local
    state gradients, or the adjoint identity dJ/dkappa ~ -sum_t (dz lambda_T dz T + dz lambda_S dz S) dt,
    reproduce its pattern. Writes stats/target_structure.json and cache/lead_decorrelation.csv."""
    from scipy.stats import spearmanr
    g = c.grid()
    d = c.run_dir(ADJ['REF'])
    wet = g['wetC']
    out = dict(leads={})
    z = np.load(c.CACHE / 'fields_REF.npz')
    for L in LEADS:
        a = np.abs(z['ADJdiffkr_L%.3f' % L][wet].astype(np.float64))
        a = a[a > 0]
        srt = np.sort(a)[::-1]
        cum = np.cumsum(srt) / srt.sum()
        out['leads']['%.3f' % L] = dict(
            log10_p01=float(np.log10(np.percentile(a, 1))), log10_p50=float(np.log10(np.percentile(a, 50))),
            log10_p99=float(np.log10(np.percentile(a, 99))), log10_max=float(np.log10(a.max())),
            frac_cells_50pct=float((cum < 0.5).sum() + 1) / wet.sum(), frac_cells_90pct=float((cum < 0.9).sum() + 1) / wet.sum())
    # decorrelation with lead: every 2nd dump against the 5-yr accumulation and against the previous kept dump
    rows = []
    fin = {v: load32(d, v, c.ITERS[0])[wet].astype(np.float64) for v in ('ADJdiffkr', 'ADJtheta')}
    prev = {}
    w = c.weights('ADJdiffkr')[wet]
    for it in c.ITERS[::2]:
        for v in ('ADJdiffkr', 'ADJtheta'):
            a = load32(d, v, it)[wet].astype(np.float64)
            rows.append(dict(var=v, iter=int(it), lead_yr=float(c.lead_years(it)), corr_with_5yr=c.pattern_corr(a, fin[v], w),
                             corr_with_previous=c.pattern_corr(a, prev[v], w) if v in prev else np.nan))
            prev[v] = a
    pd.DataFrame(rows).to_csv(c.CACHE / 'lead_decorrelation.csv', index=False)
    # local predictors from the time-mean state of the window (the run's own monthly dynDiag)
    diags = sorted(d.glob('dynDiag.*.data'))
    T = np.mean([c.read_record(str(p)[:-5], 'THETA') for p in diags], axis=0)
    S = np.mean([c.read_record(str(p)[:-5], 'SALT') for p in diags], axis=0)
    R = np.mean([c.read_record(str(p)[:-5], 'RHOAnoma') for p in diags], axis=0)
    drc = np.atleast_1d(np.squeeze(c.read_mds(c.run_dir(c.SPINUP_JOB) / 'DRC')))

    def dz_top(X):
        # derivative at the top interface of each cell (where diffKr(k) acts), zero at the surface
        D = np.zeros_like(X)
        D[1:] = (X[:-1] - X[1:]) / drc[1:X.shape[0], None, None]
        return D
    wet_if = wet.copy()
    wet_if[1:] &= wet[:-1]
    wet_if[0] = False
    target = np.load(c.CACHE / 'adxx_REF.npz')['adxx_diffkr']
    dT, dS, dR = dz_top(T), dz_top(S), dz_top(R)
    # the adjoint identity, with the window-mean state and the 5-d ADJ dumps
    ident = np.zeros_like(T)
    for it in c.ITERS:
        ident -= dz_top(load32(d, 'ADJtheta', it).astype(np.float64)) * dT + dz_top(load32(d, 'ADJsalt', it).astype(np.float64)) * dS
    ident *= c.DUMP_STRIDE * c.DT
    m = wet_if
    tgt = target[m]
    preds = {'|dT/dz|': np.abs(dT[m]), '|dS/dz|': np.abs(dS[m]), '|drho/dz| (N^2 proxy)': np.abs(dR[m]),
             'adjoint identity (window-mean state)': ident[m]}
    out['local_predictors'] = {}
    for k, v in preds.items():
        if k.startswith('adjoint'):
            per_level = [spearmanr(np.abs(ident[kk][m[kk]]), np.abs(target[kk][m[kk]])).correlation
                         for kk in range(1, c.KMAX) if m[kk].sum() > 50]
            out['local_predictors'][k] = dict(pattern_corr=c.pattern_corr(v, tgt, c.weights('adxx_diffkr')[m]),
                                              spearman_abs=float(spearmanr(np.abs(v), np.abs(tgt)).correlation),
                                              spearman_abs_within_levels=float(np.nanmean(per_level)),
                                              regression_slope=float((v * tgt).sum() / (v * v).sum()))
        else:
            full = {'|dT/dz|': np.abs(dT), '|dS/dz|': np.abs(dS), '|drho/dz| (N^2 proxy)': np.abs(dR)}[k]
            per_level = []
            for kk in range(1, c.KMAX):      # rank correlation within each level, so shared depth decay does not count
                mk = m[kk]
                if mk.sum() > 50:
                    per_level.append(spearmanr(full[kk][mk], np.abs(target[kk][mk])).correlation)
            out['local_predictors'][k] = dict(spearman_abs=float(spearmanr(v, np.abs(tgt)).correlation),
                                              spearman_abs_within_levels=float(np.nanmean(per_level)))
    np.savez_compressed(c.CACHE / 'identity_REF.npz', identity=ident.astype(np.float32))
    (c.STATS / 'target_structure.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--dev', action='store_true')
    ap.add_argument('steps', nargs='+')
    a = ap.parse_args()
    c.ensure_dirs()
    if a.dev:
        ADJ.clear()
        ADJ['REF'] = c.PREV_GMFWD_5YR_JOB
        c.CACHE = c.ANALYSIS / 'dev_cache'
        c.STATS = c.ANALYSIS / 'dev_stats'
        c.CACHE.mkdir(parents=True, exist_ok=True)
        c.STATS.mkdir(parents=True, exist_ok=True)
    steps = ['verify', 'timeseries', 'members', 'fields', 'tables', 'fd', 'structure'] if a.steps == ['all'] else a.steps
    for s in steps:
        globals()[s]()
