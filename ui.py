"""
ui.py: mbti guesser
Gradio handles all layout. CSS only touches colors, fonts, and custom HTML blocks.
The pack-open reveal is a small client-side toggle defined once in HEAD_JS;
every value inside the card is rendered server-side from the real prediction.
"""

import pathlib
import gradio as gr
from app import predict_mbti
from creature import creature_svg

CSS = (pathlib.Path(__file__).parent / "styles.css").read_text()

HEAD_JS = """
<script>
function mbtiOpenPack(packId, cardId, btnId) {
  var pack = document.getElementById(packId);
  var card = document.getElementById(cardId);
  if (!pack || !card) return;
  pack.classList.add('opening');
  setTimeout(function () {
    pack.style.display = 'none';
    card.classList.add('show');
    var btn = btnId ? document.getElementById(btnId) : null;
    if (btn) btn.classList.add('show');
  }, 380);
}

// gradio only re-fits a textarea's height to its own content on typing, so
// resizing the window (which rewraps placeholder/typed text into a
// different line count at the *old* fixed height) leaves it scroll-locked
// until the next keystroke. re-measure every textarea ourselves whenever
// the layout width could have changed.
(function () {
  function mbtiFitTextareas() {
    document.querySelectorAll('.gradio-container textarea').forEach(function (t) {
      t.style.height = 'auto';
      t.style.height = t.scrollHeight + 'px';
    });
  }
  var timer = null;
  window.addEventListener('resize', function () {
    clearTimeout(timer);
    timer = setTimeout(mbtiFitTextareas, 150);
  });
  if (window.ResizeObserver) {
    new ResizeObserver(function () {
      clearTimeout(timer);
      timer = setTimeout(mbtiFitTextareas, 150);
    }).observe(document.body);
  }
})();
</script>
"""

def hero_scene_svg():
    """
    a full-viewport pixel-game landscape wallpaper: softened classic-handheld-game
    palette (dusty blue/teal/mauve mountains, sage grass, warm dirt), plus the
    app's own trait icons (star, heart) floating in the sky as a brand callback.
    fixed piece of art, not a repeating pattern. canvas is close to a viewport's
    own proportions so the "cover" crop doesn't have to zoom in hard on one corner.
    """
    W, H = 1200, 900
    grass_y, dirt_y = 560, 720

    clouds = [(120, 110, 1.4), (520, 70, 1.1), (880, 150, 1.3), (1080, 90, 1.0)]
    cloud_svg = "".join(f'''
    <g transform="translate({cx},{cy}) scale({s})">
      <rect x="0" y="10" width="58" height="16" rx="8" fill="#FFFDF9"/>
      <rect x="13" y="0" width="32" height="18" rx="8" fill="#FFFDF9"/>
      <rect x="-9" y="13" width="28" height="11" rx="6" fill="#FFFDF9"/>
    </g>''' for cx, cy, s in clouds)

    mountains = [
        (10, grass_y, 300, 230, "#7B93B8"),
        (260, grass_y, 340, 300, "#6E9B96"),
        (560, grass_y, 300, 220, "#8C6E8C"),
        (820, grass_y, 340, 310, "#7B93B8"),
        (1090, grass_y, 300, 240, "#6E9B96"),
    ]
    mtn_svg = ""
    for bx, by, w, h, color in mountains:
        peak_x, peak_y = bx + w / 2, by - h
        mtn_svg += f'<polygon points="{bx},{by} {peak_x},{peak_y} {bx+w},{by}" fill="{color}"/>'
        cap_w, cap_h = w * 0.24, h * 0.22
        mtn_svg += (f'<polygon points="{peak_x-cap_w/2:.0f},{peak_y+cap_h:.0f} '
                    f'{peak_x:.0f},{peak_y:.0f} {peak_x+cap_w/2:.0f},{peak_y+cap_h:.0f}" fill="#FFFDF9"/>')

    icon_spots = [(190, 200, "star", "#C9A876", 1.6), (990, 160, "star", "#C9A876", 1.3), (640, 90, "heart", "#D9A0A6", 1.5)]
    icon_svg = ""
    for x, y, shape, color, s in icon_spots:
        colored_icon = ICONS[shape].replace("currentColor", color)
        icon_svg += f'<g transform="translate({x},{y}) scale({s})">{colored_icon}</g>'

    flowers = [60, 170, 320, 470, 610, 760, 880, 1010, 1130]
    flower_svg = "".join(f'''
    <g transform="translate({fx},{grass_y+70})">
      <rect x="-4" y="-11" width="8" height="8" fill="#FFFDF9"/>
      <rect x="-11" y="-4" width="8" height="8" fill="#FFFDF9"/>
      <rect x="3" y="-4" width="8" height="8" fill="#FFFDF9"/>
      <rect x="-4" y="3" width="8" height="8" fill="#FFFDF9"/>
      <rect x="-2" y="-2" width="4" height="4" fill="#C9A876"/>
    </g>''' for fx in flowers)

    rocks = [(50, dirt_y+55, 18), (200, dirt_y+75, 13), (370, dirt_y+45, 16), (540, dirt_y+70, 11),
             (700, dirt_y+50, 18), (860, dirt_y+78, 13), (1000, dirt_y+48, 16), (1140, dirt_y+72, 11)]
    rock_svg = "".join(f'<ellipse cx="{rx}" cy="{ry}" rx="{rr}" ry="{rr*0.7:.0f}" fill="#5C4A38"/>' for rx, ry, rr in rocks)

    return f'''
    <svg width="100%" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" style="display:block">
      <rect x="0" y="0" width="{W}" height="{grass_y}" fill="#A3DBD8"/>
      {cloud_svg}
      {mtn_svg}
      {icon_svg}
      <rect x="0" y="{grass_y}" width="{W}" height="{dirt_y-grass_y}" fill="#8FA06E"/>
      {flower_svg}
      <rect x="0" y="{dirt_y}" width="{W}" height="{H-dirt_y}" fill="#A67C52"/>
      {rock_svg}
    </svg>
    '''


