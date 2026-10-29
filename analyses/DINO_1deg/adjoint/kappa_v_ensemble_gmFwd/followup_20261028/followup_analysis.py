#!/usr/bin/env python3
"""Analysis of the follow-up runs of 2026-10-28/29 (the questions of the meeting of 28 October):

    python followup_analysis.py swap     operator-versus-state experiment (question 1): amplitude of ADJtheta per
                                         run at matched lead -> analysis/kappa_v_operator_vs_state/swap_results.csv
    python followup_analysis.py sweep    latitude sweep of 1-yr adjoints (question 3): correlation between
                                         neighbouring sections -> analysis/cost_section_sweep/sweep_results.csv,
                                         sweep_corr_1yr.csv
    python followup_analysis.py fd       localised kappa_v finite-difference check (questions 6/7)
                                         -> analysis/kappa_v_ensemble_gmFwd_sec43N/perturbed_diffkr/fd_box_result.json
    python followup_analysis.py ownmax   the 8x member's adjoint at its own maximum against its fixed-section
                                         adjoint (question 5) -> analysis/cost_section_sweep/ownmax_result.json

Each campaign's job_map.tsv on scratch (analysis/<campaign>/) says which run is which; the run directories are found
wherever they are filed under runs/adjoint/. Each subcommand tolerates runs that have not finished and reports what
exists. Products on scratch, as for the rest of the suite; campaign.py supplies the grid, the readers and the metrics.
"""
import csv
import glob
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ.setdefault('CAMPAIGN_NAME', 'kappa_v_ensemble_gmFwd_sec43N')
import numpy as np        # noqa: E402
import campaign as c      # noqa: E402

AN = c.OUTPUTS / 'analysis'
SWAP = AN / 'kappa_v_operator_vs_state'
SWEEP = AN / 'cost_section_sweep'
SEC43 = AN / 'kappa_v_ensemble_gmFwd_sec43N'
RUNS_ADJ = c.OUTPUTS / 'runs' / 'adjoint'
g = c.grid()
wet, vol, lat = g['wetC'], g['vol'], g['lat']
NITER0 = c.NITER0            # year 180, the start of every adjoint window here


def job_map(path):
    return list(csv.DictReader(open(path), delimiter='\t'))


def rdir(job):
    """The run directory of a job, unfiled or filed one level down under runs/adjoint/."""
    h = glob.glob(str(RUNS_ADJ / ('*_run%s' % job))) + glob.glob(str(RUNS_ADJ / '*' / ('*_run%s' % job)))
    return h[0] if h else None


def dumps(d, var='ADJtheta'):
    return sorted(int(re.search(r'\.(\d{10})\.data$', f).group(1)) for f in glob.glob('%s/%s.*.data' % (d, var)))


def field(d, var, it):
    return c.read_mds(c.dump_base(d, var, it))


def fc(d):
    try:
        return c.first_fc(d)
    except Exception:
        return None


def stats(a):
    a = np.where(wet, a, 0.0)
    return dict(rms=c.rms(a[wet], vol[wet]), sum=float(a[wet].sum()), sum_abs=float(np.abs(a[wet]).sum()),
                maxabs=float(np.abs(a).max()))


