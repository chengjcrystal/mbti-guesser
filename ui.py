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

def run_analysis(bio, captions, dms, essay, followers, following, num_posts, profile_photo, candid_photo):
    if not bio or not bio.strip():
        return (
            "<div class='error-msg'>drop in at least an instagram bio to get started ✦</div>",
            "", "", ""
        )
    try:
        mbti_type, final_scores, photo_signals = analyze(
            bio=bio,
            captions=captions,
            dms=dms,
            essay=essay,
            followers=int(followers) if followers else 0,
            following=int(following) if following else 0,
            num_posts=int(num_posts) if num_posts else 0,
            profile_photo_path=profile_photo,
            candid_photo_path=candid_photo
        )

        if not mbti_type:
            return "<div class='error-msg'>couldn't generate a result -- try adding more text.</div>", "", "", ""

        description = TYPE_DESCRIPTIONS.get(mbti_type, "")

        result_html = f"""
        <div class='result-reveal'>
            <div class='type-badge'>{mbti_type}</div>
            <div class='type-desc'>{description}</div>
        </div>
        """

        axis_labels = {"E_I": ("E", "I"), "N_S": ("N", "S"), "T_F": ("T", "F"), "J_P": ("J", "P")}
        breakdown_html = "<div class='breakdown-grid'>"
        for axis, (a, b) in axis_labels.items():
            scores = final_scores[axis]
            winner = scores["winner"]
            winner_score = scores[winner]
            loser = b if winner == a else a
            loser_score = scores[loser]
            breakdown_html += f"""
            <div class='axis-card'>
                <div class='axis-letters'>
                    <span class='letter {"active" if winner == a else "dim"}'>{a}</span>
                    <span class='vs'>vs</span>
                    <span class='letter {"active" if winner == b else "dim"}'>{b}</span>
                </div>
                <div class='bar-track'>
                    <div class='bar-fill' style='width:{winner_score}%'></div>
                </div>
                <div class='axis-score'>{winner} — {winner_score}% confidence</div>
            </div>
            """
        breakdown_html += "</div>"

        photo_html = ""
        if photo_signals:
            photo_html = "<div class='photo-signals'>"
            photo_html += f"<div class='signal-row'><span class='signal-label'>photo type</span><span class='signal-val'>{photo_signals.get('photo_type', 'unknown')}</span></div>"
            photo_html += f"<div class='signal-row'><span class='signal-label'>composition</span><span class='signal-val'>{photo_signals.get('solo_or_group', 'unknown')}</span></div>"
            photo_html += f"<div class='signal-row'><span class='signal-label'>vibe</span><span class='signal-val'>{photo_signals.get('photo_vibe', 'unknown')}</span></div>"
            photo_html += f"<div class='signal-row'><span class='signal-label'>tone</span><span class='signal-val'>{photo_signals.get('color_tone', 'unknown')}</span></div>"
            if photo_signals.get("face_detected"):
                photo_html += f"<div class='signal-row'><span class='signal-label'>emotion</span><span class='signal-val'>{photo_signals.get('dominant_emotion', 'unknown')}</span></div>"
            else:
                photo_html += "<div class='signal-row'><span class='signal-label'>face</span><span class='signal-val'>hidden, cartoon, or no face found</span></div>"
            photo_html += "</div>"

        return result_html, breakdown_html, photo_html, ""

    except Exception as e:
        return f"<div class='error-msg'>something went wrong: {str(e)}</div>", "", "", ""