# ── type data ─────────────────────────────────────────────────────────────────
MBTI_DESCRIPTIONS = {
    "INTJ": ("the architect",    "strategic, private, always three steps ahead. probably already knows what you're going to say."),
    "INTP": ("the logician",     "lives in their head, loves a rabbit hole. argues for fun and calls it curiosity."),
    "ENTJ": ("the commander",    "natural leader, extremely sure of themselves, not always gentle about it."),
    "ENTP": ("the debater",      "argues for fun, gets bored easily, always looking for the counterpoint no one else raised."),
    "INFJ": ("the advocate",     "intense, private, somehow knows what you're thinking before you do."),
    "INFP": ("the mediator",     "idealistic, emotional, writes in their notes app at 2am. feels everything deeply."),
    "ENFJ": ("the protagonist",  "makes everyone feel seen, over-commits, and checks in on you before you ask."),
    "ENFP": ("the campaigner",   "energetic, all over the place, somehow still the most magnetic person in the room."),
    "ISTJ": ("the logistician",  "reliable to a fault, shows love through acts of service, keeps everyone else on schedule."),
    "ISFJ": ("the defender",     "takes care of everyone, forgets themselves. remembers your coffee order."),
    "ESTJ": ("the executive",    "has a spreadsheet for everything. gets things done, no vibes required."),
    "ESFJ": ("the consul",       "genuinely warm, needs approval. throws the best parties and stress-cleans before you arrive."),
    "ISTP": ("the virtuoso",     "quiet but extremely competent. not big on feelings. fix-it person energy."),
    "ISFP": ("the adventurer",   "gentle, artistic, keeps real thoughts to themselves. excellent taste, won't brag."),
    "ESTP": ("the entrepreneur", "impulsive, charismatic, thrives on chaos they created."),
    "ESFP": ("the entertainer",  "the most fun person in the room, no plans, all vibes."),
}

IDENTITY_DESCRIPTIONS = {
    "A": "confident and even-keeled, doesn't lose sleep over what they can't control.",
    "T": "self-aware with a perfectionist streak, replays things more than they'd like to admit.",
}

# spoke order matches the printed type code (E/I, N/S, T/F, J/P, then A/T) so
# the pentagon and stat rows read in the same order as "ENFP-A" above them.
# "outward" is the named trait the spoke grows toward; a low reading just
# means the opposite pole, same as the axis itself, nothing invented here.
SPOKES = [
    ("E_I", "Energy",    "E", "#8FA06E", "bolt"),
    ("N_S", "Vision",    "N", "#7B93B8", "star"),
    ("T_F", "Empathy",   "F", "#D9A0A6", "heart"),
    ("J_P", "Freedom",   "P", "#C9A876", "swirl"),
    ("A_T", "Assurance", "A", "#6E9B96", "shield"),
]

ICONS = {
    "bolt": '<polygon points="9,1 3,11 8,11 6,17 15,7 9,7" fill="currentColor"/>',
    "star": '<polygon points="9,1 11,7 17,7 12,11 14,17 9,13 4,17 6,11 1,7 7,7" fill="currentColor"/>',
    "heart": '<path d="M9,16 C2,10 3,3 8,3 C9,3 9,4 9,4 C9,4 9,3 10,3 C15,3 16,10 9,16 Z" fill="currentColor"/>',
    "swirl": '<path d="M9,2 C13,2 16,5 16,9 C16,13 13,15 10,15 C7,15 6,13 6,11 C6,9 7.5,8 9.5,8.5" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>',
    "shield": '<path d="M9,1 L16,4 V9 C16,13 13,16 9,17 C5,16 2,13 2,9 V4 Z" fill="currentColor"/>',
}

FAMILY_NAMES = {"NT": "ANALYST", "NF": "DIPLOMAT", "SJ": "SENTINEL", "SP": "EXPLORER"}

TYPE_INDEX = {code: i + 1 for i, code in enumerate(sorted(MBTI_DESCRIPTIONS.keys()))}


def _point(i, n, r, cx, cy):
    import math
    angle = math.radians(-90 + i * (360 / n))
    return cx + r * math.cos(angle), cy + r * math.sin(angle)


