import gradio as gr
from app import analyze

TYPE_DESCRIPTIONS = {
    "INTJ": "the architect — strategic, private, driven by long-term vision.",
    "INTP": "the thinker — logical, curious, lives entirely inside their own head.",
    "ENTJ": "the commander — decisive, ambitious, natural at taking charge.",
    "ENTP": "the debater — quick-witted, loves ideas, always playing devil's advocate.",
    "INFJ": "the advocate — deeply empathetic, idealistic, intense inner world.",
    "INFP": "the mediator — values-driven, creative, feels everything deeply.",
    "ENFJ": "the protagonist — warm, charismatic, genuinely invested in people.",
    "ENFP": "the campaigner — enthusiastic, imaginative, sees potential everywhere.",
    "ISTJ": "the logistician — reliable, detail-oriented, gets things done quietly.",
    "ISFJ": "the defender — caring, loyal, remembers everything about everyone.",
    "ESTJ": "the executive — organized, traditional, natural at running things.",
    "ESFJ": "the consul — warm, social, puts everyone else first.",
    "ISTP": "the virtuoso — calm under pressure, hands-on, figures things out by doing.",
    "ISFP": "the adventurer — gentle, artistic, lives fully in the present.",
    "ESTP": "the entrepreneur — bold, observant, learns by jumping in.",
    "ESFP": "the entertainer — spontaneous, fun, lights up every room.",
}

PINK = "#B8607A"
PINK_DARK = "#9B4F5E"
CREAM = "#F5EDE3"
BROWN = "#6B4A4A"
NEAR_BLACK = "#1A1010"
BORDER = "#DFC4C9"
BORDER_INPUT = "#CBADB3"

def section_label(text, extra_style=""):
    return f"""
    <div style="display:flex;align-items:center;gap:14px;margin-bottom:20px;{extra_style}">
        <span style="font-size:9px;font-weight:600;letter-spacing:0.22em;text-transform:uppercase;color:{PINK_DARK};white-space:nowrap;font-family:'DM Sans',sans-serif;">{text}</span>
        <div style="flex:1;height:1px;background:{BORDER};"></div>
    </div>
    """

