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
  https://raw.githubusercontent.com/chengjcrystal/mbti-radar/main/thumbnail.png
---

<p align="center">
  <img src="https://raw.githubusercontent.com/chengjcrystal/mbti-radar/main/assets/banner.png" alt="MBTI Radar title card over pixel-art mountains, with six pixel-art animal characters standing on the grass" width="900">
</p>

`★ press start   ▮▮▮▮ no training data`

answer a few short scenarios about yourself, add a photo if you want, and get a zero-shot mbti read across all four axes, with a confidence gap on each. it runs on facebook/bart-large-mnli with no fine-tuning. [play it live](https://huggingface.co/spaces/chengjcrystal/mbti-radar).

## ⌜ the 16 ⌟

every result is one of 16 pixel-art characters, drawn in the browser.

<p align="center">
  <img src="https://raw.githubusercontent.com/chengjcrystal/mbti-radar/main/assets/types.png" alt="All 16 MBTI types as pixel-art animal characters in a grid, each labeled with its four-letter type and nickname" width="900">
</p>

## ⌜ how it reads you ⌟

| signal | what it does |
| --- | --- |
| **text** | scenarios and free-text answers, each turned into a first-person sentence and scored by zero-shot NLI against only the axes that question is written for |
| **photo** | optional. deepface reads emotion (soft t/f nudge), opencv haar cascades add face count, eye contact, background variance and smile (e/i and t/f nudges). the photo is deleted from the server right after use |
| **numeric** | follower count, how often you post, and close-friends list size nudge e/i |

the three get blended: text 65%, photo 25%, numeric 10%. with no photo, its weight goes to text instead of vanishing. the live radar shows `?` on an axis until two real answers have spoken to it, and an axis with a margin under 15 points is tagged a close call.

## ⌜ the quiz ⌟

six steps: quick picks, easy free-text (weekends, party vibe, what stresses you out), and one group-chat scenario where you pick a reply, leave it on read, or see what your closest friend says first. if you wait for her, her answer shows up on the same page and you say what you tell the group. then you describe an ideal study session and what you do when you're stuck.

every question is required except the photo, follower count and close-friends size, since some people can't or won't answer those. the whole quiz lives in `questions.py`.

## ⌜ card finishes ⌟

every result card comes in three finishes: common (just the family color border), holo (a gold border and one bold shine) and rainbow (a rainbow border with rainbow foil over the character, and on the back a holo sheet of pixel sparkles with a striped rainbow radar). hover or drag over a card to tilt it, and the shine slides so you can catch the light. the finish names, the pack count and the odds all live in `finishes.py`, and `python3 preview_finishes.py` writes a page that shows all three side by side.

## ⌜ card packs ⌟

you get 5 packs per quiz. the first one is opened for you, the other four are opened one at a time from the result page, and each one rolls a finish on the server (the odds are in `finishes.py`). shiny pulls get a longer, flashier opening. a row of slots under the card tracks which finishes of your type you've pulled, and tapping a pulled slot shows that card again. the packs you've opened are kept in the browser (`gr.BrowserState`), and anything read back from it is cleaned first (`game.py`), so a refresh keeps your pulls and a tampered value just falls back to the landing page.

## ⌜ honest limitations ⌟

this is a heuristic sketch, not a validated model. there's no labeled ground truth for real profiles, so "accuracy on real people" isn't a number that exists here. the confidence scores describe the model's certainty, not correctness. the photo and numeric signals are hand-tuned nudges, not learned from data, so read them as flavor on top of the text signal.

what is checked (`eval_axes.py`): 16 hand-written snippets, four per axis, each written to clearly describe one pole. the text pipeline gets all 16 right with a mean confidence above 97%. that says the classifier reads clear-cut text correctly, and nothing about ambiguous real-world answers. results are in `eval_results.json`.

## ⌜ run it ⌟

```bash
pip install -r requirements.txt
python ui.py   # http://127.0.0.1:7860
```

first run downloads `facebook/bart-large-mnli` (~1.6 GB) from hugging face.

for testing there's a dev mode: `MBTI_DEV=1 python3 ui.py` adds a small bar at the top that jumps straight to a result for any type and finish, so you don't have to fill in the quiz. it isn't there unless that variable is set.

## ⌜ what's in the repo ⌟

| file | what it does |
| --- | --- |
| `questions.py` | the whole quiz as data: questions, steps, which axes each answer speaks to |
| `app.py` | answer-to-sentence conversion, zero-shot scoring per axis, numeric signals, fusion |
| `photo_analysis.py` | deepface + opencv photo signals |
| `sprites.js` | the 16 pixel-art characters, drawn in the browser |
| `finishes.py` | the card finishes, the pack count and the odds, plus the roll |
| `pack_art.py` | the card pack, drawn as two little svg pieces |
| `foil_art.py` | the pixel sparkle tile and stripe fill for the rainbow finish |
| `game.py` | the pack game's state: cleaning what comes back from the browser, opening the next pack |
| `preview_finishes.py` | writes a page that shows all three finishes side by side |
| `ui.py` | gradio layout and theme |
| `styles.css` | custom styling on top of the gradio theme |
| `eval_axes.py` | sanity check for the text classifier, writes `eval_results.json` |

`mit` · see [LICENSE](LICENSE)