def _pentagon_svg(stats, size=120, show_labels=False, fill_container=False):
    """
    the shape itself is always drawn at `size` -- fixed relative to a
    cx,cy centered in that square. labels need extra room on top of that:
    the widest one ("ASSURANCE") reaches further out than `size` alone
    leaves room for, so the canvas the shape sits in is padded wider
    (mostly horizontal, since labels read left-to-right off side spokes;
    a little vertical for the top spoke's label) whenever labels are on.
    """
    cx = cy = size / 2
    r_max = size * 0.32 if show_labels else size * 0.42
    n = len(stats)
    dot_r = max(4, size * 0.028)
    canvas_w = size * 1.55 if show_labels else size
    canvas_h = size * 1.1 if show_labels else size
    ox, oy = (canvas_w - size) / 2, (canvas_h - size) / 2
    cx, cy = cx + ox, cy + oy
    rings = ""
    for frac in (1, 0.66, 0.33):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (_point(i, n, r_max * frac, cx, cy) for i in range(n)))
        rings += f'<polygon points="{pts}" fill="none" stroke="#D9CFC0" stroke-width="1"></polygon>'
    spokes = ""
    for i in range(n):
        x, y = _point(i, n, r_max, cx, cy)
        spokes += f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#D9CFC0" stroke-width="1"></line>'
    # an ambiguous axis draws at the center (no lean either way) instead of
    # its raw score -- that score is either already near-neutral (a real
    # near-tie) or was forced ambiguous because nothing eligible has been
    # answered yet, in which case plotting it for real would draw a
    # confident-looking point the axis hasn't earned.
    shape_pct = [0 if is_ambiguous else pct for _, pct, _, _, is_ambiguous in stats]
    data_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (_point(i, n, r_max * (shape_pct[i] / 100), cx, cy) for i in range(n)))
    poly = f'<polygon points="{data_pts}" fill="#4A3B5C" fill-opacity="0.18" stroke="#4A3B5C" stroke-width="2.5"></polygon>'
    dots = ""
    for i, (name, pct, color, icon, is_ambiguous) in enumerate(stats):
        dot_color = "#C7BFAE" if is_ambiguous else color
        x, y = _point(i, n, r_max * (shape_pct[i] / 100), cx, cy)
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{dot_r:.1f}" fill="{dot_color}" stroke="#4A3B5C" stroke-width="1.5"></circle>'
    labels = ""
    if show_labels:
        for i, (name, pct, color, icon, is_ambiguous) in enumerate(stats):
            x, y = _point(i, n, r_max + size * 0.14, cx, cy)
            # anchor points away from the shape (right side grows rightward,
            # left side grows leftward) so long labels like "assurance"
            # read outward instead of back over the pentagon.
            if x > cx + 2:
                anchor = "start"
            elif x < cx - 2:
                anchor = "end"
            else:
                anchor = "middle"
            labels += (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" dominant-baseline="middle" '
                       f'font-family="Silkscreen, monospace" font-size="{max(8, size*0.036):.0f}" '
                       f'font-weight="700" fill="#6B5D7D">{name.upper()}</text>')
    width_attr = "100%" if fill_container else f"{canvas_w:.0f}"
    height_attr = "auto" if fill_container else f"{canvas_h:.0f}"
    return (f'<svg width="{width_attr}" height="{height_attr}" viewBox="0 0 {canvas_w:.0f} {canvas_h:.0f}" '
            f'preserveAspectRatio="xMidYMid meet">{rings}{spokes}{poly}{dots}{labels}</svg>')


def confidence_bars_html(stats):
    """
    per-axis reading, always on screen next to the pentagon -- the shape
    alone requires cross-referencing five points against a five-sided
    outline, the bars just say the same numbers in a form you can read
    at a glance without doing that math yourself.
    """
    rows = ""
    for name, pct, color, icon, is_ambiguous in stats:
        if is_ambiguous:
            rows += f"""
    <div class="conf-row conf-row-ambiguous">
      <span class="conf-name">{name}</span>
      <div class="conf-track"><div class="conf-fill" style="width:0%"></div></div>
      <span class="conf-pct">?</span>
    </div>"""
        else:
            rows += f"""
    <div class="conf-row">
      <span class="conf-name">{name}</span>
      <div class="conf-track"><div class="conf-fill" style="width:{pct}%;background:{color}"></div></div>
      <span class="conf-pct">{pct}</span>
    </div>"""
    return f'<div class="conf-bars">{rows}</div>'


def loading_panel_html():
    """shown the instant a Next/submit click fires, before the (slow) real
    classifier call returns -- so the wait reads as "working" instead of a
    frozen page."""
    return """
    <div class="live-panel-inner">
      <div class="card-eyebrow">Live Radar</div>
      <div class="live-status loading"><span class="mbti-spinner"></span> reading their answers…</div>
    </div>
    """


def empty_progress_html():
    """starting state, before step 1 has been submitted: nothing to read yet."""
    stats = [(name, 0, color, icon, True) for _, name, _, color, icon in SPOKES]
    pentagon = _pentagon_svg(stats, size=340, show_labels=True, fill_container=True)
    return f"""
    <div class="live-panel-inner">
      <div class="card-eyebrow">Live Radar</div>
      <div class="live-status">answer step 1 to start their read</div>
      <div class="progress-pentagon-wrap">{pentagon}</div>
      {confidence_bars_html(stats)}
    </div>
    """


def step_indicator_html(current, total):
    pct = round(current / total * 100)
    return f"""
    <div class="step-indicator">
      <span>STEP {current} OF {total}</span>
      <div class="step-bar-track"><div class="step-bar-fill" style="width:{pct}%"></div></div>
    </div>
    """


def _extract_stats(axis_results):
    stats = []
    for axis_key, name, outward, color, icon in SPOKES:
        r = axis_results.get(axis_key, {})
        pct = round(r.get("scores", {}).get(outward, 50))
        stats.append((name, pct, color, icon, bool(r.get("is_ambiguous"))))
    return stats


def ai_read_html(text, axis_results):
    """
    proof-of-work, not just a progress bar: the literal blob just sent to
    the zero-shot classifier, plus its single most confident non-ambiguous
    read so far. nothing here is a lookup table -- it's the actual model
    output for the actual text, updating step to step.
    """
    if not text or not axis_results:
        return ""

    snippet = text.strip()
    if len(snippet) > 140:
        snippet = snippet[:140].rsplit(" ", 1)[0] + "…"

    confident = {k: r for k, r in axis_results.items() if not r.get("is_ambiguous")}
    if confident:
        axis_key, r = max(confident.items(), key=lambda kv: kv[1]["confidence"])
        axis_name = next((name for k, name, *_ in SPOKES if k == axis_key), axis_key)
        read_line = f'model reads this as <b>{r["winner"]}</b>-leaning on {axis_name} ({round(r["confidence"])}% confident)'
    else:
        read_line = "still gathering signal, nothing decisive yet"

    return f"""
    <div class="ai-read">
      <div class="ai-read-label">What The Model Is Reading</div>
      <div class="ai-read-snippet">&ldquo;{snippet}&rdquo;</div>
      <div class="ai-read-line">{read_line}</div>
    </div>
    """


