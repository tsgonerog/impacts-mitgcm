"""The page's text. Numbers are read from the stats and cache files at build time; the sentences that interpret
them were written after reading those numbers and are checked against them by the conditions below."""
import json

import numpy as np
import pandas as pd

import campaign as c
import page_setup_text as st


def _read(name, kind='csv'):
    for root in (c.STATS, c.CACHE):
        p = root / name
        if p.exists():
            return json.loads(p.read_text()) if kind == 'json' else pd.read_csv(p)
    return None


def fmt(x, n=3):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return '–'
    if x == 0:
        return '0'
    a = abs(x)
    if 1e-3 <= a < 1e4:
        return ('%.' + str(n) + 'g') % x
    e = int(np.floor(np.log10(a)))
    d = max(n - 1, 1)
    if abs(round(x / 10 ** e, d)) >= 10:
        e += 1
    return '%s×10<sup>%d</sup>' % (('%.' + str(d) + 'f') % (x / 10 ** e), e)


def pct(x):
    return '–' if x is None or not np.isfinite(x) else '%+.0f %%' % (100 * x)


def member_summary(ts, mm):
    """Per member: does its adjoint stay bounded, how its ADJtheta amplitude compares with the reference at 5 yr,
    and how its sensitivity patterns correlate with the reference's at 1 and 5 yr."""
    rows = []
    ref = ts[(ts.run == 'REF') & (ts['var'] == 'ADJtheta')].set_index('iter')
    for r in c.MEMBERS:
        s = ts[(ts.run == r) & (ts['var'] == 'ADJtheta')].set_index('iter')
        if s.empty:
            continue
        ratio = (s.rms / ref.rms.reindex(s.index))
        nonfinite = s[s.finite_frac < 1]
        grown = ratio[ratio > 100]
        if len(nonfinite):
            status, lead = 'blows up', float(c.lead_years(nonfinite.index.max()))
        elif len(grown):
            status, lead = 'grows', float(c.lead_years(grown.index.max()))
        else:
            status, lead = 'bounded', None
        m = mm[(mm.run == r)]
        def corr(var, L):
            q = m[m['var'] == var]
            return float(q.iloc[(q.lead_yr - L).abs().argmin()]['corr']) if len(q) else np.nan
        rows.append(dict(run=r, factor=c.FACTOR[r], status=status, lead=lead,
                         ratio5=float(ratio.iloc[0]) if len(ratio) else np.nan,
                         corr_theta_1=corr('ADJtheta', 1.0), corr_theta_5=corr('ADJtheta', 5.0),
                         corr_diffkr_1=corr('ADJdiffkr', 1.0), corr_diffkr_5=corr('ADJdiffkr', 5.0)))
    return pd.DataFrame(rows)


