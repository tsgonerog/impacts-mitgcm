#!/usr/bin/env python3
"""The vertical-diffusivity control at the reference: the array the adjoint differentiates, in 3-D and in 2-D.

    python diffkr_field.py                     # -> analysis/<campaign>/figures/diffkr_field{,_3d,_2d}.png
    python diffkr_field.py --notes ~/Proj_ImPACTS/impacts-docs/references/dino_overturning_sensitivity/notes/figures

Three figures: the 3-D view and the 2-D views each on their own (for slides), and both on one page with one
colour bar (diffkr_field.png, the figure of the notes' Section 4.1, which --notes copies there).

WHAT IS DRAWN. The forward namelist sets kappa_v as one number (diffKrT = diffKrS = 1.2E-5), and under
ALLOW_3D_DIFFKR that number initialises the array diffKr(i,j,k) (model/src/ini_mixing.F); the control
xx_diffkr is added to that array, and the adjoint returns d J / d diffKr for every cell of it. The figures
show the array as the reference adjoint used it, rebuilt from that run's own files rather than from the
committed namelist: diffKrT read from the staged `data`, plus `xx_diffkr.0000000000` (zero at the
reference: the run differentiates, it does not perturb), on the cells where `maskCtrlC` is 1. The script
checks that diffKrS equals diffKrT (the one array serves both tracers), that the perturbation is zero and
that the control mask is the model's wet mask, and stops otherwise.

So at the reference the field is uniform: every wet cell holds the same value, and only the land (the
side walls, and below about 2000 m the continental slopes and the ridge in the southern channel) gives
the figure any structure. That is the point it makes for Section 4.1 of the notes: the sensitivity is a
field because the control is an array of tied copies of one number, not because the number varies.

WHAT IS NOT IN THE ARRAY. The model's net vertical diffusivity adds two things the control never sees
(model/src/calc_3d_diffusivity.F): ivdc_kappa = 100 m2/s on every interface where the column is
statically unstable (implicitDiffusion), added to diffKr rather than replacing it, and the vertical part
of the GM/Redi tensor. Neither is drawn.

COLOUR. A log scale spanning the ensemble's eight values (0.25x to 32x the reference), each a tick, so the
reference has the colour it would have beside the other members: every member is the same uniform field
in another colour. Land is grey.
"""
import argparse
import re
import shutil
from pathlib import Path

import numpy as np

import campaign as C


# ---------------------------------------------------------------- the array, rebuilt from the run
def reference_field(job=None):
    """diffKr(k, j, i) of the reference adjoint (NaN on land), its value, the grid and the run directory."""
    d = C.run_dir(job or C.ADJ_JOB['REF'])
    txt = (d / 'data').read_text()

    def key(name):
        m = re.search(r'^\s*%s\s*=\s*([-+0-9.EeDd]+)' % name, txt, re.M)
        return float(m.group(1).replace('D', 'E').replace('d', 'e'))

    kT, kS = key('diffKrT'), key('diffKrS')
    if kT != kS:
        raise SystemExit('diffKrT %g and diffKrS %g differ: one array no longer serves both tracers' % (kT, kS))
    xx = C.read_mds(d / 'xx_diffkr.0000000000')
    if np.any(xx != 0):
        raise SystemExit('xx_diffkr is not zero in %s: this is not a reference run' % d.name)
    g = C.grid(d)
    m = C.read_mds(d / 'maskCtrlC') > 0
    if not np.array_equal(m, g['wetC']):
        raise SystemExit('maskCtrlC is not the wet mask hFacC > 0')
    return np.where(m, kT + xx, np.nan), kT, g, d


def _edges_1d(c, gc):
    """Edges from cell centres c and the grid file's corner coordinates gc along the same line. DINO's XG/YG are
    the cells' north-east corners (XG = XC + 0.5, YG[j] is the northern edge of row j: the cost row's southern face,
    42.84 N, is YG[146]), not the south-west corners MITgcm usually writes, so the side is read off the data."""
    if gc[0] > c[0]:
        return np.concatenate([[2 * c[0] - gc[0]], gc])
    return np.append(gc, 2 * c[-1] - gc[-1])


