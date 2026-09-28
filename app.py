import re

import torch
from transformers import pipeline

from questions import QUESTIONS, NO_SOCIAL, NOT_SURE, is_shown

# axis definitions. each pole is a short trait statement the NLI model scores
# a piece of text against. "labels" is first person (used on the quiz answers,
# which are written as "I ..."), "labels_3p" is the same meaning in third
# person (used by eval_axes.py on its "They ..." snippets).
#
# these are short and matched on purpose. longer "tends to make decisions by
# ..." wording gave one pole an edge on almost any text, and a topic like
# "coding and job searching" would come out 90% extraverted from noise.
AXES = {
    "E_I": {
        "labels": [
            "I get energized by being around people and I'm outgoing",
            "I need time alone to recharge and I get drained by socializing",
        ],
        "labels_3p": [
            "They get energized by being around people and they're outgoing",
            "They need time alone to recharge and get drained by socializing",
        ],
        "keys": ["E", "I"],
    },
    "N_S": {
        "labels": [
            "I think about ideas, meanings, and possibilities more than concrete details",
            "I focus on concrete facts, details, and what's actually in front of me",
        ],
        "labels_3p": [
            "They think about ideas, meanings, and possibilities more than concrete details",
            "They focus on concrete facts, details, and what's actually in front of them",
        ],
        "keys": ["N", "S"],
    },
    "T_F": {
        "labels": [
            "I value logic and honesty over people's feelings",
            "I put people's feelings and harmony ahead of being right",
        ],
        "labels_3p": [
            "They value logic and honesty over people's feelings",
            "They put people's feelings and harmony ahead of being right",
        ],
        "keys": ["T", "F"],
    },
    "J_P": {
        "labels": [
            "I like to plan ahead and stay organized",
            "I like to stay spontaneous and improvise",
        ],
        "labels_3p": [
            "They like to plan ahead and stay organized",
            "They like to stay spontaneous and improvise",
        ],
        "keys": ["J", "P"],
    },
    "A_T": {
        "labels": [
            "I don't dwell on it and I move on quickly",
            "I get bothered, keep checking, and can't let things go",
        ],
        "labels_3p": [
            "They don't dwell on it and move on quickly",
            "They get bothered, keep checking, and can't let things go",
        ],
        "keys": ["A", "T"],
    },
}

# weights for the three signal sources
TEXT_WEIGHT = 0.65
PHOTO_WEIGHT = 0.25
NUMERIC_WEIGHT = 0.10

# gap below this = axis is ambiguous, show "?" instead of a letter
AMBIGUITY_THRESHOLD = 15.0

# an axis only reads its own questions, and needs this much answered evidence
# (a full answer counts 1, a light one like humor counts less)
# before it will show a letter. below that it is "?", not a guess.
MIN_EVIDENCE = 1.5


def _has_content(value, min_chars=8):
    if isinstance(value, list):
        return len(value) > 0
    if value is None:
        return False
    text = str(value).strip()
    if len(text) < min_chars:
        return False
    if len(set(text.lower().replace(" ", ""))) <= 2:
        return False
    return True


_classifier = None

def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )
    return _classifier


def _entailment_pairs(items, batch_size=32):
    """
    items: list of (text, [label_a, label_b]).
    returns a (p_a, p_b) per item: a forced choice between the two labels,
    a softmax over each label's entailment score for that text.
    """
    clf = get_classifier()
    tok, model = clf.tokenizer, clf.model
    ent = model.config.label2id.get("entailment", 2)

    premises, hypotheses = [], []
    for text, labels in items:
        for label in labels:
            premises.append(text)
            hypotheses.append(f"{label}.")

    logits = []
    for i in range(0, len(premises), batch_size):
        enc = tok(premises[i:i + batch_size], hypotheses[i:i + batch_size],
                  return_tensors="pt", truncation=True, padding=True).to(model.device)
        with torch.no_grad():
            logits.append(model(**enc).logits[:, ent].float().cpu())
    flat = torch.cat(logits) if logits else torch.empty(0)
    pairs = flat.view(-1, 2).softmax(-1)
    return [(float(a), float(b)) for a, b in pairs]


