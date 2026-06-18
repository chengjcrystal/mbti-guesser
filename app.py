from transformers import pipeline
import re

# axis definitions 
AXES = {
    "E_I": {
        "labels": [
            "tends to seek out social interaction and feels energized being around other people",
            "tends to prefer solitude and feels drained by too much social interaction"
        ],
        "keys": ["E", "I"]
    },
    "N_S": {
        "labels": [
            "tends to think about possibilities, meaning, and the big picture rather than concrete details",
            "tends to focus on what is concrete, present, and directly observable rather than abstract ideas"
        ],
        "keys": ["N", "S"]
    },
    "T_F": {
        "labels": [
            "tends to make decisions by analyzing facts and thinking through things logically",
            "tends to make decisions based on how they feel and how it affects the people involved"
        ],
        "keys": ["T", "F"]
    },
    "J_P": {
        "labels": [
            "tends to like having a plan and prefers things to be settled and decided",
            "tends to prefer going with the flow and keeping their options open"
        ],
        "keys": ["J", "P"]
    }
}

# weights for the three signal sources
TEXT_WEIGHT = 0.65
PHOTO_WEIGHT = 0.25
NUMERIC_WEIGHT = 0.10

# gap below this = axis is ambiguous, show "?" instead of a letter
AMBIGUITY_THRESHOLD = 8.0

_classifier = None

def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli"
        )
    return _classifier


def assemble_text(
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
    fav_media
):
    """
    combine all the free-text and picker fields into one labeled blob.
    labeling each section helps the model understand context instead of
    treating everything as one undifferentiated wall of text.
    """
    parts = []

    if spotify_artists and spotify_artists.strip():
        parts.append(f"Their Spotify top artists: {spotify_artists.strip()}")

    # humor types multi-select -> sentence
    if humor_types:
        humor_str = ", ".join(humor_types)
        parts.append(f"Their humor style tends to be: {humor_str}.")

    # punctuality radio -> sentence
    punctuality_map = {
        "always early": "They are always early and plan ahead.",
        "on time": "They tend to show up right on time.",
        "always late": "They are usually late and go with the flow."
    }
    if punctuality and punctuality in punctuality_map:
        parts.append(punctuality_map[punctuality])

    # group archetypes multi-select -> sentence
    if group_archetypes:
        archetype_str = ", ".join(group_archetypes)
        parts.append(f"In their friend group they are: {archetype_str}.")

    if what_they_talk_about and what_they_talk_about.strip():
        parts.append(f"What they talk about most: {what_they_talk_about.strip()}")

    if weekend_activities and weekend_activities.strip():
        parts.append(f"How they spend their weekends: {weekend_activities.strip()}")

    # text length slider -> descriptive sentence
    text_length_descriptions = {
        1: "They text in one-word replies and barely say anything.",
        2: "Their texts are short and to the point.",
        3: "They write average-length texts, not too short or too long.",
        4: "They tend to write long texts with a lot of detail.",
        5: "They send full essays -> their texts are extremely long and detailed."
    }
    if text_length_slider and int(text_length_slider) in text_length_descriptions:
        parts.append(text_length_descriptions[int(text_length_slider)])

    # texting style checkboxes -> sentence
    if texting_style:
        style_str = ", ".join(texting_style)
        parts.append(f"Their texting style: {style_str}.")

    if stress_triggers and stress_triggers.strip():
        parts.append(f"What stresses them out: {stress_triggers.strip()}")

    if party_vibe and party_vibe.strip():
        parts.append(f"At parties or when they drink: {party_vibe.strip()}")

    if fav_media and fav_media.strip():
        parts.append(f"Their favorite shows and media: {fav_media.strip()}")

    return " ".join(parts)


