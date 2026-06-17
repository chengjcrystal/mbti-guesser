from transformers import pipeline
from photo_analysis import analyze_profile_photo, photo_to_mbti_signals

# load once at startup
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

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

# how much each source influences the final score
# text is the most reliable so it gets the most weight
WEIGHTS = {
    "text": 0.65,
    "photo": 0.25,
    "numeric": 0.10
}

def assemble_text(bio, captions, dms, music, opinions):
    # label each section so the model knows what context it's reading
    parts = []
    if bio and bio.strip():
        parts.append(f"[instagram bio]: {bio.strip()}")
    if captions and captions.strip():
        parts.append(f"[captions]: {captions.strip()}")
    if dms and dms.strip():
        parts.append(f"[messages/texts]: {dms.strip()}")
    if music and music.strip():
        # music taste is surprisingly good for n/s and f/t signals
        parts.append(f"[music taste]: {music.strip()}")
    if opinions and opinions.strip():
        # unfiltered takes = most raw signal we have, weight it accordingly
        parts.append(f"[unfiltered opinions]: {opinions.strip()}")
    return "\n".join(parts)

def classify_text(combined_text):
    # runs 4 separate classifications, one per axis
    if not combined_text.strip():
        return None

    scores = {}
    for axis, config in AXES.items():
        result = classifier(
            combined_text,
            candidate_labels=config["labels"],
            # "the text suggests" is way more stable than "this person is"
            # because the model is reading evidence, not making a leap about identity
            hypothesis_template="the text suggests the author {}."
        )
        key0, key1 = config["keys"]
        s0 = round(result["scores"][0] * 100, 1)
        s1 = round(result["scores"][1] * 100, 1)

        # gap under 8 points = noise, just call it even
        if abs(s0 - s1) < 8:
            scores[axis] = {key0: 50.0, key1: 50.0, "ambiguous": True}
        else:
            scores[axis] = {key0: s0, key1: s1}
    return scores

def numeric_signals(followers, following):
    # soft signals only, these just nudge the final score a little
    signals = {}

    # high follower/following ratio = selective about who they follow = mild i lean
    if followers and following and following > 0:
        ratio = followers / following
        signals["E_I_numeric"] = "I" if ratio > 2 else "E"

    return signals

def fuse_scores(text_scores, photo_nudges, numeric_sigs):
    # combines all three sources into one score per axis
    # text gives us a 0-100 float, photo and numeric give us a letter nudge
    # we convert the nudges into a small score boost and blend everything

    axis_map = ["E_I", "N_S", "T_F", "J_P"]
    final_scores = {}

    for axis in axis_map:
        # start with text scores (already 0-100)
        text = text_scores[axis]
        letters = list(text.keys())
        first, second = letters[0], letters[1]

        # convert to a single number where positive = first letter, negative = second
        # e.g. E_I: positive = E leaning, negative = I leaning
        text_lean = (text[first] - text[second]) * WEIGHTS["text"]

        # photo nudge -- adds or subtracts a small flat amount
        photo_lean = 0
        if axis in photo_nudges:
            photo_lean = 15 if photo_nudges[axis] == first else -15
        photo_lean *= WEIGHTS["photo"]

        # numeric nudge -- same idea, smaller effect
        numeric_lean = 0
        if axis == "E_I":
            if "E_I_numeric" in numeric_sigs:
                numeric_lean = 10 if numeric_sigs["E_I_numeric"] == first else -10
            numeric_lean *= WEIGHTS["numeric"]

        total = text_lean + photo_lean + numeric_lean

        # convert back to per-letter confidence scores
        # total > 0 means first letter wins, < 0 means second wins
        first_score = round(50 + (total / 2), 1)
        second_score = round(100 - first_score, 1)

        final_scores[axis] = {
            first: max(0, min(100, first_score)),
            second: max(0, min(100, second_score)),
            "winner": first if total > 0 else second
        }

    return final_scores

def get_mbti_type(final_scores):
    # just reads the winner from each axis
    return "".join(final_scores[axis]["winner"] for axis in ["E_I", "N_S", "T_F", "J_P"])

def analyze(bio, captions, dms, music, opinions, followers, following, profile_photo_path=None):
    # main function that ties everything together
    combined_text = assemble_text(bio, captions, dms, music, opinions)
    text_scores = classify_text(combined_text) if combined_text.strip() else {}

    photo_nudges = {}
    photo_signals = None
    if profile_photo_path:
        profile_signals = analyze_profile_photo(profile_photo_path)
        photo_nudges = photo_to_mbti_signals(profile_signals)
        photo_signals = profile_signals

    numeric_sigs = numeric_signals(followers, following)

    if not text_scores:
        return None, None, None

    final_scores = fuse_scores(text_scores, photo_nudges, numeric_sigs)
    mbti_type = get_mbti_type(final_scores)

    return mbti_type, final_scores, photo_signals


# quick test to make sure fusion is working
if __name__ == "__main__":
    mbti, scores, photo = analyze(
        bio="living slowly, thinking deeply 🌿 | philosophy student | coffee always",
        captions="some days are just for sitting with it. new city, same soul. quiet mornings > everything",
        dms="idk i just feel like people drain me sometimes lol. i'd rather just stay in",
        music="sufjan stevens, phoebe bridgers, that one arctic monkeys album everyone has a phase about",
        opinions="",
        followers=800,
        following=300,
        profile_photo_path=None
    )
    print("final scores:")
    for axis, data in scores.items():
        print(f"  {axis}: {data}")
    print(f"\npredicted type: {mbti}")