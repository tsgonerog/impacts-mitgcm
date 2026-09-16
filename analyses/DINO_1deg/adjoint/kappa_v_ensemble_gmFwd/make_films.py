#!/usr/bin/env python3
"""Films of every ADJ* dump of the campaign's adjoints, in the two forms the project needs.

    python make_films.py profiles      # per-level RMS of every 3-D dump -> cache + the level-choice figure
    python make_films.py reference     # one film per ADJ* variable of the reference adjoint (31374)
    python make_films.py members       # ADJtheta and ADJdiffkr, one film per ensemble member, plus the 8-panel films
    python make_films.py all
    python make_films.py reference --deck ~/Proj_ImPACTS/impacts-notes/references/dino_adjoint_sensitivities/slides/figures

Each film is written twice: a **multi-page PDF**, one page per frame, which the beamer deck plays with
the `animate` package, and a **GIF** for the web page and for anyone without a PDF viewer that
animates. `animations/films_index.tsv` records, for every film, which levels it shows and why.

WHICH DEPTH LEVELS A THREE-DIMENSIONAL FILM SHOWS, AND WHY
The cost J is the northward transport across 26 N *in the upper 982 m* (the upper 25 of 36 levels;
code_tap/cost_atlantic_heat.F's kmaxdepth = 25), so the water column has two distinct roles: inside
that range a perturbation changes the transport J measures directly, below it a perturbation can only
change J by changing the circulation. A film therefore shows one level from each:

    the level of largest time-mean horizontal RMS **inside** 0-982 m, and
    the level of largest time-mean horizontal RMS **below** 982 m.

Both are read off the profiles step's cache, per variable, so the choice is made by the data and not
by hand, and both depths are printed on the panels and listed in films_index.tsv. It replaces the
hand-picked 300 m / 1400 m pair of the first version of these films (2026-09-15), which came from no
rule at all; for ADJtheta the rule gives 915 m and 1844 m, and 915 m carries 3.5 times the RMS that
300 m does -- it is the level at the base of the layer the cost integrates, where a temperature
anomaly sits on the shear that defines the cell. Every other level is in the explorer
(build_explorer.py), which is what the deck links for anyone who wants a different one.

COLOUR SCALE. One symmetric scale per film, the 99.5th percentile of |field| over all its frames,
fixed for the whole film, so that growth and decay are visible as the film plays; each frame also
prints its own maximum. That is the opposite convention from the two GIFs make_figures.py already
wrote (`ref_ADJtheta_lead.gif`, `members_ADJdiffkr_lead.gif`), which normalise every frame to show
the pattern rather than the amplitude. Both are useful; the films here are the amplitude ones.

TIME. Page 1 is the end of the cost window and the film walks backwards, the order the adjoint
computes it. `--stride` is in dumps of 5 days; the default is per variable (FILM_STRIDE).
"""
from __future__ import annotations

import argparse
import io
import shutil
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image

import campaign as c

# ---------------------------------------------------------------- what each dump is
# label of the control, and the unit of dJ/d(control). Whether a dump decays backwards in time (an
# adjoint state, set once) or grows (a running total accumulated over the sweep so far) is NOT listed
# here: `kind_of` reads it off the measured RMS-against-lead curve, so a film's caption cannot
# contradict its own data. films_index.tsv carries the numbers.
INFO = {
    'ADJtheta':  ('temperature',                 'dJ / K'),
    'ADJsalt':   ('salinity',                    'dJ / (g kg$^{-1}$)'),
    'ADJdiffkr': ('vertical diffusivity',        'dJ / (m$^2$ s$^{-1}$)'),
    'ADJuvel':   ('eastward velocity',           'dJ / (m s$^{-1}$)'),
    'ADJvvel':   ('northward velocity',          'dJ / (m s$^{-1}$)'),
    'ADJwvel':   ('vertical velocity',           'dJ / (m s$^{-1}$)'),
    'ADJetan':   ('free-surface height',         'dJ / m'),
    'ADJqnet':   ('net surface heat flux',       'dJ / (W m$^{-2}$)'),
    'ADJqsw':    ('shortwave heat flux',         'dJ / (W m$^{-2}$)'),
    'ADJempmr':  ('freshwater flux E$-$P$-$R',   'dJ / (kg m$^{-2}$ s$^{-1}$)'),
    'ADJtaux':   ('eastward wind stress',        'dJ / (N m$^{-2}$)'),
    'ADJtauy':   ('northward wind stress',       'dJ / (N m$^{-2}$)'),
}
# dumps between frames (a dump is 5 days). The three films the deck has shown since 2026-09-15 keep
# their 30-day stride so the boundary-wave stage is still resolved; the other nine are 60-day, which
# halves the pages the deck has to carry.
FILM_STRIDE = {'ADJtheta': 6, 'ADJdiffkr': 6, 'ADJqnet': 6}
DEFAULT_STRIDE = 12
MEMBER_VARS = ['ADJtheta', 'ADJdiffkr']       # the two the ensemble's results rest on
KCOST = c.KMAX                                # 25: the cost integrates the upper 25 levels (982 m)

