"""
ui.py — mbti guesser
layout only; all styles live in styles.css
"""

import pathlib
import gradio as gr
from app import predict_mbti
from photo_analysis import analyze_photo

# ── load stylesheet ──────────────────────────────────────────────────────────
_CSS_PATH = pathlib.Path(__file__).parent / "styles.css"
CSS = _CSS_PATH.read_text()

# ── type metadata ────────────────────────────────────────────────────────────
MBTI_DESCRIPTIONS = {
    "INTJ": ("the architect",     "strategic, private, always three steps ahead. probably already knows what you're going to say."),
    "INTP": ("the logician",      "lives in their head, loves a rabbit hole, skeptical of most things. argues for fun and calls it curiosity."),
    "ENTJ": ("the commander",     "natural leader, extremely sure of themselves, not always gentle about it. has strong opinions on your life choices."),
    "ENTP": ("the debater",       "argues for fun, gets bored easily, full of ideas they won't always follow through on. devil's advocate as a personality."),
    "INFJ": ("the advocate",      "intense, private, somehow knows what you're thinking before you do. rarest type and they know it."),
    "INFP": ("the mediator",      "idealistic, emotional, writes in their notes app at 2am. takes everything personally and feels deeply about it."),
    "ENFJ": ("the protagonist",   "makes everyone feel seen, over-commits to plans, cries at ads. the friend who checks in on you unprompted."),
    "ENFP": ("the campaigner",    "energetic, all over the place, starts things they don't finish. somehow still the most magnetic person in the room."),
    "ISTJ": ("the logistician",   "reliable to a fault, rule-follower, shows love through acts of service. will send you a calendar invite."),
    "ISFJ": ("the defender",      "takes care of everyone around them, forgets to take care of themselves. remembers your coffee order."),
    "ESTJ": ("the executive",     "has a spreadsheet for everything, does not understand why you don't. gets things done, no vibes required."),
    "ESFJ": ("the consul",        "the friend group mom, needs approval, genuinely warm. throws the best parties and stress-cleans before you arrive."),
    "ISTP": ("the virtuoso",      "quiet but mechanically gifted, not big on feelings, extremely competent. fix-it person energy."),
    "ISFP": ("the adventurer",    "gentle, artistic, keeps their real thoughts to themselves. has excellent taste and won't brag about it."),
    "ESTP": ("the entrepreneur",  "impulsive, charismatic, probably the one daring you to do stuff. thrives on chaos they created."),
    "ESFP": ("the entertainer",   "the most fun person in the room, no plans, all vibes. will make a bit out of anything."),
}

AXIS_META = {
    "E_I": {"label": "energy",   "poles": ("E", "I"), "desc": ("extrovert", "introvert")},
    "N_S": {"label": "thinking", "poles": ("N", "S"), "desc": ("intuitive", "sensing")},
    "T_F": {"label": "deciding", "poles": ("T", "F"), "desc": ("thinker",   "feeler")},
    "J_P": {"label": "living",   "poles": ("J", "P"), "desc": ("judger",    "perceiver")},
}

AXIS_ORDER = ["E_I", "N_S", "T_F", "J_P"]