def live_pentagon_html(axis_results, text=""):
    """
    real partial read: whatever's been answered through this step, classified
    for real against all 5 axes (the shared-blob design means even one field
    already moves every axis, not just "its own"). refines each step, no
    fabricated numbers at any point.
    """
    stats = _extract_stats(axis_results)
    pentagon = _pentagon_svg(stats, size=340, show_labels=True, fill_container=True)
    return f"""
    <div class="live-panel-inner">
      <div class="card-eyebrow">Live Radar</div>
      <div class="live-status">reading their answers so far</div>
      <div class="progress-pentagon-wrap">{pentagon}</div>
      {confidence_bars_html(stats)}
      {ai_read_html(text, axis_results)}
    </div>
    """


def run_partial(spotify_artists, humor_types, punctuality, group_archetypes,
                 what_they_talk_about="", weekend_activities="", stress_triggers="", party_vibe="",
                 fav_media="", awkward_text=None, text_length_slider=None, texting_style=None,
                 followers=None, social_media_checkboxes=None, spam_friends_count=None,
                 text_length_touched=False):
    try:
        mbti_type, axis_results, text = predict_mbti(
            spotify_artists         = spotify_artists or "",
            humor_types             = humor_types or [],
            punctuality             = punctuality,
            group_archetypes        = group_archetypes or [],
            what_they_talk_about    = what_they_talk_about or "",
            weekend_activities      = weekend_activities or "",
            text_length_slider      = int(text_length_slider) if text_length_slider else None,
            texting_style           = texting_style or [],
            stress_triggers         = stress_triggers or "",
            party_vibe              = party_vibe or "",
            fav_media               = fav_media or "",
            followers               = followers,
            social_media_checkboxes = social_media_checkboxes or [],
            spam_friends_count      = spam_friends_count,
            awkward_text            = awkward_text,
            photo_results           = None,
            text_length_touched     = text_length_touched,
        )
    except Exception as e:
        print(f"partial prediction error: {e}")
        return empty_progress_html()

    if axis_results is None:
        return empty_progress_html()

    return live_pentagon_html(axis_results, text)


def build_reveal_html(mbti_type, axis_results):
    core, suffix = mbti_type.split("-")
    core_display = core.replace("?", "X")  # keep svg/lookups safe if an axis was ambiguous
    title, desc = MBTI_DESCRIPTIONS.get(core_display, ("an unusual mix", "not enough signal to place them cleanly, that's a real result too."))
    identity_desc = IDENTITY_DESCRIPTIONS.get(suffix, "signal was too close to call.")

    e_i = core_display[0] if len(core_display) > 0 else "E"
    n_s = core_display[1] if len(core_display) > 1 else "N"
    t_f = core_display[2] if len(core_display) > 2 else "F"
    j_p = core_display[3] if len(core_display) > 3 else "J"

    family_key = ("N" if n_s == "N" else "S") + (t_f if n_s == "N" else j_p)
    family_name, family_color = FAMILY_NAMES.get(family_key, "UNPLACED"), {
        "NT": "#7B93B8", "NF": "#8FA06E", "SJ": "#6E9B96", "SP": "#C9A876"
    }.get(family_key, "#8C6E8C")

    stats = _extract_stats(axis_results)
    pentagon = _pentagon_svg(stats, size=250, show_labels=True, fill_container=True)

    # the pentagon spoke always grows toward "outward" so the shape stays
    # readable, but the row below it should name the actual winner (or "?" if
    # the axis never cleared the ambiguity threshold) with THAT letter's own
    # confidence -- not "outward" and its score regardless of who actually won.
    stat_rows = ""
    for axis_key, name, outward, color, icon in SPOKES:
        r = axis_results.get(axis_key, {})
        letter = "?" if r.get("is_ambiguous") else r.get("winner", outward)
        num = round(r.get("confidence", 50))
        stat_rows += f'''
    <div class="stat-row">
      <svg class="stat-icon" viewBox="0 0 18 18" style="color:{color}">{ICONS[icon]}</svg>
      <span class="stat-name">{name} <span class="stat-letter">({letter})</span></span>
      <span class="stat-num">{num}</span>
    </div>'''

    avg_spread = sum(abs(p - 50) for _, p, _, _, _ in stats) / len(stats)
    if avg_spread > 30:
        rarity, rarity_color = "RARE", "#D9A0A6"
    elif avg_spread > 15:
        rarity, rarity_color = "UNCOMMON", "#8FA06E"
    else:
        rarity, rarity_color = "MIXED SIGNAL", "#C9A876"

    creature = creature_svg(e_i, n_s, t_f, j_p, suffix, size=40)
    index = TYPE_INDEX.get(core_display, 0)

    return f"""
<div class="reveal-wrap">
  <div class="pack-stage">
    <div class="pack" id="pack1" onclick="mbtiOpenPack('pack1','card1','again1')">
      <div class="pack-emblem-ring">
        <svg width="40" height="40" viewBox="0 0 40 40">
          <polygon points="20,4 24,15 36,15 26,22 30,34 20,26 10,34 14,22 4,15 16,15"
                    fill="#C9A876" stroke="#4A3B5C" stroke-width="2" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="pack-banner"><span>TYPE PACK</span></div>
      <div class="pack-tap">&#9656; TAP TO OPEN</div>
    </div>

    <div class="tcg-card" id="card1">
      <div class="tcg-inner">
        <div class="tcg-top">
          <div class="family-badge">
            <div class="family-swatch" style="background:{family_color}"></div>
            <span class="family-label">{family_name}</span>
          </div>
          <span class="card-index">&#8470; {index:02d}</span>
        </div>

        <div class="name-row">
          <div class="name-row-text">
            <span class="card-code">{core_display}-{suffix}</span>
            <span class="card-title">{title}</span>
          </div>
          <div class="card-avatar">{creature}</div>
        </div>

        <div class="art-panel">{pentagon}</div>

        <div class="stage-banner"><span>{family_name} TYPE</span></div>

        <div class="stat-rows">{stat_rows}</div>

        <div class="rarity-tag" style="background:{rarity_color}">{rarity}</div>

        <div class="flavor-bar">{desc}</div>
        <div class="identity-bar"><b>{suffix}-identity:</b> {identity_desc}</div>
      </div>
    </div>
  </div>
  <button class="again-btn" id="again1" onclick="document.getElementById('card1').classList.remove('show'); document.getElementById('pack1').style.display='flex'; document.getElementById('pack1').classList.remove('opening'); this.classList.remove('show');">OPEN ANOTHER PACK</button>
</div>
"""