def build_pieces(answers):
    """
    turn the raw answers into first-person pieces of text, each routed to the
    axes its question was written for.
    """
    pieces = []
    for q in QUESTIONS:
        if q["kind"] in ("scene", "image") or q.get("numeric") or not q.get("axes"):
            continue
        if not is_shown(q, answers):
            continue   # its chip isn't ticked, so it was never asked
        qid = q["id"]
        v = answers.get(qid)
        text = None
        raw = None   # the person's own words, kept for the live "what the model read" panel

        if q["kind"] == "checks":
            if v:
                text = q["piece"].format(v=", ".join(v))
        elif q["kind"] == "radio":
            if v and q.get("piece_map") and v in q["piece_map"]:
                text = q["piece_map"][v]
        elif q["kind"] == "slider":
            if v and int(v) in q["piece_map"]:   # 0 means the slider was never moved
                text = q["piece_map"][int(v)]
        elif q["kind"] == "pick":
            # a row of pills: only the ones that carry a sentence say anything about you
            ticked = [c for c in q["chips"] if answers.get(c["id"]) and c.get("piece")]
            if ticked:
                text = ticked[0]["piece"]
                raw = "(" + ticked[0]["label"] + ")"
        elif q["kind"] == "msg":
            if v and len(str(v).strip()) >= 2:
                v = str(v).strip()
                raw = v
                text = q["piece"].format(v=v)
        elif q["kind"] == "text":
            floor = 2 if q.get("min") == "reply" else 8
            if v and (len(str(v).strip()) >= floor if floor == 2 else _has_content(v, floor)):
                v = str(v).strip()
                raw = v
                text = q["piece"].format(v=v)

        if text:
            # one answer can count for more on one stat than another
            weights = q.get("axis_weights") or {axis: q.get("weight", 1.0) for axis in q["axes"]}
            pieces.append({"id": qid, "text": text, "raw": raw, "axes": q["axes"], "weights": weights})
    return pieces


def score_axes(pieces):
    """
    per axis: forced-choice each routed piece against that axis's two poles,
    then a weighted average. an axis with too little evidence is flagged so
    it can show "?" instead of a confident-looking number from noise.
    """
    items, owners = [], []
    for p in pieces:
        for axis in p["axes"]:
            items.append((p["text"], AXES[axis]["labels"]))
            owners.append((axis, p["weights"][axis], p))
    probs = _entailment_pairs(items) if items else []

    per_axis = {axis: {"num": 0.0, "den": 0.0} for axis in AXES}
    reads = {axis: [] for axis in AXES}
    for (axis, weight, piece), (p_a, _p_b) in zip(owners, probs):
        per_axis[axis]["num"] += weight * p_a
        per_axis[axis]["den"] += weight
        if piece.get("raw") and weight >= 0.6:
            keys = AXES[axis]["keys"]
            reads[axis].append({"raw": piece["raw"], "key": keys[0] if p_a >= 0.5 else keys[1], "pct": round(max(p_a, 1 - p_a) * 100)})

    results = {}
    for axis, data in AXES.items():
        keys = data["keys"]
        den = per_axis[axis]["den"]
        p_a = per_axis[axis]["num"] / den if den else 0.5
        # thin evidence pulls toward 50/50, so one answer can't read as a strong result
        p_a = 0.5 + (p_a - 0.5) * min(1.0, den / MIN_EVIDENCE)
        scores = {keys[0]: p_a * 100, keys[1]: (1 - p_a) * 100}
        winner = keys[0] if p_a >= 0.5 else keys[1]
        gap = abs(scores[keys[0]] - scores[keys[1]])
        results[axis] = {
            "winner": winner,
            "confidence": max(scores.values()),
            "gap": gap,
            "evidence": den,
            "has_evidence": den >= MIN_EVIDENCE,
            "is_ambiguous": gap < AMBIGUITY_THRESHOLD or den < MIN_EVIDENCE,
            "scores": scores,
            "reads": reads[axis],
        }
    return results