# ── result rendering ─────────────────────────────────────────────────────────
def format_results(mbti_type: str, axis_results: dict) -> str:
    if axis_results is None:
        return '<div class="result-empty">fill in a few more fields and try again.</div>'

    has_ambiguous = "?" in mbti_type

    if has_ambiguous:
        title_label = "mixed signals"
        desc_text   = "a few axes didn't have enough signal to call — see the breakdown below."
    else:
        title_label, desc_text = MBTI_DESCRIPTIONS.get(
            mbti_type,
            ("unknown type", "an unusual combination — see the breakdown below.")
        )

    # animated letter badges
    letter_badges = ""
    for i, ch in enumerate(mbti_type):
        delay = i * 0.08
        cls = "type-letter-ambiguous" if ch == "?" else "type-letter"
        letter_badges += f'<span class="{cls}" style="animation-delay:{delay}s">{ch}</span>'

    # axis bars
    bars_html = ""
    for i, axis in enumerate(AXIS_ORDER):
        r    = axis_results[axis]
        meta = AXIS_META[axis]
        p0, p1 = meta["poles"]
        d0, d1 = meta["desc"]

        is_ambiguous = r["is_ambiguous"]
        winner       = r["winner"]
        conf         = r["confidence"]
        gap          = r["gap"]

        if is_ambiguous:
            letter_display = "?"
            conf_label     = f"only {gap:.1f}pt gap"
            winner_desc    = "not enough signal"
            bar_inner      = '<div class="bar-center-tick"></div>'
            letter_cls     = "axis-letter axis-ambiguous"
        else:
            letter_display = winner
            conf_label     = f"{conf:.0f}%"
            winner_idx     = meta["poles"].index(winner)
            winner_desc    = meta["desc"][winner_idx]
            letter_cls     = "axis-letter"

            fill_pct = max(0.0, min(100.0, (conf - 50) / 50 * 100))

            if winner == p0:
                bar_inner = (
                    f'<div class="bar-half bar-half-left">'
                    f'  <div class="bar-fill bar-fill-left" style="width:{fill_pct}%;animation-delay:{i*0.12+0.3}s"></div>'
                    f'</div>'
                    f'<div class="bar-half bar-half-right"></div>'
                )
            else:
                bar_inner = (
                    f'<div class="bar-half bar-half-left"></div>'
                    f'<div class="bar-half bar-half-right">'
                    f'  <div class="bar-fill bar-fill-right" style="width:{fill_pct}%;animation-delay:{i*0.12+0.3}s"></div>'
                    f'</div>'
                )

        bars_html += f"""
<div class="axis-row" style="animation-delay:{i * 0.12}s">
  <div class="axis-meta">
    <span class="axis-eyebrow">{meta['label']}</span>
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
  <span class="result-eyebrow">✦ predicted type</span>
  <div class="result-type-row">{letter_badges}</div>
  <div class="result-title-label">{title_label}</div>
  <p class="result-desc">{desc_text}</p>
  <div class="result-divider"></div>
  <span class="axes-eyebrow">axis breakdown</span>
  {bars_html}
</div>"""


# ── prediction handler ────────────────────────────────────────────────────────
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
        spotify_artists        = spotify_artists or "",
        humor_types            = humor_types or [],
        punctuality            = punctuality,
        group_archetypes       = group_archetypes or [],
        what_they_talk_about   = what_they_talk_about or "",
        weekend_activities     = weekend_activities or "",
        text_length_slider     = int(text_length_slider) if text_length_slider else 3,
        texting_style          = texting_style or [],
        stress_triggers        = stress_triggers or "",
        party_vibe             = party_vibe or "",
        fav_media              = fav_media or "",
        followers              = followers,
        following              = following,
        social_media_checkboxes= social_media_checkboxes or [],
        spam_friends_count     = spam_friends_count,
        photo_results          = photo_results,
    )

    if axis_results is None:
        return '<div class="result-empty">fill in at least a few fields to get a prediction.</div>'

    return format_results(mbti_type, axis_results)


