"""
creature.py

generates an original, procedural pixel-style creature per type instead of
16 hand-drawn sprites. each of the 5 traits swaps in one visual part, so the
creature's look is literally derived from the personality read, not decoration.
no real Pokemon designs, names, or assets are used anywhere here.
"""

PLUM = "#4A3B5C"
CREAM = "#EDE6D3"
BLUSH = "#D9A0A6"
GOLD = "#C9A876"
SKY = "#C6E2F5"

FAMILIES = {
    ("N", "T"): ("ANALYST", "#7B93B8"),
    ("N", "F"): ("DIPLOMAT", "#8FA06E"),
    ("S", "J"): ("SENTINEL", "#6E9B96"),
    ("S", "P"): ("EXPLORER", "#C9A876"),
}


def get_family(ns_letter, tf_letter, jp_letter):
    if ns_letter == "N":
        return FAMILIES[("N", "T" if tf_letter == "T" else "F")]
    return FAMILIES[("S", "J" if jp_letter == "J" else "P")]


def _ears(letter, body_color):
    if letter == "E":
        return f'''
        <polygon points="34,44 26,18 46,38" fill="{body_color}" stroke="{PLUM}" stroke-width="3" stroke-linejoin="round"/>
        <polygon points="86,44 94,18 74,38" fill="{body_color}" stroke="{PLUM}" stroke-width="3" stroke-linejoin="round"/>
        '''
    return f'''
    <circle cx="34" cy="38" r="11" fill="{body_color}" stroke="{PLUM}" stroke-width="3"/>
    <circle cx="86" cy="38" r="11" fill="{body_color}" stroke="{PLUM}" stroke-width="3"/>
    '''


def _eyes(letter):
    if letter == "N":
        return f'''
        <ellipse cx="48" cy="66" rx="8" ry="10" fill="#fff" stroke="{PLUM}" stroke-width="2"/>
        <ellipse cx="72" cy="66" rx="8" ry="10" fill="#fff" stroke="{PLUM}" stroke-width="2"/>
        <circle cx="49" cy="69" r="4" fill="{PLUM}"/>
        <circle cx="73" cy="69" r="4" fill="{PLUM}"/>
        <circle cx="46.5" cy="64.5" r="1.6" fill="#fff"/>
        <circle cx="70.5" cy="64.5" r="1.6" fill="#fff"/>
        <polygon points="86,52 88,57 93,58 88,59 86,64 84,59 79,58 84,57" fill="#fff"/>
        '''
    return f'''
    <circle cx="48" cy="68" r="5.5" fill="{PLUM}"/>
    <circle cx="72" cy="68" r="5.5" fill="{PLUM}"/>
    '''


def _marking(letter):
    if letter == "F":
        return f'''
        <path d="M60,92 C50,84 52,74 59,74 C60,74 60,75.5 60,75.5 C60,75.5 60,74 61,74 C68,74 70,84 60,92 Z" fill="{BLUSH}" stroke="{PLUM}" stroke-width="1.5"/>
        '''
    return f'''
    <rect x="52" y="76" width="16" height="16" fill="{CREAM}" stroke="{PLUM}" stroke-width="1.5" transform="rotate(45 60 84)"/>
    '''


def _tail(letter, body_color):
    if letter == "J":
        return f'''
        <path d="M96,86 C106,86 108,76 100,72 C106,74 110,82 102,90 C98,94 94,92 96,86 Z" fill="{body_color}" stroke="{PLUM}" stroke-width="3" stroke-linejoin="round"/>
        '''
    return f'''
    <path d="M96,90 L110,80 L102,76 L114,68 L104,66 L112,56" fill="none" stroke="{body_color}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>
    <path d="M96,90 L110,80 L102,76 L114,68 L104,66 L112,56" fill="none" stroke="{PLUM}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" opacity="0" />
    '''


def _accessory(letter):
    if letter == "A":
        return f'''
        <polygon points="60,4 63,12 71,12 64.5,17 67,25 60,20 53,25 55.5,17 49,12 57,12"
                  fill="{GOLD}" stroke="{PLUM}" stroke-width="2" stroke-linejoin="round"/>
        '''
    return f'''
    <path d="M92,30 C96,36 96,42 92,45 C88,42 88,36 92,30 Z" fill="{SKY}" stroke="{PLUM}" stroke-width="2"/>
    '''


def creature_svg(e_i, n_s, t_f, j_p, a_t, size=140):
    """
    builds an SVG creature from the 5 trait letters. every part is chosen by
    a real letter from the read, nothing here is random or decorative-only.
    """
    _, body_color = get_family(n_s, t_f, j_p)

    parts = [
        f'<svg width="{size}" height="{size}" viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg">',
        _tail(j_p, body_color),
        f'<ellipse cx="60" cy="70" rx="40" ry="36" fill="{body_color}" stroke="{PLUM}" stroke-width="3.5"/>',
        _ears(e_i, body_color),
        _eyes(n_s),
        _marking(t_f),
        _accessory(a_t),
        "</svg>",
    ]
    return "".join(parts)
