"""
ui.py — mbti guesser
"""

import gradio as gr
from app import predict_mbti
from photo_analysis import analyze_photo

MBTI_DESCRIPTIONS = {
    "INTJ": ("the architect", "strategic, private, always three steps ahead. probably already knows what you're going to say."),
    "INTP": ("the logician", "lives in their head, loves a rabbit hole, skeptical of most things. argues for fun and calls it curiosity."),
    "ENTJ": ("the commander", "natural leader, extremely sure of themselves, not always gentle about it. has strong opinions on your life choices."),
    "ENTP": ("the debater", "argues for fun, gets bored easily, full of ideas they won't always follow through on. devil's advocate as a personality."),
    "INFJ": ("the advocate", "intense, private, somehow knows what you're thinking before you do. rarest type and they know it."),
    "INFP": ("the mediator", "idealistic, emotional, writes in their notes app at 2am. takes everything personally and feels deeply about it."),
    "ENFJ": ("the protagonist", "makes everyone feel seen, over-commits to plans, cries at ads. the friend who checks in on you unprompted."),
    "ENFP": ("the campaigner", "energetic, all over the place, starts things they don't finish. somehow still the most magnetic person in the room."),
    "ISTJ": ("the logistician", "reliable to a fault, rule-follower, shows love through acts of service. will send you a calendar invite."),
    "ISFJ": ("the defender", "takes care of everyone around them, forgets to take care of themselves. remembers your coffee order."),
    "ESTJ": ("the executive", "has a spreadsheet for everything, does not understand why you don't. gets things done, no vibes required."),
    "ESFJ": ("the consul", "the friend group mom, needs approval, genuinely warm. throws the best parties and stress-cleans before you arrive."),
    "ISTP": ("the virtuoso", "quiet but mechanically gifted, not big on feelings, extremely competent. fix-it person energy."),
    "ISFP": ("the adventurer", "gentle, artistic, keeps their real thoughts to themselves. has excellent taste and won't brag about it."),
    "ESTP": ("the entrepreneur", "impulsive, charismatic, probably the one daring you to do stuff. thrives on chaos they created."),
    "ESFP": ("the entertainer", "the most fun person in the room, no plans, all vibes. will make a bit out of anything."),
}

AXIS_META = {
    "E_I": {"label": "energy",   "poles": ("E", "I"), "desc": ("extrovert", "introvert")},
    "N_S": {"label": "thinking", "poles": ("N", "S"), "desc": ("intuitive", "sensing")},
    "T_F": {"label": "deciding", "poles": ("T", "F"), "desc": ("thinker",   "feeler")},
    "J_P": {"label": "living",   "poles": ("J", "P"), "desc": ("judger",    "perceiver")},
}

AXIS_ORDER = ["E_I", "N_S", "T_F", "J_P"]