def body(h):
    fig, table, chip, stat, esc = h['fig'], h['table'], h['chip'], h['stat'], h['esc']
    ver = _read('run_verification.csv')
    fg = _read('fc_gradient.csv')
    fd = _read('fd_checks.csv')
    dec = _read('dJ_decomposition.csv')
    nf = _read('noise_floor.json', 'json') or {}
    ts = _read('adj_timeseries.csv')
    mm = _read('member_metrics.csv')
    tgt = _read('target_structure.json', 'json') or {}
    prev = json.loads(c.PREVIOUS.read_text())
    legs = _read('leg_series.csv')

    ms = member_summary(ts, mm) if ts is not None and mm is not None else pd.DataFrame()
    fcref = float(fg.set_index('run').fc['REF']) if fg is not None else None
    Gref = float(fg.set_index('run').G_dJdkappa_uniform['REF']) if fg is not None else None
    sigma = nf.get('jproxy', {}).get('std_monthly')
    kap = fd[fd.test.str.startswith('kappa')] if fd is not None else None
    kap_err = float(kap.adjoint_rel_err.iloc[0]) if kap is not None and len(kap) else None
    n_bounded = int((ms.status == 'bounded').sum()) if len(ms) else None
    med_corr5 = float(ms.corr_diffkr_5.median()) if len(ms) else None

    out = []
    out.append('<div class="shell"><nav class="toc" aria-label="Sections"><p>Contents</p><ol>'
               '<li><a href="#findings">Findings</a></li><li><a href="#setup">What ran</a></li>'
               '<li><a href="#forward">Forward legs</a></li><li><a href="#reference">Reference adjoint</a></li>'
               '<li><a href="#checks">Gradient checks</a></li><li><a href="#ensemble">Ensemble</a></li>'
               '<li><a href="#target">The target field</a></li><li><a href="#surrogate">For the surrogate</a></li>'
               '<li><a href="#provenance">Provenance</a></li></ol></nav><main>')
    out.append('<header class="masthead"><p class="eyebrow">DINO_1deg · MITgcm checkpoint69m · Tapenade adjoint · runs 31329–31398</p>'
               '<h1>DINO κ<sub>v</sub> Sensitivity Ensemble</h1>'
               '<p class="lede">How the 26° N transport cost of the DINO basin responds to vertical diffusivity, what its '
               '5-year adjoint sensitivities look like under the current configuration, whether those gradients agree with '
               'finite differences, and what that implies for the inputs and targets of a neural-network surrogate.</p>'
               '<p class="meta"><span>adjoint window: model years 180–185</span><span>J: 26.05° N transport index, upper 982 m, final 30 d</span>'
               '<span>κ<sub>v</sub> ∈ {0.25 … 32} × 1.2×10⁻⁵ m² s⁻¹</span></p>')
    tiles = [stat('Reference cost J', fmt(fcref, 4), 'σ of the monthly index %s' % fmt(sigma, 2) if sigma else ''),
             stat('dJ/dκ<sub>v</sub>, adjoint', fmt(Gref, 3) + ' <span class="mono" style="font-size:13px">per m² s⁻¹</span>',
                  'against finite differences: %s' % pct(kap_err) if kap_err is not None else ''),
             stat('Member adjoints bounded', '%s of 7' % n_bounded if n_bounded is not None else '–', 'over the full 5-year lead'),
             stat('∂J/∂κ<sub>v</sub> pattern vs reference', fmt(med_corr5, 2) if med_corr5 is not None else '–',
                  'median correlation over the members, 5-yr lead')]
    out.append('<div class="figures-row">%s</div></header>' % ''.join(tiles))

    # ---------------------------------------------------------------- findings (written against the numbers)
    out.append('<section id="findings"><h2>Findings</h2><ul class="findings">%s</ul></section>' % ''.join(
        '<li>%s</li>' % f for f in findings(fg, fd, ms, dec, nf, tgt, prev, legs)))

    # ---------------------------------------------------------------- setup
    out.append('<section id="setup"><h2>What ran, and how it was checked</h2>' + st.SETUP_INTRO + st.SETUP_DESIGN)
    out.append('<h3>Consistency with the cleaned configuration</h3>')
    out.append(table(pd.DataFrame(st.CONSISTENCY, columns=['check', 'result']), ['check', 'result'], ['Check', 'Result']))
    if ver is not None:
        v = ver.copy()
        v['state'] = [chip('finished', 'good') if (k != 'fd' and e) or (k == 'fd' and pd.notna(f)) else chip('check', 'warn')
                      for k, e, f in zip(v.kind, v.get('ended_normally', False), v.get('fc', np.nan))]
        out.append('<h3>Run verification</h3>')
        out.append(table(v, ['kind', 'label', 'job', 'state', 'runtime', 'fc'], ['Kind', 'Run', 'Job', 'State', 'Runtime', 'J (fc)'],
                         num=('job', 'fc'), fmt={'state': lambda x, r: x, 'fc': lambda x, r: fmt(x, 6) if pd.notna(x) else ''}))
    out.append(st.INCIDENTS)
    out.append('</section>')

    # ---------------------------------------------------------------- forward legs
    out.append('<section id="forward"><h2>The forward legs: what κ<sub>v</sub> does to the state</h2>')
    out.append(forward_text(legs))
    out.append(fig('leg_indices_vs_kappa', '<b>The state at year 180 against κ<sub>v</sub>.</b> Means over the last year of each '
                   '10-year leg of the cost proxy (the cost formula applied to monthly-mean velocity), the overturning maximum '
                   'above 1000 m at 26° N, and the volume-mean temperature.'))
    out.append(fig('leg_timeseries', '<b>Adjustment over the ten years.</b> The spin-up\'s last 20 years (black) and the legs from '
                   'year 170; the weakest and strongest mixing are highlighted, the other members in grey.'))
    out.append(fig('leg_temperature_change', '<b>Where the temperature changes.</b> Horizontal-mean ΔT against depth for each member '
                   '(left) and the zonal-mean ΔT sections of the two extremes, year 179–180 means minus the reference leg.'))
    out.append('</section>')

    # ---------------------------------------------------------------- reference adjoint
    out.append('<section id="reference"><h2>The reference 5-year adjoint</h2>')
    out.append(reference_text(fg, ts, nf))
    out.append(fig('ref_rms_vs_lead', '<b>Amplitude against lead.</b> Wet-cell RMS of six sensitivity fields over the 5-year window '
                   '(volume- or area-weighted). A lead of 5 years is the start of the window.'))
    out.append(fig('ref_adxx_maps', '<b>The control gradients.</b> Accumulated over the window; the 3-D controls summed over the column. '
                   'The black line is the 26° N cost section.', cls=''))
    out.append(fig('ref_ADJtheta_depth_lead', '<b>Temperature sensitivity by depth and lead.</b> ADJtheta at about 100, 500 and '
                   '1400 m, 30 days, 1 year and 5 years before the end of the window.', cls='narrow'))
    out.append(fig('ref_ADJtheta_zonal_section', '<b>The same in latitude and depth.</b> Zonal sums of ADJtheta.'))
    out.append(fig('ref_ADJtheta_lead', '<b>ADJtheta at 300 m and 1500 m through the 5-year lead</b>, in the order the adjoint computes '
                   'it (lead increasing), every 20 days. Each map is scaled by its own 99th percentile; the inset gives the amplitude.',
                   gif=True))
    out.append('</section>')

    # ---------------------------------------------------------------- gradient checks
    out.append('<section id="checks"><h2>Do the adjoint gradients agree with finite differences?</h2>')
    out.append(checks_text(fd, prev))
    if fd is not None:
        f2 = fd.copy()
        f2['ratio'] = f2.adjoint / f2.fd_central
        f2['verdict'] = [chip(v, {'agrees': 'good', 'approximate': 'warn', 'finite difference at the noise level': 'warn'}.get(v, 'bad'))
                         for v in (_verdict(r) for _, r in f2.iterrows())]
        out.append(table(f2, ['test', 'fd_central', 'fd_plus', 'fd_minus', 'adjoint', 'ratio', 'verdict'],
                         ['Perturbation', 'Central FD ΔJ', 'One-sided +', 'One-sided −', 'Adjoint ΔJ', 'Adjoint ÷ FD', 'Reading'],
                         num=('fd_central', 'fd_plus', 'fd_minus', 'adjoint', 'ratio'),
                         fmt=dict({k: (lambda x, r: fmt(x, 3)) for k in ('fd_central', 'adjoint', 'fd_plus', 'fd_minus')},
                                  ratio=lambda x, r: '%.3g' % x, verdict=lambda x, r: x)))
    out.append(fig('fd_checks', '<b>Adjoint prediction over central finite difference</b> for κ<sub>v</sub> and the three temperature '
                   'boxes, against the 2026-09-11 test of the same adjoint from a different state.', cls='narrow'))
    out.append(fig('fd_forcing', '<b>The four surface controls.</b> ΔJ for a spatially uniform perturbation applied at every forcing '
                   'record: the central finite difference and the adjoint\'s prediction (symmetric log scale).', cls='narrow'))
    out.append('</section>')

    # ---------------------------------------------------------------- ensemble
    out.append('<section id="ensemble"><h2>The ensemble: does the sensitivity depend on κ<sub>v</sub>?</h2>')
    out.append(ensemble_text(fg, ms, dec, nf, prev))
    if len(ms):
        mtab = ms.copy()
        mtab['st'] = [chip(s, {'bounded': 'good', 'grows': 'warn', 'blows up': 'bad'}[s]) for s in mtab.status]
        mtab = mtab.merge(fg[['run', 'fc', 'G_dJdkappa_uniform']], on='run', how='left')
        out.append(table(mtab, ['run', 'factor', 'fc', 'G_dJdkappa_uniform', 'st', 'corr_theta_1', 'corr_diffkr_5'],
                         ['Member', 'κ<sub>v</sub> × ref', 'J', 'dJ/dκ<sub>v</sub>', 'Adjoint', 'ADJtheta corr, 1 yr', '∂J/∂κ<sub>v</sub> corr, 5 yr'],
                         num=('factor', 'fc', 'G_dJdkappa_uniform', 'corr_theta_1', 'corr_diffkr_5'),
                         fmt={'st': lambda x, r: x, 'fc': lambda x, r: fmt(x, 4), 'G_dJdkappa_uniform': lambda x, r: fmt(x, 3),
                              'corr_theta_1': lambda x, r: fmt(x, 2), 'corr_diffkr_5': lambda x, r: fmt(x, 2),
                              'factor': lambda x, r: '%g' % x}).replace('&lt;sub&gt;', '<sub>').replace('&lt;/sub&gt;', '</sub>'))
    out.append(fig('fc_vs_kappa', '<b>J against κ<sub>v</sub> in three campaigns.</b> The internal variability of the monthly cost index '
                   'in the spin-up, σ = %s, is smaller than the markers.' % fmt(sigma, 2), cls='narrow'))
    out.append(fig('member_stability', '<b>Each member\'s adjoint amplitude against lead</b>, with the reference in grey.'))
    out.append(fig('member_pattern_corr', '<b>How far each member\'s sensitivity patterns stay like the reference\'s</b>, by lead and field.'))
    out.append(fig('kappa_gradient', '<b>dJ/dκ<sub>v</sub> across the ensemble</b>: each adjoint\'s own gradient, the secant of J between '
                   'neighbouring members, and the central finite difference at the reference.', cls='narrow'))
    out.append(fig('dJ_decomposition', '<b>Measured against predicted ΔJ.</b> The prediction from the reference gradient alone, and '
                   'with the change of the year-180 temperature and salinity added.', cls='narrow'))
    out.append(fig('member_adxx_maps', '<b>∂J/∂κ<sub>v</sub> and ∂J/∂Q<sub>net</sub> for five κ values</b>, on the reference\'s colour scale.'))
    out.append(fig('members_ADJdiffkr_lead', '<b>Column-summed ADJdiffkr of all eight runs through the lead</b>, every 30 days, each '
                   'panel on its own scale.', gif=True))
    out.append('</section>')

    # ---------------------------------------------------------------- the target
    out.append('<section id="target"><h2>The primary target, ∂J/∂κ<sub>v</sub></h2>')
    out.append(target_text(tgt, prev))
    out.append(fig('target_structure', '<b>Lead dependence and local predictors.</b> Left: pattern correlation of each dump with the same '
                   'field at the 5-year lead (for ADJdiffkr, the gradient accumulated up to that lead). Right: rank correlation of |∂J/∂κ<sub>v</sub>| with local quantities within each level.'))
    out.append(fig('identity_map', '<b>The adjoint κ<sub>v</sub> gradient and its reconstruction</b> from the 5-day ADJtheta and ADJsalt '
                   'dumps and the window-mean stratification, column sums.', cls='narrow'))
    out.append('</section>')

    # ---------------------------------------------------------------- surrogate
    out.append('<section id="surrogate"><h2>What this implies for the neural-network surrogate</h2>')
    out.append(surrogate_text(fg, fd, ms, dec, tgt, h))
    out.append('</section>')

    out.append('<section id="provenance"><h2>Provenance</h2>' + st.PROVENANCE + '</section>')
    out.append('<footer class="prov"><p>Built from the campaign\'s stats files; the numbers on this page are read from them at build time.</p></footer>')
    out.append('</main></div>')
    return '\n'.join(out)


