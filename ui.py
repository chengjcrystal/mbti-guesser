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
            return "<div class='error-msg'>couldn't generate a result — try adding more text.</div>", "", "", ""

        description = TYPE_DESCRIPTIONS.get(mbti_type, "")

        # build result card html
        result_html = f"""
        <div class='result-reveal'>
            <div class='type-badge'>{mbti_type}</div>
            <div class='type-desc'>{description}</div>
        </div>
        """

        # axis breakdown
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

        # photo signals
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
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400;1,700&family=DM+Sans:wght@300;400;500&display=swap');

/* base reset */
* { box-sizing: border-box; margin: 0; padding: 0; }

body, .gradio-container {
    background-color: #F7F0E6 !important;
    font-family: 'DM Sans', sans-serif !important;
    color: #2D1F1F !important;
}

/* hide gradio chrome we don't need */
.gradio-container > .main > .wrap { max-width: 1100px; margin: 0 auto; padding: 0 2rem; }
footer { display: none !important; }

/* hero section */
.hero {
    text-align: center;
    padding: 80px 0 60px;
    animation: fadeUp 0.9s ease both;
}

.hero-eyebrow {
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: #C97D8A;
    margin-bottom: 20px;
}

.hero-title {
    font-family: 'Playfair Display', serif;
    font-size: clamp(64px, 10vw, 120px);
    font-weight: 900;
    line-height: 0.95;
    color: #2D1F1F;
    letter-spacing: -0.02em;
    margin-bottom: 24px;
}

.hero-title em {
    font-style: italic;
    color: #C97D8A;
}

.hero-sub {
    font-family: 'DM Sans', sans-serif;
    font-size: 16px;
    font-weight: 300;
    color: #7A5C5C;
    max-width: 480px;
    margin: 0 auto 0;
    line-height: 1.7;
}

/* section labels */
.section-label {
    font-family: 'DM Sans', sans-serif;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #C97D8A;
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid #E8C4CC;
}

/* input card panels */
.input-panel {
    background: #FDF8F3;
    border: 1px solid #EDD8DC;
    border-radius: 20px;
    padding: 32px;
    margin-bottom: 20px;
    transition: box-shadow 0.2s ease;
}
.input-panel:hover { box-shadow: 0 8px 40px rgba(201, 125, 138, 0.12); }

/* override gradio input styles */
.gradio-container textarea,
.gradio-container input[type=number],
.gradio-container input[type=text] {
    background: #F7F0E6 !important;
    border: 1.5px solid #E8C4CC !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    color: #2D1F1F !important;
    padding: 14px 16px !important;
    transition: border-color 0.2s ease !important;
}
.gradio-container textarea:focus,
.gradio-container input:focus {
    border-color: #C97D8A !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(201, 125, 138, 0.12) !important;
}

/* labels */
.gradio-container label span {
    font-family: 'DM Sans', sans-serif !important;
    font-size: 12px !important;
    font-weight: 500 !important;
    letter-spacing: 0.05em !important;
    color: #7A5C5C !important;
    text-transform: uppercase !important;
}

/* number inputs row */
.nums-row { display: flex; gap: 16px; }
.nums-row > * { flex: 1; }

/* analyze button */
.analyze-btn-wrap { text-align: center; padding: 40px 0 20px; }
.gradio-container button.primary {
    background: #2D1F1F !important;
    color: #F7F0E6 !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    border: none !important;
    border-radius: 100px !important;
    padding: 18px 52px !important;
    cursor: pointer !important;
    transition: all 0.25s ease !important;
}
.gradio-container button.primary:hover {
    background: #C97D8A !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 32px rgba(201, 125, 138, 0.35) !important;
}

/* divider */
.divider {
    border: none;
    border-top: 1px solid #EDD8DC;
    margin: 48px 0;
}

/* result reveal */
.result-reveal {
    text-align: center;
    padding: 48px 0 32px;
    animation: fadeUp 0.6s ease both;
}

.type-badge {
    font-family: 'Playfair Display', serif;
    font-size: clamp(72px, 12vw, 140px);
    font-weight: 900;
    font-style: italic;
    color: #C97D8A;
    line-height: 1;
    letter-spacing: -0.03em;
    animation: popIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}

