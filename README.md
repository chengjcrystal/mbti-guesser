---
title: MBTI Radar
emoji: 🧠
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.18.0
app_file: ui.py
pinned: false
thumbnail: >-
  https://raw.githubusercontent.com/chengjcrystal/mbti-guesser/main/thumbnail.png
---

# MBTI Radar

**Answer short scenarios about yourself (and add a photo if you want) and get a zero-shot MBTI read across all four axes.**

No training data, no fine-tuning. Text goes through zero-shot NLI classification, an optional photo runs through DeepFace and OpenCV, and everything gets fused into one type with a per-axis confidence gap.

[Live Demo](https://huggingface.co/spaces/chengjcrystal/mbti-guesser)

## How It Works

1. **Text.** Two pages of quick picks, a page of easy free-text questions (weekends, what stresses you out, party vibe, what you talk about), and one short scenario: a group chat of five about studying together tomorrow, where you pick what you do (reply, leave it on read, or see what your closest friend says first). If you wait for her, her answer shows up on the same page and you then say what you tell the group. From there you describe your ideal study session and say what you do when you're stuck on a question. Every question except the photo is required, apart from the follower count and the close friends list, which some people can't or won't answer. Two pages of quick picks also ask how often you post to your feed and to your story. Each question is written for particular axes, and each answer is turned into a first-person sentence and scored against only those axes' two poles by `facebook/bart-large-mnli` (zero-shot NLI, a forced choice between the two trait statements). The whole quiz lives in `questions.py`.
2. **Photo (optional).** DeepFace reads dominant emotion as a soft T/F signal. OpenCV Haar cascades pull face count (solo vs. group), rough eye contact, background color variance, and smile presence as E/I and T/F nudges. Each detector is wrapped in its own try/except, so one failing doesn't take the others down.
3. **Numeric.** Follower count, how often they post to their feed, and spam/close-friends account size nudge E/I.
4. **Fusion.** The three sources are weighted-blended (text 65%, photo 25%, numeric 10%), and if there's no photo, its weight gets redistributed into text instead of just vanishing. The live radar shows `?` for an axis until two real answers have spoken to it. The final card always names one of the 16 types; an axis with a margin under 15 points, or thin evidence, is tagged a close call.

## Honest Limitations

This is a heuristic sketch, not a validated model. There's no labeled ground truth for real profiles, so "accuracy on real people" isn't a number that exists here. The confidence scores describe the model's certainty, not correctness. The numeric and photo signals in particular are hand-tuned nudges, not learned from data, and should be read as flavor on top of the text signal, not independent evidence.

What is checked (`eval_axes.py`): 16 hand-written test snippets, four per axis, each written to unambiguously describe one pole (e.g. a clearly extroverted description vs. a clearly introverted one). The text pipeline recovers the intended label on all 16, with a mean confidence above 97%. That confirms the classifier reads clear-cut text correctly, it says nothing about how it handles the ambiguous, real-world profiles this app is actually used on. Results are in `eval_results.json`.

## Run It

```bash
pip install -r requirements.txt
python ui.py   # http://127.0.0.1:7860
```

First run downloads `facebook/bart-large-mnli` (~1.6 GB) from Hugging Face.

## What's In The Repo

| File | What it does |
|---|---|
| `questions.py` | The whole quiz as data: questions, steps, which axes each answer speaks to |
| `app.py` | Answer-to-sentence conversion, zero-shot NLI scoring per axis, numeric signals, fusion |
| `photo_analysis.py` | DeepFace + OpenCV photo signals |
| `sprites.js` | The 16 pixel-art type characters, drawn in the browser |
| `ui.py` | Gradio layout and theme |
| `styles.css` | Custom styling on top of the Gradio theme |
| `eval_axes.py` | Sanity-check script for the text classifier, writes `eval_results.json` |

## License

MIT. See [LICENSE](LICENSE).