custom_css = """
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400;1,700&family=DM+Sans:wght@300;400;500;600&display=swap');

/* reset */
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

/* hero */
.hero {
    text-align: center;
    padding: 80px 0 60px;
    animation: fadeUp 0.9s ease both;
}

.hero-eyebrow {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #9B4F5E;
    margin-bottom: 18px;
}

.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(64px, 10vw, 120px);
    font-weight: 900;
    line-height: 0.93;
    color: #1A1010;
    letter-spacing: -0.03em;
    margin-bottom: 22px;
}

.hero-title em {
    font-style: italic;
    color: #B8607A;
}

.hero-sub {
    font-size: 15px;
    font-weight: 400;
    color: #6B4A4A;
    max-width: 420px;
    margin: 0 auto;
    line-height: 1.75;
}

/* section rules -- label + extending line */
.section-label {
    display: flex;
    align-items: center;
    gap: 14px;
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: #9B4F5E;
    margin-bottom: 20px;
    /* no background, no border box -- just the label itself */
}

.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #DFC4C9;
}

/* inputs -- transparent bg so there's no white box */
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

/* labels */
.gradio-container label span {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 10px !important;
    font-weight: 600 !important;
    letter-spacing: 0.14em !important;
    color: #6B4A4A !important;
    text-transform: uppercase !important;
}

/* kill the default gradio form group backgrounds */
.gradio-container .form,
.gradio-container .gap,
.gradio-container .block,
.gradio-container .panel {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* image upload -- keep it minimal */
.gradio-container .upload-container,
.gradio-container [data-testid="image"] {
    border: 1.5px dashed #CBADB3 !important;
    border-radius: 10px !important;
    background: transparent !important;
    box-shadow: none !important;
}

/* analyze button */
.analyze-btn-wrap {
    text-align: center;
    padding: 40px 0 20px;
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

/* divider */
.divider {
    border: none;
    border-top: 1px solid #DFC4C9;
    margin: 48px 0;
}

/* result card */
.result-reveal {
    text-align: center;
    padding: 44px 0 28px;
    animation: fadeUp 0.6s ease both;
}

.type-badge {
    font-family: 'Playfair Display', serif;
    font-size: clamp(72px, 12vw, 140px);
    font-weight: 900;
    font-style: italic;
    color: #B8607A;
    line-height: 1;
    letter-spacing: -0.03em;
    animation: popIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

.type-desc {
    font-size: 15px;
    font-weight: 400;
    color: #6B4A4A;
    margin-top: 14px;
    letter-spacing: 0.01em;
}

/* axis grid */
.breakdown-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 14px;
    margin-top: 8px;
}

.axis-card {
    border: 1px solid #DFC4C9;
    border-radius: 14px;
    padding: 22px;
    /* no background fill -- matches page */
    animation: fadeUp 0.5s ease both;
}

.axis-letters {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 14px;
}

.letter {
    font-family: 'Playfair Display', serif;
    font-size: 26px;
    font-weight: 700;
    font-style: italic;
}
.letter.active { color: #B8607A; }
.letter.dim { color: #D4B4BA; }

.vs {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #BBA5A5;
}

.bar-track {
    height: 3px;
    background: #E8D0D4;
    border-radius: 100px;
    overflow: hidden;
    margin-bottom: 9px;
}

.bar-fill {
    height: 100%;
    background: #B8607A;
    border-radius: 100px;
    transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.axis-score {
    font-size: 11px;
    font-weight: 400;
    color: #9B7A7A;
    letter-spacing: 0.03em;
}

/* photo signals */
.photo-signals {
    border: 1px solid #DFC4C9;
    border-radius: 14px;
    padding: 22px;
    /* no bg fill here either */
    margin-top: 8px;
}

.signal-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 9px 0;
    border-bottom: 1px solid #EDD8DC;
    font-size: 12px;
}
.signal-row:last-child { border-bottom: none; }

.signal-label {
    font-size: 9px;
    font-weight: 600;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #9B7A7A;
}

.signal-val {
    color: #1A1010;
    font-weight: 400;
}

/* error */
.error-msg {
    text-align: center;
    font-size: 13px;
    color: #9B4F5E;
    padding: 32px;
}

/* results eyebrow label */
.results-header {
    font-family: 'Playfair Display', serif;
    font-size: 13px;
    font-style: italic;
    color: #9B4F5E;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
}

/* output boxes -- no gradio chrome */
.gradio-container .output-html {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    box-shadow: none !important;
}

/* animations */
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
    <div class='hero'>
        <div class='hero-eyebrow'>digital footprint analysis</div>
        <div class='hero-title'>read the<br><em>room.</em></div>
        <div class='hero-sub'>paste in someone's online presence. get a personality read. no quiz, just signal.</div>
    </div>
    """)

    with gr.Row():
        with gr.Column(scale=3):
            gr.HTML("<div class='section-label'>text signals</div>")
            bio = gr.Textbox(
                label="instagram bio ✦ required",
                placeholder="e.g.  living slowly, thinking deeply 🌿 | philosophy | coffee always",
                lines=2
            )
            captions = gr.Textbox(
                label="caption dump — optional",
                placeholder="paste 5-10 recent captions",
                lines=4
            )
            dms = gr.Textbox(
                label="texts or dms — optional",
                placeholder="paste some messages they sent you",
                lines=3
            )
            essay = gr.Textbox(
                label="personal writing — optional",
                placeholder="college essay, cover letter, anything longer form",
                lines=3
            )

        with gr.Column(scale=2):
            gr.HTML("<div class='section-label'>numeric signals</div>")
            with gr.Row():
                followers = gr.Number(label="followers", value=0)
                following = gr.Number(label="following", value=0)
            num_posts = gr.Number(label="number of posts", value=0)

            gr.HTML("<div class='section-label' style='margin-top:28px;'>photo signals — optional</div>")
            profile_photo = gr.Image(label="profile photo", type="filepath")
            candid_photo = gr.Image(label="candid or tagged photo", type="filepath")

    gr.HTML("<div class='analyze-btn-wrap'>")
    analyze_btn = gr.Button("analyze ↗", variant="primary")
    gr.HTML("</div>")

    gr.HTML("<hr class='divider'>")

    gr.HTML("<div class='results-header'>your read</div>")

    result_type = gr.HTML()

    with gr.Row():
        with gr.Column():
            gr.HTML("<div class='section-label'>axis confidence</div>")
            result_breakdown = gr.HTML()
        with gr.Column():
            gr.HTML("<div class='section-label'>photo read</div>")
            result_photo = gr.HTML()

    result_error = gr.HTML(visible=False)

    analyze_btn.click(
        fn=run_analysis,
        inputs=[bio, captions, dms, essay, followers, following, num_posts, profile_photo, candid_photo],
        outputs=[result_type, result_breakdown, result_photo, result_error]
    )

if __name__ == "__main__":
    demo.launch()