def run_analysis(bio, captions, dms, music, opinions, followers, following, profile_photo):
    if not bio or not bio.strip():
        return (
            f"<div style='text-align:center;font-size:13px;color:{PINK_DARK};padding:32px;font-family:DM Sans,sans-serif;'>drop in at least an instagram bio to get started ✦</div>",
            "", "", ""
        )
    try:
        mbti_type, final_scores, photo_signals = analyze(
            bio=bio,
            captions=captions,
            dms=dms,
            music=music,
            opinions=opinions,
            followers=int(followers) if followers else 0,
            following=int(following) if following else 0,
            profile_photo_path=profile_photo,
        )

        if not mbti_type:
            return f"<div style='text-align:center;font-size:13px;color:{PINK_DARK};padding:32px;'>couldn't generate a result -- try adding more text.</div>", "", "", ""

        description = TYPE_DESCRIPTIONS.get(mbti_type, "")

        result_html = f"""
        <div style='text-align:center;padding:44px 0 28px;'>
            <div style='font-family:"Playfair Display",serif;font-size:clamp(72px,12vw,140px);font-weight:900;font-style:italic;color:{PINK};line-height:1;letter-spacing:-0.03em;'>{mbti_type}</div>
            <div style='font-size:15px;font-weight:400;color:{BROWN};margin-top:14px;letter-spacing:0.01em;font-family:"DM Sans",sans-serif;'>{description}</div>
        </div>
        """

        axis_labels = {"E_I": ("E", "I"), "N_S": ("N", "S"), "T_F": ("T", "F"), "J_P": ("J", "P")}
        breakdown_html = "<div style='display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin-top:8px;'>"
        for axis, (a, b) in axis_labels.items():
            scores = final_scores[axis]
            winner = scores["winner"]
            winner_score = scores[winner]
            loser = b if winner == a else a
            a_color = PINK if winner == a else "#D4B4BA"
            b_color = PINK if winner == b else "#D4B4BA"
            breakdown_html += f"""
            <div style='border:1px solid {BORDER};border-radius:14px;padding:22px;'>
                <div style='display:flex;align-items:center;gap:12px;margin-bottom:14px;'>
                    <span style='font-family:"Playfair Display",serif;font-size:26px;font-weight:700;font-style:italic;color:{a_color};'>{a}</span>
                    <span style='font-size:9px;font-weight:600;letter-spacing:0.16em;text-transform:uppercase;color:#BBA5A5;font-family:"DM Sans",sans-serif;'>vs</span>
                    <span style='font-family:"Playfair Display",serif;font-size:26px;font-weight:700;font-style:italic;color:{b_color};'>{b}</span>
                </div>
                <div style='height:3px;background:#E8D0D4;border-radius:100px;overflow:hidden;margin-bottom:9px;'>
                    <div style='height:100%;width:{winner_score}%;background:{PINK};border-radius:100px;'></div>
                </div>
                <div style='font-size:11px;font-weight:400;color:#9B7A7A;letter-spacing:0.03em;font-family:"DM Sans",sans-serif;'>{winner} — {winner_score}% confidence</div>
            </div>
            """
        breakdown_html += "</div>"

        photo_html = ""
        if photo_signals:
            def row(label, val):
                return f"<div style='display:flex;justify-content:space-between;align-items:center;padding:9px 0;border-bottom:1px solid #EDD8DC;font-size:12px;font-family:DM Sans,sans-serif;'><span style='font-size:9px;font-weight:600;letter-spacing:0.16em;text-transform:uppercase;color:#9B7A7A;'>{label}</span><span style='color:{NEAR_BLACK};font-weight:400;'>{val}</span></div>"

            photo_html = f"<div style='border:1px solid {BORDER};border-radius:14px;padding:22px;margin-top:8px;'>"
            photo_html += row("photo type", photo_signals.get("photo_type", "unknown"))
            photo_html += row("composition", photo_signals.get("solo_or_group", "unknown"))
            photo_html += row("vibe", photo_signals.get("photo_vibe", "unknown"))
            photo_html += row("tone", photo_signals.get("color_tone", "unknown"))
            if photo_signals.get("face_detected"):
                photo_html += row("emotion", photo_signals.get("dominant_emotion", "unknown"))
            else:
                photo_html += row("face", "hidden, cartoon, or no face found")
            photo_html = photo_html.rstrip("</div>") + "</div>"
            photo_html += "</div>"

        return result_html, breakdown_html, photo_html, ""

    except Exception as e:
        return f"<div style='text-align:center;font-size:13px;color:{PINK_DARK};padding:32px;'>something went wrong: {str(e)}</div>", "", "", ""


custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400;1,700&family=DM+Sans:wght@300;400;500;600&display=swap');

* { box-sizing: border-box; margin: 0; padding: 0; }

body, .gradio-container {
    background-color: #F5EDE3 !important;
    font-family: 'DM Sans', sans-serif !important;
    color: #1A1010 !important;
}

.gradio-container > .main > .wrap {
    max-width: 1100px;
    margin: 0 auto;
    padding: 0 2rem;
}

footer { display: none !important; }

