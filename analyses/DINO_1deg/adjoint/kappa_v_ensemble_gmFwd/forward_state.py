#!/usr/bin/env python3
"""Forward-model side of the campaign: the cost proxy's internal variability, the forward legs, and
the restart check.

    python forward_state.py spinup     # 31203's 2,400 monthly dynDiag -> cache/spinup_series.csv,
                                       #   stats/noise_floor.json
    python forward_state.py legs       # the eight 10-yr legs -> cache/leg_series.csv,
                                       #   cache/leg_final_profiles.npz, stats/restart_check.json

Indices per monthly (30.5-d mean) dynDiag record: jproxy, the compiled cost formula applied to VVEL
(campaign.jproxy; fc itself averages the final 30 d of an adjoint window); the overturning maximum
above 1000 m at 26 N and 41 N; the volume-mean temperature and salinity.
"""
import json
import sys
from multiprocessing import Pool
from pathlib import Path
import filecmp
import glob
import re

import numpy as np
import pandas as pd

import campaign as c


def indices(base):
    g = c.grid()
    v = c.read_record(base, 'VVEL')
    th = c.read_record(base, 'THETA')
    sa = c.read_record(base, 'SALT')
    it = int(re.search(r'\.(\d{10})$', str(base)).group(1))
    return dict(iter=it, year=it / c.STEPS_PER_YEAR, jproxy=c.jproxy(v, g),
                amoc26=c.amoc_index(v, 26.0, g), amoc41=c.amoc_index(v, 41.0, g),
                Tmean=float((th * g['vol']).sum() / g['vol'].sum()),
                Smean=float((sa * g['vol']).sum() / g['vol'].sum()))


def series(d):
    bases = sorted(p[:-5] for p in glob.glob(str(Path(d) / 'dynDiag.*.data')))
    c.grid()
    with Pool(6) as pool:
        rows = pool.map(indices, bases, chunksize=20)
    return pd.DataFrame(rows).sort_values('iter').reset_index(drop=True)


def spinup():
    c.ensure_dirs()
    d = c.run_dir(c.SPINUP_JOB)
    df = series(d)
    df.to_csv(c.CACHE / 'spinup_series.csv', index=False)
    # internal variability over the last 100 years, after removing a linear trend
    w = df[df.year > 100].copy()
    t = w.year.values
    out = {}
    for k in ('jproxy', 'amoc26'):
        x = w[k].values
        x_d = x - np.polyval(np.polyfit(t, x, 1), t)
        ann = pd.Series(x_d).groupby(np.arange(len(x_d)) // 12).mean().values
        out[k] = dict(mean=float(x.mean()), std_monthly=float(x_d.std(ddof=1)),
                      std_annual=float(ann.std(ddof=1)),
                      lag1_monthly=float(np.corrcoef(x_d[:-1], x_d[1:])[0, 1]),
                      lag1_annual=float(np.corrcoef(ann[:-1], ann[1:])[0, 1]),
                      trend_per_century=float(np.polyfit(t, x, 1)[0] * 100))
    out['spinup_job'] = c.SPINUP_JOB
    out['years'] = [float(w.year.min()), float(w.year.max())]
    out['n_months'] = int(len(w))
    out['note'] = ('std of 30.5-d means of the cost formula applied to the spin-up\'s dynDiag VVEL, from year 100 to its '
                   'end, linear trend removed; fc is one terminal 30-d mean, so std_monthly is its noise floor')
    (c.STATS / 'noise_floor.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


def legs():
    c.ensure_dirs()
    g = c.grid()
    frames, prof = [], {}
    spin = c.run_dir(c.SPINUP_JOB)
    for r in c.RUN_ORDER:
        d = c.run_dir(c.LEG_JOB[r])
        df = series(d)
        df.insert(0, 'run', r)
        frames.append(df)
        last = sorted(glob.glob(str(d / 'dynDiag.*.data')))[-12:]
        th = np.mean([c.read_record(p[:-5], 'THETA') for p in last], axis=0)
        sa = np.mean([c.read_record(p[:-5], 'SALT') for p in last], axis=0)
        v = np.mean([c.read_record(p[:-5], 'VVEL') for p in last], axis=0)
        prof[r + '_T'], prof[r + '_S'], prof[r + '_psi'] = th, sa, c.overturning(v, g)
    # the spin-up's own years 170-180 for the same indices
    sp = pd.read_csv(c.CACHE / 'spinup_series.csv')
    sp = sp[sp.iter > c.LEG_NITER0 - 20 * c.STEPS_PER_YEAR].copy()      # the spin-up's last 20 years, as context
    sp.insert(0, 'run', 'spinup')
    pd.concat(frames + [sp]).to_csv(c.CACHE / 'leg_series.csv', index=False)
    np.savez_compressed(c.CACHE / 'leg_final_profiles.npz', **prof)
    # The rerun of the spin-up's last 61 days against the spin-up itself (every file both wrote, and the %MON blocks),
    # and the new spin-up's year-170 and the REF leg's year-180 pickups against the production spin-up 31203's.
    res = {}
    end = c.run_dir(c.SPINUP_END_JOB) if c.SPINUP_END_JOB else None
    if end is not None:
        both = sorted(p.name for p in end.glob('*.data') if (spin / p.name).exists() and not (end / p.name).is_symlink()
                      and not (spin / p.name).is_symlink() and p.name.startswith(('dynDiag', 'surfDiag', 'atmDiag', 'viscDiag', 'pickup.0')))
        same = [n for n in both if filecmp.cmp(end / n, spin / n, shallow=False)]
        res['spinup_end_rerun_vs_spinup'] = dict(files_compared=both, identical=len(same), different=len(both) - len(same))
    ref = c.run_dir(c.LEG_JOB['REF'])
    rel = 'runs/forward/spinup_200yr_viscRef_ReMax2/DINO_1deg_frd_200yr_from_rest_viscRef_ReMax2_run31203'
    old = next((r / rel for r in (c.OUTPUTS, c.EARLIER_OUTPUTS) if (r / rel).is_dir()), c.OUTPUTS / rel)
    yr170 = (end or spin) / ('pickup.%010d.data' % c.LEG_NITER0)
    try:
        res['spinup_year170_vs_31203'] = bool(filecmp.cmp(yr170, old / ('pickup.%010d.data' % c.LEG_NITER0), shallow=False))
        res['REF_leg_year180_vs_31203'] = bool(filecmp.cmp(ref / ('pickup.%010d.data' % c.NITER0), old / ('pickup.%010d.data' % c.NITER0), shallow=False))
    except OSError as e:
        res['vs_31203'] = 'not compared: 31203 not readable (%s)' % type(e).__name__
    (c.STATS / 'restart_check.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))

if __name__ == '__main__':
    {'spinup': spinup, 'legs': legs}[sys.argv[1]]()
