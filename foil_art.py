"""
foil_art.py: the little pixel patterns for the rainbow finish. a tile of sparkles (pluses and dots)
that sits over the back of the card, and the diagonal stripe fill for the radar shape.
same hard edges as the rest of the app, nothing smooth.
"""

import urllib.parse

RAINBOW = ["#E86A6A", "#F0A35E", "#F3D66B", "#8FCB7A", "#6FA8DC", "#A98BD9"]
TILE = 84   # the sparkle tile is a square this wide, it repeats across the back

def _plus(x, y, arm, fill, op=1):
    return (f'<rect x="{x - arm}" y="{y - 1}" width="{arm * 2}" height="2" fill="{fill}" fill-opacity="{op}"/>'
            f'<rect x="{x - 1}" y="{y - arm}" width="2" height="{arm * 2}" fill="{fill}" fill-opacity="{op}"/>')


def sparkle_tile_css(alpha=1.0):
    """a css url(...) for one repeating tile. alpha fades the whole thing, so the same tile can sit
    loud in the radar window and faint behind the stats."""
    a = alpha
    body = (
        _plus(12, 14, 4, "#FFFFFF", a)
        + _plus(64, 52, 3, RAINBOW[4], a * 0.8)
        + _plus(22, 62, 2, RAINBOW[5], a * 0.8)
        + f'<rect x="40" y="36" width="3" height="3" fill="{RAINBOW[2]}" fill-opacity="{a}"/>'
        + _plus(72, 26, 2, "#FFFFFF", a)
    )
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{TILE}" height="{TILE}" viewBox="0 0 {TILE} {TILE}" '
           f'shape-rendering="crispEdges">{body}</svg>')
    return 'url("data:image/svg+xml,' + urllib.parse.quote(svg) + '")'


def stripes_defs(pattern_id="mbtiStripes", band=9):
    """the pattern that fills the radar shape: hard rainbow bands leaning like the foil on the front."""
    rects = "".join(f'<rect x="{i * band}" y="0" width="{band}" height="{band * len(RAINBOW)}" fill="{c}"/>'
                    for i, c in enumerate(RAINBOW))
    size = band * len(RAINBOW)
    return (f'<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>'
            f'<pattern id="{pattern_id}" width="{size}" height="{size}" patternUnits="userSpaceOnUse" '
            f'patternTransform="rotate(45)" shape-rendering="crispEdges">{rects}</pattern></defs></svg>')
