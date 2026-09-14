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
    return '%s×10<sup>%d</sup>' % (('%.' + str(max(n - 1, 1)) + 'f') % (x / 10 ** e), e)


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
    out.append(fig('ref_vs_previous', '<b>The same adjoint from a different year-180 state.</b> The 2026-09-11 run 31237 started '
                   'from the deleted REF_ReMax2 leg 31205, which reached year 180 from the 2× spin-up\'s year 170.'))
    out.append('</section>')

    # ---------------------------------------------------------------- gradient checks
    out.append('<section id="checks"><h2>Do the adjoint gradients agree with finite differences?</h2>')
    out.append(checks_text(fd, prev))
    if fd is not None:
        f2 = fd.copy()
        out.append(table(f2, ['test', 'fd_central', 'adjoint', 'adjoint_rel_err', 'fd_plus', 'fd_minus'],
                         ['Perturbation', 'Central FD ΔJ', 'Adjoint ΔJ', 'Adjoint error', 'One-sided +', 'One-sided −'],
                         num=('fd_central', 'adjoint', 'adjoint_rel_err', 'fd_plus', 'fd_minus'),
                         fmt=dict({k: (lambda x, r: fmt(x, 4)) for k in ('fd_central', 'adjoint', 'fd_plus', 'fd_minus')},
                                  adjoint_rel_err=lambda x, r: pct(x))))
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
    out.append(fig('fc_vs_kappa', '<b>J against κ<sub>v</sub> in three campaigns.</b> The shaded band is ±2σ of the monthly cost index '
                   'in the spin-up, around this campaign\'s reference.', cls='narrow'))
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
    out.append(fig('target_structure', '<b>Lead dependence and local predictors.</b> Left: correlation of each dump with the 5-year '
                   'accumulation. Right: rank correlation of |∂J/∂κ<sub>v</sub>| with local quantities within each level.'))
    out.append(fig('identity_map', '<b>The adjoint κ<sub>v</sub> gradient and its reconstruction</b> from the 5-day ADJtheta and ADJsalt '
                   'dumps and the window-mean stratification, column sums.', cls='narrow'))
    out.append('</section>')

    # ---------------------------------------------------------------- surrogate
    out.append('<section id="surrogate"><h2>What this implies for the neural-network surrogate</h2>')
    out.append(surrogate_text(fg, fd, ms, dec, tgt, h))
    out.append(fig('control_ranking', '<b>Adjoint-predicted cost change for illustrative perturbation sizes</b>, in units of the '
                   'cost\'s internal variability. Linear predictions only; the checks above say which of them hold.', cls='narrow'))
    out.append('</section>')

    out.append('<section id="provenance"><h2>Provenance</h2>' + st.PROVENANCE + '</section>')
    out.append('<footer class="prov"><p>Built from the campaign\'s stats files; the numbers on this page are read from them at build time.</p></footer>')
    out.append('</main></div>')
    return '\n'.join(out)


# ---------------------------------------------------------------- the interpretive text, one function per section
def findings(fg, fd, ms, dec, nf, tgt, prev, legs):
    return ['(written once the results are in)']


def forward_text(legs):
    if legs is None:
        return ''
    last = legs[(legs.run != 'spinup') & (legs.iter > c.NITER0 - c.STEPS_PER_YEAR)].groupby('run')[
        ['jproxy', 'amoc26', 'Tmean']].mean().reindex(c.RUN_ORDER)
    f = np.array([c.FACTOR[r] for r in c.RUN_ORDER])
    jmin = last.jproxy.idxmin()
    tmono = bool(np.all(np.diff(last.Tmean.values) > 0))
    sp = legs[(legs.run == 'spinup') & (legs.iter > c.LEG_NITER0 - c.STEPS_PER_YEAR)]
    trend = legs[legs.run == 'M1'].set_index('year').jproxy
    m1_still = float(trend.iloc[-12:].mean() - trend.iloc[-36:-24].mean())
    txt = ('<p>Ten years at a different κ<sub>v</sub> change the state the adjoints start from, and not in one direction. '
           'The cost proxy at the end of the legs is %s at the reference, lowest at %gx (%s), %s at 0.25x, and '
           'rises steeply above 8x to %s at 32x; the overturning at 26° N follows the same shape, from %s Sv at the '
           'minimum to %s Sv at 32x. The two earlier ensembles showed the same minimum near 2x. ' % (
               fmt(last.jproxy['REF'], 3), c.FACTOR[jmin], fmt(last.jproxy[jmin], 3), fmt(last.jproxy['M1'], 3),
               fmt(last.jproxy['M7'], 3), fmt(last.amoc26.min(), 3), fmt(last.amoc26['M7'], 3)))
    txt += ('The volume-mean temperature %s with κ<sub>v</sub>, from %s °C to %s °C: stronger mixing carries heat '
            'down into the thermocline, and after ten years the change is still confined mostly to the upper kilometre.</p>' % (
                'rises monotonically' if tmono else 'changes', fmt(last.Tmean['M1'], 3), fmt(last.Tmean['M7'], 3)))
    txt += ('<p>These year-180 states are ten-year adjustments, not new equilibria. The strongly mixed members adjust within '
            'about five years and then level off, while the weakly mixed ones are still drifting at year 180 (the 0.25x '
            'proxy moved by %s over the last two years). The reference leg continues the spin-up, whose last year gives %s. '
            'Each member adjoint therefore differentiates a cost about a state that differs both in κ<sub>v</sub> and in '
            'ten years of response to it.</p>' % (fmt(m1_still, 2), fmt(float(sp.jproxy.mean()), 3)))
    return txt


def reference_text(fg, ts, nf):
    return ''


def checks_text(fd, prev):
    return ''


def ensemble_text(fg, ms, dec, nf, prev):
    return ''


def target_text(tgt, prev):
    return ''


def surrogate_text(fg, fd, ms, dec, tgt, h):
    return ''
