#!/usr/bin/env python3
"""One schematic of the κ_v experiments: which run starts from which saved state, for how long, in which direction,
with what changed, and what each output is used for.

    python workflow_schematic.py          # -> analysis/<campaign>/figures/workflow_schematic.png
    python workflow_schematic.py --notes ~/Proj_ImPACTS/impacts-docs/references/dino_overturning_sensitivity/notes/figures

EVERY NUMBER IS READ FROM THE RUNS, not typed in: the spin-up's length and time step from its staged `data`; each
leg's start, length, diffusivity and the spin-up pickup it links; each adjoint's start, length, dump interval, the
leg pickup it links and its staged `data.cost` (cost row, interface, averaging window); the job ranges of the four
cost-section campaigns and of the follow-up runs from their `job_map.tsv`; the configuration that every run shares
from the reference adjoint's staged namelists. The script also checks that the reference leg's year-180 state is
byte-identical to the spin-up's (so the spin-up is the reference forward run) and that every member adjoint starts
from its own leg's year-180 state with its own diffusivity, and stops otherwise.

Time runs left to right in model years, with years 0-170 of the spin-up compressed. Forward integrations are drawn
left to right, adjoint backward sweeps right to left; a diamond is a saved state (a pickup) that another run starts
from. The legs are coloured by their diffusivity on the same scale as the notes' Figure of the κ_v control.
"""
import argparse
import re
import shutil
import textwrap
from pathlib import Path

import numpy as np

import campaign as C

SECTIONS = [('25 S', 'kappa_v_ensemble_gmFwd_sec25S_Sv'), ('26 N', 'kappa_v_ensemble_gmFwd_sec26N_Sv848'),
            ('43 N', 'kappa_v_ensemble_gmFwd_sec43N_Sv'), ('60 N', 'kappa_v_ensemble_gmFwd_sec60N_Sv848')]
FOLLOWUPS = ['kappa_v_operator_vs_state_Sv', 'cost_section_sweep_Sv']
DAYS_PER_YEAR = 366   # DINO's calendar (DAYS_PER_YEAR in the setup's scripts/setup_params.sh)


# ---------------------------------------------------------------- reading the runs
def nml(path, key):
    """The value of `key` in a staged namelist file (last assignment wins), as a float or a stripped string."""
    txt = Path(path).read_text()
    hits = re.findall(r'^\s*%s\s*=\s*([^,\n]+)' % re.escape(key), txt, re.M | re.I)
    if not hits:
        return None
    v = hits[-1].strip().strip("'\"")
    try:
        return float(v.replace('D', 'E').replace('d', 'e'))
    except ValueError:
        return v


def pickup_source(d, it):
    p = Path(d) / ('pickup.%010d.data' % it)
    return Path(p.resolve()).parent if p.is_symlink() else None