def classify_text(text):
    """
    one blob of third-person text against all five axes. used by
    eval_axes.py to sanity check the labels on hand-written snippets.
    """
    if not text or not text.strip():
        return None
    axes = list(AXES)
    probs = _entailment_pairs([(text, AXES[a]["labels_3p"]) for a in axes])
    results = {}
    for axis, (p_a, p_b) in zip(axes, probs):
        keys = AXES[axis]["keys"]
        scores = {keys[0]: p_a * 100, keys[1]: p_b * 100}
        winner = max(scores, key=scores.get)
        gap = abs(scores[keys[0]] - scores[keys[1]])
        results[axis] = {
            "winner": winner,
            "confidence": scores[winner],
            "gap": gap,
            "is_ambiguous": gap < AMBIGUITY_THRESHOLD,
            "scores": scores,
        }
    return results


# posting cadence on the main feed, as concrete frequencies instead of "posts
# a lot" / "lurker", since what counts as a lot is different for everyone.
# negative = E lean, positive = I lean.
POSTING_NUDGE = {
    "a few times a week or more": -0.4,
    "about once a week": -0.2,
    "a couple times a month": 0.0,
    "about once a month": 0.15,
    "a few times a year": 0.3,
    "once a year or less": 0.4,
}


# how often they post to stories. lighter than a feed post, so a smaller nudge
STORY_NUDGE = {
    "most days": -0.3,
    "a few times a week": -0.2,
    "about once a week": -0.05,
    "a couple times a month": 0.1,
    "a few times a year": 0.2,
    "basically never": 0.3,
}


def numeric_signals(followers, posting_frequency, social_media_checkboxes, spam_friends_count=None, story_frequency=None):
    """
    returns a dict of axis -> score nudges based on follower count, how often
    they post, and a couple of account habits. scores are in [-1, 1] range
    where -1 is strong first label (E/N/T/J) and +1 is strong second (I/S/F/P).
    """
    nudges = {"E_I": 0.0}
    social_media_checkboxes = social_media_checkboxes or []

    # "not sure" is an honest admission of no signal, not a guess -- don't
    # let a stray follower-count number (left over from before, or just the
    # field's own default) sneak in a nudge it isn't meant to carry.
    if posting_frequency == NOT_SURE:
        return nudges

    # no account at all is itself a real, fairly strong I signal, and it
    # makes the follower-count field meaningless, so it short-circuits the
    # usual threshold math below rather than feeding it a bogus 0.
    if posting_frequency == NO_SOCIAL:
        nudges["E_I"] += 0.6
        return nudges

    # follower count thresholds for E/I
    # positive = I lean, negative = E lean
    if followers is not None and str(followers).strip():
        try:
            f = int(followers)
            if f < 100:
                nudges["E_I"] += 0.8   # strong I signal
            elif f < 500:
                nudges["E_I"] += 0.4   # mild I
            elif f < 800:
                nudges["E_I"] += 0.0   # no lean
            elif f < 1500:
                nudges["E_I"] -= 0.4   # mild E
            else:
                nudges["E_I"] -= 0.8   # strong E
        except (ValueError, TypeError):
            pass

    nudges["E_I"] += POSTING_NUDGE.get(posting_frequency, 0.0)
    nudges["E_I"] += STORY_NUDGE.get(story_frequency, 0.0)

    # spam/close friends account: nudge depends on list size
    # small list = selective/private = I lean, big list = basically public = E lean
    if "has a spam/close friends account" in social_media_checkboxes:
        if spam_friends_count is not None and str(spam_friends_count).strip():
            try:
                count = int(spam_friends_count)
                if count < 15:
                    nudges["E_I"] += 0.4    # very small circle, very introverted
                elif count < 50:
                    nudges["E_I"] += 0.2    # still pretty selective
                elif count <= 80:
                    pass                     # neutral zone, no lean either way
                elif count <= 110:
                    nudges["E_I"] -= 0.2    # getting pretty social
                else:
                    nudges["E_I"] -= 0.4    # 110+ = basically a second public account
            except (ValueError, TypeError):
                nudges["E_I"] += 0.3        # has account but count unknown = mild I default
        else:
            nudges["E_I"] += 0.3            # no count provided, still an I nudge

    # clamp to [-1, 1]
    for k in nudges:
        nudges[k] = max(-1.0, min(1.0, nudges[k]))

    return nudges


