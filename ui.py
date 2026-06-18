"""
ui.py

gradio interface for the mbti guesser. no quiz, no personality test vibes,
just tell me about your friend and we'll figure it out.
"""

import gradio as gr
from app import predict_mbti
from photo_analysis import analyze_photo

# descriptions for all 16 types
MBTI_DESCRIPTIONS = {
    "INTJ": "the architect — strategic, private, and always three steps ahead.",
    "INTP": "the logician — lives in their head, loves a rabbit hole, skeptical of most things.",
    "ENTJ": "the commander — natural leader, very sure of themselves, not always nice about it.",
    "ENTP": "the debater — argues for fun, gets bored easily, full of ideas they won't follow through on.",
    "INFJ": "the advocate — intense, private, somehow knows what you're thinking before you do.",
    "INFP": "the mediator — idealistic, emotional, writes in their notes app at 2am.",
    "ENFJ": "the protagonist — makes everyone feel seen, over-commits to plans, cries at ads.",
    "ENFP": "the campaigner — energetic, all over the place, starts things they don't finish.",
    "ISTJ": "the logistician — reliable to a fault, rule-follower, shows love through acts of service.",
    "ISFJ": "the defender — takes care of everyone, forgets to take care of themselves.",
    "ESTJ": "the executive — has a spreadsheet for everything, does not understand why you don't.",
    "ESFJ": "the consul — the friend group mom, needs approval, genuinely warm.",
    "ISTP": "the virtuoso — quiet but mechanically gifted, not big on feelings, very competent.",
    "ISFP": "the adventurer — gentle, artistic, keeps their real thoughts to themselves.",
    "ESTP": "the entrepreneur — impulsive, charismatic, probably dares you to do stuff.",
    "ESFP": "the entertainer — the most fun person in the room, no plans, all vibes.",
}

AXIS_LABELS = {
    "E_I": ("E", "I", "extraversion vs introversion"),
    "N_S": ("N", "S", "intuition vs sensing"),
    "T_F": ("T", "F", "thinking vs feeling"),
    "J_P": ("J", "P", "judging vs perceiving"),
}

def format_results(mbti_type, axis_results):
    """turn the prediction output into readable gradio markdown."""
    if axis_results is None:
        return "## couldn't get a prediction\n\nfill in a few more fields and try again!"

    # header
    lines = []

    # type badge
    type_display = mbti_type if "?" not in mbti_type else mbti_type
    desc = MBTI_DESCRIPTIONS.get(mbti_type, "a rare or ambiguous type, interesting.")

    lines.append(f"# {type_display}")
    if mbti_type in MBTI_DESCRIPTIONS:
        lines.append(f"*{desc}*")
    else:
        lines.append(f"*some axes were ambiguous, see breakdown below.*")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### axis breakdown")
    lines.append("")

    axis_order = ["E_I", "N_S", "T_F", "J_P"]
    for axis in axis_order:
        r = axis_results[axis]
        first_key, second_key, axis_name = AXIS_LABELS[axis]

        if r["is_ambiguous"]:
            lines.append(
                f"**{first_key}/{second_key}** ({axis_name}): **?** — "
                f"not enough signal to call this one (gap: {r['gap']:.1f}pts)"
            )
        else:
            winner = r["winner"]
            conf = r["confidence"]
            lines.append(
                f"**{first_key}/{second_key}** ({axis_name}): **{winner}** — {conf:.1f}% confidence"
            )

    return "\n".join(lines)


def run_prediction(
    spotify_artists,
    humor_types,
    punctuality,
    group_archetypes,
    what_they_talk_about,
    weekend_activities,
    text_length_slider,
    texting_style,
    stress_triggers,
    party_vibe,
    fav_media,
    followers,
    following,
    social_media_checkboxes,
    photo
):
    # handle photo if provided
    photo_results = None
    if photo is not None:
        try:
            photo_results = analyze_photo(photo)
        except Exception as e:
            print(f"photo analysis errored: {e}")

    # run prediction
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
        photo_results=photo_results
    )

    if axis_results is None:
        return "fill in at least a few fields to get a prediction!"

    return format_results(mbti_type, axis_results)


# ----- BUILDING INTERFACE -----