def run_prediction(
    spotify_artists, humor_types, punctuality, group_archetypes,
    what_they_talk_about, weekend_activities, stress_triggers, party_vibe, fav_media, awkward_text,
    text_length_slider, texting_style, followers, social_media_checkboxes, spam_friends_count,
    text_length_touched, photo,
):
    # generator: the photo analysis + classifier call below can take a
    # while, so the button flips to a disabled loading label the instant
    # it's clicked instead of just sitting there looking unresponsive.
    yield gr.update(), gr.update(), gr.update(), gr.update(value="Reading their type…", interactive=False)

    photo_results = None
    if photo is not None:
        try:
            from photo_analysis import analyze_photo
            photo_results = analyze_photo(photo)
        except Exception as e:
            print(f"photo analysis error: {e}")

    reset_btn = gr.update(value="open their type pack ↗", interactive=True)

    try:
        mbti_type, axis_results, _text = predict_mbti(
            spotify_artists         = spotify_artists or "",
            humor_types             = humor_types or [],
            punctuality             = punctuality,
            group_archetypes        = group_archetypes or [],
            what_they_talk_about    = what_they_talk_about or "",
            weekend_activities      = weekend_activities or "",
            text_length_slider      = int(text_length_slider) if text_length_slider else 3,
            texting_style           = texting_style or [],
            stress_triggers         = stress_triggers or "",
            party_vibe              = party_vibe or "",
            fav_media               = fav_media or "",
            followers               = followers,
            social_media_checkboxes = social_media_checkboxes or [],
            spam_friends_count      = spam_friends_count,
            awkward_text            = awkward_text,
            photo_results           = photo_results,
            text_length_touched     = text_length_touched,
        )
    except Exception as e:
        print(f"prediction error: {e}")
        yield (
            '<div class="result-empty">having trouble right now, give it a moment and try again.</div>',
            gr.update(visible=True), gr.update(visible=False), reset_btn,
        )
        return

    if axis_results is None:
        yield (
            '<div class="result-empty">fill in at least a few fields to get a read.</div>',
            gr.update(visible=True), gr.update(visible=False), reset_btn,
        )
        return
    yield build_reveal_html(mbti_type, axis_results), gr.update(visible=False), gr.update(visible=True), reset_btn


# ── theme ─────────────────────────────────────────────────────────────────────
theme = gr.themes.Soft(
    primary_hue=gr.themes.Color(
        c50="#F7F3EA", c100="#EDE6D3", c200="#DED0AE", c300="#CBB989",
        c400="#B69C6E", c500="#C9A876", c600="#9C8460", c700="#7C6A4E",
        c800="#5C4E3B", c900="#4A3B5C", c950="#2E2440",
    ),
    secondary_hue="emerald",
    neutral_hue="stone",
    font=gr.themes.GoogleFont("Rubik"),
    font_mono=gr.themes.GoogleFont("Silkscreen"),
).set(
    # every color below also sets its _dark twin to the same value: this
    # theme is a fixed cream/plum look, not one that should reflow when the
    # os is in dark mode, so nothing here is allowed to diverge between the
    # two.
    body_background_fill="#FFFDF9",
    body_background_fill_dark="#FFFDF9",
    block_background_fill="#EDE6D3",
    block_background_fill_dark="#EDE6D3",
    block_border_color="#4A3B5C",
    block_border_color_dark="#4A3B5C",
    block_border_width="2px",
    block_radius="8px",
    block_shadow="none",
    block_label_text_size="sm",
    block_label_text_weight="600",
    block_label_text_color="#362B47",
    block_label_text_color_dark="#362B47",
    block_label_background_fill="transparent",
    block_label_background_fill_dark="transparent",
    block_label_border_width="0px",
    block_label_padding="0px",
    block_label_margin="0px",
    block_label_radius="0px",
    block_label_shadow="none",
    block_title_text_color="#362B47",
    block_title_text_color_dark="#362B47",
    block_title_background_fill="transparent",
    block_title_background_fill_dark="transparent",
    input_background_fill="#FFFFFF",
    input_background_fill_dark="#FFFFFF",
    input_border_color="#4A3B5C",
    input_border_color_dark="#4A3B5C",
    input_border_color_focus="#8FA06E",
    input_border_color_focus_dark="#8FA06E",
    input_shadow="none",
    input_shadow_focus="0 0 0 3px rgba(143,160,110,0.25)",
    input_radius="4px",
    checkbox_background_color="#FFFFFF",
    checkbox_background_color_dark="#FFFFFF",
    checkbox_border_color="#4A3B5C",
    checkbox_border_color_dark="#4A3B5C",
    checkbox_border_color_selected="#4A3B5C",
    checkbox_border_color_selected_dark="#4A3B5C",
    checkbox_background_color_selected="#8FA06E",
    checkbox_background_color_selected_dark="#8FA06E",
    checkbox_label_background_fill="#FFFFFF",
    checkbox_label_background_fill_dark="#FFFFFF",
    checkbox_label_background_fill_hover="#F7F3EA",
    checkbox_label_background_fill_hover_dark="#F7F3EA",
    checkbox_label_background_fill_selected="#8FA06E",
    checkbox_label_background_fill_selected_dark="#8FA06E",
    checkbox_label_border_color="#4A3B5C",
    checkbox_label_border_color_dark="#4A3B5C",
    checkbox_label_border_color_hover="#4A3B5C",
    checkbox_label_border_color_hover_dark="#4A3B5C",
    checkbox_label_border_color_selected="#4A3B5C",
    checkbox_label_border_color_selected_dark="#4A3B5C",
    checkbox_label_text_color="#6B5D7D",
    checkbox_label_text_color_dark="#6B5D7D",
    checkbox_label_text_color_selected="#FFFFFF",
    checkbox_label_text_color_selected_dark="#FFFFFF",
    button_primary_background_fill="#4A3B5C",
    button_primary_background_fill_dark="#4A3B5C",
    button_primary_background_fill_hover="#8FA06E",
    button_primary_background_fill_hover_dark="#8FA06E",
    button_primary_text_color="#EDE6D3",
    button_primary_text_color_dark="#EDE6D3",
    button_primary_border_color="transparent",
    button_primary_border_color_dark="transparent",
    button_large_radius="6px",
    button_large_padding="14px 32px",
    slider_color="#8FA06E",
    slider_color_dark="#8FA06E",
    border_color_primary="#4A3B5C",
    border_color_primary_dark="#4A3B5C",
    color_accent="#8FA06E",
    color_accent_soft="#F7F3EA",
    color_accent_soft_dark="#F7F3EA",
    link_text_color="#8FA06E",
    link_text_color_dark="#8FA06E",
    body_text_color="#362B47",
    body_text_color_dark="#362B47",
    body_text_color_subdued="#6B5D7D",
    body_text_color_subdued_dark="#6B5D7D",
)