def edges(g):
    """Cell edges: longitude (52), latitude (199), depth (37, positive down)."""
    xe = _edges_1d(g['XC'][0], g['XG'][0])
    ye = _edges_1d(g['YC'][:, 0], g['YG'][:, 0])
    if np.any(np.diff(xe) <= 0) or np.any(np.diff(ye) <= 0):
        raise SystemExit('cell edges are not monotonic: the grid convention is not the one this script reads')
    ze = -np.asarray(g['RF']).ravel()
    return xe, ye, ze


def colour(kT):
    from matplotlib.colors import LogNorm
    cm = C.sequential_cmap()
    values = [kT * C.FACTOR[r] for r in C.RUN_ORDER]
    return cm, LogNorm(vmin=min(values), vmax=max(values)), values


def rgba(a, cm, norm):
    """Face colours for a 2-D slab of the field, land grey."""
    from matplotlib.colors import to_rgba
    out = cm(norm(np.where(np.isfinite(a), a, norm.vmin)))
    out[~np.isfinite(a)] = to_rgba(C.LAND)
    return out


def colourbar(fig, cax, cm, norm, values, kT, orientation='horizontal'):
    import matplotlib as mpl
    cb = fig.colorbar(mpl.cm.ScalarMappable(norm=norm, cmap=cm), cax=cax, orientation=orientation)
    cb.minorticks_off()
    cb.set_ticks(values)
    cb.set_ticklabels(['%gx' % (v / kT) for v in values])
    cb.set_label(r'$\kappa_v$ as a multiple of the reference, $1.2\times10^{-5}\ \mathrm{m^2\,s^{-1}}$ (log scale)')
    cb.outline.set_edgecolor(C.AXIS_C)
    return cb


# ---------------------------------------------------------------- the 3-D view
ICUT = 25            # the block is cut open along the meridian between columns 24 and 25 (26 W): its western half
J0, J1 = 1, 196      # the wet rows; rows 0, 196 and 197 are land at every level


def surface(ax, X, Y, Z, fc):
    ax.plot_surface(X, Y, Z, facecolors=fc, rstride=1, cstride=1, shade=False, linewidth=0, antialiased=False,
                    zorder=1)


