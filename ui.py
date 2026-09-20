"""
ui.py: mbti guesser
Gradio handles all layout. CSS only touches colors, fonts, and custom HTML blocks.
The pack-open reveal is a small client-side toggle defined once in HEAD_JS;
every value inside the card is rendered server-side from the real prediction.
"""

import pathlib
import gradio as gr
from app import predict_mbti
from creature import creature_svg, get_family

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
</script>
"""

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

# fixed spoke order for the pentagon + stat rows. "outward" is the named trait
# the spoke grows toward; a low reading just means the opposite pole, same as
# the axis itself, nothing invented here.
SPOKES = [
    ("E_I", "Energy",   "E", "#8FA06E", "bolt"),
    ("T_F", "Empathy",  "F", "#D9A0A6", "heart"),
    ("J_P", "Freedom",  "P", "#C9A876", "swirl"),
    ("N_S", "Vision",   "N", "#7B93B8", "star"),
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

AXIS_ORDER = ["E_I", "N_S", "T_F", "J_P", "A_T"]


def _point(i, n, r, cx, cy):
    import math
    angle = math.radians(-90 + i * (360 / n))
    return cx + r * math.cos(angle), cy + r * math.sin(angle)


def _pentagon_svg(stats, size=120, show_labels=False):
    cx = cy = size / 2
    r_max = size * 0.32 if show_labels else size * 0.42
    n = len(stats)
    dot_r = max(4, size * 0.028)
    rings = ""
    for frac in (1, 0.66, 0.33):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (_point(i, n, r_max * frac, cx, cy) for i in range(n)))
        rings += f'<polygon points="{pts}" fill="none" stroke="#D9CFC0" stroke-width="1"></polygon>'
    spokes = ""
    for i in range(n):
        x, y = _point(i, n, r_max, cx, cy)
        spokes += f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="#D9CFC0" stroke-width="1"></line>'
    data_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (_point(i, n, r_max * (stats[i][1] / 100), cx, cy) for i in range(n)))
    poly = f'<polygon points="{data_pts}" fill="#4A3B5C" fill-opacity="0.18" stroke="#4A3B5C" stroke-width="2.5"></polygon>'
    dots = ""
    for i, (name, pct, color, icon) in enumerate(stats):
        x, y = _point(i, n, r_max * (pct / 100), cx, cy)
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{dot_r:.1f}" fill="{color}" stroke="#4A3B5C" stroke-width="1.5"></circle>'
    labels = ""
    if show_labels:
        for i, (name, pct, color, icon) in enumerate(stats):
            x, y = _point(i, n, r_max + size * 0.14, cx, cy)
            if x > cx + 2:
                anchor = "end"
            elif x < cx - 2:
                anchor = "start"
            else:
                anchor = "middle"
            labels += (f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" dominant-baseline="middle" '
                       f'font-family="Silkscreen, monospace" font-size="{max(8, size*0.036):.0f}" '
                       f'font-weight="700" fill="#6B5D7D">{name.upper()}</text>')
    return f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">{rings}{spokes}{poly}{dots}{labels}</svg>'


def empty_progress_html():
    """starting state, before step 1 has been submitted: nothing to read yet."""
    stats = [(name, 20, color, icon) for _, name, _, color, icon in SPOKES]
    pentagon = _pentagon_svg(stats, size=170, show_labels=True)
    return f"""
    <div class="live-panel-inner">
      <div class="card-eyebrow">Live Read</div>
      <div class="live-status">answer step 1 to start their read</div>
      <div class="progress-pentagon-wrap">{pentagon}</div>
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
        stats.append((name, pct, color, icon))
    return stats


def live_pentagon_html(axis_results):
    """
    real partial read: whatever's been answered through this step, classified
    for real against all 5 axes (the shared-blob design means even one field
    already moves every axis, not just "its own"). refines each step, no
    fabricated numbers at any point.
    """
    stats = _extract_stats(axis_results)
    pentagon = _pentagon_svg(stats, size=190, show_labels=True)
    return f"""
    <div class="live-panel-inner">
      <div class="card-eyebrow">Live Read</div>
      <div class="live-status">reading their answers so far</div>
      <div class="progress-pentagon-wrap">{pentagon}</div>
    </div>
    """