# ── wizard step handlers ────────────────────────────────────────────────────
TOTAL_STEPS = 4


def _step1_valid(humor_types, punctuality, group_archetypes):
    ok = bool(humor_types) and bool(punctuality) and bool(group_archetypes)
    return gr.update(interactive=ok)


def _is_substantial(text, min_chars=8):
    """
    catches the "typed a single letter to get past a required field" case --
    not a judgment of quality, just a floor: too short, or too little
    actual variety in the characters (a repeated key mashed a few times),
    isn't enough for the model to read anything real off of.
    """
    if not text:
        return False
    stripped = text.strip()
    if len(stripped) < min_chars:
        return False
    if len(set(stripped.lower().replace(" ", ""))) <= 2:
        return False
    return True


def _field_hint_html(text):
    if text and text.strip() and not _is_substantial(text):
        return '<div class="field-hint">add a bit more detail, the model needs something real to read</div>'
    return ""


def _step2_valid(what_they_talk_about, weekend_activities, awkward_text):
    ok = _is_substantial(what_they_talk_about) and _is_substantial(weekend_activities) and bool(awkward_text)
    return gr.update(interactive=ok)


def _step3_valid(texting_style, social_media_checkboxes):
    ok = bool(texting_style) and bool(social_media_checkboxes)
    return gr.update(interactive=ok)


def next1_handler(spotify_artists, humor_types, punctuality, group_archetypes):
    # a generator so the loading state reaches the page immediately, before
    # the (slow) classifier call below even starts -- the real result
    # replaces it in a second yield once run_partial returns.
    yield loading_panel_html(), gr.update(), gr.update(), gr.update(), gr.update(value="Loading…", interactive=False)
    panel = run_partial(spotify_artists, humor_types, punctuality, group_archetypes)
    yield panel, gr.update(visible=False), gr.update(visible=True), step_indicator_html(2, TOTAL_STEPS), gr.update(value="Next →", interactive=True)


def next2_handler(spotify_artists, humor_types, punctuality, group_archetypes,
                   what_they_talk_about, weekend_activities, stress_triggers, party_vibe, fav_media, awkward_text):
    yield loading_panel_html(), gr.update(), gr.update(), gr.update(), gr.update(value="Loading…", interactive=False)
    panel = run_partial(spotify_artists, humor_types, punctuality, group_archetypes,
                         what_they_talk_about, weekend_activities, stress_triggers, party_vibe, fav_media, awkward_text)
    yield panel, gr.update(visible=False), gr.update(visible=True), step_indicator_html(3, TOTAL_STEPS), gr.update(value="Next →", interactive=True)


def next3_handler(spotify_artists, humor_types, punctuality, group_archetypes,
                   what_they_talk_about, weekend_activities, stress_triggers, party_vibe, fav_media, awkward_text,
                   text_length_slider, texting_style, followers, social_media_checkboxes, spam_friends_count,
                   text_length_touched):
    yield loading_panel_html(), gr.update(), gr.update(), gr.update(), gr.update(value="Loading…", interactive=False)
    panel = run_partial(spotify_artists, humor_types, punctuality, group_archetypes,
                         what_they_talk_about, weekend_activities, stress_triggers, party_vibe, fav_media, awkward_text,
                         text_length_slider, texting_style, followers, social_media_checkboxes, spam_friends_count,
                         text_length_touched)
    yield panel, gr.update(visible=False), gr.update(visible=True), step_indicator_html(4, TOTAL_STEPS), gr.update(value="Next →", interactive=True)