PROFILES = c.CACHE / 'level_rms_profiles.npz'
INDEX = c.ANIMS / 'films_index.tsv'


# ---------------------------------------------------------------- per-level RMS, and the level choice
def profiles(stride=12, **_):
    """Time-mean horizontal RMS of each 3-D dump at each level, and RMS against lead for all 12.

    Writes cache/level_rms_profiles.npz (`prof_<var>` (nz,), `lead` (nt,), `rms_<var>` (nt,)) and the
    figure that explains the level choice. One pass over the reference adjoint's dumps.
    """
    g = c.grid()
    d = c.run_dir(c.ADJ_JOB['REF'])
    its = c.ITERS[::stride]
    out = {'lead': c.lead_years(its), 'iters': its, 'rc': g['RC']}
    for var in INFO:
        m = c.mask(var)
        three = var in c.ADJ_3D
        prof = np.zeros(g['RC'].size)
        ser = np.zeros(its.size)
        for n, it in enumerate(its):
            a = c.read_mds(c.dump_base(d, var, it), np.float32).astype(np.float64)
            ser[n] = c.rms(np.where(m, a, np.nan))
            if three:
                for k in range(g['RC'].size):
                    if m[k].any():
                        prof[k] += np.sqrt(np.mean(a[k][m[k]] ** 2))
        if three:
            out['prof_' + var] = prof / its.size
        out['rms_' + var] = ser
        print('%-10s rms  lead 0 %.3g -> lead 5 %.3g  (%s)'
              % (var, ser[-1], ser[0], 'grows backwards: a running total' if ser[0] > ser[-1] else 'decays backwards: a state'),
              flush=True)
    c.CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(PROFILES, **out)
    print('wrote', PROFILES)
    _figure_level_choice()


def kind_of(var):
    """(phrase for the caption, peak lead in yr, ratio rms(5 yr)/rms(0)) from the measured curve.

    An adjoint state is set once, at the start of the window, so its dump peaks near lead 0 and
    decays backwards; a running total peaks at the far end of the window. Measured, not assumed:
    ADJtauy and ADJqsw are neither, and the caption says so.
    """
    z = np.load(PROFILES)
    lead, s = z['lead'], z['rms_' + var]
    o = np.argsort(lead)
    lead, s = lead[o], s[o]
    peak, r = float(lead[s.argmax()]), float(s[-1] / s[0]) if s[0] > 0 else np.inf
    span = lead[-1]
    if peak > 0.8 * span and r > 3:
        return 'running total so far', peak, r
    if peak < 0.2 * span and r < 0.5:
        return 'adjoint state, decays backwards', peak, r
    return 'peaks %.1f yr back' % peak, peak, r


def levels_of(var):
    """(k_inside, k_below): the two levels a 3-D film shows -- see the module docstring."""
    p = np.load(PROFILES)['prof_' + var]
    return int(p[:KCOST].argmax()), KCOST + int(p[KCOST:].argmax())


