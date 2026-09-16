"""
ui.py: mbti guesser
Gradio handles all layout. CSS only touches colors, fonts, and custom HTML blocks.
"""

import pathlib
import gradio as gr
from app import predict_mbti

CSS = (pathlib.Path(__file__).parent / "styles.css").read_text()

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
        title, desc = "mixed signals", "a few axes didn't have enough signal, see the breakdown below."
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
            lean_cls  = "axis-lean-1" if r["winner"] == p0 else "axis-lean-2"
            ltr_cls   = f"axis-letter {lean_cls}"
            pct       = max(0.0, min(100.0, (r["confidence"] - 50) / 50 * 100))
            if r["winner"] == p0:
                bar_inner = (f'<div class="bar-half bar-half-left">'
                             f'<div class="bar-fill-left" style="width:{pct}%"></div></div>'
                             f'<div class="bar-half bar-half-right"></div>')
            else:
                bar_inner = (f'<div class="bar-half bar-half-left"></div>'
                             f'<div class="bar-half bar-half-right">'
                             f'<div class="bar-fill-right" style="width:{pct}%"></div></div>')

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
  <span class="result-eyebrow">predicted type</span>
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
    followers, social_media_checkboxes, spam_friends_count, photo,
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
            photo_results           = photo_results,
        )
    except Exception as e:
        print(f"prediction error: {e}")
        return '<div class="result-empty">having trouble right now, give it a moment and try again.</div>'

    if axis_results is None:
        return '<div class="result-empty">fill in at least a few fields to get a prediction.</div>'
    return format_results(mbti_type, axis_results)


# ── build a Soft theme that matches the palette ───────────────────────────────
theme = gr.themes.Soft(
    primary_hue=gr.themes.Color(
        c50="#F2F1FC", c100="#E5E2FA", c200="#CBC5F4", c300="#AEA4EC",
        c400="#8A7DE0", c500="#3D34B0", c600="#332B94", c700="#282178",
        c800="#1E195C", c900="#141140", c950="#0A0821",
    ),
    secondary_hue="emerald",
    neutral_hue="slate",
    font=gr.themes.GoogleFont("IBM Plex Sans"),
    font_mono=gr.themes.GoogleFont("IBM Plex Sans"),
).set(
    body_background_fill="#F3F4FA",
    body_background_fill_dark="#F3F4FA",
    block_background_fill="#FFFFFF",
    block_border_color="#E1E3EE",
    block_border_width="1px",
    block_radius="14px",
    block_shadow="none",
    block_label_text_size="sm",
    block_label_text_weight="600",
    block_label_text_color="#14172A",
    block_label_background_fill="transparent",
    block_label_border_width="0px",
    block_label_padding="0px",
    block_label_margin="0px",
    block_label_radius="0px",
    block_label_shadow="none",
    block_title_text_color="#14172A",
    block_title_background_fill="transparent",
    input_background_fill="#F3F4FA",
    input_border_color="#CBCEE0",
    input_border_color_focus="#3D34B0",
    input_shadow="none",
    input_shadow_focus="0 0 0 3px rgba(61,52,176,0.12)",
    input_radius="9px",
    checkbox_background_color="#FFFFFF",
    checkbox_border_color="#CBCEE0",
    checkbox_border_color_selected="#3D34B0",
    checkbox_background_color_selected="#3D34B0",
    checkbox_label_background_fill="#FFFFFF",
    checkbox_label_background_fill_hover="#ECEAFB",
    checkbox_label_background_fill_selected="#ECEAFB",
    checkbox_label_border_color="#CBCEE0",
    checkbox_label_border_color_hover="#3D34B0",
    checkbox_label_border_color_selected="#3D34B0",
    checkbox_label_text_color="#565B72",
    checkbox_label_text_color_selected="#3D34B0",
    button_primary_background_fill="#3D34B0",
    button_primary_background_fill_hover="#2F2890",
    button_primary_text_color="#FFFFFF",
    button_primary_border_color="transparent",
    button_large_radius="10px",
    button_large_padding="14px 32px",
    slider_color="#3D34B0",
    border_color_primary="#E1E3EE",
    color_accent="#3D34B0",
    color_accent_soft="#ECEAFB",
    link_text_color="#3D34B0",
    body_text_color="#14172A",
    body_text_color_subdued="#565B72",
)


# ── layout ────────────────────────────────────────────────────────────────────
with gr.Blocks(title="mbti guesser", css=CSS, theme=theme) as demo:

    gr.HTML("""
    <div class="mbti-hero">
      <span class="hero-eyebrow">mbti guesser</span>
      <h1 class="hero-title">who are they, <em>really?</em></h1>
      <p class="hero-sub">describe anyone and we'll figure out their mbti type.</p>
    </div>
    """)

    with gr.Column(elem_classes=["main-content"]):

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

        with gr.Group(elem_classes=["mbti-card"]):
            gr.HTML('<span class="section-label">how they text</span>')
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

        with gr.Group(elem_classes=["mbti-card"]):
            gr.HTML('<span class="section-label">social media</span>')
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

        with gr.Group(elem_classes=["mbti-card"]):
            gr.HTML('<span class="section-label">photo <span style="font-size:10px;color:#9296AC;letter-spacing:0.1em">optional</span></span>')
            photo = gr.Image(
                label="drop a photo of them",
                type="filepath",
                sources=["upload", "clipboard"],
                elem_classes=["photo-upload-wrap"],
            )
            gr.HTML('<p class="photo-note">expression, solo vs. group, eye contact, background context all analyzed locally.</p>')

        output = gr.HTML("")

        submit_btn = gr.Button("figure out their mbti ↗", variant="primary", size="lg")

    gr.HTML('<div class="mbti-footer">predictions use facebook/bart-large-mnli || axes marked "?" had insufficient signal</div>')

    submit_btn.click(
        fn=run_prediction,
        inputs=[
            spotify_artists, humor_types, punctuality, group_archetypes,
            what_they_talk_about, weekend_activities, text_length_slider,
            texting_style, stress_triggers, party_vibe, fav_media,
            followers, social_media_checkboxes, spam_friends_count, photo,
        ],
        outputs=output,
    )

if __name__ == "__main__":
    demo.launch(share=False)