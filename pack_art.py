"""
pack_art.py: the card pack drawn as two little svg pieces, the tear-off top and the body.
the top and bottom edges use the exact same crimp pattern (one flipped over the other)
so the pack reads as one balanced object. everything sits on a 10px grid with hard edges.
"""

PLUM, BLUSH, BLUSH_DARK = "#4A3B5C", "#D9A0A6", "#C98A92"
CREAM, GOLD, SPARK = "#EDE6D3", "#C9A876", "#F3DC8E"
W = 260            # pack width
TOOTH = 10         # width of one crimp tooth
STEP = 8           # how tall a crimp tooth is
TOP_H, BODY_H = 56, 284
TEXT_FONT = "font-family: 'Press Start 2P', monospace"   # a plain svg font-family attribute can't take a name that starts a word with a digit


def _crimp(y_hi, y_lo):
    """a row of square teeth across the whole width, left to right."""
    pts = [(0, y_lo)]
    for k in range(W // (TOOTH * 2)):
        x = k * TOOTH * 2
        pts += [(x, y_hi), (x + TOOTH, y_hi), (x + TOOTH, y_lo), (x + TOOTH * 2, y_lo)]
    return pts


def _path(points, close=False):
    d = "M" + " L".join(f"{x},{y}" for x, y in points)
    return d + (" Z" if close else "")


def _plus(x, y, arm, thick, fill, opacity=1):
    return (f'<rect x="{x - arm}" y="{y - thick / 2}" width="{arm * 2}" height="{thick}" fill="{fill}" fill-opacity="{opacity}"/>'
            f'<rect x="{x - thick / 2}" y="{y - arm}" width="{thick}" height="{arm * 2}" fill="{fill}" fill-opacity="{opacity}"/>')


def _svg(inner, height):
    return (f'<svg class="pack-svg" width="{W + 6}" height="{height + 6}" viewBox="-3 -3 {W + 6} {height + 6}" '
            f'shape-rendering="crispEdges" aria-hidden="true">{inner}</svg>')


def top_piece():
    """the strip that tears off. open at the bottom, the body draws the seam line."""
    pts = [(0, TOP_H)] + _crimp(0, STEP) + [(W, TOP_H)]
    sparkles = "".join(_plus(x, 34, 5, 3, CREAM, 0.85) for x in range(26, W, 26))
    inner = (
        f'<path d="{_path(pts, close=True)}" fill="{BLUSH_DARK}"/>'
        f'<rect x="4" y="15" width="{W - 8}" height="3" fill="{CREAM}" fill-opacity=".45"/>'
        f'{sparkles}'
        f'<path d="{_path(pts)}" fill="none" stroke="{PLUM}" stroke-width="5" stroke-linejoin="miter"/>'
    )
    return _svg(inner, TOP_H)


def body_piece(uid="pack"):
    """the front of the pack: a kawaii star on a cream medallion and a banner, with the bottom
    edge crimped exactly like the top."""
    bottom = list(reversed(_crimp(BODY_H, BODY_H - STEP)))
    pts = [(0, 0), (W, 0)] + bottom
    star = "20,4 24,15 36,15 26,22 30,34 20,26 10,34 14,22 4,15 16,15"
    face = (
        '<rect x="14.6" y="15" width="3.2" height="4.4" fill="#4A3B5C"/><rect x="22.2" y="15" width="3.2" height="4.4" fill="#4A3B5C"/>'
        '<rect x="12.2" y="20.4" width="3.6" height="2.2" fill="#D9A0A6"/><rect x="24.2" y="20.4" width="3.6" height="2.2" fill="#D9A0A6"/>'
        '<rect x="17.8" y="21.2" width="4.4" height="1.4" fill="#4A3B5C"/>'
    )
    sparkles = "".join(_plus(x, y, 6, 3, SPARK) for x, y in [(62, 78), (200, 86), (70, 168), (192, 172)])
    inner = (
        f'<clipPath id="clip-{uid}"><path d="{_path(pts, close=True)}"/></clipPath>'
        f'<path d="{_path(pts, close=True)}" fill="{BLUSH}"/>'
        # two hard edged glare stripes, like light catching foil
        f'<g clip-path="url(#clip-{uid})" fill="{CREAM}">'
        f'<polygon points="150,0 196,0 66,{BODY_H} 20,{BODY_H}" fill-opacity=".20"/>'
        f'<polygon points="206,0 222,0 92,{BODY_H} 76,{BODY_H}" fill-opacity=".15"/></g>'
        f'{sparkles}'
        f'<circle cx="131" cy="122" r="48" fill="{CREAM}" stroke="{PLUM}" stroke-width="4"/>'
        f'<g transform="translate(93 86) scale(1.9)"><polygon points="{star}" fill="{GOLD}" stroke="{PLUM}" stroke-width="1.6" stroke-linejoin="round"/>{face}</g>'
        f'<rect x="30" y="200" width="200" height="38" fill="{CREAM}" stroke="{PLUM}" stroke-width="3.5"/>'
        f'{_plus(48, 219, 4, 3, GOLD)}{_plus(212, 219, 4, 3, GOLD)}'
        f'<text x="130" y="224" text-anchor="middle" font-size="11" fill="{PLUM}" shape-rendering="auto" style="{TEXT_FONT}">TYPE PACK</text>'
        f'<path d="{_path(pts, close=True)}" fill="none" stroke="{PLUM}" stroke-width="5" stroke-linejoin="miter"/>'
    )
    return _svg(inner, BODY_H)