def draw_3d(fig, rect, field, kT, g):
    """The western half of the basin as a solid block in the axes at `rect`: the surface layer on top, the cut along
    26 W facing east, the southernmost wet row facing south. The faces are not shaded: on this colour scale a darker
    face would read as a larger diffusivity, so the block's edges are drawn instead."""
    cm, norm, values = colour(kT)
    xe, ye, ze = edges(g)
    xs, ys = xe[:ICUT + 1], ye[J0:J1 + 1]
    ax = fig.add_axes(rect, projection='3d', computed_zorder=False)
    X, Y = np.meshgrid(xs, ys)
    surface(ax, X, Y, np.zeros_like(X), rgba(field[0, J0:J1, :ICUT], cm, norm))
    Y, Z = np.meshgrid(ys, -ze)
    surface(ax, np.full_like(Y, xs[-1]), Y, Z, rgba(field[:, J0:J1, ICUT - 1], cm, norm))
    X, Z = np.meshgrid(xs, -ze)
    surface(ax, X, np.full_like(X, ys[0]), Z, rgba(field[:, J0, :ICUT], cm, norm))
    edge = dict(color=C.INK2, lw=0.8, zorder=4)
    zb = -ze[-1]
    for x, y in ((xs[0], ys[0]), (xs[-1], ys[0]), (xs[-1], ys[-1])):
        ax.plot([x, x], [y, y], [0, zb], **edge)
    ax.plot([xs[0], xs[-1], xs[-1]], [ys[0], ys[0], ys[-1]], [0, 0, 0], **edge)
    ax.plot([xs[0], xs[0], xs[-1]], [ys[-1], ys[0], ys[0]], [0, 0, 0], **edge)
    ax.plot([xs[0], xs[-1], xs[-1]], [ys[0], ys[0], ys[-1]], [zb, zb, zb], **edge)
    # the cost row on the top face, and down the cut to the depth the cost integrates to
    yc, acc = ye[C.JSEC], C.SERIES[1]
    ax.plot([xs[0], xs[-1]], [yc, yc], [0, 0], color=acc, lw=1.4, zorder=5)
    ax.plot([xs[-1], xs[-1]], [yc, yc], [0, -ze[C.KMAX]], color=acc, lw=2.4, zorder=5)
    ax.text(xs[0] - 1, yc, 300, 'cost row, %.0f N' % C.sec_lat(), color=acc, fontsize=8.5, ha='right', va='bottom',
            zdir=None, zorder=5)
    ax.set_box_aspect((1.0, 2.6, 0.95))
    ax.view_init(elev=24, azim=-58)
    ax.set_xlim(xs[0], xs[-1]); ax.set_ylim(ys[0], ys[-1]); ax.set_zlim(zb, 0)
    ax.set_xticks([-50, -40, -30]); ax.set_yticks([-60, -30, 0, 30, 60])
    ax.set_zticks([0, -1000, -2000, -3000, -4000])
    ax.set_zticklabels(['0', '1000', '2000', '3000', '4000'])
    ax.set_xlabel('longitude (E)', labelpad=2)
    ax.set_ylabel('latitude (N)', labelpad=6)
    ax.set_zlabel('depth (m)', labelpad=12)
    for a in (ax.xaxis, ax.yaxis, ax.zaxis):
        a.pane.set_facecolor(C.SURFACE); a.pane.set_edgecolor(C.GRID_C)
    ax.grid(False)
    return ax, -xs[-1]


def headline(field):
    return ('Every one of the %s wet cells holds the same value, '
            r'$\kappa_v = 1.2\times10^{-5}\ \mathrm{m^2\,s^{-1}}$'
            % format(int(np.isfinite(field).sum()), ',').replace(',', '\u2009'))