.type-desc {
    font-family: 'DM Sans', sans-serif;
    font-size: 16px;
    font-weight: 300;
    color: #7A5C5C;
    margin-top: 16px;
    letter-spacing: 0.02em;
}

/* axis breakdown grid */
.breakdown-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 16px;
    margin-top: 8px;
}

.axis-card {
    background: #FDF8F3;
    border: 1px solid #EDD8DC;
    border-radius: 16px;
    padding: 24px;
    animation: fadeUp 0.5s ease both;
}

.axis-letters {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
}

.letter {
    font-family: 'Playfair Display', serif;
    font-size: 28px;
    font-weight: 700;
    font-style: italic;
}
.letter.active { color: #C97D8A; }
.letter.dim { color: #D4B8BC; }

.vs {
    font-family: 'DM Sans', sans-serif;
    font-size: 10px;
    font-weight: 500;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #BBA8A8;
}

.bar-track {
    height: 4px;
    background: #EDD8DC;
    border-radius: 100px;
    overflow: hidden;
    margin-bottom: 10px;
}

.bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #E8A4B0, #C97D8A);
    border-radius: 100px;
    transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.axis-score {
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    font-weight: 400;
    color: #A08080;
    letter-spacing: 0.03em;
}

/* photo signals */
.photo-signals {
    background: #FDF8F3;
    border: 1px solid #EDD8DC;
    border-radius: 16px;
    padding: 24px;
    margin-top: 8px;
}

.signal-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #EDD8DC;
    font-family: 'DM Sans', sans-serif;
    font-size: 13px;
}
.signal-row:last-child { border-bottom: none; }

.signal-label {
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-size: 10px;
    color: #A08080;
}

.signal-val {
    color: #2D1F1F;
    font-weight: 300;
}

/* error */
.error-msg {
    text-align: center;
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    color: #C97D8A;
    padding: 32px;
}

/* results section label */
.results-header {
    font-family: 'Playfair Display', serif;
    font-size: 13px;
    font-style: italic;
    color: #C97D8A;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
}

/* animations */
@keyframes fadeUp {
    from { opacity: 0; transform: translateY(24px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes popIn {
    from { opacity: 0; transform: scale(0.7); }
    to { opacity: 1; transform: scale(1); }
}

/* image upload area */
.gradio-container .upload-container,
.gradio-container [data-testid="image"] {
    border: 1.5px dashed #E8C4CC !important;
    border-radius: 12px !important;
    background: #F7F0E6 !important;
}

/* result output boxes: remove default gradio styling */
.gradio-container .output-html {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}
"""

with gr.Blocks(css=custom_css, title="mbti guesser") as demo:

    # hero
    gr.HTML("""
    <div class='hero'>
        <div class='hero-eyebrow'>digital footprint analysis</div>
        <div class='hero-title'>read the<br><em>room.</em></div>
        <div class='hero-sub'>paste in someone's online presence. get a personality read. no quiz, just signal.</div>
    </div>
    """)

    # inputs
    with gr.Row():
        with gr.Column(scale=3):
            gr.HTML("<div class='input-panel'>")
            gr.HTML("<div class='section-label'>text signals</div>")
            bio = gr.Textbox(
                label="instagram bio ✦ required",
                placeholder="e.g.  living slowly, thinking deeply 🌿 | philosophy | coffee always",
                lines=2
            )
            captions = gr.Textbox(
                label="caption dump — optional",
                placeholder="paste 5–10 recent captions",
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
            gr.HTML("</div>")

        with gr.Column(scale=2):
            gr.HTML("<div class='input-panel'>")
            gr.HTML("<div class='section-label'>numeric signals</div>")
            with gr.Row():
                followers = gr.Number(label="followers", value=0)
                following = gr.Number(label="following", value=0)
            num_posts = gr.Number(label="number of posts", value=0)
            gr.HTML("</div>")

            gr.HTML("<div class='input-panel'>")
            gr.HTML("<div class='section-label'>photo signals — optional</div>")
            profile_photo = gr.Image(label="profile photo", type="filepath")
            candid_photo = gr.Image(label="candid or tagged photo", type="filepath")
            gr.HTML("</div>")

    # button
    gr.HTML("<div class='analyze-btn-wrap'>")
    analyze_btn = gr.Button("analyze ↗", variant="primary")
    gr.HTML("</div>")

    gr.HTML("<hr class='divider'>")

    # results
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