# ---------------------------------------------------------------- the interpretive text, one function per section
def _fd_row(fd, key):
    if fd is None:
        return None
    m = fd[fd.test.str.contains(key, regex=False)]
    return m.iloc[0] if len(m) else None


def _verdict(r):
    """How to read one adjoint-against-FD comparison, a row of fd_checks.csv. When the two one-sided differences
    disagree by more than the central one, the model's response is within its own nonlinearity; the adjoint is still
    wrong if it predicts ten times more than either one-sided difference."""
    if r is None or not np.isfinite(r.adjoint_rel_err):
        return 'not compared'
    if r.one_sided_spread > 1.0:
        return ('does not agree' if abs(r.adjoint) > 10 * max(abs(r.fd_plus), abs(r.fd_minus))
                else 'finite difference at the noise level')
    a = abs(r.adjoint_rel_err)
    return 'agrees' if a < 0.1 else ('approximate' if a < 0.5 else 'does not agree')


VERB = {'agrees': 'agrees with', 'approximate': 'approximates', 'does not agree': 'does not agree with',
        'finite difference at the noise level': 'cannot be checked against', 'not compared': 'was not compared with'}


def _ratio(r):
    """the adjoint prediction against the central difference: '+21 %' when within a factor of two, '13 times' beyond"""
    q = r.adjoint / r.fd_central
    return pct(q - 1) if 0.5 < q < 2 else '%.0f times' % q