def run_partial(spotify_artists, humor_types, punctuality, group_archetypes,
                 what_they_talk_about="", weekend_activities="", stress_triggers="", party_vibe="",
                 fav_media="", awkward_text=None, text_length_slider=3, texting_style=None,
                 followers=None, social_media_checkboxes=None, spam_friends_count=None):
    try:
        mbti_type, axis_results = predict_mbti(
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
            photo_results           = None,
        )
    except Exception as e:
        print(f"partial prediction error: {e}")
        return empty_progress_html()

    if axis_results is None:
        return empty_progress_html()

    return live_pentagon_html(axis_results)


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

    stat_rows = "".join(f'''
    <div class="stat-row">
      <svg class="stat-icon" viewBox="0 0 18 18" style="color:{color}">{ICONS[icon]}</svg>
      <span class="stat-name">{name}</span>
      <span class="stat-num">{pct}</span>
    </div>''' for name, pct, color, icon in stats)

    avg_spread = sum(abs(p - 50) for _, p, _, _ in stats) / len(stats)
    if avg_spread > 30:
        rarity, rarity_color = "RARE", "#D9A0A6"
    elif avg_spread > 15:
        rarity, rarity_color = "UNCOMMON", "#8FA06E"
    else:
        rarity, rarity_color = "MIXED SIGNAL", "#C9A876"

    creature = creature_svg(e_i, n_s, t_f, j_p, suffix, size=40)
    pentagon = _pentagon_svg(stats, size=250, show_labels=True)
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
    text_length_slider, texting_style, followers, social_media_checkboxes, spam_friends_count, photo,
):
    photo_results = None
    if photo is not None:
        try:
            from photo_analysis import analyze_photo
            photo_results = analyze_photo(photo)
        except Exception as e:
            print(f"photo analysis error: {e}")

    try:
        mbti_type, axis_results = predict_mbti(
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
        )
    except Exception as e:
        print(f"prediction error: {e}")
        return (
            '<div class="result-empty">having trouble right now, give it a moment and try again.</div>',
            gr.update(visible=True), gr.update(visible=False),
        )

    if axis_results is None:
        return (
            '<div class="result-empty">fill in at least a few fields to get a read.</div>',
            gr.update(visible=True), gr.update(visible=False),
        )
    return build_reveal_html(mbti_type, axis_results), gr.update(visible=False), gr.update(visible=True)


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
    body_background_fill="#FFFDF9",
    body_background_fill_dark="#FFFDF9",
    block_background_fill="#EDE6D3",
    block_border_color="#4A3B5C",
    block_border_width="2px",
    block_radius="8px",
    block_shadow="none",
    block_label_text_size="sm",
    block_label_text_weight="600",
    block_label_text_color="#362B47",
    block_label_background_fill="transparent",
    block_label_border_width="0px",
    block_label_padding="0px",
    block_label_margin="0px",
    block_label_radius="0px",
    block_label_shadow="none",
    block_title_text_color="#362B47",
    block_title_background_fill="transparent",
    input_background_fill="#FFFFFF",
    input_border_color="#4A3B5C",
    input_border_color_focus="#8FA06E",
    input_shadow="none",
    input_shadow_focus="0 0 0 3px rgba(143,160,110,0.25)",
    input_radius="4px",
    checkbox_background_color="#FFFFFF",
    checkbox_border_color="#4A3B5C",
    checkbox_border_color_selected="#4A3B5C",
    checkbox_background_color_selected="#8FA06E",
    checkbox_label_background_fill="#FFFFFF",
    checkbox_label_background_fill_hover="#F7F3EA",
    checkbox_label_background_fill_selected="#8FA06E",
    checkbox_label_border_color="#4A3B5C",
    checkbox_label_border_color_hover="#4A3B5C",
    checkbox_label_border_color_selected="#4A3B5C",
    checkbox_label_text_color="#6B5D7D",
    checkbox_label_text_color_selected="#FFFFFF",
    button_primary_background_fill="#4A3B5C",
    button_primary_background_fill_hover="#8FA06E",
    button_primary_text_color="#EDE6D3",
    button_primary_border_color="transparent",
    button_large_radius="6px",
    button_large_padding="14px 32px",
    slider_color="#8FA06E",
    border_color_primary="#4A3B5C",
    color_accent="#8FA06E",
    color_accent_soft="#F7F3EA",
    link_text_color="#8FA06E",
    body_text_color="#362B47",
    body_text_color_subdued="#6B5D7D",
)