def facts():
    """Everything the schematic states, read and cross-checked."""
    f = {}
    sd = C.run_dir(C.SPINUP_JOB)
    dt = nml(sd / 'data', 'deltaT')
    spy = 86400 * DAYS_PER_YEAR / dt
    if spy != C.STEPS_PER_YEAR:
        raise SystemExit('the spin-up\'s time step does not give the campaign\'s %d steps a year' % C.STEPS_PER_YEAR)
    f.update(dt=dt, spy=spy, spin_job=C.SPINUP_JOB, spin_years=nml(sd / 'data', 'nTimeSteps') / spy,
             spin_k=nml(sd / 'data', 'diffKrT'), spin_start=nml(sd / 'data', 'nIter0') or 0)
    legs = {}
    for r in C.RUN_ORDER:
        d = C.run_dir(C.LEG_JOB[r])
        it0 = int(nml(d / 'data', 'nIter0'))
        src = pickup_source(d, it0)
        if src is None or not src.name.endswith('_run%d' % C.SPINUP_JOB):
            raise SystemExit('leg %s does not start from the spin-up %d' % (r, C.SPINUP_JOB))
        legs[r] = dict(job=C.LEG_JOB[r], start=it0 / spy, years=nml(d / 'data', 'nTimeSteps') / spy,
                       k=nml(d / 'data', 'diffKrT'), dir=d)
    f['legs'] = legs
    # the reference leg reproduces the spin-up: same year-180 state, byte for byte
    it180 = int(round((legs['REF']['start'] + legs['REF']['years']) * spy))
    a = (legs['REF']['dir'] / ('pickup.%010d.data' % it180)).read_bytes()
    b = (sd / ('pickup.%010d.data' % it180)).read_bytes()
    f['ref_leg_identical'] = a == b
    adj = {}
    for r in C.RUN_ORDER:
        d = C.run_dir(C.ADJ_JOB[r])
        it0 = int(nml(d / 'data', 'nIter0'))
        src = pickup_source(d, it0)
        if src is None or src != legs[r]['dir']:
            raise SystemExit('adjoint %s does not start from its own leg' % r)
        k = nml(d / 'data', 'diffKrT')
        if k != legs[r]['k']:
            raise SystemExit('adjoint %s runs with a diffusivity other than its leg\'s' % r)
        adj[r] = dict(job=C.ADJ_JOB[r], start=it0 / spy, years=nml(d / 'data', 'nTimeSteps') / spy, k=k)
    f['adj'] = adj
    rd = C.run_dir(C.ADJ_JOB['REF'])
    g = C.grid(rd)
    f['dump_days'] = nml(rd / 'data', 'adjDumpFreq') / 86400
    f['window_days'] = nml(rd / 'data.cost', 'lastinterval') / 86400
    f['ndump'] = int(round(adj['REF']['years'] * spy * dt / 86400 / f['dump_days']))
    f['interface_m'] = float(-np.asarray(g['RF']).ravel()[int(nml(rd / 'data.cost', 'cost_atl_kmaxdepth'))])
    f['nlev'] = int(nml(rd / 'data.cost', 'cost_atl_kmaxdepth'))
    f['grid'] = tuple(int(n) for n in g['hFacC'].shape[::-1])
    f['visc_remax'] = nml(rd / 'data', 'viscAhReMax')
    f['adv'] = int(nml(rd / 'data', 'tempAdvScheme'))
    f['ivdc'] = nml(rd / 'data', 'ivdc_kappa')
    f['gm_k'] = nml(rd / 'data.gmredi', 'GM_background_K')
    f['gm_in_ad'] = nml(rd / 'data.autodiff', 'useGMRediInAdMode')
    f['approx_adv'] = nml(rd / 'data.autodiff', 'useApproxAdvectionInAdMode')
    secs = []
    for name, camp in SECTIONS:
        m = C._job_map(camp)
        a = sorted(j for j, role, t in m if 'adjoint' in role)
        fd = sorted(j for j, role, t in m if role.startswith('FD'))
        dref = C.run_dir(a[0])
        row = int(nml(dref / 'data.cost', 'cost_atl_jsec'))
        kmx = int(nml(dref / 'data.cost', 'cost_atl_kmaxdepth'))
        secs.append(dict(name=name, row=row, kmax=kmx, adj=(a[0], a[-1]), n_adj=len(a), n_fd=len(fd)))
    f['sections'] = secs
    fu = {}
    for camp in FOLLOWUPS:
        m = C._job_map(camp)
        jobs = sorted(j for j, role, t in m)
        fu[camp] = dict(jobs=(jobs[0], jobs[-1]), n=len(jobs), rows=m)
    f['followups'] = fu
    return f


# ---------------------------------------------------------------- drawing
W, H = 6.5, 8.65                   # inches; the axes are in inches too
X0, X170, X185 = 1.95, 2.42, 6.02  # years 0 and 170 (compressed), 185
XB = 2.17                          # where the compressed spin-up years are broken


def xy(year):
    """Model year -> x in inches: 0-170 compressed into [X0, X170], 170-185 linear to X185."""
    if year <= 170:
        return X0 + (X170 - X0) * year / 170.0
    return X170 + (X185 - X170) * (year - 170) / 15.0


def wrap(s, n):
    return '\n'.join(textwrap.fill(p, n) for p in s.split('\n'))