# ---------------------------------------------------------------- the 2-D views
def draw_2d(fig, axes, field, kT, g, letters='abcd', short=False):
    """Into the four axes `axes` (surface map, deepest-level map, section at the cost row, profile): the same array
    in two dimensions. `short` shortens the titles for the one-row layout."""
    from matplotlib.patches import Rectangle
    cm, norm, values = colour(kT)
    xe, ye, ze = edges(g)
    acc = C.SERIES[1]
    kdeep = int(np.nonzero(np.isfinite(field).any(axis=(1, 2)))[0][-1])
    js, kc = C.JSEC, C.KMAX
    ms, md, sec, prof = axes
    for n, (ax, k) in enumerate(((ms, 0), (md, kdeep))):
        ax.pcolormesh(xe, ye, np.ma.masked_invalid(field[k]), cmap=cm, norm=norm, rasterized=True)
        ax.axhline(ye[js], color=acc, lw=1.2)
        ax.set_xlim(xe[0], xe[-1]); ax.set_ylim(ye[0], ye[-1])
        ax.set_xticks([-40, 0] if short else [-40, -20, 0]); ax.set_yticks([-60, -30, 0, 30, 60])
        ax.grid(False)
        ax.set_title('(%s) %.0f m' % (letters[n], -g['RC'][k]), loc='left', fontsize=9.5)
        ax.set_xlabel('longitude (E)')
    ms.set_ylabel('latitude (N)')
    md.set_yticklabels([])
    ms.text(xe[0] + 1, ye[js] + 2, 'cost row', color=acc, fontsize=8, va='bottom')
    # the zonal section at the cost row, with the part the cost integrates over outlined
    sec.pcolormesh(xe, ze, np.ma.masked_invalid(field[:, js, :]), cmap=cm, norm=norm, rasterized=True)
    wet = np.nonzero(np.isfinite(field[0, js]))[0]
    sec.add_patch(Rectangle((xe[wet[0]], 0), xe[wet[-1] + 1] - xe[wet[0]], ze[kc], fill=False, ec=acc, lw=1.4))
    sec.text(xe[wet[0]] + 1.5, ze[kc] + 120, 'J: northward transport\nabove %.0f m' % ze[kc], color=acc,
             fontsize=8, va='top', linespacing=1.3)
    sec.set_xlim(xe[0], xe[-1]); sec.set_ylim(ze[-1], 0)
    sec.set_xticks([-40, -20, 0] if short else [-50, -40, -30, -20, -10, 0]); sec.set_yticks([0, 1000, 2000, 3000, 4000])
    sec.grid(False)
    sec.set_xlabel('longitude (E)'); sec.set_ylabel('depth (m)')
    sec.set_title(('(%s) the cost row, %.1f N' if short else '(%s) the zonal section at the cost row, %.1f N')
                  % (letters[2], C.sec_lat()), loc='left', fontsize=9.5)
    # the profile: one dot per wet level, the other members' values for scale
    zc = -np.asarray(g['RC']).ravel()
    for r, v in zip(C.RUN_ORDER, values):
        if r != 'REF':
            prof.axvline(v, color=C.AXIS_C, lw=0.9, zorder=1)
            if not short or C.FACTOR[r] in (0.25, 32.0):
                prof.text(v, -60, '%gx' % C.FACTOR[r], color=C.MUTED, fontsize=7.5, ha='center', va='bottom')
    kw = np.isfinite(field).any(axis=(1, 2))
    prof.plot([kT] * int(kw.sum()), zc[kw], 'o', ms=2.6, color=cm(norm(kT)), mec=C.SERIES[0], mew=0.6, zorder=3)
    prof.axvline(kT, color=C.SERIES[0], lw=1.2, zorder=2)
    prof.text(kT, -60, '1x', color=C.SERIES[0], fontsize=7.5, ha='center', va='bottom', fontweight='bold')
    prof.axhline(ze[kc], color=acc, lw=0.9, ls='--')
    prof.text(values[-1] * 1.5, ze[kc] + 60, '%.0f m' % ze[kc], color=acc, fontsize=7.5, ha='right', va='top')
    prof.set_xscale('log'); prof.set_xlim(values[0] / 1.6, values[-1] * 1.6); prof.set_ylim(ze[-1], 0)
    prof.set_yticks([0, 1000, 2000, 3000, 4000])
    prof.minorticks_off()
    prof.set_xlabel(r'$\kappa_v$ (m$^2$ s$^{-1}$)')
    if short:                       # beside the section, whose depth axis it shares
        prof.set_yticklabels([])
    else:
        prof.set_ylabel('depth (m)')
    prof.set_title(('(%s) %d wet levels' if short else '(%s) the profile: one dot per level, %d wet levels')
                   % (letters[3], int(kw.sum())), loc='left', fontsize=9.5, pad=14)


# ---------------------------------------------------------------- the three figures
def plot_3d(field, kT, g, out):
    """The 3-D view on its own, for slides."""
    import matplotlib.pyplot as plt
    cm, norm, values = colour(kT)
    fig = plt.figure(figsize=(6.5, 5.0))
    ax, wlon = draw_3d(fig, [-0.04, 0.12, 1.0, 0.86], field, kT, g)
    fig.text(0.03, 0.975, headline(field), fontsize=9.5, color=C.INK, va='top')
    fig.text(0.03, 0.935, 'The western half of the basin, cut open along %.0f W. Grey: land (the continental slopes, '
             'and the sea floor below 4000 m).' % wlon, fontsize=8.5, color=C.INK2, va='top')
    colourbar(fig, fig.add_axes([0.12, 0.08, 0.76, 0.025]), cm, norm, values, kT)
    fig.savefig(out)
    plt.close(fig)


