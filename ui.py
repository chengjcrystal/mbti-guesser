"""
ui.py — mbti guesser
Gradio handles all layout. CSS only touches colors, fonts, and custom HTML blocks.
"""

import pathlib
import gradio as gr
from app import predict_mbti
from photo_analysis import analyze_photo

CSS = (pathlib.Path(__file__).parent / "styles.css").read_text()

# ── type data ─────────────────────────────────────────────────────────────────
MBTI_DESCRIPTIONS = {
    "INTJ": ("the architect",    "strategic, private, always three steps ahead. probably already knows what you're going to say."),
    "INTP": ("the logician",     "lives in their head, loves a rabbit hole. argues for fun and calls it curiosity."),
    "ENTJ": ("the commander",    "natural leader, extremely sure of themselves, not always gentle about it."),
    "ENTP": ("the debater",      "argues for fun, gets bored easily. devil's advocate as a personality."),
    "INFJ": ("the advocate",     "intense, private, somehow knows what you're thinking before you do."),
    "INFP": ("the mediator",     "idealistic, emotional, writes in their notes app at 2am. feels everything deeply."),
    "ENFJ": ("the protagonist",  "makes everyone feel seen, over-commits, cries at ads. checks in on you unprompted."),
    "ENFP": ("the campaigner",   "energetic, all over the place, somehow still the most magnetic person in the room."),
    "ISTJ": ("the logistician",  "reliable to a fault, shows love through acts of service. will send you a calendar invite."),
    "ISFJ": ("the defender",     "takes care of everyone, forgets themselves. remembers your coffee order."),
    "ESTJ": ("the executive",    "has a spreadsheet for everything. gets things done, no vibes required."),
    "ESFJ": ("the consul",       "genuinely warm, needs approval. throws the best parties and stress-cleans before you arrive."),
    "ISTP": ("the virtuoso",     "quiet but extremely competent. not big on feelings. fix-it person energy."),
    "ISFP": ("the adventurer",   "gentle, artistic, keeps real thoughts to themselves. excellent taste, won't brag."),
    "ESTP": ("the entrepreneur", "impulsive, charismatic, thrives on chaos they created."),
    "ESFP": ("the entertainer",  "the most fun person in the room, no plans, all vibes."),
}

AXIS_META = {
    "E_I": {"label": "energy",   "poles": ("E", "I"), "desc": ("extrovert", "introvert")},
    "N_S": {"label": "thinking", "poles": ("N", "S"), "desc": ("intuitive", "sensing")},
    "T_F": {"label": "deciding", "poles": ("T", "F"), "desc": ("thinker",   "feeler")},
    "J_P": {"label": "living",   "poles": ("J", "P"), "desc": ("judger",    "perceiver")},
}
AXIS_ORDER = ["E_I", "N_S", "T_F", "J_P"]


# ── rendering ─────────────────────────────────────────────────────────────────
def format_results(mbti_type, axis_results):
    if axis_results is None:
        return '<div class="result-empty">fill in a few more fields and try again.</div>'

    if "?" in mbti_type:
        title, desc = "mixed signals", "a few axes didn't have enough signal — see the breakdown below."
    else:
        title, desc = MBTI_DESCRIPTIONS.get(mbti_type, ("unknown type", "an unusual combination."))

    badges = "".join(
        f'<span class="{"type-letter-ambiguous" if c == "?" else "type-letter"}">{c}</span>'
        for c in mbti_type
    )

    bars = ""
    for i, axis in enumerate(AXIS_ORDER):
        r    = axis_results[axis]
        meta = AXIS_META[axis]
        p0, p1 = meta["poles"]

        if r["is_ambiguous"]:
            ltr        = "?"
            conf_txt   = f"only {r['gap']:.1f}pt gap"
            desc_txt   = "not enough signal"
            bar_inner  = '<div class="bar-center-tick"></div>'
            ltr_cls    = "axis-letter axis-ambiguous"
        else:
            ltr       = r["winner"]
            conf_txt  = f"{r['confidence']:.0f}%"
            desc_txt  = meta["desc"][meta["poles"].index(r["winner"])]
            ltr_cls   = "axis-letter"
            pct       = max(0.0, min(100.0, (r["confidence"] - 50) / 50 * 100))
            if r["winner"] == p0:
                bar_inner = (f'<div class="bar-half bar-half-left">'
                             f'<div class="bar-fill bar-fill-left" style="width:{pct}%"></div></div>'
                             f'<div class="bar-half bar-half-right"></div>')
            else:
                bar_inner = (f'<div class="bar-half bar-half-left"></div>'
                             f'<div class="bar-half bar-half-right">'
                             f'<div class="bar-fill bar-fill-right" style="width:{pct}%"></div></div>')

        bars += f"""
<div class="axis-row">
  <div class="axis-meta">
    <span class="axis-eyebrow">{meta['label']}</span>
    <span class="{ltr_cls}">{ltr}</span>
    <span class="axis-winner-desc">{desc_txt}</span>
    <span class="axis-conf">{conf_txt}</span>
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
  <div class="result-type-row">{badges}</div>
  <div class="result-title-label">{title}</div>
  <p class="result-desc">{desc}</p>
  <div class="result-divider"></div>
  <span class="axes-eyebrow">axis breakdown</span>
  {bars}
</div>"""