def _figure_level_choice():
    """The profiles the rule reads, with the two chosen levels marked. This IS the explanation."""
    z = np.load(PROFILES)
    rc = z['rc']
    v3 = [v for v in INFO if v in c.ADJ_3D]
    fig, axs = plt.subplots(1, len(v3), figsize=(2.05 * len(v3), 3.5), sharey=True)
    for ax, var in zip(np.atleast_1d(axs), v3):
        p = z['prof_' + var]
        p = p / (p.max() or 1.0)
        ki, kb = levels_of(var)
        ax.plot(p, -rc, color=c.SERIES[0], lw=1.5)
        ax.axhspan(0, 982, color=c.SERIES[0], alpha=0.07, lw=0)
        for k, col in ((ki, c.SERIES[1]), (kb, c.SERIES[2])):
            ax.plot([p[k]], [-rc[k]], 'o', color=col, ms=5.5)
            ax.annotate('%d m' % round(-rc[k]), (p[k], -rc[k]), textcoords='offset points',
                        xytext=(6, -2), fontsize=7.5, color=col)
        ax.set_title(var.replace('ADJ', ''), fontsize=9.5)
        ax.set_xlim(0, 1.35)
        ax.set_xticks([0, 0.5, 1])
        ax.grid(True, alpha=0.5)
    np.atleast_1d(axs)[0].set_ylim(4400, 0)
    np.atleast_1d(axs)[0].set_ylabel('depth [m]')
    fig.text(0.5, -0.02, 'time-mean horizontal RMS of the dump, normalised by its column maximum; '
                         'the shaded band is the upper 982 m the cost integrates',
             ha='center', fontsize=8, color=c.INK2)
    fig.savefig(c.FIGS / 'adj_level_choice.png', bbox_inches='tight')
    plt.close(fig)
    print('wrote', c.FIGS / 'adj_level_choice.png')


# ---------------------------------------------------------------- drawing
def _panel(ax, f2d, vmax, title):
    g = c.grid()
    pm = ax.pcolormesh(g['XC'], g['YC'], np.ma.masked_invalid(f2d), cmap=c.diverging_cmap(),
                       vmin=-vmax, vmax=vmax, shading='auto', rasterized=True)
    ax.plot(g['XC'][c.JSEC], g['YC'][c.JSEC], color=c.INK, lw=1.0)
    ax.set_title(title, fontsize=9)
    ax.grid(False)
    ax.tick_params(labelsize=7.5)
    return pm


class Film:
    """Collects frames one at a time: a page into the multi-page PDF, a thumbnail into the GIF.

    Streaming matters -- a 61-frame film held as 61 open matplotlib figures is a few GB. `close()`
    finishes the PDF in the animations directory, writes the GIF and the last-frame still, and copies
    the PDF to any extra directory (the deck's figures/).
    """

    def __init__(self, stem, copy_to=()):
        c.ANIMS.mkdir(parents=True, exist_ok=True)
        self.stem, self.copy_to, self.ims = stem, [d for d in copy_to if d], []
        self.path = c.ANIMS / ('film_%s.pdf' % stem)
        self.pdf = PdfPages(str(self.path))

    def add(self, fig):
        self.pdf.savefig(fig, dpi=120)
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=72, facecolor=c.SURFACE)
        buf.seek(0)
        self.ims.append(Image.open(buf).convert('RGB'))
        plt.close(fig)

    def close(self):
        self.pdf.close()
        print('  wrote %s (%d pages, %.2f MB)' % (self.path, len(self.ims), self.path.stat().st_size / 1e6))
        pal = [im.convert('P', palette=Image.ADAPTIVE, colors=160) for im in self.ims]
        gif = c.ANIMS / ('film_%s.gif' % self.stem)
        pal[0].save(gif, save_all=True, append_images=pal[1:], duration=130, loop=0, optimize=True)
        self.ims[-1].save(str(gif)[:-4] + '_still.png')     # the longest lead, for reduced motion
        print('  wrote %s (%.2f MB)' % (gif, gif.stat().st_size / 1e6))
        for od in self.copy_to:
            Path(od).mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.path, Path(od) / self.path.name)
            print('  copied to %s' % (Path(od) / self.path.name))
        self.ims = []


def _rows():
    return [] if not INDEX.exists() else INDEX.read_text().splitlines()[1:]


def _index(rows):
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    keep = {r.split('\t')[0]: r for r in _rows()}
    for r in rows:
        keep[r.split('\t')[0]] = r
    INDEX.write_text('film\trun\tvariable\twhat\tpanels\tframes\tstride_days\tlead_yr\tscale\tunits\n'
                     + '\n'.join(keep[k] for k in sorted(keep)) + '\n')
    print('wrote', INDEX)