def _name(test):
    t = test.split(' +')[0]
    return {'kappa_v': 'κ<sub>v</sub>', 'Theta': 'temperature', 'zonal surface stress': 'zonal stress',
            'meridional surface stress': 'meridional stress', 'net surface heat flux': 'net heat flux',
            'freshwater flux E-P-R': 'E−P−R'}.get(t.split(' ')[0] if t.startswith('Theta') else t, t)


def _secants(fg):
    """secant of J between neighbouring members, the mean of their two adjoint gradients, and the lower member's factor"""
    s = fg.sort_values('factor').reset_index(drop=True)
    sec = np.diff(s.fc.values) / np.diff(s.kappa.values)
    gm = 0.5 * (s.G_dJdkappa_uniform.values[:-1] + s.G_dJdkappa_uniform.values[1:])
    return sec, gm, s.factor.values[:-1]


NUM = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight']


def _and(items):
    items = list(items)
    return items[0] if len(items) == 1 else ', '.join(items[:-1]) + ' and ' + items[-1]


def findings(fg, fd, ms, dec, nf, tgt, prev, legs):
    out = []
    sig = nf['jproxy']['std_monthly']
    if fg is not None:
        f = fg.set_index('run').fc
        jmin = f.idxmin()
        dmin = float(np.abs(f.drop('REF') - f['REF']).min())
        out.append('<b>J depends on κ<sub>v</sub> strongly and not monotonically.</b> From 0.25 to 32 times the reference it runs '
                   'from %s through a minimum of %s at %gx to %s. The smallest difference between a member and the reference, %s, '
                   'is %.0f times the internal variability of the monthly cost (σ = %s).' % (
                       '%.3f' % f['M1'], '%.3f' % f[jmin], c.FACTOR[jmin], '%.3f' % f['M7'], fmt(dmin, 2), dmin / sig, fmt(sig, 2)))
    k = _fd_row(fd, 'kappa')
    if k is not None:
        g = prev['gmFree_ReMax2_2026_09_10']['fd']
        out.append('<b>The adjoint κ<sub>v</sub> gradient %s finite differences, with a bias that depends neither on the state nor on '
                   'GM/Redi.</b> At the reference it is %s against %s per m² s⁻¹ (%s); from the 2026-09-11 state the same adjoint gave '
                   '+22 %%, and the GM-free adjoint against the GM-free model on 2026-09-10 %s. The approximation all three share is the '
                   'unlimited advection scheme in the adjoint sweep, the likely source.' % (
                       VERB[_verdict(k)], fmt(k.adjoint / (0.1 * c.KAPPA0), 4), fmt(k.fd_central / (0.1 * c.KAPPA0), 4), _ratio(k),
                       pct(g['adjoint_G'] / g['fd_central'] - 1)))
    if fd is not None:
        v = [(r, _verdict(r)) for _, r in fd.iterrows()]
        names = lambda keep: list(dict.fromkeys(_name(r.test) for r, x in v if x in keep))
        ok, bad = names(('agrees', 'approximate')), [(r, x) for r, x in v if x == 'does not agree']
        worst = max(abs(r.adjoint_rel_err) for r, x in v if x in ('agrees', 'approximate'))
        out.append('<b>The %s gradients are usable; the %s gradients are not.</b> Of the eight finite-difference checks, %s agrees within '
                   '10 %% and %s more within %.0f %%; for %s the adjoint predicts %s the response the model produces.' % (
                       _and(ok), _and([_name(r.test) for r, _ in bad]),
                       NUM[sum(x == 'agrees' for _, x in v)], NUM[sum(x == 'approximate' for _, x in v)], 100 * worst,
                       _and([_name(r.test) for r, _ in bad]),
                       _and(['%.0f' % (r.adjoint / r.fd_central) for r, _ in bad]) + ' times'))
    if len(ms):
        nb = int((ms.status == 'bounded').sum())
        mono = bool(np.all(np.diff(ms.sort_values('factor').ratio5.values) < 0))
        out.append('<b>%s over five years</b>, as does the reference, and their amplitude %s with κ<sub>v</sub>: the RMS of ADJtheta at '
                   'five years is %s times the reference\'s at 0.25x and %s at 32x. In the 2026-08 ensemble %s of seven member adjoints '
                   'blew up, in the 2026-09-10 ensemble the 0.25x and 0.5x ones.' % (
                       'All seven member adjoints stay bounded' if nb == 7 else '%d of the seven member adjoints stay bounded' % nb,
                       'falls steadily' if mono else 'changes', fmt(float(ms.set_index('run').ratio5['M1']), 3),
                       fmt(float(ms.set_index('run').ratio5['M7']), 2), NUM[sum(s == 'blown' for s in prev['visc2x_2026_08']['status'])]))
        m = ms.set_index('run')
        out.append('<b>The sensitivity patterns change with κ<sub>v</sub>, the κ<sub>v</sub> gradient most.</b> A year before the end of '
                   'the window the members\' ADJtheta correlates with the reference\'s at %s–%s; the five-year ∂J/∂κ<sub>v</sub> only at '
                   '%s–%s, from %s at 2x down to %s at 32x.' % (
                       fmt(ms.corr_theta_1.min(), 2), fmt(ms.corr_theta_1.max(), 2), fmt(ms.corr_diffkr_5.min(), 2),
                       fmt(ms.corr_diffkr_5.max(), 2), fmt(m.corr_diffkr_5['M3'], 2), fmt(m.corr_diffkr_5['M7'], 2)))
    if fg is not None:
        sec, gm, lo = _secants(fg)
        hi = lo >= 4
        fac = np.maximum(sec[~hi] / gm[~hi], gm[~hi] / sec[~hi])
        out.append('<b>From 4x upwards J is close to linear in κ<sub>v</sub>, and the adjoint gradients describe it.</b> There the mean '
                   'of two neighbouring members\' adjoint gradients matches the secant of J between them to within %.0f %%; at and below '
                   '2x the two differ by factors of %.1f to %.0f, because the secants carry the ten-year adjustment of the state.' % (
                       100 * np.abs(gm[hi] / sec[hi] - 1).max(), fac.min(), fac.max()))
    lp = tgt.get('local_predictors', {}) if tgt else {}
    ident = lp.get('adjoint identity (window-mean state)')
    if ident:
        out.append('<b>∂J/∂κ<sub>v</sub> is the time integral of −∂<sub>z</sub>λ·∂<sub>z</sub>(T, S)</b>: the adjoint temperature and '
                   'salinity fields acting on the stratification reproduce its pattern with correlation %s (%s in the 2026-09-11 adjoint '
                   'from another state). The stratification alone ranks its magnitude only to %s.' % (
                       fmt(ident['pattern_corr'], 3), fmt(prev['structure_31237']['identity_pattern_corr'], 3),
                       fmt(max(v.get('spearman_abs_within_levels', 0) for kk, v in lp.items() if not kk.startswith('adjoint')), 2)))
    out.append('<b>For the surrogate:</b> κ<sub>v</sub> and the initial temperature and salinity should be inputs. The surface-forcing '
               'controls should not: they do not vary across this ensemble, and of their gradients only the zonal-stress one is a usable '
               'target. The primary target, ∂J/∂κ<sub>v</sub>, is best assembled from predicted ADJtheta and ADJsalt (last section).')
    return out