def run_prediction(
    spotify_artists, humor_types, punctuality, group_archetypes,
    what_they_talk_about, weekend_activities, text_length_slider,
    texting_style, stress_triggers, party_vibe, fav_media,
    followers, following, social_media_checkboxes, spam_friends_count, photo,
):
    photo_results = None
    if photo is not None:
        try:
            photo_results = analyze_photo(photo)
        except Exception as e:
            print(f"photo analysis error: {e}")

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
        following               = following,
        social_media_checkboxes = social_media_checkboxes or [],
        spam_friends_count      = spam_friends_count,
        photo_results           = photo_results,
    )
    if axis_results is None:
        return '<div class="result-empty">fill in at least a few fields to get a prediction.</div>'
    return format_results(mbti_type, axis_results)


# ── build a Soft theme that matches the palette ───────────────────────────────
theme = gr.themes.Soft(
    primary_hue=gr.themes.Color(
        c50="#fdf0f3", c100="#f9dce3", c200="#f2bac6", c300="#e896a9",
        c400="#dc738d", c500="#C2758A", c600="#a85d72", c700="#8c475a",
        c800="#703344", c900="#54202f", c950="#380f1c",
    ),
    secondary_hue="rose",
    neutral_hue="stone",
    font=gr.themes.GoogleFont("DM Sans"),
    font_mono=gr.themes.GoogleFont("DM Sans"),
).set(
    body_background_fill="#F4EDE4",
    body_background_fill_dark="#F4EDE4",
    block_background_fill="#FDFAF7",
    block_border_color="#EDD5DC",
    block_border_width="1px",
    block_radius="16px",
    block_shadow="none",
    block_label_text_size="sm",
    block_label_text_weight="500",
    block_label_text_color="#1E1414",
    input_background_fill="#FFFFFF",
    input_border_color="#DEC8CE",
    input_border_color_focus="#C2758A",
    input_shadow="none",
    input_shadow_focus="0 0 0 3px rgba(194,117,138,0.12)",
    input_radius="10px",
    checkbox_background_color="#FFFFFF",
    checkbox_border_color="#DEC8CE",
    checkbox_border_color_selected="#C2758A",
    checkbox_background_color_selected="#C2758A",
    checkbox_label_background_fill="#FFFFFF",
    checkbox_label_background_fill_hover="#F7EBF0",
    checkbox_label_background_fill_selected="#C2758A",
    checkbox_label_border_color="#DEC8CE",
    checkbox_label_border_color_hover="#C2758A",
    checkbox_label_border_color_selected="#C2758A",
    checkbox_label_text_color="#1E1414",
    checkbox_label_text_color_selected="#FFFFFF",
    button_primary_background_fill="#1E1414",
    button_primary_background_fill_hover="#C2758A",
    button_primary_text_color="#F4EDE4",
    button_primary_border_color="transparent",
    button_large_radius="100px",
    button_large_padding="16px 32px",
    slider_color="#C2758A",
    border_color_primary="#EDD5DC",
    color_accent="#C2758A",
    color_accent_soft="#F7EBF0",
    link_text_color="#C2758A",
    body_text_color="#1E1414",
    body_text_color_subdued="#6B4C4C",
)