def format_results(mbti_type, axis_results):
    if axis_results is None:
        return '<div class="result-empty">fill in a few more fields and try again.</div>'

    has_ambiguous = "?" in mbti_type

    if has_ambiguous:
        title_label = "mixed signals"
        desc_text = "a few axes didn't have enough signal to call — see the breakdown below."
    else:
        title_label, desc_text = MBTI_DESCRIPTIONS.get(
            mbti_type,
            ("unknown type", "an unusual combination — see the axis breakdown below.")
        )

    # build animated letter badges for the 4-letter type
    letter_badges = ""
    for i, ch in enumerate(mbti_type):
        delay = i * 0.08
        is_q = ch == "?"
        cls = "type-letter-ambiguous" if is_q else "type-letter"
        letter_badges += f'<span class="{cls}" style="animation-delay:{delay}s">{ch}</span>'

    # axis bars — bidirectional from center
    bars_html = ""
    for i, axis in enumerate(AXIS_ORDER):
        r = axis_results[axis]
        meta = AXIS_META[axis]
        p0, p1 = meta["poles"]
        d0, d1 = meta["desc"]
        axis_label = meta["label"]
        winner = r["winner"]
        conf = r["confidence"]
        gap = r["gap"]
        is_ambiguous = r["is_ambiguous"]

        if is_ambiguous:
            letter_display = "?"
            conf_label = f"only {gap:.1f}pt gap"
            winner_desc = "not enough signal"
            # ambiguous: show a faint center mark, no fill
            bar_inner = '<div class="bar-center-tick"></div>'
            letter_cls = "axis-letter axis-ambiguous"
        else:
            letter_display = winner
            conf_label = f"{conf:.0f}%"
            winner_idx = meta["poles"].index(winner)
            winner_desc = meta["desc"][winner_idx]
            letter_cls = "axis-letter"

            # bidirectional bar: winner E/N/T/J fills left half leftward,
            # winner I/S/F/P fills right half rightward
            fill_pct = (conf - 50) / 50 * 100  # 0-100 within the winning half
            fill_pct = max(0, min(100, fill_pct))

            if winner == p0:
                # fills the left half going left from center
                bar_inner = f'''
                  <div class="bar-half bar-half-left">
                    <div class="bar-fill bar-fill-left" style="width:{fill_pct}%;animation-delay:{i*0.12+0.3}s"></div>
                  </div>
                  <div class="bar-half bar-half-right"></div>'''
            else:
                # fills the right half going right from center
                bar_inner = f'''
                  <div class="bar-half bar-half-left"></div>
                  <div class="bar-half bar-half-right">
                    <div class="bar-fill bar-fill-right" style="width:{fill_pct}%;animation-delay:{i*0.12+0.3}s"></div>
                  </div>'''

        row_delay = i * 0.12

        bars_html += f"""
<div class="axis-row" style="animation-delay:{row_delay}s">
  <div class="axis-meta">
    <span class="axis-eyebrow">{axis_label}</span>
    <span class="{letter_cls}">{letter_display}</span>
    <span class="axis-winner-desc">{winner_desc}</span>
    <span class="axis-conf">{conf_label}</span>
  </div>
  <div class="axis-bar-wrap">
    <span class="axis-pole">{p0}</span>
    <div class="bar-track">{bar_inner}</div>
    <span class="axis-pole">{p1}</span>
  </div>
</div>"""

    return f"""
<div class="result-wrap">
  <div class="result-eyebrow">✦ predicted type</div>
  <div class="result-type-row">{letter_badges}</div>
  <div class="result-title-label">{title_label}</div>
  <p class="result-desc">{desc_text}</p>
  <div class="result-divider"></div>
  <div class="axes-eyebrow">axis breakdown</div>
  {bars_html}
</div>"""


def run_prediction(
    spotify_artists, humor_types, punctuality, group_archetypes,
    what_they_talk_about, weekend_activities, text_length_slider,
    texting_style, stress_triggers, party_vibe, fav_media,
    followers, following, social_media_checkboxes, spam_friends_count, photo
):
    photo_results = None
    if photo is not None:
        try:
            photo_results = analyze_photo(photo)
        except Exception as e:
            print(f"photo analysis error: {e}")

    mbti_type, axis_results = predict_mbti(
        spotify_artists=spotify_artists or "",
        humor_types=humor_types or [],
        punctuality=punctuality,
        group_archetypes=group_archetypes or [],
        what_they_talk_about=what_they_talk_about or "",
        weekend_activities=weekend_activities or "",
        text_length_slider=int(text_length_slider) if text_length_slider else 3,
        texting_style=texting_style or [],
        stress_triggers=stress_triggers or "",
        party_vibe=party_vibe or "",
        fav_media=fav_media or "",
        followers=followers,
        following=following,
        social_media_checkboxes=social_media_checkboxes or [],
        spam_friends_count=spam_friends_count,
        photo_results=photo_results
    )

    if axis_results is None:
        return '<div class="result-empty">fill in at least a few fields to get a prediction.</div>'

    return format_results(mbti_type, axis_results)


# ---------------------------------------------------------------------------
# css
# ---------------------------------------------------------------------------

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400;1,700&family=DM+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ---- root ---- */
.gradio-container {
    background: #F7F0E6 !important;
    font-family: 'DM Sans', sans-serif !important;
    max-width: 1120px !important;
    margin: 0 auto !important;
    padding: 0 2rem !important;
    min-height: 100vh;
}

/* kill gradio chrome */
.gradio-container .block,
.gradio-container .panel,
.gradio-container > div,
footer { background: transparent !important; box-shadow: none !important; border: none !important; }