def plot_2d(field, kT, g, out):
    """The 2-D views on their own, for slides: two maps beside the section and the profile."""
    import matplotlib.pyplot as plt
    cm, norm, values = colour(kT)
    fig = plt.figure(figsize=(6.5, 5.2))
    gs = fig.add_gridspec(2, 4, width_ratios=[1, 1, 0.25, 2.3], height_ratios=[1, 1],
                          left=0.07, right=0.98, top=0.93, bottom=0.2, wspace=0.16, hspace=0.55)
    axes = [fig.add_subplot(gs[:, 0]), fig.add_subplot(gs[:, 1]), fig.add_subplot(gs[0, 3]), fig.add_subplot(gs[1, 3])]
    draw_2d(fig, axes, field, kT, g)
    colourbar(fig, fig.add_axes([0.12, 0.07, 0.76, 0.022]), cm, norm, values, kT)
    fig.savefig(out)
    plt.close(fig)


def plot_notes(field, kT, g, out):
    """Both on one page, for the notes: the 3-D view (a) with its headline beside it, the 2-D views (b-e) in one
    row beneath, one colour bar."""
    import matplotlib.pyplot as plt
    cm, norm, values = colour(kT)
    fig = plt.figure(figsize=(6.5, 7.7))
    ax, wlon = draw_3d(fig, [-0.07, 0.47, 0.76, 0.55], field, kT, g)
    fig.text(0.015, 0.975, '(a)', fontsize=9.5, color=C.INK, va='top')
    fig.text(0.715, 0.90, 'Every one of the\n%s wet cells holds\nthe same value,\n'
             r'$\kappa_v = 1.2\times10^{-5}\ \mathrm{m^2\,s^{-1}}$'
             % format(int(np.isfinite(field).sum()), ',').replace(',', '\u2009'),
             fontsize=9.5, color=C.INK, va='top', linespacing=1.45)
    fig.text(0.715, 0.72, 'The western half of the\nbasin, cut open along %.0f W.\nGrey: land (the continental\n'
             'slopes, and the sea floor\nbelow 4000 m).' % wlon, fontsize=8.5, color=C.INK2, va='top', linespacing=1.4)
    gs = fig.add_gridspec(1, 5, width_ratios=[0.62, 0.62, 0.34, 1.5, 1.1], left=0.085, right=0.985, top=0.43,
                          bottom=0.15, wspace=0.22)    # the third column is a spacer for the section's depth axis
    axes = [fig.add_subplot(gs[0, n]) for n in (0, 1, 3, 4)]
    draw_2d(fig, axes, field, kT, g, letters='bcde', short=True)
    axes[1].set_ylabel('')
    colourbar(fig, fig.add_axes([0.14, 0.055, 0.72, 0.017]), cm, norm, values, kT)
    fig.savefig(out)
    plt.close(fig)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--notes', default=None,
                    help="also copy the notes' figure (diffkr_field.png) into this directory (the notes' figures/)")
    a = ap.parse_args()
    C.setup_style()
    C.ensure_dirs()
    field, kT, g, d = reference_field()
    print('reference run %s: diffKr = %g m2/s in %d wet cells of %d' % (d.name, kT, np.isfinite(field).sum(), field.size))
    plot_3d(field, kT, g, C.FIGS / 'diffkr_field_3d.png')
    plot_2d(field, kT, g, C.FIGS / 'diffkr_field_2d.png')
    plot_notes(field, kT, g, C.FIGS / 'diffkr_field.png')
    for name in ('diffkr_field_3d.png', 'diffkr_field_2d.png', 'diffkr_field.png'):
        print(C.FIGS / name)
    if a.notes:
        dest = Path(a.notes).expanduser() / 'diffkr_field.png'
        shutil.copy2(C.FIGS / 'diffkr_field.png', dest)
        print('  copied to', dest)


if __name__ == '__main__':
    main()