# ── wizard step handlers ────────────────────────────────────────────────────
TOTAL_STEPS = 4


def next1_handler(spotify_artists, humor_types, punctuality, group_archetypes):
    panel = run_partial(spotify_artists, humor_types, punctuality, group_archetypes)
    return panel, gr.update(visible=False), gr.update(visible=True), step_indicator_html(2, TOTAL_STEPS)


def next2_handler(spotify_artists, humor_types, punctuality, group_archetypes,
                   what_they_talk_about, weekend_activities, stress_triggers, party_vibe, fav_media, awkward_text):
    panel = run_partial(spotify_artists, humor_types, punctuality, group_archetypes,
                         what_they_talk_about, weekend_activities, stress_triggers, party_vibe, fav_media, awkward_text)
    return panel, gr.update(visible=False), gr.update(visible=True), step_indicator_html(3, TOTAL_STEPS)


def next3_handler(spotify_artists, humor_types, punctuality, group_archetypes,
                   what_they_talk_about, weekend_activities, stress_triggers, party_vibe, fav_media, awkward_text,
                   text_length_slider, texting_style, followers, social_media_checkboxes, spam_friends_count):
    panel = run_partial(spotify_artists, humor_types, punctuality, group_archetypes,
                         what_they_talk_about, weekend_activities, stress_triggers, party_vibe, fav_media, awkward_text,
                         text_length_slider, texting_style, followers, social_media_checkboxes, spam_friends_count)
    return panel, gr.update(visible=False), gr.update(visible=True), step_indicator_html(4, TOTAL_STEPS)


