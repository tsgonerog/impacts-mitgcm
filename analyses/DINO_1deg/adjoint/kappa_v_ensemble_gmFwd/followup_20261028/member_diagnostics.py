#!/usr/bin/env python3
"""Two diagnostics of the kappa_v ensemble made for the meeting review of 2026-10-28 (question 1), for the campaign
CAMPAIGN_NAME (default the 43 N one):

    python member_diagnostics.py sums    per member and lead, the volume-weighted RMS of ADJtheta, its plain sum over
                                         wet cells (the response of J to a uniform +1 K warming), the sum of its
                                         absolute value, and the same restricted to the upper 1000 m
                                         -> analysis/<campaign>/stats/theta_sum_vs_rms_by_member.json
    python member_diagnostics.py state   how the members' adjusted states differ at the cost row (zonal mean over wet
                                         cells): upper-848 m mean T, T below, the depth of the steepest temperature
                                         gradient, dT/dz at 791 m, a first-mode speed proxy, the basin-mean T and the
                                         overturning maximum at the row -> analysis/<campaign>/stats/leg_state_at_<row>.txt
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ.setdefault('CAMPAIGN_NAME', 'kappa_v_ensemble_gmFwd_sec43N')
import numpy as np        # noqa: E402
import campaign as c      # noqa: E402

g = c.grid()
vol, wet, RC, RF, DRF = g['vol'], g['wetC'], g['RC'], g['RF'], g['DRF']


def sums():
    upper = RC > -1000.0
    leads = [0.082, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0]
    out = {}
    for run in c.RUN_ORDER:
        job = c.ADJ_JOB[run]
        out[run] = {}
        for L in leads:
            it = c.nearest_iter(L)
            a = np.where(wet, c.adj(job, 'ADJtheta', it), 0.0)
            up = wet & upper[:, None, None]
            out[run]['%.3f' % L] = dict(
                iter=int(it), lead_yr=float(c.lead_years(it)), rms_vol=c.rms(a[wet], vol[wet]),
                sum_vol=float((vol * a).sum()), sum_abs_vol=float((vol * np.abs(a)).sum()),
                sum_cell=float(a[wet].sum()), sum_abs_cell=float(np.abs(a[wet]).sum()),
                sum_vol_upper1000=float((vol * a)[up].sum()), sum_abs_vol_upper1000=float((vol * np.abs(a))[up].sum()))
            r = out[run]['%.3f' % L]
            print('%-4s %5.3f rms %.3e sum %.3e |sum| %.3e' % (run, L, r['rms_vol'], r['sum_cell'], r['sum_abs_cell']), flush=True)
    c.STATS.mkdir(parents=True, exist_ok=True)
    json.dump(out, open(c.STATS / 'theta_sum_vs_rms_by_member.json', 'w'), indent=1)
    print('wrote', c.STATS / 'theta_sum_vs_rms_by_member.json')


def state():
    d = np.load(str(c.CACHE / 'leg_final_profiles.npz'))
    j, kmax = c.JSEC, c.KMAX
    lines = ['row %d (centre %.2f), interface %.0f m' % (j + 1, g['lat'][j], -RF[kmax]),
             'run  factor  T_up_row  T_below_row  z_maxdTdz  dTdz_791m  c1proxy  Tbasin  psi_max_row']
    k791 = int(np.argmin(np.abs(RC + 791)))
    for run in c.RUN_ORDER:
        T = d[run + '_T']; psi = d[run + '_psi']
        w = wet[:, j, :]
        Tz = np.array([T[k, j, :][w[k]].mean() if w[k].any() else np.nan for k in range(36)])
        up = np.nansum(Tz[:kmax] * DRF[:kmax]) / DRF[:kmax].sum()
        lo = np.nanmean(Tz[kmax:30])
        dTdz = np.gradient(Tz, RC)                                   # z upward: positive when warmer above
        kk = 4 + int(np.nanargmax(np.abs(dTdz[4:30])))               # below the mixed layer
        N = np.sqrt(np.maximum(9.81 * 2e-4 * dTdz, 0)); c1 = np.nansum(N * DRF) / np.pi
        Tb = float((vol * T)[wet].sum() / vol[wet].sum())
        lines.append('%-4s %5.2f  %8.3f  %8.3f  %8.0f  %9.4f  %7.2f  %7.3f  %7.2f' % (
            run, c.FACTOR[run], up, lo, RC[kk], dTdz[k791], c1, Tb, np.nanmax(psi[:, j])))
    c.STATS.mkdir(parents=True, exist_ok=True)
    out = c.STATS / ('leg_state_at_%s.txt' % c.SEC_NAME.replace(' ', ''))
    out.write_text('\n'.join(lines) + '\n'); print('\n'.join(lines)); print('wrote', out)


if __name__ == '__main__':
    {'sums': sums, 'state': state}[sys.argv[1]]()
