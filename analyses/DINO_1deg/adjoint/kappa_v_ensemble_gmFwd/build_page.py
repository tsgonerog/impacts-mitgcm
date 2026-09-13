#!/usr/bin/env python3
"""Assemble the published analysis page from the campaign's figures, animations and tables.

    python build_page.py        # -> page/index.html plus page/fig/*, next to this script

page/ is build output: its .html/.png/.gif are ignored by git (analyses/**/*.{png,gif,html}); the
canonical figures stay on scratch in analysis/<campaign>/figures and animations. The narrative lives in
page_text.py, written after the numbers were read; every number quoted there is read from the stats
files at build time.
"""
import html
import json
import shutil
from pathlib import Path

import pandas as pd

import campaign as c

HERE = Path(__file__).resolve().parent
PAGE = HERE / 'page'
FIGDIR = PAGE / 'fig'


def esc(x):
    return html.escape(str(x))


def fig(name, caption, cls='', alt=None, gif=False):
    """A figure block; copies the file into page/fig/. A GIF gets a still PNG for reduced motion."""
    src = (c.ANIMS if gif else c.FIGS) / (name + ('.gif' if gif else '.png'))
    FIGDIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, FIGDIR / src.name)
    alt = esc(alt or caption.split('.')[0])
    if gif:
        still = c.ANIMS / (name + '_still.png')
        pic = '<img src="fig/%s" alt="%s" loading="lazy">' % (src.name, alt)
        if still.exists():
            shutil.copy2(still, FIGDIR / still.name)
            pic = ('<picture><source srcset="fig/%s" media="(prefers-reduced-motion: reduce)">%s</picture>'
                   % (still.name, pic))
    else:
        pic = '<img src="fig/%s" alt="%s" loading="lazy">' % (src.name, alt)
    return '<figure class="%s"><div class="plate">%s</div><figcaption>%s</figcaption></figure>' % (cls, pic, caption)


def table(df, cols, heads, num=(), mono=(), fmt=None):
    fmt = fmt or {}
    h = ''.join('<th>%s</th>' % esc(x) for x in heads)
    rows = []
    for _, r in df.iterrows():
        cells = []
        for k in cols:
            v = r[k]
            if k in fmt:
                v = fmt[k](v, r)
                raw = True
            else:
                raw = False
            klass = 'num' if k in num else ('mono' if k in mono else '')
            cells.append('<td class="%s">%s</td>' % (klass, v if raw else esc(v)))
        rows.append('<tr>%s</tr>' % ''.join(cells))
    return '<div class="table-wrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (h, ''.join(rows))


def chip(text, kind):
    return '<span class="chip %s">%s</span>' % (kind, esc(text))


def stat(label, value, note=''):
    return ('<div class="stat"><div class="label">%s</div><div class="value">%s</div><div class="note">%s</div></div>'
            % (esc(label), value, note))


def build():
    import page_text
    PAGE.mkdir(exist_ok=True)
    css = (HERE / 'page_style.css').read_text()
    body = page_text.body(dict(fig=fig, table=table, chip=chip, stat=stat, esc=esc, pd=pd, json=json, c=c))
    doc = ('<title>DINO κ_v Sensitivity Ensemble</title>\n'
           '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
           '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
           '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&'
           'family=IBM+Plex+Sans+Condensed:wght@500;600&family=IBM+Plex+Sans:ital,wght@0,400;0,600;1,400&display=swap">\n'
           '<style>\n%s\n</style>\n%s\n' % (css, body))
    (PAGE / 'index.html').write_text(doc)
    print('wrote', PAGE / 'index.html', '%.0f kB' % ((PAGE / 'index.html').stat().st_size / 1e3))
    print('files:', sorted(p.name for p in FIGDIR.iterdir()))


if __name__ == '__main__':
    build()
