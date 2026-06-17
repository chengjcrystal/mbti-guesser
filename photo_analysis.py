import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import deepface
from deepface import DeepFace

# load clip once at startup -- it's a vision-language model that scores
# how well an image matches a text description
clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

def clip_score(image_path, labels):
    # clip scores each label against the image and returns confidence %s
    # think of it like zero-shot classification but for images
    image = Image.open(image_path).convert("RGB")
    inputs = clip_processor(text=labels, images=image, return_tensors="pt", padding=True)
    
    with torch.no_grad():
        outputs = clip_model(**inputs)
    
    # softmax turns raw scores into probabilities that add up to 100%
    probs = outputs.logits_per_image.softmax(dim=1)[0]
    return {label: round(float(probs[i]) * 100, 1) for i, label in enumerate(labels)}

def analyze_profile_photo(image_path):
    # runs all our signal checks on a single photo and returns a dict of mbti signals
    signals = {}

    # clip checks (good for broad image-level questions)

    # is this even a real person or something else entirely
    content_scores = clip_score(image_path, [
        "a real persons face",
        "a cartoon or anime character",
        "a celebrity or idol photo",
        "a landscape or scenery photo",
        "an aesthetic or object photo"
    ])
    signals["photo_type"] = max(content_scores, key=content_scores.get)
    signals["photo_type_scores"] = content_scores

    # solo vs group: e/i signal
    group_scores = clip_score(image_path, [
        "one person alone in the photo",
        "multiple people or a group in the photo"
    ])
    signals["solo_or_group"] = max(group_scores, key=group_scores.get)

    # posed/curated vs candid: j/p signal
    vibe_scores = clip_score(image_path, [
        "a posed and curated photo",
        "a candid and natural photo"
    ])
    signals["photo_vibe"] = max(vibe_scores, key=vibe_scores.get)

    # warm vs cool tones: softer aesthetic signal
    tone_scores = clip_score(image_path, [
        "warm tones, golden, cozy aesthetic",
        "cool tones, blue, minimal aesthetic",
        "dark moody tones",
        "bright colorful tones"
    ])
    signals["color_tone"] = max(tone_scores, key=tone_scores.get)

    # deepface checks (good for actual face-level details)
    # only run if clip thinks there's a real person in the photo
    real_person_confidence = content_scores.get("a real persons face", 0)

    if real_person_confidence > 40:
        try:
            # deepface can detect emotion, age, gender from a face
            analysis = DeepFace.analyze(
                image_path,
                actions=["emotion"],
                enforce_detection=False  # don't crash if face is partially hidden
            )
            # analysis returns a list, grab the first (most prominent) face
            face = analysis[0]
            signals["dominant_emotion"] = face["dominant_emotion"]
            signals["emotion_scores"] = face["emotion"]

            # smiling is a decent f signal: warmth/expressiveness
            signals["is_smiling"] = face["dominant_emotion"] in ["happy"]

            # check if a face was actually detected or just guessed
            signals["face_detected"] = face["face_confidence"] > 0.7

        except Exception as e:
            # deepface sometimes fails on unusual photos, that's ok
            signals["face_detected"] = False
            signals["deepface_error"] = str(e)
    else:
        # no real face found, mild i signal (hidden/obscured self)
        signals["face_detected"] = False

    return signals

def photo_to_mbti_signals(profile_signals):
    # translates raw photo analysis into mbti axis nudges
    # these are soft signals so they influence but don't override text scores
    mbti_nudges = {}

    # hidden face or no real person = mild i lean
    if not profile_signals.get("face_detected", False):
        mbti_nudges["E_I"] = "I"
    elif "one person alone" in profile_signals.get("solo_or_group", ""):
        mbti_nudges["E_I"] = "I"
    else:
        mbti_nudges["E_I"] = "E"

    # smiling = mild f lean
    if profile_signals.get("is_smiling"):
        mbti_nudges["T_F"] = "F"

    # posed = mild j lean, candid = mild p lean
    if "posed" in profile_signals.get("photo_vibe", ""):
        mbti_nudges["J_P"] = "J"
    elif "candid" in profile_signals.get("photo_vibe", ""):
        mbti_nudges["J_P"] = "P"

    return mbti_nudges


# test: swap in any image path on your computer
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: python photo_analysis.py path/to/photo.jpg")
        print("drag an image file into your terminal to get its path")
    else:
        image_path = sys.argv[1]
        print(f"\nanalyzing: {image_path}")
        print("running clip + deepface...\n")

        signals = analyze_profile_photo(image_path)
        print("raw signals:")
        for k, v in signals.items():
            print(f"  {k}: {v}")

        nudges = photo_to_mbti_signals(signals)
        print("\nmbti nudges from photo:")
        print(nudges)