/* ---- hero ---- */
.mbti-hero {
    padding: 80px 0 52px;
    text-align: center;
    animation: fadeUp 0.8s ease both;
    position: relative;
}

/* decorative background monogram: the signature element */
.mbti-hero::before {
    content: "MBTI";
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -44%) scaleX(1.15);
    font-family: 'Playfair Display', serif;
    font-weight: 900;
    font-size: clamp(100px, 18vw, 200px);
    color: transparent;
    -webkit-text-stroke: 1px rgba(201, 125, 138, 0.08);
    letter-spacing: 0.08em;
    pointer-events: none;
    user-select: none;
    white-space: nowrap;
    z-index: 0;
}

.mbti-hero > * { position: relative; z-index: 1; }

.hero-eyebrow {
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.28em;
    text-transform: uppercase;
    color: #C97D8A;
    margin-bottom: 22px;
    display: block;
}

.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(48px, 7.5vw, 88px);
    font-weight: 900;
    font-style: italic;
    line-height: 0.95;
    letter-spacing: -0.02em;
    color: #2D1F1F;
    margin-bottom: 24px;
}

.hero-title em {
    color: #C97D8A;
    font-style: italic;
}

.hero-sub {
    font-size: 15px;
    font-weight: 300;
    color: #7A5C5C;
    line-height: 1.75;
    max-width: 440px;
    margin: 0 auto;
}

/* ---- two-col shell ---- */
.mbti-shell {
    display: grid !important;
    grid-template-columns: 1fr 400px !important;
    gap: 20px !important;
    align-items: start !important;
    padding-bottom: 80px;
}

@media (max-width: 860px) {
    .mbti-shell { grid-template-columns: 1fr !important; }
}

/* ---- form panel ---- */
.form-panel {
    background: #FDF8F3 !important;
    border: 1px solid #EDD8DC !important;
    border-radius: 24px !important;
    padding: 40px 40px 32px !important;
}

/* ---- section dividers ---- */
.section-head {
    padding: 32px 0 14px;
    border-top: 1px solid #EDD8DC;
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.section-head:first-of-type { border-top: none; padding-top: 0; }

.section-eyebrow {
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: #C97D8A;
}

.section-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: #E8C4CC;
    flex-shrink: 0;
}

/* ---- gradio input overrides ---- */
.gradio-container label span,
.gradio-container .svelte-1ed2p3z {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 11px !important;
    font-weight: 500 !important;
    letter-spacing: 0.07em !important;
    color: #7A5C5C !important;
    text-transform: uppercase !important;
}

.gradio-container .info {
    font-size: 12px !important;
    font-weight: 300 !important;
    color: #A08080 !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
}

.gradio-container input[type="text"],
.gradio-container textarea,
.gradio-container input[type="number"] {
    background: #F7F0E6 !important;
    border: 1.5px solid #E8C4CC !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    font-weight: 300 !important;
    color: #2D1F1F !important;
    padding: 13px 16px !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}

.gradio-container input[type="text"]:focus,
.gradio-container textarea:focus,
.gradio-container input[type="number"]:focus {
    border-color: #C97D8A !important;
    box-shadow: 0 0 0 3px rgba(201, 125, 138, 0.11) !important;
    outline: none !important;
}

.gradio-container input::placeholder,
.gradio-container textarea::placeholder {
    color: #BBA8A8 !important;
    font-weight: 300 !important;
}

/* checkbox + radio chip style */
.gradio-container .wrap.svelte-vt7tkb,
.gradio-container .wrap { gap: 7px !important; flex-wrap: wrap !important; }

.gradio-container .wrap label {
    background: #F7F0E6 !important;
    border: 1.5px solid #E8C4CC !important;
    border-radius: 100px !important;
    padding: 7px 14px !important;
    cursor: pointer !important;
    transition: all 0.18s ease !important;
}

.gradio-container .wrap label:hover {
    border-color: #C97D8A !important;
    background: #FDF8F3 !important;
}

.gradio-container .wrap input:checked + span,
.gradio-container .wrap label:has(input:checked) {
    background: #2D1F1F !important;
    border-color: #2D1F1F !important;
    color: #F7F0E6 !important;
}