def plot(f, out):
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch, Rectangle
    from matplotlib.colors import LogNorm
    from matplotlib.transforms import Bbox
    C.setup_style()
    cm = C.sequential_cmap()
    ks = [f['legs'][r]['k'] for r in C.RUN_ORDER]
    norm = LogNorm(vmin=min(ks), vmax=max(ks))
    BLUE, ORANGE, GREEN = C.SERIES
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
    FS = 6.8                         # body text

    def arrow(x1, y1, x2, y2, color, lw=1.2, ls='-', head=7, z=3):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1), zorder=z,
                    arrowprops=dict(arrowstyle='-|>', color=color, lw=lw, ls=ls, mutation_scale=head,
                                    shrinkA=0, shrinkB=0))

    def diamond(x, y, color=C.INK, ms=4.0, z=6):
        ax.plot([x], [y], 'D', ms=ms, color='white', mec=color, mew=1.0, zorder=z)

    def lane(y, title, sub):
        ax.text(0.06, y, title, fontsize=8.4, fontweight='bold', color=C.INK, va='center')
        ax.text(0.06, y - 0.12, sub, fontsize=FS, color=C.INK2, va='top', linespacing=1.32)

    def ink_on(rgba):
        r, g, b = rgba[:3]
        return 'white' if 0.299 * r + 0.587 * g + 0.114 * b < 0.55 else C.INK

    x170, x180, x185 = xy(170), xy(180), xy(185)
    kref = f['spin_k']
    # ---- title, legend, time axis
    ax.text(0.06, H - 0.08, 'The DINO $\\kappa_v$ experiments: runs, branch points and outputs', fontsize=10.5,
            fontweight='bold', va='top')
    ly = H - 0.42
    arrow(0.06, ly, 0.38, ly, BLUE, lw=1.4)
    ax.text(0.44, ly, 'forward integration', fontsize=7.3, va='center')
    arrow(1.95, ly, 1.63, ly, ORANGE, lw=2.0)
    ax.text(2.01, ly, 'adjoint backward sweep', fontsize=7.3, va='center')
    diamond(3.46, ly)
    ax.text(3.56, ly, 'saved state a later run starts from', fontsize=7.3, va='center')
    ax.add_patch(Rectangle((5.55, ly - 0.05), 0.06, 0.1, color=ORANGE, zorder=4))
    ax.text(5.65, ly, 'cost window', fontsize=7.3, va='center')
    ty = H - 0.78
    ax.plot([X0, XB - 0.04], [ty, ty], color=C.AXIS_C, lw=0.8)
    ax.plot([XB + 0.04, x185 + 0.3], [ty, ty], color=C.AXIS_C, lw=0.8)
    for xb in (XB - 0.03, XB + 0.03):
        ax.plot([xb - 0.02, xb + 0.02], [ty - 0.05, ty + 0.05], color=C.MUTED, lw=0.8)
    for yr in (0, 170, 175, 180, 185):
        ax.plot([xy(yr)] * 2, [ty - 0.035, ty + 0.035], color=C.MUTED, lw=0.8)
        ax.text(xy(yr), ty + 0.06, '%d' % yr, fontsize=7.4, ha='center', va='bottom', color=C.INK2)
    ax.text(X0 - 0.07, ty, 'model year', fontsize=7.2, ha='right', va='center', color=C.INK2)

    # ---- the spin-up, which is the reference forward run
    ys = ty - 0.42
    ax.add_patch(Rectangle((X0, ys - 0.065), x185 + 0.12 - X0, 0.13, color=cm(norm(kref)), zorder=2))
    for xb in (XB - 0.03, XB + 0.03):
        ax.plot([xb - 0.025, xb + 0.025], [ys - 0.09, ys + 0.09], color=C.SURFACE, lw=2.4, zorder=3)
    arrow(x185 + 0.1, ys, x185 + 0.22, ys, BLUE, lw=1.2)
    ax.text(x185 + 0.24, ys, '%d' % round(f['spin_years']), fontsize=7.0, va='center', color=C.INK2)
    ax.text(x170 + 0.05, ys + 0.1, 'from rest   $\\kappa_v = %s$ m$^2$ s$^{-1}$   %d years of %d-s steps' %
            (sci(kref), round(f['spin_years']), f['dt']), fontsize=FS, color=C.INK2, va='bottom')
    diamond(x170, ys); diamond(x180, ys)
    lane(ys + 0.03, 'Reference forward run', 'the spin-up, run %d' % f['spin_job'])

    # ---- the eight forward legs, from the spin-up's year 170
    dyl = 0.135
    order = C.RUN_ORDER[::-1]                                   # 32x on top
    ylegs = {r: ys - 0.36 - n * dyl for n, r in enumerate(order)}
    ax.plot([x170] * 2, [ys - 0.05, ylegs[order[-1]]], color=C.INK2, lw=0.8, zorder=1)
    for r in order:
        L, y = f['legs'][r], ylegs[r]
        x1, x2 = xy(L['start']), xy(L['start'] + L['years'])
        col = cm(norm(L['k']))
        ax.add_patch(Rectangle((x1, y - 0.05), x2 - x1, 0.1, color=col, zorder=2, ec=C.INK if r == 'REF' else 'none',
                               lw=0.8))
        diamond(x2, y, ms=3.6)
        ax.text(x1 - 0.06, y, ('REF  ' if r == 'REF' else '') + '%gx' % C.FACTOR[r], fontsize=FS, ha='right',
                va='center', color=C.INK, fontweight='bold' if r == 'REF' else 'normal')
        inside = '$%s$ m$^2$ s$^{-1}$' % sci(L['k'])
        if r == 'REF' and f['ref_leg_identical']:
            inside += ',  identical to the spin-up'
        ax.text((x1 + x2) / 2, y, inside, fontsize=6.2, ha='center', va='center', color=ink_on(col), zorder=4)
        ax.text(x2 + 0.07, y, '%d' % L['job'], fontsize=6.4, va='center', color=C.MUTED)
    lane(ylegs[order[0]] - 0.02, 'Forward legs',
         '8 members, %d years each,\nfrom the spin-up\'s year %d;\nonly $\\kappa_v$ differs' %
         (round(f['legs']['REF']['years']), round(f['legs']['REF']['start'])))

    # ---- the adjoints, each from its own leg's year-180 state
    dya = 0.135
    ya_top = ylegs[order[-1]] - 0.38
    yadj = {r: ya_top - n * dya for n, r in enumerate(order)}
    ax.plot([x180] * 2, [ylegs[order[0]], yadj[order[-1]]], color=C.INK2, lw=0.8, ls=':', zorder=1)
    ax.text(x180 - 0.06, ya_top + 0.2, 'each member\'s year-180 state starts its own adjoint', fontsize=FS,
            ha='right', va='center', color=C.INK2)
    ax.text(x185, ya_top + 0.2, 'J: last %d days' % round(f['window_days']), fontsize=FS, ha='right', va='center',
            color=ORANGE)
    for r in order:
        A, y = f['adj'][r], yadj[r]
        x1, x2 = xy(A['start']), xy(A['start'] + A['years'])
        ax.plot([x1, x2], [y + 0.03, y + 0.03], color=BLUE, lw=0.8, zorder=2)
        arrow(x2 - 0.06, y - 0.02, x1 + 0.05, y - 0.02, ORANGE, lw=1.8, head=6)
        ax.add_patch(Rectangle((x2 - 0.06, y - 0.05), 0.06, 0.1, color=ORANGE, zorder=4))
        diamond(x1, y, ms=3.6)
        ax.text(x1 - 0.07, y, '%gx' % C.FACTOR[r], fontsize=FS, ha='right', va='center', color=C.INK,
                fontweight='bold' if r == 'REF' else 'normal')
        ax.text(x2 + 0.07, y, '%d' % A['job'], fontsize=6.4, va='center', color=C.MUTED)
    yb = yadj[order[-1]] - 0.11
    ax.text(W - 0.06, yb, 'thin: the forward sweep, years 180 to 185 with the member\'s $\\kappa_v$, J at its end\n'
            'thick: the backward sweep, 185 back to 180', fontsize=6.4, ha='right', va='top', color=C.INK2,
            linespacing=1.3, zorder=5, bbox=dict(fc=C.SURFACE, ec='none', pad=1.0))
    sec_lines = '\n'.join('%s: %d-%02d' % (q['name'], q['adj'][0], q['adj'][1] % 100) for q in f['sections'])
    lane(yadj[order[0]] - 0.02, 'Adjoint runs',
         '8 members x 4 cost sections,\n%d years each; shown: 43 N\n%s' % (round(f['adj']['REF']['years']), sec_lines))

    # ---- finite-difference checks, forward only, from the reference state
    yf = yb - 0.5
    s = f['sections']
    fds = [('$\\kappa_v \\times 1.1$ and $\\times 0.9$ everywhere', '2'),
           ('$\\kappa_v \\times 1.1$ and $\\times 0.9$ in one box (43 N)', '2'),
           ('$\\theta$ raised and lowered in 4 to 6 boxes', '8-12'),
           ('surface stress, heat and freshwater flux raised and lowered', '8')]
    for n, (txt, cnt) in enumerate(fds):
        y = yf - n * 0.14
        arrow(x180, y, x185 - 0.03, y, BLUE, lw=0.9, ls='--', head=5)
        ax.plot([x185], [y], 'o', ms=3.6, color=GREEN, zorder=5)
        ax.text(x180 - 0.06, y, '%s  [%s]' % (txt, cnt), fontsize=FS, ha='right', va='center', color=C.INK)
    ax.plot([x180] * 2, [ylegs['REF'], yf - 3 * 0.14], color=GREEN, lw=0.8, ls=':', zorder=1)
    ax.text(x185 + 0.05, yf - 3 * 0.14 - 0.1, 'each run gives J only, and is stopped once it has printed J',
            fontsize=6.4, ha='right', va='top', color=GREEN)
    nfd = '%d-%d' % (min(q['n_fd'] for q in s), max(q['n_fd'] for q in s))
    lane(yf + 0.02, 'Finite-difference checks', 'forward only, %d years, from the\nREF year-180 state; %s runs per\n'
         'section, [runs] in +/- pairs' % (round(f['adj']['REF']['years']), nfd))

    # ---- the follow-up adjoints of the review of 28 October
    yu = yf - 3 * 0.14 - 0.46
    fu = f['followups']
    sw, sp = fu['kappa_v_operator_vs_state_Sv'], fu['cost_section_sweep_Sv']
    rows = [('REF or 32x state, with REF or 32x $\\kappa_v$ in the adjoint', 30 / 366., '30 d'),
            ('the same four combinations', 1.0, '1 yr'),
            ('REF state, cost at 14 rows, 30 S to 60 N', 1.0, '1 yr'),
            ('8x state, cost at its own maximum, 68.8 N', 5.0, '5 yr')]
    for n, (txt, yrs, tag) in enumerate(rows):
        y = yu - n * 0.14
        x2 = xy(180 + yrs)
        arrow(max(x2, x180 + 0.07), y, x180, y, ORANGE, lw=1.4, head=5)
        ax.text(max(x2, x180 + 0.07) + 0.06, y, tag, fontsize=FS, va='center', color=C.INK2)
        ax.text(x180 - 0.06, y, txt, fontsize=FS, ha='right', va='center', color=C.INK)
    lane(yu + 0.02, 'Follow-up adjoints', 'review of 28 October,\nruns %d-%d, %d-%d' %
         (sw['jobs'][0], sw['jobs'][1] % 100, sp['jobs'][0], sp['jobs'][1] % 100))

    # ---- bottom: what changes, and what each output is used for
    top = yu - 3 * 0.14 - 0.24
    for x in (0.06, 3.31):
        ax.add_patch(FancyBboxPatch((x, 0.05), 3.13, top - 0.05, boxstyle='round,pad=0,rounding_size=0.06',
                                    fc='white', ec=C.GRID_C, lw=0.8, zorder=0))
    left = [('Between members', 'only $\\kappa_v$ (diffKrT = diffKrS): %s to %s times $%s$ m$^2$ s$^{-1}$ in factors '
             'of two, in the leg and in its adjoint; so also the year-180 state each adjoint starts from.'
             % ('%g' % C.FACTOR[C.RUN_ORDER[0]], '%g' % C.FACTOR[C.RUN_ORDER[-1]], sci(kref))),
            ('Between cost sections', 'only the cost row: %s, each to %d m; the same legs and states serve all four.'
             % (', '.join('%s (row %d)' % (q['name'], q['row']) for q in s), round(f['interface_m']))),
            ('Fixed in every member and section', 'grid %d x %d x %d; %d-s step; the surface forcing; viscosity (grid-Reynolds floor %g); '
             'advection scheme %d; GM/Redi %g m$^2$ s$^{-1}$; convection %g m$^2$ s$^{-1}$; the year-170 start.'
             % (f['grid'] + (f['dt'], f['visc_remax'], f['adv'], f['gm_k'], f['ivdc']))),
            ('Only in the backward sweeps', 'scheme 30 replaces %d, and GM/Redi is left out: the approximate adjoint.'
             % f['adv'])]
    right = [('J of each member', 'the curve $J(\\kappa_v)$; slopes between members give the total derivative, the '
              'ten-year adjustment included.'),
             ('The $\\kappa_v$ gradient field (adxx_diffkr)', 'its sum is $\\partial J/\\partial\\kappa_v$ at fixed '
              'state; its map shows where mixing matters.'),
             ('Gradients for initial $\\theta$, $S$ and forcing', 'sensitivity maps; the surrogate\'s training targets.'),
             ('Dumps every %d days, %d per run' % (round(f['dump_days']), f['ndump']), 'the sensitivity at each lead: '
              'films, adjoint waves.'),
             ('Finite differences', 'the measured change of J, against the adjoint\'s prediction.')]
    for x, title, items in ((0.06, 'What changes between runs', left), (3.31, 'What each output is used for', right)):
        yy = top - 0.1
        ax.text(x + 0.1, yy, title, fontsize=8.2, fontweight='bold', va='top')
        yy -= 0.25
        for head, body in items:
            ax.text(x + 0.1, yy, head, fontsize=FS, fontweight='bold', va='top', color=C.INK)
            t = ax.text(x + 0.18, yy - 0.115, wrap(body, 58), fontsize=FS, va='top', color=C.INK2, linespacing=1.28)
            yy -= 0.115 + 0.112 * (t.get_text().count('\n') + 1) + 0.07
        if yy < 0.07:
            print('WARNING: the panel "%s" overflows its box by %.2f in' % (title, 0.07 - yy))
    fig.savefig(out, dpi=250, bbox_inches=Bbox.from_bounds(0, 0, W, H))
    plt.close(fig)