# ── layout ────────────────────────────────────────────────────────────────────
with gr.Blocks(title="mbti guesser", css=CSS, theme=theme) as demo:

    gr.HTML("""
    <div class="mbti-hero">
      <span class="hero-eyebrow">✦ personality decoder</span>
      <h1 class="hero-title">who are they, <em>really?</em></h1>
      <p class="hero-sub">no quiz. tell me about your friend — or your crush — and we'll figure out their type.</p>
    </div>
    """)

    with gr.Row(equal_height=False):

        with gr.Column(scale=3):

            with gr.Group():
                gr.HTML('<span class="section-label">the basics</span>')
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
                        "The Mom (plans everything)", "The Chaos Agent",
                        "The Researcher (googles before anyone asks)", "The Therapist Friend",
                        "The Flake", "The Hype Person", "The Background One", "The Realist",
                    ],
                    info="can pick more than one",
                )

            with gr.Group():
                gr.HTML('<span class="section-label">what they\'re like</span>')
                what_they_talk_about = gr.Textbox(
                    label="what do they talk about most?",
                    placeholder="the show they're obsessed with, their job, conspiracy theories…",
                    lines=2,
                )
                weekend_activities = gr.Textbox(
                    label="how do they spend their weekends?",
                    placeholder="hiking alone, hosting people, sleeping until noon…",
                    lines=2,
                )
                stress_triggers = gr.Textbox(
                    label="what stresses them out?",
                    placeholder="last-minute changes, conflict, falling behind…",
                    lines=2,
                )
                party_vibe = gr.Textbox(
                    label="vibe at parties — or what kind of drunk are they?",
                    placeholder="disappears to talk to one person, center of everything, goes home early…",
                    lines=2,
                    info="best indirect introvert/extrovert signal",
                )
                fav_media = gr.Textbox(
                    label="favorite shows, movies, or books",
                    placeholder="succession, studio ghibli, crime podcasts, philosophy youtube…",
                    lines=2,
                )

            with gr.Group():
                gr.HTML('<span class="section-label">how they text</span>')
                text_length_slider = gr.Slider(
                    minimum=1, maximum=5, step=1, value=3,
                    label="how long are their texts?",
                    info="1 = one-word replies   •   5 = full essays",
                )
                texting_style = gr.CheckboxGroup(
                    label="texting style",
                    choices=["quick replies", "slow replies", "emoji heavy", "no emoji",
                             "all lowercase", "uses punctuation", "leaves people on read"],
                )

            with gr.Group():
                gr.HTML('<span class="section-label">social media</span>')
                with gr.Row():
                    followers = gr.Number(label="follower count", precision=0, minimum=0, info="main account")
                    following = gr.Number(label="following count", precision=0, minimum=0)
                social_media_checkboxes = gr.CheckboxGroup(
                    label="social media behavior",
                    choices=["posts a lot", "mostly a lurker", "stories person",
                             "feed poster", "has a spam/close friends account"],
                )
                spam_friends_count = gr.Number(
                    label="close friends / spam list size",
                    minimum=0, visible=False,
                    info="under 10 = very private   •   110+ = basically a second public account",
                )
                social_media_checkboxes.change(
                    fn=lambda c: gr.update(visible="has a spam/close friends account" in c),
                    inputs=social_media_checkboxes,
                    outputs=spam_friends_count,
                )

            with gr.Group():
                gr.HTML('<span class="section-label">photo <span style="font-size:10px;color:#C9B4B4;letter-spacing:0.1em">optional</span></span>')
                photo = gr.Image(
                    label="drop a photo of them",
                    type="filepath", sources=["upload", "clipboard"], height=160,
                )
                gr.HTML('<p class="photo-note">analyzed locally — expression, solo vs. group, eye contact, background context.</p>')

            submit_btn = gr.Button("figure out their type ↗", variant="primary", size="lg")

        with gr.Column(scale=2):
            output = gr.HTML("""
            <div class="result-placeholder">
              fill in a few fields on the left,<br>then hit the button.<br><br>
              <span style="font-family:'Playfair Display',serif;font-style:italic;font-size:72px;color:#EDD5DC;line-height:1">?</span>
            </div>
            """)

    gr.HTML('<div class="mbti-footer">predictions use facebook/bart-large-mnli · axes marked "?" had insufficient signal</div>')

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