.gradio-container .wrap label span {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    font-weight: 400 !important;
    letter-spacing: 0 !important;
    text-transform: none !important;
    color: #2D1F1F !important;
}

.gradio-container .wrap input { display: none !important; }

/* slider */
.gradio-container input[type="range"] {
    accent-color: #C97D8A !important;
    height: 4px !important;
}

/* ---- submit row ---- */
.mbti-submit { margin-top: 36px !important; }

.mbti-submit button {
    background: #2D1F1F !important;
    color: #F7F0E6 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 100px !important;
    padding: 20px 0 !important;
    width: 100% !important;
    cursor: pointer !important;
    transition: all 0.25s ease !important;
}

.mbti-submit button:hover {
    background: #C97D8A !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 14px 36px rgba(201, 125, 138, 0.35) !important;
}

/* ---- sticky result panel ---- */
.result-panel {
    background: #FDF8F3 !important;
    border: 1px solid #EDD8DC !important;
    border-radius: 24px !important;
    padding: 36px 32px !important;
    position: sticky !important;
    top: 24px !important;
    transition: box-shadow 0.3s ease !important;
}

.result-panel:hover {
    box-shadow: 0 8px 48px rgba(201, 125, 138, 0.13) !important;
}

/* ---- result content ---- */
.result-wrap { animation: fadeUp 0.45s ease both; }

.result-eyebrow {
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: #C97D8A;
    margin-bottom: 16px;
    display: block;
}

/* individual letter badges */
.result-type-row {
    display: flex;
    gap: 6px;
    margin-bottom: 14px;
    align-items: flex-end;
}

.type-letter {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-family: 'Playfair Display', serif;
    font-size: clamp(48px, 8vw, 68px);
    font-weight: 900;
    font-style: italic;
    line-height: 1;
    color: #C97D8A;
    animation: popIn 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both;
    letter-spacing: -0.01em;
}