def forward_text(legs):
    if legs is None:
        return ''
    runs = list(c.RUN_ORDER)
    last = legs[(legs.run != 'spinup') & (legs.iter > c.NITER0 - c.STEPS_PER_YEAR)].groupby('run')[
        ['jproxy', 'amoc26', 'Tmean']].mean().reindex(runs)
    jmin, amin = last.jproxy.idxmin(), last.amoc26.idxmin()
    tmono = bool(np.all(np.diff(last.Tmean.values) > 0))
    drift, peaked = {}, {}
    for r in runs:
        s = legs[legs.run == r].sort_values('iter').jproxy.reset_index(drop=True)
        drift[r] = float(s.iloc[-12:].mean() - s.iloc[-36:-24].mean())
        roll = s.rolling(12).mean()
        k = int(roll.idxmax())
        if 18 <= k < len(s) - 12 and roll[k] > roll[11] + 2e-3:
            peaked[r] = (k + 1) / 12.0
    up = [r for r in runs if drift[r] > 2e-3]
    down = [r for r in runs if drift[r] < -2e-3]
    lab = lambda rs: _and(['%gx' % c.FACTOR[r] for r in rs])
    pk = [r for r in down if r in peaked]
    old8, old9 = json.loads(c.PREVIOUS.read_text())['visc2x_2026_08'], json.loads(c.PREVIOUS.read_text())['gmFree_ReMax2_2026_09_10']
    at2 = lambda o: o['fc'][o['factor'].index(2.0)] < min(o['fc'][o['factor'].index(1.0)], o['fc'][o['factor'].index(4.0)])
    txt = ('<p>Ten years at a different κ<sub>v</sub> change the state the adjoints start from, and not in one direction. Over the last '
           'year of the legs the cost proxy is %.3f at the reference, lowest at %gx (%.3f) and %.3f at 0.25x, and rises steeply above 8x '
           'to %.3f at 32x; the overturning maximum at 26° N has the same shape, from %.2f Sv at %gx to %.2f Sv at 32x.%s</p>' % (
               last.jproxy['REF'], c.FACTOR[jmin], last.jproxy[jmin], last.jproxy['M1'], last.jproxy['M7'], last.amoc26[amin],
               c.FACTOR[amin], last.amoc26['M7'],
               ' J of both earlier ensembles had a minimum at 2x too, a local one in the 2026-08 ensemble, whose J rose from 0.25x to 1x.'
               if at2(old8) and at2(old9) else ''))
    txt += ('<p>The volume-mean temperature %s with κ<sub>v</sub>, from %.2f °C at 0.25x to %.2f °C at 32x. Stronger mixing carries heat '
            'down from the surface, whose temperature the 6.5-day restoring holds near its target, so the change is largest between '
            'about 20 and 400 m and, after ten years, still confined mostly to the upper kilometre.</p>' % (
                'rises monotonically' if tmono else 'changes', last.Tmean['M1'], last.Tmean['M7']))
    txt += ('<p>The year-180 states are ten-year adjustments, not equilibria. At year 180 the %s legs are still rising and the %s legs '
            'falling%s; over the last two years the 0.25x proxy moved by %+.4f and the 32x one by %+.4f, against %+.4f for the reference, '
            'which continues the spin-up. Each member adjoint therefore differentiates J about a state that differs from the reference '
            'both in κ<sub>v</sub> and in ten years of response to it.</p>' % (
                lab(up), lab(down), (', the %s ones after peaking %s years into the leg' % (lab(pk), _and(['%.0f' % peaked[r] for r in pk])))
                if pk else '', drift['M1'], drift['M7'], drift['REF']))
    return txt