# ── layout ────────────────────────────────────────────────────────────────────
with gr.Blocks(title="mbti guesser", css=CSS, theme=theme, head=HEAD_JS) as demo:

    gr.HTML(f"""
    <div class="hero-scene">{hero_scene_svg()}</div>
    <div class="mbti-hero">
      <span class="hero-eyebrow">mbti guesser</span>
      <h1 class="hero-title">type radar</h1>
    </div>
    """)

    with gr.Column(elem_classes=["main-content"]) as form_page:
        with gr.Row(elem_classes=["console"]):

            with gr.Column(elem_classes=["form-col"]):
                step_indicator = gr.HTML(step_indicator_html(1, TOTAL_STEPS), elem_classes=["step-indicator-wrap"])

                with gr.Column(visible=True) as step1:
                    with gr.Group(elem_classes=["mbti-card"]):
                        gr.HTML('<span class="section-label">the basics</span>')
                        spotify_artists = gr.Textbox(
                            label="spotify top artists (optional)",
                            placeholder="olivia rodrigo, daniel caesar, le sserafim, clairo…",
                        )
                        humor_types = gr.CheckboxGroup(
                            label="their humor (required)",
                            choices=["dry", "unhinged", "wholesome", "dark", "sarcastic", "self-deprecating"],
                        )
                        punctuality = gr.Radio(
                            label="early, on time, or late? (required)",
                            choices=["always early", "usually early", "on time", "usually late", "always late"],
                        )
                        group_archetypes = gr.CheckboxGroup(
                            label="their role in the friend group (required)",
                            choices=[
                                "the mom", "the one who does it for the plot",
                                "the navigator", "the therapist friend",
                                "the flake", "the nonchalant one", "the instigator",
                                "the yapper", "the listener",
                            ],            )
                    next1_btn = gr.Button("Next →", variant="primary", size="lg", interactive=False)
                    for _comp in (humor_types, punctuality, group_archetypes):
                        _comp.change(
                            fn=_step1_valid,
                            inputs=[humor_types, punctuality, group_archetypes],
                            outputs=next1_btn,
                        )

                with gr.Column(visible=False) as step2:
                    with gr.Group(elem_classes=["mbti-card"]):
                        gr.HTML('<span class="section-label">what they\'re like</span>')
                        what_they_talk_about = gr.Textbox(
                            label="what do they talk about most? (required)",
                            placeholder="the nba finals, their love life, conspiracy theories…",
                            lines=2,
                        )
                        what_they_talk_about_hint = gr.HTML("", elem_classes=["field-hint-wrap"])
                        weekend_activities = gr.Textbox(
                            label="how do they spend their weekends? (required)",
                            placeholder="hiking alone, cafe hopping, sleeping until noon…",
                            lines=2,
                        )
                        weekend_activities_hint = gr.HTML("", elem_classes=["field-hint-wrap"])
                        stress_triggers = gr.Textbox(
                            label="what stresses them out? (optional)",
                            placeholder="last-minute changes, overstimulating noises, falling behind…",
                            lines=2,
                        )
                        party_vibe = gr.Textbox(
                            label="vibe at parties / what kind of drunk are they? (optional)",
                            placeholder="talks to one person all night, or works the whole room…",
                            lines=2,
                        )
                        fav_media = gr.Textbox(
                            label="favorite shows, movies, or books (optional)",
                            placeholder="la la land, attack on titan, hunger games…",
                            lines=2,
                        )
                        awkward_text = gr.Radio(
                            label="they sent a slightly awkward text an hour ago. they... (required)",
                            choices=["already forgot about it", "still replaying it in their head"],
                        )
                    with gr.Row():
                        back2_btn = gr.Button("← Back", variant="secondary")
                        next2_btn = gr.Button("Next →", variant="primary", interactive=False)
                    step2_gate_fields = [what_they_talk_about, weekend_activities, awkward_text]
                    for _comp in (what_they_talk_about, weekend_activities, awkward_text):
                        _comp.change(fn=_step2_valid, inputs=step2_gate_fields, outputs=next2_btn)
                    what_they_talk_about.change(fn=_field_hint_html, inputs=what_they_talk_about, outputs=what_they_talk_about_hint)
                    weekend_activities.change(fn=_field_hint_html, inputs=weekend_activities, outputs=weekend_activities_hint)

                with gr.Column(visible=False) as step3:
                    with gr.Group(elem_classes=["mbti-card"]):
                        gr.HTML('<span class="section-label">digital habits</span>')
                        text_length_slider = gr.Slider(
                            minimum=1, maximum=5, step=1, value=3,
                            label="how long are their texts? (optional)",
                            info="1 = one-word replies   ||   5 = full essays",
                        )
                        # a slider can't render "blank" the way a text box can --
                        # it always reports *some* number -- so whether the
                        # default was ever actually chosen has to be tracked
                        # separately instead of trusting the value alone.
                        text_length_touched = gr.State(False)
                        text_length_slider.input(fn=lambda: True, outputs=text_length_touched)
                        texting_style = gr.CheckboxGroup(
                            label="texting style (required)",
                            choices=["quick replies", "slow replies", "emoji heavy", "no emojis",
                                        "all lowercase", "uses punctuation", "leaves people on read"],
                        )
                        # gr.Number renders a blank/None value as a literal "0" in
                        # this gradio version -- indistinguishable from someone
                        # actually answering "0" -- so this uses a plain textbox
                        # (genuinely empty by default) instead.
                        followers = gr.Textbox(label="follower count (optional)", placeholder="e.g. 340 -- leave blank if unsure", info="main account")
                        social_media_checkboxes = gr.CheckboxGroup(
                            label="social media behavior (required)",
                            choices=["posts a lot", "mostly a lurker", "stories person",
                                        "feed poster", "has a spam/close friends account",
                                        "no social media", "not sure / don't know"],
                        )
                        spam_friends_count = gr.Textbox(
                            label="close friends / spam list size (optional)",
                            placeholder="e.g. 25", visible=False,
                            info="under 10 = very private || 110+ = basically a second public account",
                        )

                        def _social_media_visibility(checkboxes):
                            # a real number here is only meaningful once "no social
                            # media" / "not sure" are ruled out -- otherwise it's
                            # either contradictory or a guess dressed up as data.
                            checkboxes = checkboxes or []
                            has_no_signal = "no social media" in checkboxes or "not sure / don't know" in checkboxes
                            return (
                                gr.update(visible=not has_no_signal),
                                gr.update(visible=(not has_no_signal) and "has a spam/close friends account" in checkboxes),
                            )

                        social_media_checkboxes.change(
                            fn=_social_media_visibility,
                            inputs=social_media_checkboxes,
                            outputs=[followers, spam_friends_count],
                        )
                    with gr.Row():
                        back3_btn = gr.Button("← Back", variant="secondary")
                        next3_btn = gr.Button("Next →", variant="primary", interactive=False)
                    for _comp in (texting_style, social_media_checkboxes):
                        _comp.change(
                            fn=_step3_valid,
                            inputs=[texting_style, social_media_checkboxes],
                            outputs=next3_btn,
                        )

                with gr.Column(visible=False) as step4:
                    with gr.Group(elem_classes=["mbti-card"]):
                        gr.HTML('<span class="section-label">photo <span style="font-size:10px;color:#9296AC;letter-spacing:0.1em">optional</span></span>')
                        photo = gr.Image(
                            label="drop a photo of them",
                            type="filepath",
                            sources=["upload", "clipboard"],
                            elem_classes=["photo-upload-wrap"],
                        )
                        gr.HTML('<p class="photo-note">expression, solo vs. group, eye contact, background context all analyzed locally.</p>')
                    with gr.Row():
                        back4_btn = gr.Button("← Back", variant="secondary")
                        submit_btn = gr.Button("open their type pack ↗", variant="primary", size="lg")

            with gr.Column(elem_classes=["live-col"]):
                with gr.Group(elem_classes=["mbti-card"]):
                    progress_panel = gr.HTML(empty_progress_html())

    with gr.Column(elem_classes=["main-content", "reveal-page-inner"], visible=False) as reveal_page:
        output = gr.HTML("")
        with gr.Row(elem_classes=["again-row"]):
            again_btn = gr.Button("↺ retake the quiz", size="sm")

    gr.HTML('<div class="mbti-footer">predictions use facebook/bart-large-mnli || axes marked "?" had insufficient signal</div>')

    step1_fields = [spotify_artists, humor_types, punctuality, group_archetypes]
    step2_fields = step1_fields + [what_they_talk_about, weekend_activities, stress_triggers, party_vibe, fav_media, awkward_text]
    step3_fields = step2_fields + [text_length_slider, texting_style, followers, social_media_checkboxes, spam_friends_count, text_length_touched]

    next1_btn.click(fn=next1_handler, inputs=step1_fields, outputs=[progress_panel, step1, step2, step_indicator, next1_btn], show_progress="hidden")
    next2_btn.click(fn=next2_handler, inputs=step2_fields, outputs=[progress_panel, step2, step3, step_indicator, next2_btn], show_progress="hidden")
    next3_btn.click(fn=next3_handler, inputs=step3_fields, outputs=[progress_panel, step3, step4, step_indicator, next3_btn], show_progress="hidden")

    back2_btn.click(fn=lambda: (gr.update(visible=True), gr.update(visible=False), step_indicator_html(1, TOTAL_STEPS)), outputs=[step1, step2, step_indicator])
    back3_btn.click(fn=lambda: (gr.update(visible=True), gr.update(visible=False), step_indicator_html(2, TOTAL_STEPS)), outputs=[step2, step3, step_indicator])
    back4_btn.click(fn=lambda: (gr.update(visible=True), gr.update(visible=False), step_indicator_html(3, TOTAL_STEPS)), outputs=[step3, step4, step_indicator])

    submit_inputs = step3_fields + [photo]
    submit_btn.click(fn=run_prediction, inputs=submit_inputs, outputs=[output, form_page, reveal_page, submit_btn], show_progress="hidden")

    def again_reset_pages():
        return gr.update(visible=True), gr.update(visible=False)  # form_page, reveal_page

    def again_reset_late_steps():
        return gr.update(visible=False), gr.update(visible=False)  # step3, step4

    def again_reset_early_steps():
        return gr.update(visible=True), gr.update(visible=False)  # step1, step2

    def again_reset_panels():
        return (
            step_indicator_html(1, TOTAL_STEPS),
            empty_progress_html(),
            gr.update(interactive=False), gr.update(interactive=False), gr.update(interactive=False),  # next1/2/3 btns
        )

    def again_reset_step1_fields():
        # step2-4's own field values are left as-is: writing into a field that
        # lives inside an already-hidden sibling column, in the same batch as
        # other sibling-column visibility changes, triggers a Gradio render
        # glitch that leaves an empty ghost card in the layout. Answering
        # those steps again on the next pass through the wizard overwrites
        # them naturally, so nothing stale ever reaches a real prediction.
        return "", [], None, []

    # Gradio's Column-visibility diffing only stays clean up to 2 sibling
    # columns changing per event (matching how Next/Back already only ever
    # flip 2 siblings each) -- so the 4-sibling step1..4 reset is split into
    # two lockstep-safe stages instead of one batch.
    again_btn.click(
        fn=again_reset_pages, outputs=[form_page, reveal_page],
    ).then(
        fn=again_reset_late_steps, outputs=[step3, step4],
    ).then(
        fn=again_reset_early_steps, outputs=[step1, step2],
    ).then(
        fn=again_reset_panels, outputs=[step_indicator, progress_panel, next1_btn, next2_btn, next3_btn],
    ).then(
        fn=again_reset_step1_fields,
        outputs=[spotify_artists, humor_types, punctuality, group_archetypes],
    )

if __name__ == "__main__":
    demo.launch(share=False, favicon_path="favicon.svg")