# ── layout ────────────────────────────────────────────────────────────────────
with gr.Blocks(title="mbti guesser", css=CSS, theme=theme, head=HEAD_JS) as demo:

    gr.HTML("""
    <div class="mbti-hero">
      <span class="hero-eyebrow">mbti guesser</span>
      <h1 class="hero-title">type radar</h1>
      <p class="hero-sub">answer a few questions and open their type card.</p>
    </div>
    """)

    with gr.Column(elem_classes=["main-content"]) as form_page:
        with gr.Row(elem_classes=["console"]):

            with gr.Column(elem_classes=["form-col"]):
                step_indicator = gr.HTML(step_indicator_html(1, TOTAL_STEPS))

                with gr.Column(visible=True) as step1:
                    with gr.Group(elem_classes=["mbti-card"]):
                        gr.HTML('<span class="section-label">the basics</span>')
                        spotify_artists = gr.Textbox(
                            label="spotify top artists",
                            placeholder="olivia rodrigo, daniel caesar, le sserafim, clairo…",
                        )
                        humor_types = gr.CheckboxGroup(
                            label="their humor",
                            choices=["dry", "unhinged", "wholesome", "dark", "sarcastic", "self-deprecating"],
                        )
                        punctuality = gr.Radio(
                            label="early, on time, or late?",
                            choices=["always early", "usually early", "on time", "usually late", "always late"],
                        )
                        group_archetypes = gr.CheckboxGroup(
                            label="their role in the friend group",
                            choices=[
                                "the mom (plans everything)", "the one who does it for the plot",
                                "the researcher (googles before anyone asks)", "the therapist friend",
                                "the flake", "the hype person", "the nonchalant one", "the instigator",
                            ],            )
                    next1_btn = gr.Button("Next →", variant="primary", size="lg")

                with gr.Column(visible=False) as step2:
                    with gr.Group(elem_classes=["mbti-card"]):
                        gr.HTML('<span class="section-label">what they\'re like</span>')
                        what_they_talk_about = gr.Textbox(
                            label="what do they talk about most?",
                            placeholder="the nba finals, their love life, conspiracy theories…",
                            lines=2,
                        )
                        weekend_activities = gr.Textbox(
                            label="how do they spend their weekends?",
                            placeholder="hiking alone, cafe hopping, sleeping until noon…",
                            lines=2,
                        )
                        stress_triggers = gr.Textbox(
                            label="what stresses them out?",
                            placeholder="last-minute changes, overstimulating noises, falling behind…",
                            lines=2,
                        )
                        party_vibe = gr.Textbox(
                            label="vibe at parties / what kind of drunk are they?",
                            placeholder="disappears to talk to one person, center of attention, goes home early…",
                            lines=2,
                        )
                        fav_media = gr.Textbox(
                            label="favorite shows, movies, or books",
                            placeholder="lalaland, attack on titan, hunger games…",
                            lines=2,
                        )
                        awkward_text = gr.Radio(
                            label="they sent a slightly awkward text an hour ago. they...",
                            choices=["already forgot about it", "still replaying it in their head"],
                        )
                    with gr.Row():
                        back2_btn = gr.Button("← Back", variant="secondary")
                        next2_btn = gr.Button("Next →", variant="primary")

                with gr.Column(visible=False) as step3:
                    with gr.Group(elem_classes=["mbti-card"]):
                        gr.HTML('<span class="section-label">digital habits</span>')
                        text_length_slider = gr.Slider(
                            minimum=1, maximum=5, step=1, value=3,
                            label="how long are their texts?",
                            info="1 = one-word replies   ||   5 = full essays",
                        )
                        texting_style = gr.CheckboxGroup(
                            label="texting style",
                            choices=["quick replies", "slow replies", "emoji heavy", "no emojis",
                                        "all lowercase", "uses punctuation", "leaves people on read"],
                        )
                        followers = gr.Number(label="follower count", precision=0, minimum=0, info="main account")
                        social_media_checkboxes = gr.CheckboxGroup(
                            label="social media behavior",
                            choices=["posts a lot", "mostly a lurker", "stories person",
                                        "feed poster", "has a spam/close friends account"],
                        )
                        spam_friends_count = gr.Number(
                            label="close friends / spam list size",
                            minimum=0, visible=False,
                            info="under 10 = very private || 110+ = basically a second public account",
                        )
                        social_media_checkboxes.change(
                            fn=lambda c: gr.update(visible="has a spam/close friends account" in c),
                            inputs=social_media_checkboxes,
                            outputs=spam_friends_count,
                        )
                    with gr.Row():
                        back3_btn = gr.Button("← Back", variant="secondary")
                        next3_btn = gr.Button("Next →", variant="primary")

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
            again_btn = gr.Button("answer again", size="sm")

    gr.HTML('<div class="mbti-footer">predictions use facebook/bart-large-mnli || axes marked "?" had insufficient signal</div>')

    step1_fields = [spotify_artists, humor_types, punctuality, group_archetypes]
    step2_fields = step1_fields + [what_they_talk_about, weekend_activities, stress_triggers, party_vibe, fav_media, awkward_text]
    step3_fields = step2_fields + [text_length_slider, texting_style, followers, social_media_checkboxes, spam_friends_count]

    next1_btn.click(fn=next1_handler, inputs=step1_fields, outputs=[progress_panel, step1, step2, step_indicator])
    next2_btn.click(fn=next2_handler, inputs=step2_fields, outputs=[progress_panel, step2, step3, step_indicator])
    next3_btn.click(fn=next3_handler, inputs=step3_fields, outputs=[progress_panel, step3, step4, step_indicator])

    back2_btn.click(fn=lambda: (gr.update(visible=True), gr.update(visible=False), step_indicator_html(1, TOTAL_STEPS)), outputs=[step1, step2, step_indicator])
    back3_btn.click(fn=lambda: (gr.update(visible=True), gr.update(visible=False), step_indicator_html(2, TOTAL_STEPS)), outputs=[step2, step3, step_indicator])
    back4_btn.click(fn=lambda: (gr.update(visible=True), gr.update(visible=False), step_indicator_html(3, TOTAL_STEPS)), outputs=[step3, step4, step_indicator])

    submit_inputs = step3_fields + [photo]
    submit_btn.click(fn=run_prediction, inputs=submit_inputs, outputs=[output, form_page, reveal_page])
    again_btn.click(
        fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
        outputs=[form_page, reveal_page],
    )

if __name__ == "__main__":
    demo.launch(share=False)