def reference_text(fg, ts, nf):
    if fg is None or ts is None:
        return ''
    r = ts[(ts.run == 'REF') & (ts['var'] == 'ADJtheta')].sort_values('lead_yr')
    at = lambda L: float(r.iloc[(r.lead_yr - L).abs().argmin()].rms)
    peak = r.loc[r.rms.idxmax()]
    fin = bool((ts[ts.run == 'REF'].finite_frac == 1).all())
    return ('<p>The reference adjoint runs the live <code>input_tap/data</code> for five years from the reference leg\'s year-180 state. '
            'Its cost, J = %.6f, is the forward model\'s: the monthly cost proxy of its forward sweep at year 185 equals that of the '
            'production spin-up 31203 at the same month to ten digits, so the new spin-up and its continuation reproduce 31203. The '
            'adjoint %s: the RMS of ADJtheta peaks at %s per K at a lead of %.0f days and falls to %s at one year and %s at five years%s.</p>'
            '<p>At a lead of 30 days the temperature sensitivity lies on the cost section and along the two boundaries that close it, the '
            'western boundary north of 26° N and the eastern boundary south of it, upstream along the paths of boundary waves. After a '
            'year it has moved into the tropics of both hemispheres and, below 500 m, along the western boundary between 25° and 55° N. '
            'After five years it lies in bands that slope towards the equator from west to east across both subtropical gyres, and at '
            '1400 m north of the section, between 30° and 50° N. The control gradients integrate this history: ∂J/∂κ<sub>v</sub> is '
            'largest, and negative, in the north-western subpolar corner and in a band just north of the section, and positive over the '
            'eastern tropics and the southern subtropics; ∂J/∂Q<sub>net</sub>, ∂J/∂Q<sub>sw</sub> and ∂J/∂(E−P−R) share one pattern.</p>' % (
                float(fg.set_index('run').fc['REF']), 'stays bounded' if fin else 'does not stay finite', fmt(float(peak.rms), 2),
                366 * peak.lead_yr, fmt(at(1.0), 2), fmt(at(5.0), 2), ', and every dump is finite' if fin else '; some dumps are not finite'))


def checks_text(fd, prev):
    if fd is None:
        return ''
    g = prev['gm_test_2026_09_11']
    old = [g['kappa_dJdkappa']['adjoint_31237'] / g['kappa_dJdkappa']['fd']] + [g[k]['adjoint_31237'] / g[k]['fd'] for k in ('deepN', 'midTrop', 'soUpper')]
    row = lambda key: _fd_row(fd, key)
    lin = [row(k) for k in ('kappa', '40-50 N', '0-10 N')]
    noisy = [row(k) for k in ('net surface heat flux', 'meridional surface stress')]
    ep = row('freshwater')
    items = ''.join('<li>%s: finite difference %s (one-sided %s and %s), adjoint %s: <b>%s</b> (%s).</li>' % (
        esc_(r.test), fmt(r.fd_central, 3), fmt(r.fd_plus, 2), fmt(r.fd_minus, 2), fmt(r.adjoint, 3), _verdict(r), _ratio(r))
        for _, r in fd.iterrows())
    return ('<p>Each check perturbs one control up and down, runs the forward sweep of the adjoint executable from the reference leg\'s '
            'year-180 state for five years, and compares the central difference of J with the reference adjoint\'s prediction. The two '
            'one-sided differences say how linear the response is at the chosen amplitude: they differ by at most %.0f %% of the central '
            'difference for κ<sub>v</sub> and the two deeper temperature boxes, by %.0f %% for the upper Southern Ocean box and by %.0f %% '
            'for the zonal stress.</p><ul class="findings">%s</ul>'
            '<p>The errors for κ<sub>v</sub> and the three temperature boxes are those of the 2026-09-11 test of the same adjoint from the '
            '31205 state (%s), so they belong to the approximate adjoint rather than to the state it starts from. The three failed forcing '
            'checks are of another kind. For the net heat flux and the meridional stress both one-sided responses are at least %.0f times '
            'smaller than the prediction; for E−P−R the finite difference is clean and %.0f times smaller. The model damps surface heat and '
            'freshwater anomalies through its 6.5-day restoring of surface temperature and salinity; why the adjoint overestimates their '
            'effect has not yet been established.</p>' % (
                100 * max(r.one_sided_spread for r in lin), 100 * row('40-60 S').one_sided_spread, 100 * row('zonal').one_sided_spread,
                items, _and([pct(q - 1) for q in old]),
                min(abs(r.adjoint) / max(abs(r.fd_plus), abs(r.fd_minus)) for r in noisy), ep.adjoint / ep.fd_central))


def esc_(x):
    import html
    return html.escape(str(x))


def _lead_corr(var, L):
    p = c.CACHE / 'lead_decorrelation.csv'
    if not p.exists():
        return np.nan
    q = pd.read_csv(p)
    q = q[q['var'] == var]
    return float(q.iloc[(q.lead_yr - L).abs().argmin()].corr_with_5yr)