def swap():
    rows = []
    for r in job_map(SWAP / 'job_map.tsv'):
        d = rdir(r['job'])
        its = dumps(d) if d else []
        if not its:
            print(r['job'], r['experiment'], 'no dumps yet'); continue
        n = int(r['duration_d']) * 48
        lead_days = [(NITER0 + n - it) / 48.0 for it in its]
        want = [30] if int(r['duration_d']) == 30 else [30, 180, 366]
        want = [L for L in want if max(lead_days) >= L - 3]
        if not want:
            print(r['job'], r['experiment'], 'incomplete: last lead %.0f d' % max(lead_days)); continue
        for L in want:
            k = int(np.argmin([abs(x - L) for x in lead_days]))
            st = stats(field(d, 'ADJtheta', its[k]))
            rows.append(dict(job=r['job'], experiment=r['experiment'], duration_d=r['duration_d'],
                             lead_d=round(lead_days[k], 1), fc=fc(d), **st))
    with open(SWAP / 'swap_results.csv', 'w') as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
    ref = {(x['duration_d'], x['lead_d']): x for x in rows if 'REFstate_REFkappa' in x['experiment']}
    print('%-32s %5s %7s %10s %10s %10s %10s' % ('experiment', 'dur', 'lead', 'rms', 'rms/ref', 'sum', 'fc'))
    for x in rows:
        rf = ref.get((x['duration_d'], x['lead_d']))
        print('%-32s %5s %7.1f %10.3e %10.2f %10.3e %10s' % (
            x['experiment'], x['duration_d'], x['lead_d'], x['rms'], x['rms'] / rf['rms'] if rf else np.nan, x['sum'],
            ('%.4f' % x['fc']) if x['fc'] else '-'))


def sweep():
    runs = sorted([r for r in job_map(SWEEP / 'job_map.tsv') if r['experiment'].startswith('sweep')],
                  key=lambda r: int(r['jsec']))
    data = {}
    for r in runs:
        d = rdir(r['job']); its = dumps(d) if d else []
        if not its:
            print(r['job'], r['experiment'], 'no dumps yet'); continue
        n = 366 * 48
        lead_days = [(NITER0 + n - it) / 48.0 for it in its]
        if max(lead_days) < 360:
            print(r['job'], r['experiment'], 'incomplete: last lead %.0f d' % max(lead_days)); continue
        k30 = int(np.argmin([abs(x - 30) for x in lead_days])); k1 = int(np.argmin([abs(x - 366) for x in lead_days]))
        data[int(r['jsec'])] = dict(job=r['job'], lat=float(lat[int(r['jsec']) - 1]), f30=field(d, 'ADJtheta', its[k30]),
                                    f1=field(d, 'ADJtheta', its[k1]), fc=fc(d))
    js = sorted(data)
    rows = []
    print('%-6s %7s %10s %10s %10s %8s %8s' % ('jsec', 'lat', 'J', 'rms30d', 'rms1yr', 'r30(nb)', 'r1yr(nb)'))
    for a, b in zip(js, js[1:] + [None]):
        A = data[a]
        row = dict(jsec=a, lat=A['lat'], job=A['job'], J=A['fc'], rms_30d=stats(A['f30'])['rms'], rms_1yr=stats(A['f1'])['rms'])
        if b is not None:
            B = data[b]; row['next_jsec'] = b; row['dlat'] = B['lat'] - A['lat']
            row['corr_30d_next'] = c.pattern_corr(A['f30'][wet], B['f30'][wet], vol[wet])
            row['corr_1yr_next'] = c.pattern_corr(A['f1'][wet], B['f1'][wet], vol[wet])
        rows.append(row)
        print('%-6d %7.2f %10.4f %10.3e %10.3e %8s %8s' % (
            a, A['lat'], A['fc'] or np.nan, row['rms_30d'], row['rms_1yr'],
            ('%.2f' % row['corr_30d_next']) if b else '-', ('%.2f' % row['corr_1yr_next']) if b else '-'))
    M = np.array([[c.pattern_corr(data[a]['f1'][wet], data[b]['f1'][wet], vol[wet]) for b in js] for a in js])
    np.savetxt(SWEEP / 'sweep_corr_1yr.csv', M, delimiter=',', header=','.join(str(j) for j in js), fmt='%.3f')
    with open(SWEEP / 'sweep_results.csv', 'w') as f:
        keys = sorted({k for r in rows for k in r}); wr = csv.DictWriter(f, fieldnames=keys); wr.writeheader(); wr.writerows(rows)
    labels = ['%.0f %s' % (abs(l), 'N' if l > 0 else 'S') for l in (data[j]['lat'] for j in js)]
    for a in range(len(js)):
        dd = [abs(data[js[b]]['lat'] - data[js[a]]['lat']) for b in range(len(js))
              if M[a, b] < 0.5 and np.sign(data[js[b]]['lat']) == np.sign(data[js[a]]['lat'])]
        print('%6s: correlation below 0.5 beyond %s' % (labels[a], ('%.0f deg' % min(dd)) if dd else 'the sampled range'))