def blend_signals(text_results, photo_results, numeric_nudges):
    """
    combine text, photo, and numeric signals using weighted blending.

    text_results: output from score_axes()
    photo_results: dict from photo_analysis.py, or None
    numeric_nudges: dict from numeric_signals()

    returns final axis decisions as dict
    """
    final = {}

    for axis_name, axis_data in AXES.items():
        keys = axis_data["keys"]  # e.g. ["E", "I"]

        # text scores (0-100). even thin evidence gives a lean to report, it is
        # just flagged as a close call below when it is under MIN_EVIDENCE
        text_ok = bool(text_results) and text_results[axis_name]["has_evidence"]
        text_any = bool(text_results) and text_results[axis_name]["evidence"] > 0
        if text_any:
            text_scores = text_results[axis_name]["scores"]
            # convert to [-1, 1] where -1 = first key, +1 = second key
            text_val = (text_scores[keys[1]] - text_scores[keys[0]]) / 100.0
        else:
            text_val = 0.0

        # photo signal: only E_I and T_F are affected
        photo_val = 0.0
        if photo_results:
            if axis_name == "E_I" and "E_I" in photo_results:
                photo_val = photo_results["E_I"]  # expected in [-1, 1]
            elif axis_name == "T_F" and "T_F" in photo_results:
                photo_val = photo_results["T_F"]

        # numeric nudges (already in [-1, 1])
        numeric_val = numeric_nudges.get(axis_name, 0.0)

        # weighted blend
        has_photo = photo_results is not None and axis_name in photo_results
        if has_photo:
            blended = (
                text_val * TEXT_WEIGHT +
                photo_val * PHOTO_WEIGHT +
                numeric_val * NUMERIC_WEIGHT
            )
        else:
            # redistribute photo weight to text when no photo
            adjusted_text_w = TEXT_WEIGHT + PHOTO_WEIGHT
            adjusted_numeric_w = NUMERIC_WEIGHT
            total = adjusted_text_w + adjusted_numeric_w
            blended = (
                text_val * (adjusted_text_w / total) +
                numeric_val * (adjusted_numeric_w / total)
            )

        # convert back to confidence percentages
        # blended is in [-1, 1] where negative = first key, positive = second key
        second_key_pct = (blended + 1) / 2 * 100
        first_key_pct = 100 - second_key_pct

        winner = keys[0] if first_key_pct > second_key_pct else keys[1]
        winner_pct = max(first_key_pct, second_key_pct)
        gap = abs(first_key_pct - second_key_pct)

        # a photo actually scored on this axis is its own real evidence,
        # independent of whatever has been answered so far.
        has_real_signal = text_ok or has_photo
        is_ambiguous = (gap < AMBIGUITY_THRESHOLD) or not has_real_signal

        final[axis_name] = {
            "winner": winner,
            "confidence": winner_pct,
            "gap": gap,
            "is_ambiguous": is_ambiguous,
            "scores": {keys[0]: first_key_pct, keys[1]: second_key_pct},
            "reads": text_results[axis_name]["reads"] if text_results else [],
        }

    return final


def predict_mbti(answers, photo_results=None):
    """
    main entry point. takes the answers dict (question id -> value), runs the
    scoring, returns the predicted type and per-axis breakdown.
    """
    pieces = build_pieces(answers)
    if not pieces:
        return None, None, ""

    text_results = score_axes(pieces)

    numeric_nudges = numeric_signals(
        answers.get("followers"),
        answers.get("posting_frequency"),
        answers.get("social_media_checkboxes") or [],
        answers.get("spam_friends_count"),
        answers.get("story_frequency"),
    )

    final_results = blend_signals(text_results, photo_results, numeric_nudges)

    # build the type string: 4 core letters, then a dash, then the identity suffix
    # (A/T). the final answer always names a letter per axis, since only 16 types
    # exist. an unsure axis still leans one way, and is_ambiguous flags it as a
    # close call for the result card (the live radar can still show "?").
    axis_order = ["E_I", "N_S", "T_F", "J_P", "A_T"]
    type_letters = [final_results[axis]["winner"] for axis in axis_order]

    mbti_type = "".join(type_letters[:4]) + "-" + type_letters[4]

    return mbti_type, final_results, " ".join(p["text"] for p in pieces)