# ── layout ────────────────────────────────────────────────────────────────────
with gr.Blocks(title="mbti guesser", css=CSS) as demo:

    gr.HTML("""
    <div class="mbti-hero">
      <span class="hero-eyebrow">✦ personality decoder</span>
      <h1 class="hero-title">who are they,<br><em>really?</em></h1>
      <p class="hero-sub">no quiz. tell me about your friend — or your crush — and we'll figure out their type.</p>
    </div>
    """)

    with gr.Row(elem_classes=["mbti-shell"]):

        # ── form column ──────────────────────────────────────────────────────
        with gr.Column(elem_classes=["form-panel"]):

            gr.HTML('<div class="section-head"><span class="section-eyebrow">the basics</span></div>')

            spotify_artists = gr.Textbox(
                label="spotify top artists",
                placeholder="mitski, clairo, brockhampton, glass animals…",
                info="what's always in their headphones?",
            )

            humor_types = gr.CheckboxGroup(
                label="their humor",
                choices=["dry", "chaotic", "wholesome", "dark", "sarcastic", "surreal", "self-deprecating"],
                info="check everything that fits",
            )

            punctuality = gr.Radio(
                label="early, on time, or always late?",
                choices=["always early", "on time", "always late"],
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
                    "The Realist",
                ],
                info="can pick more than one",
            )

            gr.HTML('<div class="section-head"><span class="section-eyebrow">what they\'re like</span></div>')

            what_they_talk_about = gr.Textbox(
                label="what do they talk about most?",
                placeholder="the show they're obsessed with, their job, conspiracy theories, local drama…",
                lines=2,
            )

            weekend_activities = gr.Textbox(
                label="how do they spend their weekends?",
                placeholder="hiking alone, hosting people, working on a project, sleeping until noon…",
                lines=2,
            )

            stress_triggers = gr.Textbox(
                label="what stresses them out?",
                placeholder="last-minute changes, conflict, falling behind, too many obligations…",
                lines=2,
            )

            party_vibe = gr.Textbox(
                label="vibe at parties — or what kind of drunk are they?",
                placeholder="disappears to talk to one person all night, center of everything, goes home early…",
                lines=2,
                info="best indirect introvert/extrovert signal",
            )

            fav_media = gr.Textbox(
                label="favorite shows, movies, or books",
                placeholder="succession, studio ghibli, crime podcasts, philosophy youtube…",
                lines=2,
            )

            gr.HTML('<div class="section-head"><span class="section-eyebrow">how they text</span></div>')

            text_length_slider = gr.Slider(
                minimum=1, maximum=5, step=1, value=3,
                label="how long are their texts?",
                info="1 = one-word replies   •   5 = full essays",
            )

            texting_style = gr.CheckboxGroup(
                label="texting style",
                choices=[
                    "quick replies", "slow replies", "emoji heavy", "no emoji",
                    "all lowercase", "uses punctuation", "leaves people on read",
                ],
            )

            gr.HTML('<div class="section-head"><span class="section-eyebrow">social media</span></div>')

            with gr.Row():
                followers = gr.Number(
                    label="follower count",
                    precision=0, minimum=0,
                    info="on their main account",
                )
                following = gr.Number(
                    label="following count",
                    precision=0, minimum=0,
                )

            social_media_checkboxes = gr.CheckboxGroup(
                label="social media behavior",
                choices=[
                    "posts a lot", "mostly a lurker", "stories person",
                    "feed poster", "has a spam/close friends account",
                ],
            )

            spam_friends_count = gr.Number(
                label="how many people are on their close friends / spam list?",
                minimum=0,
                visible=False,
                info="under 10 = very private   •   110+ = basically a second public account",
            )

            social_media_checkboxes.change(
                fn=lambda c: gr.update(visible="has a spam/close friends account" in c),
                inputs=social_media_checkboxes,
                outputs=spam_friends_count,
            )

            gr.HTML("""
            <div class="section-head">
              <span class="section-eyebrow">photo</span>
              <span style="font-size:10px;color:#C9B4B4;letter-spacing:0.12em">optional</span>
            </div>
            """)

            photo = gr.Image(
                label="drop a photo of them — profile pic, tagged photo, anything",
                type="filepath",
                sources=["upload", "clipboard"],
                height=172,
            )

            gr.HTML("""
            <p class="photo-note">
              analyzed locally using deepface + opencv — we look at expression,
              solo vs. group, eye contact, and background context.
            </p>
            """)

            with gr.Row(elem_classes=["mbti-submit"]):
                submit_btn = gr.Button("figure out their type ↗", variant="primary")

        # ── result column ────────────────────────────────────────────────────
        with gr.Column(elem_classes=["result-panel"]):
            output = gr.HTML("""
            <div class="result-placeholder">
              fill in a few fields<br>on the left, then<br>hit the button.
              <span style="font-family:'Playfair Display',serif;font-style:italic;
                           font-size:80px;color:#EDD5DC;line-height:1;
                           display:block;margin-top:12px;">?</span>
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
            followers, following, social_media_checkboxes, spam_friends_count, photo,
        ],
        outputs=output,
    )


if __name__ == "__main__":
    demo.launch(share=False)