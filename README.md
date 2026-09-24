---
title: MBTI Guesser
emoji: 🧠
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: 6.18.0
app_file: ui.py
pinned: false
thumbnail: >-
  https://huggingface.co/spaces/chengjcrystal/mbti-guesser/resolve/main/thumbnail.png
---

# MBTI Guesser

**Describe someone (texts, humor, weekend habits, a photo if you've got one) and get a zero-shot MBTI read across all four axes.**

No training data, no fine-tuning. Text goes through zero-shot NLI classification, an optional photo runs through DeepFace and OpenCV, and everything gets fused into one type with a per-axis confidence gap.

[Live Demo](https://huggingface.co/spaces/chengjcrystal/mbti-guesser)

## How It Works

1. **Text.** Free-text fields (talk topics, weekend activities, texting style, and more) get assembled into one labeled blob and run through `facebook/bart-large-mnli` as zero-shot classification, separately for each of the four axes.
2. **Photo (optional).** DeepFace reads dominant emotion as a soft T/F signal. OpenCV Haar cascades pull face count (solo vs. group), rough eye contact, background color variance, and smile presence as E/I and T/F nudges. Each detector is wrapped in its own try/except, so one failing doesn't take the others down.
3. **Numeric.** Follower count and a few social-media behavior checkboxes (lurker, spam/close-friends account size) nudge E/I.
4. **Fusion.** The three sources are weighted-blended (text 65%, photo 25%, numeric 10%), and if there's no photo, its weight gets redistributed into text instead of just vanishing. An axis shows `?` instead of a letter when the winning margin is under 8 points.

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
| `app.py` | Text assembly, zero-shot NLI classification, numeric signals, fusion |
| `photo_analysis.py` | DeepFace + OpenCV photo signals |
| `creature.py` | Procedural creature SVG, one visual part per trait letter |
| `ui.py` | Gradio layout and theme |
| `styles.css` | Custom styling on top of the Gradio theme |
| `eval_axes.py` | Sanity-check script for the text classifier, writes `eval_results.json` |

## License

MIT. See [LICENSE](LICENSE).