def fd_check():
    info = json.load(open(SEC43 / 'perturbed_diffkr' / 'box_definition.json'))
    J = {}
    for r in job_map(SEC43 / 'job_map.tsv'):
        if 'diffkrBox' in r['role']:
            d = rdir(r['job']); J['p' if 'diffkrBox_p' in r['role'] else 'm'] = fc(d) if d else None
    J0 = c.first_fc(c.run_dir(c.ADJ_JOB['REF']))
    print('J+ %s  J- %s  J0 %.6f' % (J.get('p'), J.get('m'), J0))
    if J.get('p') and J.get('m'):
        fdc = 0.5 * (J['p'] - J['m']); pred = info['predicted_dJ_central']
        out = dict(J_plus=J['p'], J_minus=J['m'], J0=J0, fd_central=fdc, fd_plus=J['p'] - J0, fd_minus=J0 - J['m'],
                   adjoint=pred, adjoint_rel_err=pred / fdc - 1, sigma=info['sigma_J_monthly'],
                   fd_over_sigma=abs(fdc) / info['sigma_J_monthly'], box=info['box'])
        json.dump(out, open(SEC43 / 'perturbed_diffkr' / 'fd_box_result.json', 'w'), indent=1)
        print(json.dumps(out, indent=1))


def ownmax():
    r = [x for x in job_map(SWEEP / 'job_map.tsv') if x['experiment'].startswith('ownmax')][0]
    d = rdir(r['job']); its = dumps(d) if d else []
    if not its:
        print('own-max run: no dumps yet'); return
    ref = str(c.run_dir(c.ADJ_JOB['M5']))      # the 8x member's fixed-section adjoint (31558)
    n = 1830 * 48
    print('own-max run %s: %d dumps, fc %s; fixed-section run %s fc %s' % (r['job'], len(its), fc(d), ref, fc(ref)))
    res = {}
    for L in (30, 366, 1098, 1830):
        it = min(its, key=lambda x: abs((NITER0 + n - x) / 48.0 - L))
        a = field(d, 'ADJtheta', it); b = field(ref, 'ADJtheta', it)
        res[L] = dict(corr=c.pattern_corr(a[wet], b[wet], vol[wet]), rms_ratio=stats(a)['rms'] / stats(b)['rms'],
                      corr_colsum=c.pattern_corr(np.where(wet, a, 0).sum(0)[wet[0]], np.where(wet, b, 0).sum(0)[wet[0]]))
        print('lead %5d d (iter %d): corr(own-max, fixed) = %.3f  column-sum corr %.3f  rms ratio %.2f' % (
            L, it, res[L]['corr'], res[L]['corr_colsum'], res[L]['rms_ratio']))
        if L == 366:
            np.savez(SWEEP / 'ownmax_1yr_fields.npz', own=np.where(wet, a, 0).sum(0), fixed=np.where(wet, b, 0).sum(0))
    for v in ('adxx_theta', 'adxx_diffkr'):
        a = c.read_mds('%s/%s.0000000000' % (d, v)); b = c.read_mds('%s/%s.0000000000' % (ref, v))
        res[v] = dict(corr=c.pattern_corr(a[wet], b[wet], vol[wet]), sum_own=float(a[wet].sum()), sum_fixed=float(b[wet].sum()))
        print('%s: corr %.3f, sum own %.4g fixed %.4g' % (v, res[v]['corr'], res[v]['sum_own'], res[v]['sum_fixed']))
    json.dump(dict(fc_own=fc(d), fc_fixed=fc(ref), leads=res), open(SWEEP / 'ownmax_result.json', 'w'), indent=1)


if __name__ == '__main__':
    {'swap': swap, 'sweep': sweep, 'fd': fd_check, 'ownmax': ownmax}[sys.argv[1]]()