def plot_slide(f, out):
    """A landscape version for a 16:9 slide: the run lanes only (no bottom panels), larger text, fewer words."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    from matplotlib.colors import LogNorm
    from matplotlib.transforms import Bbox
    C.setup_style()
    Ws, Hs = 9.6, 5.3
    x0, x170, x185 = 2.55, 3.15, 8.95

    def X(year):
        return x0 + (x170 - x0) * year / 170.0 if year <= 170 else x170 + (x185 - x170) * (year - 170) / 15.0

    cm = C.sequential_cmap()
    norm = LogNorm(vmin=min(f['legs'][r]['k'] for r in C.RUN_ORDER) / 1.5,
                   vmax=max(f['legs'][r]['k'] for r in C.RUN_ORDER))
    BLUE, ORANGE, GREEN = C.SERIES
    fig = plt.figure(figsize=(Ws, Hs))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, Ws); ax.set_ylim(0, Hs); ax.axis('off')
    FS = 9.5

    def arrow(x1, y1, x2, y2, color, lw=1.4, ls='-', head=8):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1), zorder=3,
                    arrowprops=dict(arrowstyle='-|>', color=color, lw=lw, ls=ls, mutation_scale=head,
                                    shrinkA=0, shrinkB=0))

    def diamond(x, y, ms=5):
        ax.plot([x], [y], 'D', ms=ms, color='white', mec=C.INK, mew=1.1, zorder=6)

    def lane(y, title, sub):
        ax.text(0.08, y, title, fontsize=11, fontweight='bold', va='center', color=C.INK)
        ax.text(0.08, y - 0.17, sub, fontsize=FS - 0.5, va='top', color=C.INK2, linespacing=1.3)

    # legend and axis
    ly = Hs - 0.22
    arrow(0.08, ly, 0.5, ly, BLUE, lw=1.6); ax.text(0.58, ly, 'forward run', fontsize=FS, va='center')
    arrow(2.35, ly, 1.93, ly, ORANGE, lw=2.4); ax.text(2.43, ly, 'adjoint, backward in time', fontsize=FS, va='center')
    diamond(4.62, ly); ax.text(4.75, ly, 'saved state a later run starts from', fontsize=FS, va='center')
    ax.add_patch(Rectangle((7.55, ly - 0.07), 0.08, 0.14, color=ORANGE, zorder=4))
    ax.text(7.7, ly, 'cost window (30 d)', fontsize=FS, va='center')
    ty = Hs - 0.62
    ax.plot([x0, x0 + 0.25], [ty, ty], color=C.AXIS_C, lw=0.9)
    ax.plot([x0 + 0.35, x185 + 0.35], [ty, ty], color=C.AXIS_C, lw=0.9)
    for xb in (x0 + 0.27, x0 + 0.33):
        ax.plot([xb - 0.025, xb + 0.025], [ty - 0.06, ty + 0.06], color=C.MUTED, lw=0.9)
    for yr in (0, 170, 175, 180, 185):
        ax.plot([X(yr)] * 2, [ty - 0.04, ty + 0.04], color=C.MUTED, lw=0.9)
        ax.text(X(yr), ty + 0.07, '%d' % yr, fontsize=FS, ha='center', va='bottom', color=C.INK2)
    ax.text(x0 - 0.08, ty, 'model year', fontsize=FS - 0.5, ha='right', va='center', color=C.INK2)

    # the reference run: the spin-up
    ys = ty - 0.4
    kref = f['spin_k']
    ax.add_patch(Rectangle((x0, ys - 0.08), x185 + 0.15 - x0, 0.16, color=cm(norm(kref)), zorder=2))
    for xb in (x0 + 0.27, x0 + 0.33):
        ax.plot([xb - 0.03, xb + 0.03], [ys - 0.11, ys + 0.11], color=C.SURFACE, lw=2.6, zorder=3)
    arrow(x185 + 0.13, ys, x185 + 0.38, ys, BLUE)
    ax.text(x185 + 0.4, ys, '200', fontsize=FS - 0.5, va='center', color=C.INK2)
    ax.text(X(170) + 0.08, ys + 0.12, 'from rest, $\\kappa_v = %s$ m$^2$ s$^{-1}$' % sci(kref), fontsize=FS - 0.5,
            color=C.INK2, va='bottom')
    diamond(X(170), ys); diamond(X(180), ys)
    lane(ys + 0.02, 'Reference run', 'spin-up %d' % f['spin_job'])

    # the eight legs
    order = C.RUN_ORDER[::-1]
    dy = 0.155
    yl = {r: ys - 0.38 - n * dy for n, r in enumerate(order)}
    ax.plot([X(170)] * 2, [ys - 0.06, yl[order[-1]]], color=C.INK2, lw=0.9, zorder=1)
    for r in order:
        y = yl[r]
        ax.add_patch(Rectangle((X(170), y - 0.055), X(180) - X(170), 0.11, color=cm(norm(f['legs'][r]['k'])),
                               ec=C.INK if r == 'REF' else 'none', lw=0.9, zorder=2))
        diamond(X(180), y, ms=4.4)
        ax.text(X(170) - 0.07, y, ('REF ' if r == 'REF' else '') + '%gx' % C.FACTOR[r], fontsize=FS - 1, ha='right',
                va='center', fontweight='bold' if r == 'REF' else 'normal')
    ax.text((X(170) + X(180)) / 2, yl['REF'], 'identical to the spin-up', fontsize=FS - 1.5, ha='center', va='center',
            color=C.INK, zorder=4)
    lane(yl[order[1]] - 0.03, 'Forward legs', '8 members, 10 years each,\nonly $\\kappa_v$ differs')

    # the adjoints
    ya = {r: yl[order[-1]] - 0.42 - n * dy for n, r in enumerate(order)}
    ax.plot([X(180)] * 2, [yl[order[0]], ya[order[-1]]], color=C.INK2, lw=0.9, ls=':', zorder=1)
    for r in order:
        y = ya[r]
        ax.plot([X(180), X(185)], [y + 0.035, y + 0.035], color=BLUE, lw=0.9, zorder=2)
        arrow(X(185) - 0.08, y - 0.025, X(180) + 0.06, y - 0.025, ORANGE, lw=2.0, head=7)
        ax.add_patch(Rectangle((X(185) - 0.08, y - 0.06), 0.08, 0.12, color=ORANGE, zorder=4))
        diamond(X(180), y, ms=4.4)
        ax.text(X(180) - 0.08, y, '%gx' % C.FACTOR[r], fontsize=FS - 1, ha='right', va='center',
                fontweight='bold' if r == 'REF' else 'normal')
    ax.text(X(180) - 0.6, (ya[order[0]] + ya[order[-1]]) / 2,
            'each member\nfrom its own\nyear-180 state,\nwith its own $\\kappa_v$', fontsize=FS - 1, ha='right',
            va='center', color=C.INK2, linespacing=1.3)
    lane(ya[order[0]] - 0.03, 'Adjoint runs', '5 years each; the 8 members\nfor each of 4 cost sections\n'
         '(25 S, 26 N, 43 N, 60 N)')

    # finite-difference checks and the follow-ups, from the year-180 states
    yo = ya[order[-1]] - 0.45
    rows = [('finite-difference checks: forward only, from REF, J only', 5.0, 'fd'),
            ('latitude sweep: REF state, cost at 14 rows, 1 year', 1.0, 'adj'),
            ('8x state, cost at its own maximum (69 N), 5 years', 5.0, 'adj')]
    for n, (txt, yrs, kind) in enumerate(rows):
        y = yo - n * 0.2
        if kind == 'fd':
            arrow(X(180), y, X(180 + yrs) - 0.03, y, BLUE, lw=1.1, ls='--', head=7)
            ax.plot([X(180 + yrs)], [y], 'o', ms=5, color=GREEN, zorder=5)
        else:
            arrow(X(180 + yrs), y, X(180), y, ORANGE, lw=1.7, head=7)
        ax.text(X(180) - 0.08, y, txt, fontsize=FS - 1, ha='right', va='center', color=C.INK)
    lane(yo + 0.02, 'Checks and follow-ups', 'from the same\nyear-180 states')
    fig.savefig(out, dpi=220, bbox_inches=Bbox.from_bounds(0, max(0, yo - 2 * 0.2 - 0.25), Ws, Hs - max(0, yo - 0.65)))
    plt.close(fig)


def sci(v):
    m, e = ('%.1e' % v).split('e')
    return '%s\\times10^{%d}' % (m, int(e))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--notes', default=None, help="also copy the figure into this directory (the notes' figures/)")
    a = ap.parse_args()
    C.ensure_dirs()
    f = facts()
    print('spin-up %d: %.1f yr of %d s steps; legs %d-%d: %.1f yr from year %.1f; adjoints: %.1f yr from year %.1f; '
          'REF leg identical to the spin-up at year 180: %s' % (
              f['spin_job'], f['spin_years'], f['dt'], f['legs']['REF']['job'], f['legs']['M7']['job'],
              f['legs']['REF']['years'], f['legs']['REF']['start'], f['adj']['REF']['years'], f['adj']['REF']['start'],
              f['ref_leg_identical']))
    out = C.FIGS / 'workflow_schematic.png'
    plot(f, out)
    print(out)
    plot_slide(f, C.FIGS / 'workflow_schematic_slide.png')
    print(C.FIGS / 'workflow_schematic_slide.png')
    if a.notes:
        dest = Path(a.notes).expanduser() / out.name
        shutil.copy2(out, dest)
        print('  copied to', dest)


if __name__ == '__main__':
    main()