# ---------------------------------------------------------------- the reference adjoint, all 12 dumps
def reference(stride=None, deck=None, only=None, **_):
    g = c.grid()
    job = c.ADJ_JOB['REF']
    d = c.run_dir(job)
    deck_films = {'film_%s' % v.replace('ADJ', '') for v in INFO}     # the deck embeds all twelve
    rows = []
    for var in (only or list(INFO)):
        what, units = INFO[var]
        kind, peak, ratio = kind_of(var)
        st = stride or FILM_STRIDE.get(var, DEFAULT_STRIDE)
        its = c.ITERS[::st][::-1]                       # page 1 = the end of the window
        three = var in c.ADJ_3D
        m = c.mask(var)
        ks = levels_of(var) if three else ()
        data = []
        for it in its:
            a = c.read_mds(c.dump_base(d, var, it), np.float32).astype(np.float64)
            data.append(np.stack([np.where(m[k], a[k], np.nan) for k in ks]) if three
                        else np.where(m, a, np.nan)[None])
        data = np.array(data)
        vmax = c.robust_sym(data, 99.5)
        e = int(np.floor(np.log10(vmax))) if vmax > 0 else 0
        npan = data.shape[1]
        stem = var.replace('ADJ', '')
        film = Film(stem, [deck] if deck and ('film_' + stem) in deck_films else [])
        for n, it in enumerate(its):
            L = float(c.lead_years(it))
            fig, axs = plt.subplots(1, npan, figsize=(4.7 * npan if npan > 1 else 6.2, 4.6), squeeze=False)
            fig.subplots_adjust(top=0.80, bottom=0.11)
            for p_, ax in enumerate(axs[0]):
                pm = _panel(ax, data[n][p_] / 10.0 ** e, vmax / 10.0 ** e,
                            ('%d m' % round(-g['RC'][ks[p_]])) if three else '')
                ax.set_xlabel('longitude')
                if p_ == 0:
                    ax.set_ylabel('latitude')
            fig.suptitle('sensitivity of $J$ to %s   $\\cdot$   %s\n'
                         'lead %4.2f yr before the end of the cost window   $\\cdot$   frame max %.2e'
                         % (what, kind, L, np.nanmax(np.abs(data[n]))), fontsize=10, y=0.985)
            cb = fig.colorbar(pm, ax=axs[0], shrink=0.85, pad=0.02)
            cb.set_label(('%s  $\\times10^{%d}$' % (units, e)) if e else units, fontsize=9)
            cb.ax.tick_params(labelsize=8)
            film.add(fig)
        film.close()
        rows.append('\t'.join(['film_%s' % stem, str(job), var,
                               '%s (%s; peak at lead %.2f yr, rms 5 yr / rms 0 = %.3g)' % (what, kind, peak, ratio),
                               ' + '.join('%d m' % round(-g['RC'][k]) for k in ks) or 'surface',
                               str(len(its)), str(5 * st), '%.2f-%.2f' % (0.0, float(c.lead_years(its[-1]))),
                               'fixed, 99.5th pct = %.3e' % vmax, units.replace('$', '')]))
    _index(rows)