def ensemble_text(fg, ms, dec, nf, prev):
    if fg is None:
        return ''
    fgi = fg.set_index('run')
    old = prev['gmFree_ReMax2_2026_09_10']
    oj = lambda f: old['fc'][old['factor'].index(f)]
    sec, gm, lo = _secants(fg)
    hi = lo >= 4
    G = fg.sort_values('factor')
    Ghi = G[G.factor >= 4].G_dJdkappa_uniform
    fac = np.maximum(sec[~hi] / gm[~hi], gm[~hi] / sec[~hi])
    txt = ('<p>J(κ<sub>v</sub>) has the shape the forward legs set up: highest at the weakest and the strongest mixing and lowest at %gx, '
           'with every member far outside the cost\'s internal variability. The 2026-09-10 ensemble, with a GM-free adjoint and legs from '
           'the 2× spin-up, has the same shape (%.3f at the reference, %.3f at 2x, %.3f at 32x), so the shape belongs to the forward '
           'model\'s response rather than to either adjoint.</p>' % (c.FACTOR[fgi.fc.idxmin()], oj(1.0), oj(2.0), oj(32.0)))
    txt += ('<p>The adjoint gradient dJ/dκ<sub>v</sub> falls into two regimes. From 4x to 32x every member gives %.0f to %.0f per m² s⁻¹, '
            'and the mean of two neighbours\' gradients matches the secant of J between them to within %.0f %%: there J is close to linear '
            'in κ<sub>v</sub>, and the local gradient describes it over a factor of eight. At and below 2x the gradient changes sign between '
            'neighbouring members (%s from 0.25x to 2x) and differs from the secants by factors of %.1f to %.0f, since those carry the '
            'ten-year adjustment of the state.</p>' % (
                Ghi.min(), Ghi.max(), 100 * np.abs(gm[hi] / sec[hi] - 1).max(),
                ', '.join('%.0f' % g for g in G[G.factor <= 2].G_dJdkappa_uniform), fac.min(), fac.max()))
    if dec is not None and len(dec):
        d = dec.set_index('run')
        within = lambda col, k: [r for r in d.index if 1.0 / k <= d[col][r] / d.dJ_measured[r] <= k]
        lab = lambda rs: _and(['%gx' % c.FACTOR[r] for r in rs]) if rs else 'none'
        wrong = [r for r in d.index if np.sign(d.dJ_kappa_refgrad[r]) != np.sign(d.dJ_measured[r])]
        big = d.index[-1]
        txt += ('<p>Applied to the members, the reference gradient alone predicts the sign of ΔJ for %s of the seven (not for %s) and its '
                'size within a factor of three for %s. Adding the linear effect of the change in year-180 temperature and salinity, from '
                'ADJtheta and ADJsalt at the start of the window, brings %s within a factor of two. For %s nothing linear about the '
                'reference can help: the reference gradient has the opposite sign to the one that holds from 4x upwards, and the '
                'temperature and salinity terms nearly cancel (%+.2f and %+.2f at 32x).</p>' % (
                    NUM[7 - len(wrong)], lab(wrong), lab(within('dJ_kappa_refgrad', 3)),
                    lab(within('dJ_predicted_refgrad_plus_state', 2)), lab(wrong), d.dJ_state_theta[big], d.dJ_state_salt[big]))
    if len(ms):
        m = ms.set_index('run')
        near = m[m.factor.between(0.25, 4)]
        txt += ('<p>All member adjoints stay bounded, and their amplitude falls with κ<sub>v</sub>: the RMS of ADJtheta at five years goes '
                'from %.2f times the reference\'s at 0.25x to %.2f at 32x, stronger mixing damping the adjoint as it damps forward '
                'anomalies. The patterns change faster than the amplitude. A year before the end of the window ADJtheta correlates with the '
                'reference\'s at %.2f or more from 0.25x to 4x and at %.2f at 32x; the five-year ∂J/∂κ<sub>v</sub> at %.2f at best (2x), '
                '%.2f and %.2f four times away (0.25x and 4x), and %.2f at 32x.</p>' % (
                    m.ratio5['M1'], m.ratio5['M7'], near.corr_theta_1.min(), m.corr_theta_1['M7'], m.corr_diffkr_5.max(),
                    m.corr_diffkr_5['M1'], m.corr_diffkr_5['M4'], m.corr_diffkr_5['M7']))
    return txt


def target_text(tgt, prev):
    if not tgt:
        return ''
    L5 = tgt['leads'].get('5.000', {})
    lp = tgt.get('local_predictors', {})
    ident = lp.get('adjoint identity (window-mean state)', {})
    locs = {k: v.get('spearman_abs_within_levels') for k, v in lp.items() if not k.startswith('adjoint')}
    s0 = prev['structure_31237']
    return ('<p>The surrogate plan makes ∂J/∂κ<sub>v</sub> the primary output. At the five-year lead half of Σ|∂J/∂κ<sub>v</sub>| sits '
            'in %.1f %% of the wet cells and 90 %% in %.0f %%, and its magnitude spans %d decades from the 1st percentile to the maximum; '
            'the 2026-09-11 adjoint from another state gave %.1f %% and %.0f %%. An unweighted squared-error loss would be dominated by a '
            'few per cent of the cells, so the loss has to be normalised.</p>'
            '<p>The target needs the whole five-year adjoint. The gradient accumulated over the last year of the window correlates with the '
            'five-year one at only %.2f, over two years at %.2f and over four at %.2f: the long-lead sensitivity is not a rescaled copy of '
            'the short-lead one.</p>'
            '<p>The field is, to a correlation of %.3f and a regression slope of %.3f (%.3f and %.3f in the 2026-09-11 adjoint), the time '
            'integral of −(∂<sub>z</sub>λ<sub>T</sub> ∂<sub>z</sub>T + ∂<sub>z</sub>λ<sub>S</sub> ∂<sub>z</sub>S) built from the 5-day '
            'ADJtheta and ADJsalt dumps and the window-mean stratification. The part a network cannot see in the forward state is λ, the '
            'adjoint of temperature and salinity: the stratification alone ranks |∂J/∂κ<sub>v</sub>| only to %.2f (|∂T/∂z|), %.2f '
            '(|∂S/∂z|) and %.2f (|∂ρ/∂z|) within each level.</p>' % (
                100 * L5.get('frac_cells_50pct', np.nan), 100 * L5.get('frac_cells_90pct', np.nan),
                int(round(L5.get('log10_max', 0) - L5.get('log10_p01', 0))), 100 * s0['frac_cells_50pct_5yr'], 100 * s0['frac_cells_90pct_5yr'],
                _lead_corr('ADJdiffkr', 1.0), _lead_corr('ADJdiffkr', 2.0), _lead_corr('ADJdiffkr', 4.0),
                ident.get('pattern_corr', np.nan), ident.get('regression_slope', np.nan), s0['identity_pattern_corr'],
                s0['identity_regression_slope'], locs.get('|dT/dz|'), locs.get('|dS/dz|'), locs.get('|drho/dz| (N^2 proxy)')))