.type-letter-ambiguous {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-family: 'Playfair Display', serif;
    font-size: clamp(48px, 8vw, 68px);
    font-weight: 900;
    font-style: italic;
    line-height: 1;
    color: #D8C4C4;
    animation: popIn 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

.result-title-label {
    font-family: 'Playfair Display', serif;
    font-size: 17px;
    font-weight: 700;
    color: #2D1F1F;
    margin-bottom: 8px;
    line-height: 1.3;
}

.result-desc {
    font-size: 13.5px;
    font-weight: 300;
    color: #7A5C5C;
    line-height: 1.7;
}

.result-divider {
    height: 1px;
    background: #EDD8DC;
    margin: 24px 0 20px;
}

/* ---- axis breakdown ---- */
.axes-eyebrow {
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #BBA8A8;
    margin-bottom: 18px;
    display: block;
}

.axis-row {
    margin-bottom: 20px;
    animation: fadeUp 0.4s ease both;
}

.axis-meta {
    display: flex;
    align-items: baseline;
    gap: 7px;
    margin-bottom: 7px;
}

.axis-eyebrow {
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #C9B0B0;
    min-width: 52px;
    flex-shrink: 0;
}

.axis-letter {
    font-family: 'Playfair Display', serif;
    font-size: 20px;
    font-weight: 900;
    font-style: italic;
    color: #2D1F1F;
    line-height: 1;
    flex-shrink: 0;
}

.axis-ambiguous { color: #C9B0B0 !important; }

.axis-winner-desc {
    font-size: 12px;
    font-weight: 300;
    color: #A08080;
    flex: 1;
}

.axis-conf {
    font-size: 11px;
    font-weight: 500;
    color: #BBA8A8;
    white-space: nowrap;
    margin-left: auto;
}

/* bidirectional bar */
.axis-bar-wrap {
    display: flex;
    align-items: center;
    gap: 7px;
}

.axis-pole {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.04em;
    color: #C9B0B0;
    min-width: 14px;
    flex-shrink: 0;
}

.bar-track {
    flex: 1;
    height: 3px;
    background: #EDD8DC;
    border-radius: 100px;
    overflow: hidden;
    display: flex;
    position: relative;
}

.bar-half {
    flex: 1;
    height: 100%;
    overflow: hidden;
    display: flex;
}

/* left half: fill grows from right edge (center) leftward */
.bar-half-left { justify-content: flex-end; }
.bar-fill-left {
    height: 100%;
    background: linear-gradient(270deg, #E8A4B0, #C97D8A);
    border-radius: 100px;
    transform-origin: right center;
    animation: growBar 0.75s cubic-bezier(0.16, 1, 0.3, 1) both;
}

/* right half: fill grows from left edge (center) rightward */
.bar-half-right { justify-content: flex-start; }
.bar-fill-right {
    height: 100%;
    background: linear-gradient(90deg, #E8A4B0, #C97D8A);
    border-radius: 100px;
    transform-origin: left center;
    animation: growBar 0.75s cubic-bezier(0.16, 1, 0.3, 1) both;
}

/* ambiguous center tick */
.bar-center-tick {
    position: absolute;
    left: 50%;
    top: 0;
    transform: translateX(-50%);
    width: 2px;
    height: 100%;
    background: #D0BCBC;
    border-radius: 100px;
}

/* ---- placeholder / empty states ---- */
.result-placeholder {
    font-size: 14px;
    font-weight: 300;
    color: #BBA8A8;
    line-height: 1.75;
    text-align: center;
    padding: 48px 0 40px;
}

.result-empty {
    font-size: 13px;
    font-weight: 300;
    color: #A08080;
    padding: 16px 0;
    line-height: 1.6;
}

/* ---- photo note ---- */
.photo-note {
    font-size: 12px;
    font-weight: 300;
    color: #A08080;
    line-height: 1.65;
    margin-top: 10px;
}

/* ---- footer ---- */
.mbti-footer {
    font-size: 11px;
    font-weight: 300;
    color: #C9B0B0;
    text-align: center;
    padding-bottom: 56px;
    line-height: 1.7;
    letter-spacing: 0.02em;
}

/* ---- animations ---- */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(18px); }
    to   { opacity: 1; transform: translateY(0); }
}

@keyframes popIn {
    from { opacity: 0; transform: scale(0.6) rotate(-4deg); }
    to   { opacity: 1; transform: scale(1)   rotate(0deg); }
}

@keyframes growBar {
    from { width: 0 !important; }
    to   { /* width is set inline */ }
}

/* reduced motion */
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
"""

# ---------------------------------------------------------------------------
# interface
# ---------------------------------------------------------------------------

with gr.Blocks(title="mbti guesser", css=CSS) as demo:

    # hero
    gr.HTML("""
    <div class="mbti-hero">
      <span class="hero-eyebrow">✦ personality decoder</span>
      <h1 class="hero-title">who are they,<br><em>really?</em></h1>
      <p class="hero-sub">no quiz. just tell me about your friend — or your crush — and we'll figure out their type.</p>
    </div>
    """)

    with gr.Row(elem_classes=["mbti-shell"]):

        # ---- left col: form ----
        with gr.Column(elem_classes=["form-panel"]):

            gr.HTML('<div class="section-head"><div class="section-dot"></div><span class="section-eyebrow">the basics</span></div>')

            spotify_artists = gr.Textbox(
                label="spotify top artists",
                placeholder="mitski, clairo, brockhampton, glass animals...",
                info="what's always in their headphones?"
            )

            humor_types = gr.CheckboxGroup(
                label="their humor",
                choices=["dry", "chaotic", "wholesome", "dark", "sarcastic", "surreal", "self-deprecating"],
                info="check everything that fits"
            )

            punctuality = gr.Radio(
                label="early, on time, or always late?",
                choices=["always early", "on time", "always late"]
            )

            group_archetypes = gr.CheckboxGroup(
                label="their role in the friend group",
                choices=[
                    "The Mom (plans everything)",
                    "The Chaos Agent",
                    "The Researcher (googles before anyone asks)",
                    "The Therapist Friend",
                    "The Flake",
                    "The Hype Person",
                    "The Background One",
                    "The Realist"
                ],
                info="can pick more than one"
            )

            gr.HTML('<div class="section-head"><div class="section-dot"></div><span class="section-eyebrow">what they\'re like</span></div>')

            what_they_talk_about = gr.Textbox(
                label="what do they talk about most?",
                placeholder="the show they're obsessed with, their job, conspiracy theories, local drama...",
                lines=2
            )

            weekend_activities = gr.Textbox(
                label="how do they spend their weekends?",
                placeholder="hiking alone, hosting people, working on a project, sleeping until noon...",
                lines=2
            )

            stress_triggers = gr.Textbox(
                label="what stresses them out?",
                placeholder="last-minute changes, conflict, falling behind, too many obligations...",
                lines=2
            )

            party_vibe = gr.Textbox(
                label="vibe at parties — or what kind of drunk are they?",
                placeholder="disappears to talk to one person all night, center of everything, goes home early...",
                lines=2,
                info="best indirect introvert/extrovert signal"
            )

            fav_media = gr.Textbox(
                label="favorite shows, movies, or books",
                placeholder="succession, studio ghibli, crime podcasts, philosophy youtube...",
                lines=2
            )

            gr.HTML('<div class="section-head"><div class="section-dot"></div><span class="section-eyebrow">how they text</span></div>')

            text_length_slider = gr.Slider(
                minimum=1, maximum=5, step=1, value=3,
                label="how long are their texts?",
                info="1 = one-word replies   •   5 = full essays"
            )

            texting_style = gr.CheckboxGroup(
                label="texting style",
                choices=[
                    "quick replies", "slow replies", "emoji heavy", "no emoji",
                    "all lowercase", "uses punctuation", "leaves people on read"
                ]
            )

            gr.HTML('<div class="section-head"><div class="section-dot"></div><span class="section-eyebrow">social media</span></div>')

            with gr.Row():
                followers = gr.Number(
                    label="follower count", precision=0, minimum=0,
                    info="on their main account"
                )
                following = gr.Number(
                    label="following count", precision=0, minimum=0
                )

            social_media_checkboxes = gr.CheckboxGroup(
                label="social media behavior",
                choices=[
                    "posts a lot", "mostly a lurker", "stories person",
                    "feed poster", "has a spam/close friends account"
                ]
            )

            spam_friends_count = gr.Number(
                label="how many people are on their close friends / spam list?",
                minimum=0,
                visible=False,
                info="under 10 = very private   •   110+ = basically a second public account"
            )

            # reveal spam count input when spam box is checked
            social_media_checkboxes.change(
                fn=lambda choices: gr.update(visible="has a spam/close friends account" in choices),
                inputs=social_media_checkboxes,
                outputs=spam_friends_count
            )

            gr.HTML('<div class="section-head"><div class="section-dot"></div><span class="section-eyebrow">photo <span style="color:#BBA8A8;font-size:9px;letter-spacing:0.1em">(optional)</span></span></div>')

            photo = gr.Image(
                label="drop a photo of them — profile pic, tagged photo, anything",
                type="filepath",
                sources=["upload", "clipboard"],
                height=175
            )

            gr.HTML("""
            <p class="photo-note">
              analyzed locally using deepface + opencv — we look at expression,
              solo vs. group, eye contact, and background context.
            </p>
            """)

            with gr.Row(elem_classes=["mbti-submit"]):
                submit_btn = gr.Button("figure out their type ↗", variant="primary")

        # ---- right col: sticky result ----
        with gr.Column(elem_classes=["result-panel"]):
            output = gr.HTML("""
            <div class="result-placeholder">
              fill in a few fields<br>on the left, then<br>hit the button.<br><br>
              <span style="font-family:'Playfair Display',serif;font-style:italic;font-size:72px;color:#EDD8DC;line-height:1;display:block;margin-top:8px;">?</span>
            </div>
            """)

    gr.HTML("""
    <div class="mbti-footer">
      predictions use facebook/bart-large-mnli via zero-shot classification.<br>
      axes marked "?" didn't have enough signal to call either way.
    </div>
    """)

    submit_btn.click(
        fn=run_prediction,
        inputs=[
            spotify_artists, humor_types, punctuality, group_archetypes,
            what_they_talk_about, weekend_activities, text_length_slider,
            texting_style, stress_triggers, party_vibe, fav_media,
            followers, following, social_media_checkboxes, spam_friends_count, photo
        ],
        outputs=output
    )


if __name__ == "__main__":
    demo.launch(share=False)