def numeric_signals(followers, following, social_media_checkboxes):
    """
    returns a dict of axis -> score nudges based on follower counts
    and social media behavior checkboxes. scores are in [-1, 1] range
    where -1 is strong first label (E/N/T/J) and +1 is strong second (I/S/F/P).
    """
    nudges = {"E_I": 0.0}

    # follower count thresholds for E/I
    # positive = I lean, negative = E lean
    if followers is not None:
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

    # social media checkboxes
    if social_media_checkboxes:
        if "mostly a lurker" in social_media_checkboxes:
            nudges["E_I"] += 0.25
        if "posts a lot" in social_media_checkboxes:
            nudges["E_I"] -= 0.25

        # spam/close friends account: nudge depends on how many people are on it
        # small list = more selective/private = introvert lean, big list = basically public = extravert lean
        if "has a spam/close friends account" in social_media_checkboxes:
            count = spam_friends_count  # comes from the number input below
            if count is not None:
                if count < 10:
                    nudges["E_I"] += 0.4
                elif count < 50:
                    nudges["E_I"] += 0.2
                elif count <= 80:
                    pass
                elif count <= 110:
                    nudges["E_I"] -= 0.2
                else:
                    nudges["E_I"] -= 0.4

        # clamp to [-1, 1]
        for k in nudges:
            nudges[k] = max(-1.0, min(1.0, nudges[k]))

        return nudges


def classify_text(text):
    """
    run zero-shot classification on each axis separately.
    returns dict of axis -> (winning_key, confidence_pct, is_ambiguous)
    """
    if not text or not text.strip():
        return None

    clf = get_classifier()
    results = {}

    for axis_name, axis_data in AXES.items():
        labels = axis_data["labels"]
        keys = axis_data["keys"]

        # hypothesis template matters a lot here
        output = clf(
            text,
            candidate_labels=labels,
            hypothesis_template="the text suggests the author {}.",
            multi_label=False
        )

        # map back to our keys
        label_to_key = dict(zip(labels, keys))
        scored = {label_to_key[l]: s * 100 for l, s in zip(output["labels"], output["scores"])}

        winner = max(scored, key=scored.get)
        loser = min(scored, key=scored.get)
        gap = scored[winner] - scored[loser]
        is_ambiguous = gap < AMBIGUITY_THRESHOLD

        results[axis_name] = {
            "winner": winner,
            "confidence": scored[winner],
            "gap": gap,
            "is_ambiguous": is_ambiguous,
            "scores": scored
        }

    return results


def blend_signals(text_results, photo_results, numeric_nudges):
    """
    combine text, photo, and numeric signals using weighted blending.
    
    text_results: output from classify_text()
    photo_results: dict from photo_analysis.py, or None
    numeric_nudges: dict from numeric_signals()
    
    returns final axis decisions as dict
    """
    final = {}

    for axis_name, axis_data in AXES.items():
        keys = axis_data["keys"]  # i.e. ["E", "I"]

        # start with text scores (in 0-100 range)
        if text_results and axis_name in text_results:
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
        is_ambiguous = gap < AMBIGUITY_THRESHOLD

        final[axis_name] = {
            "winner": winner,
            "confidence": winner_pct,
            "gap": gap,
            "is_ambiguous": is_ambiguous,
            "scores": {keys[0]: first_key_pct, keys[1]: second_key_pct}
        }

    return final


def predict_mbti(
    spotify_artists="",
    humor_types=None,
    punctuality=None,
    group_archetypes=None,
    what_they_talk_about="",
    weekend_activities="",
    text_length_slider=3,
    texting_style=None,
    stress_triggers="",
    party_vibe="",
    fav_media="",
    followers=None,
    following=None,
    social_media_checkboxes=None,
    photo_results=None
):
    """
    main entry point. takes all inputs, runs classification, returns
    the predicted type and per-axis breakdown.
    """
    # build the text blob
    text = assemble_text(
        spotify_artists=spotify_artists,
        humor_types=humor_types or [],
        punctuality=punctuality,
        group_archetypes=group_archetypes or [],
        what_they_talk_about=what_they_talk_about,
        weekend_activities=weekend_activities,
        text_length_slider=text_length_slider,
        texting_style=texting_style or [],
        stress_triggers=stress_triggers,
        party_vibe=party_vibe,
        fav_media=fav_media
    )

    if not text.strip():
        return None, "fill in at least a few fields to get a prediction!"

    # classify text
    text_results = classify_text(text)

    # numeric signals
    numeric_nudges = numeric_signals(followers, following, social_media_checkboxes or [])

    # blend everything together
    final_results = blend_signals(text_results, photo_results, numeric_nudges)

    # build the type string
    axis_order = ["E_I", "N_S", "T_F", "J_P"]
    type_letters = []
    for axis in axis_order:
        r = final_results[axis]
        if r["is_ambiguous"]:
            type_letters.append("?")
        else:
            type_letters.append(r["winner"])

    mbti_type = "".join(type_letters)

    return mbti_type, final_results