.gradio-container .form,
.gradio-container .gap,
.gradio-container .block,
.gradio-container .panel,
.gradio-container .wrap,
.gradio-container .border-none,
.gradio-container .bg-white,
.gradio-container .gr-box,
.gradio-container .gr-panel {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

.gradio-container textarea,
.gradio-container input[type=number],
.gradio-container input[type=text] {
    background: transparent !important;
    border: 1.5px solid #CBADB3 !important;
    border-radius: 10px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    color: #1A1010 !important;
    padding: 13px 15px !important;
    transition: border-color 0.2s ease !important;
    box-shadow: none !important;
}

.gradio-container textarea:focus,
.gradio-container input:focus {
    border-color: #B8607A !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(184, 96, 122, 0.1) !important;
}

.gradio-container label span,
.gradio-container .label-wrap span {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.14em !important;
    color: #6B4A4A !important;
    text-transform: uppercase !important;
}

.gradio-container .upload-container,
.gradio-container [data-testid="image"] {
    border: 1.5px dashed #CBADB3 !important;
    border-radius: 10px !important;
    background: transparent !important;
    box-shadow: none !important;
}

.gradio-container button.primary {
    background: #1A1010 !important;
    color: #F5EDE3 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 100px !important;
    padding: 17px 52px !important;
    cursor: pointer !important;
    transition: all 0.25s ease !important;
    box-shadow: none !important;
}

.gradio-container button.primary:hover {
    background: #B8607A !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 28px rgba(184, 96, 122, 0.3) !important;
}

.gradio-container .output-html,
.gradio-container [data-testid="html"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}

@keyframes fadeUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes popIn {
    from { opacity: 0; transform: scale(0.75); }
    to { opacity: 1; transform: scale(1); }
}
"""

with gr.Blocks(css=custom_css, title="mbti guesser") as demo:

    gr.HTML("""
    <div style='text-align:center;padding:80px 0 60px;animation:fadeUp 0.9s ease both;'>
        <div style='font-size:10px;font-weight:600;letter-spacing:0.22em;text-transform:uppercase;color:#9B4F5E;margin-bottom:18px;font-family:"DM Sans",sans-serif;'>digital footprint analysis</div>
        <div style='font-family:"Playfair Display",serif;font-size:clamp(64px,10vw,120px);font-weight:900;line-height:0.93;color:#1A1010;letter-spacing:-0.03em;margin-bottom:22px;'>read the<br><em style="font-style:italic;color:#B8607A;">room.</em></div>
        <div style='font-size:15px;font-weight:400;color:#6B4A4A;max-width:420px;margin:0 auto;line-height:1.75;font-family:"DM Sans",sans-serif;'>paste in someone's online presence. get a personality read. no quiz, just signal.</div>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=3):
            gr.HTML(section_label("text signals"))

            bio = gr.Textbox(
                label="instagram bio ✦ required",
                placeholder="she/her | manifesting",
                lines=2
            )
            captions = gr.Textbox(
                label="recent captions",
                placeholder="paste 5-10 captions",
                lines=4
            )
            dms = gr.Textbox(
                label="texts or dms",
                placeholder="paste messages sent",
                lines=3
            )

            gr.HTML(section_label("more signals", "margin-top:28px;"))

            music = gr.Textbox(
                label="spotify or music taste",
                placeholder="top artists, a playlist name, wrapped screenshot description",
                lines=2
            )
            opinions = gr.Textbox(
                label="twitter, reddit, or any unfiltered takes",
                placeholder="tweets, reddit comments, discord rants",
                lines=3
            )

        with gr.Column(scale=2):
            gr.HTML(section_label("the numbers"))

            with gr.Row():
                followers = gr.Number(label="followers", value=0)
                following = gr.Number(label="following", value=0)

            gr.HTML(section_label("profile photo — optional", "margin-top:28px;"))
            profile_photo = gr.Image(label="profile photo", type="filepath")

    gr.HTML("<div style='text-align:center;padding:40px 0 20px;'>")
    analyze_btn = gr.Button("analyze ↗", variant="primary")
    gr.HTML("</div>")

    gr.HTML("<hr style='border:none;border-top:1px solid #DFC4C9;margin:48px 0;'>")

    gr.HTML(f"<div style='font-family:\"Playfair Display\",serif;font-size:13px;font-style:italic;color:{PINK_DARK};letter-spacing:0.04em;margin-bottom:4px;'>your read</div>")

    result_type = gr.HTML()

    with gr.Row():
        with gr.Column():
            gr.HTML(section_label("axis confidence"))
            result_breakdown = gr.HTML()
        with gr.Column():
            gr.HTML(section_label("photo read"))
            result_photo = gr.HTML()

    result_error = gr.HTML(visible=False)

    analyze_btn.click(
        fn=run_analysis,
        inputs=[bio, captions, dms, music, opinions, followers, following, profile_photo],
        outputs=[result_type, result_breakdown, result_photo, result_error]
    )

if __name__ == "__main__":
    demo.launch()