# ---------------------------------------------------------------- the ensemble
def members(stride=None, deck=None, **_):
    """One film per member per variable, and the all-members panel film the deck embeds."""
    g = c.grid()
    dirs = {r: c.run_dir(c.ADJ_JOB[r]) for r in c.RUN_ORDER}
    rows = []
    for var in MEMBER_VARS:
        what, units = INFO[var]
        kind = kind_of(var)[0]
        st = stride or DEFAULT_STRIDE
        its = c.ITERS[::st][::-1]
        m = c.mask(var)
        ki, kb = levels_of(var)
        # the panel films show the column sum, the quantity the ensemble figures compare
        cols = {}
        for r in c.RUN_ORDER:
            fr = []
            for it in its:
                a = c.read_mds(c.dump_base(dirs[r], var, it), np.float32).astype(np.float64)
                fr.append(np.where(m.any(axis=0), np.where(m, a, 0.0).sum(axis=0), np.nan))
            cols[r] = np.array(fr)
        vmax = c.robust_sym(np.array([cols[r] for r in c.RUN_ORDER]), 99.5)
        e = int(np.floor(np.log10(vmax))) if vmax > 0 else 0
        film = Film('members_' + var.replace('ADJ', ''), [deck] if deck else [])
        for n, it in enumerate(its):
            L = float(c.lead_years(it))
            fig, axs = plt.subplots(1, len(c.RUN_ORDER), figsize=(1.55 * len(c.RUN_ORDER), 4.2),
                                    squeeze=False, sharey=True)
            fig.subplots_adjust(top=0.80, bottom=0.08, left=0.04, right=0.90, wspace=0.12)
            for ax, r in zip(axs[0], c.RUN_ORDER):
                pm = _panel(ax, cols[r][n] / 10.0 ** e, vmax / 10.0 ** e, c.LABEL[r])
                ax.set_xticks([])
                ax.set_yticks([])
            fig.suptitle('column sum of the sensitivity of $J$ to %s, every member\n'
                         'lead %4.2f yr before the end of the cost window' % (what, L), fontsize=10.5, y=0.985)
            cb = fig.colorbar(pm, ax=axs[0], shrink=0.8, pad=0.015)
            cb.set_label(('%s m  $\\times10^{%d}$' % (units, e)) if e else units, fontsize=8.5)
            cb.ax.tick_params(labelsize=7.5)
            film.add(fig)
        film.close()
        stem = 'members_' + var.replace('ADJ', '')
        rows.append('\t'.join(['film_%s' % stem, '31374-31381', var, what + ', all eight members',
                               'column sum', str(len(its)), str(5 * st),
                               '%.2f-%.2f' % (0.0, float(c.lead_years(its[-1]))),
                               'fixed, 99.5th pct = %.3e' % vmax, units.replace('$', '') + ' m']))

        # and one film per member, at the two levels of the rule -- the full collection, not embedded
        for r in c.RUN_ORDER:
            data = []
            for it in its:
                a = c.read_mds(c.dump_base(dirs[r], var, it), np.float32).astype(np.float64)
                data.append(np.stack([np.where(m[k], a[k], np.nan) for k in (ki, kb)]))
            data = np.array(data)
            vm = c.robust_sym(data, 99.5)
            em = int(np.floor(np.log10(vm))) if vm > 0 else 0
            film = Film('%s_%s' % (r, var.replace('ADJ', '')))
            for n, it in enumerate(its):
                L = float(c.lead_years(it))
                fig, axs = plt.subplots(1, 2, figsize=(9.0, 4.5), squeeze=False)
                fig.subplots_adjust(top=0.82, bottom=0.10)
                for p_, (ax, k) in enumerate(zip(axs[0], (ki, kb))):
                    pm = _panel(ax, data[n][p_] / 10.0 ** em, vm / 10.0 ** em, '%d m' % round(-g['RC'][k]))
                    ax.set_xlabel('longitude')
                    if p_ == 0:
                        ax.set_ylabel('latitude')
                fig.suptitle('%s: sensitivity of $J$ to %s  ($\\kappa_v = %g \\times$ reference)\n'
                             'lead %4.2f yr before the end of the cost window'
                             % (r, what, c.FACTOR[r], L), fontsize=11, y=0.985)
                cb = fig.colorbar(pm, ax=axs[0], shrink=0.85, pad=0.02)
                cb.set_label(('%s  $\\times10^{%d}$' % (units, em)) if em else units, fontsize=9)
                cb.ax.tick_params(labelsize=8)
                film.add(fig)
            film.close()
            stem = '%s_%s' % (r, var.replace('ADJ', ''))
            rows.append('\t'.join(['film_%s' % stem, str(c.ADJ_JOB[r]), var,
                                   '%s, member %s (%gx reference)' % (what, r, c.FACTOR[r]),
                                   '%d m + %d m' % (round(-g['RC'][ki]), round(-g['RC'][kb])),
                                   str(len(its)), str(5 * st),
                                   '%.2f-%.2f' % (0.0, float(c.lead_years(its[-1]))),
                                   'fixed, 99.5th pct = %.3e' % vm, units.replace('$', '')]))
    _index(rows)


STEPS = {'profiles': profiles, 'reference': reference, 'members': members}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('steps', nargs='+', help='profiles | reference | members | all')
    ap.add_argument('--stride', type=int, default=None, help='dumps between frames (a dump is 5 d)')
    ap.add_argument('--deck', default=None, help='also write the deck-embedded films here')
    ap.add_argument('--only', nargs='*', default=None, help='restrict `reference` to these variables')
    a = ap.parse_args()
    c.setup_style()
    c.ensure_dirs()
    for s in (list(STEPS) if a.steps == ['all'] else a.steps):
        print('=== %s' % s, flush=True)
        STEPS[s](stride=a.stride, deck=a.deck, only=a.only)