with gr.Blocks(
    title="mbti guesser",
    theme=gr.themes.Soft(),
    css="""
    .gradio-container { max-width: 860px !important; margin: 0 auto; }
    h1 { font-size: 2rem !important; }
    .result-box { font-size: 1.05rem; line-height: 1.7; }
    """
) as demo:
    gr.Markdown(
        """
        # mbti guesser
        tell me about your friend (or your crush, no judgment). no quiz, no personality test.
        just describe them and we'll figure out their type.
        """
    )

    with gr.Row():
        with gr.Column(scale=2):

            gr.Markdown("### the basics")

            spotify_artists = gr.Textbox(
                label="spotify top artists",
                placeholder="e.g. mitski, brockhampton, clairo, glass animals",
                info="their music taste says a lot; what are they always listening to?"
            )

            humor_types = gr.CheckboxGroup(
                label="their humor",
                choices=["dry", "chaotic", "wholesome", "dark", "sarcastic", "surreal", "self-deprecating"],
                info="check everything that fits"
            )

            punctuality = gr.Radio(
                label="early, on time, or always late?",
                choices=["always early", "on time", "always late"],
                info="their default setting"
            )

            group_archetypes = gr.CheckboxGroup(
                label="what's their role in the friend group?",
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

            gr.Markdown("### what they're like")

            what_they_talk_about = gr.Textbox(
                label="what do they talk about most?",
                placeholder="e.g. theories about the show they're watching, local drama, their job, philosophy",
                lines=2
            )

            weekend_activities = gr.Textbox(
                label="how do they spend their weekends?",
                placeholder="e.g. hiking alone, hosting people, working on a project, sleeping, random errands",
                lines=2
            )

            stress_triggers = gr.Textbox(
                label="what stresses them out?",
                placeholder="e.g. last minute changes, conflict, being behind, too many obligations",
                lines=2
            )

            party_vibe = gr.Textbox(
                label="vibe at parties / what kind of drunk are they?",
                placeholder="e.g. disappears to talk to one person all night, the center of everything, goes home early",
                lines=2,
                info="best indirect intro/extrovert signal"
            )

            fav_media = gr.Textbox(
                label="favorite shows, movies, or books",
                placeholder="e.g. succession, studio ghibli, crime podcasts, philosophy youtube",
                lines=2
            )

            gr.Markdown("### how they text")

            text_length_slider = gr.Slider(
                minimum=1,
                maximum=5,
                step=1,
                value=3,
                label="how long are their texts?",
                info="1 = one-word replies  |  5 = full essays"
            )

            texting_style = gr.CheckboxGroup(
                label="texting style",
                choices=[
                    "quick replies",
                    "slow replies",
                    "emoji heavy",
                    "no emoji",
                    "all lowercase",
                    "uses punctuation",
                    "leaves people on read"
                ]
            )

            gr.Markdown("### social media")

            with gr.Row():
                followers = gr.Number(
                    label="follower count",
                    precision=0,
                    minimum=0,
                    info="on their main account"
                )
                following = gr.Number(
                    label="following count",
                    precision=0,
                    minimum=0
                )

            social_media_checkboxes = gr.CheckboxGroup(
                label="social media behavior",
                choices=[
                    "posts a lot",
                    "mostly a lurker",
                    "stories person",
                    "feed poster",
                    "has a spam/close friends account"
                ]
            )

            # shows up only if they checked the spam account box
            spam_friends_count = gr.Number(
                label="how many people are on their close friends/spam list?",
                minimum=0,
                visible=False,
                info="under 10 = very private, 110+ = basically a second public account"
            )

            # toggle the count input based on whether spam account is checked
            social_media_checkboxes.change(
                fn=lambda choices: gr.update(visible="has a spam/close friends account" in choices),
                inputs=social_media_checkboxes,
                outputs=spam_friends_count
            )

            gr.Markdown("### photo (optional)")

            photo = gr.Image(
                label="drop a photo of them: profile pic, tagged photo, anything works",
                type="filepath",
                sources=["upload", "clipboard"],
                height=200
            )

            gr.Markdown(
                "_photo is analyzed locally using deepface and opencv. "
                "we look at facial expression, whether it's a group or solo photo, "
                "and background context._"
            )

            submit_btn = gr.Button("figure out their type", variant="primary", size="lg")

        with gr.Column(scale=1):
            gr.Markdown("### result")
            output = gr.Markdown(
                value="*fill in the fields and hit the button.*",
                elem_classes=["result-box"]
            )

    submit_btn.click(
        fn=run_prediction,
        inputs=[
            spotify_artists,
            humor_types,
            punctuality,
            group_archetypes,
            what_they_talk_about,
            weekend_activities,
            text_length_slider,
            texting_style,
            stress_triggers,
            party_vibe,
            fav_media,
            followers,
            following,
            social_media_checkboxes,
            photo
        ],
        outputs=output
    )

    gr.Markdown(
        """
        ---
        *predictions are based on zero-shot classification using facebook/bart-large-mnli.
        if an axis shows "?" it means the signal wasn't strong enough to call it either way.*
        """
    )


if __name__ == "__main__":
    demo.launch(share=False)