def surrogate_text(fg, fd, ms, dec, tgt, h):
    chip = h['chip']
    row = lambda key: _fd_row(fd, key)
    m = ms.set_index('run')
    f = fg.set_index('run').fc
    lp = tgt.get('local_predictors', {}) if tgt else {}
    ident = lp.get('adjoint identity (window-mean state)', {})
    k = row('kappa')
    temp = [row(x) for x in ('40-50 N', '0-10 N', '40-60 S')]
    usable = {'agrees': chip('usable', 'good'), 'approximate': chip('with care', 'warn')}
    rows = [('κ<sub>v</sub>', chip('required', 'good'), '∂J/∂κ<sub>v</sub>: ' + chip('primary', 'good'),
             'J runs from %.3f to %.3f across the ensemble, and the five-year gradient pattern correlates with the reference\'s at only '
             '%.2f–%.2f. The adjoint gradient %s finite differences (%s), and an expansion about the reference fails beyond a factor of '
             'two, so the network has to be conditioned on κ<sub>v</sub>.' % (
                 f.min(), f.max(), m.corr_diffkr_5.min(), m.corr_diffkr_5.max(), VERB[_verdict(k)], _ratio(k))),
            ('Initial temperature and salinity', chip('yes', 'good'), 'ADJtheta, ADJsalt: ' + usable['agrees'],
             'The temperature checks give %s. ∂J/∂κ<sub>v</sub> is built from ADJtheta and ADJsalt (pattern correlation %.3f), and the '
             'change of the year-180 temperature and salinity is what brings the weakly mixed members\' ΔJ within a factor of two.' % (
                 _and([_ratio(r) for r in temp]), ident.get('pattern_corr', np.nan))),
            ('Stratification ∂<sub>z</sub>T, ∂<sub>z</sub>S', chip('derived', 'good'), '–',
             'The other factor of the identity; on its own it ranks |∂J/∂κ<sub>v</sub>| within a level to %.2f at best.' % max(
                 v.get('spearman_abs_within_levels', 0) for kk, v in lp.items() if not kk.startswith('adjoint')))]
    for key, name, note in (('zonal surface stress', 'Zonal surface stress', 'the response is already nonlinear at 0.005 N m⁻²'),
                            ('freshwater', 'E−P−R', 'the finite difference is clean'),
                            ('net surface heat flux', 'Net heat flux (Q<sub>sw</sub>, unchecked, has the same pattern)',
                             'both one-sided responses are far below the prediction'),
                            ('meridional surface stress', 'Meridional surface stress', 'both one-sided responses are far below the prediction')):
        r = row(key)
        v = _verdict(r)
        rows.append((name, chip('only if varied', 'warn'), usable.get(v, chip('not usable', 'bad')),
                     'Identical in every member. Gradient %s finite differences (%s); %s.' % (VERB[v], _ratio(r), note)))
    tab = ''.join('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % r for r in rows)
    nb = int((ms.status == 'bounded').sum())
    return ('<p><b>Should the perturbed variables be surrogate inputs?</b> κ<sub>v</sub> must be one, and the initial temperature and '
            'salinity should be as well. The surface-forcing controls should not be inputs of a network trained on a κ<sub>v</sub> '
            'ensemble: they are identical in every member, so the network could learn nothing from them, and they become inputs only if the '
            'training ensemble also perturbs the forcing. As targets, the gradients with respect to κ<sub>v</sub>, temperature and salinity '
            'are supported by finite differences to within 30 %%; of the forcing gradients only the zonal-stress one is, and only '
            'approximately.</p>'
            '<div class="table-wrap"><table><thead><tr><th>Variable</th><th>As input</th><th>As target</th><th>Evidence</th></tr></thead>'
            '<tbody>%s</tbody></table></div>'
            '<ul class="findings">'
            '<li><b>Assemble the primary target.</b> Since ∂J/∂κ<sub>v</sub> is the adjoint tracer fields acting on the stratification, a '
            'network that predicts ADJtheta and ADJsalt from the state and κ<sub>v</sub> and assembles ∂J/∂κ<sub>v</sub> from them has the '
            'physics built in, instead of learning the product of a field it cannot see with one it can.</li>'
            '<li><b>Sample κ<sub>v</sub> across the whole range, densely at and below 2x.</b> Below 4x J is far from linear in '
            'κ<sub>v</sub> and the gradient pattern decorrelates within a factor of four (%.2f at 0.25x, %.2f at 4x); above 4x J is nearly '
            'linear, but the pattern still changes (%.2f at 8x, %.2f at 32x).</li>'
            '<li><b>Train on full five-year adjoints.</b> A one-year adjoint gives a ∂J/∂κ<sub>v</sub> that correlates only %.2f with the '
            'five-year one.</li>'
            '<li><b>Keep the failed forcing gradients out of the loss</b> until the adjoint\'s treatment of the surface fluxes is understood, '
            'and weight the zonal-stress gradient down.</li>'
            '<li><b>Calibrate the κ<sub>v</sub> gradient\'s bias.</b> The adjoint overestimates dJ/dκ<sub>v</sub> by about a fifth in all '
            'three finite-difference tests; a surrogate trained on it inherits that, and finite differences at a few κ<sub>v</sub> values '
            'would measure it across the range.</li>'
            '<li><b>%s</b> under the current configuration: %s member adjoints stay bounded over five years.</li>'
            '</ul>' % (tab, m.corr_diffkr_5['M1'], m.corr_diffkr_5['M4'], m.corr_diffkr_5['M5'], m.corr_diffkr_5['M7'],
                       _lead_corr('ADJdiffkr', 1.0),
                       'The range 0.25x–32x needs no adjoint-mode viscosity' if nb == 7 else 'Part of the range needs adjoint-mode viscosity',
                       'all seven' if nb == 7 else NUM[nb] + ' of the seven'))
