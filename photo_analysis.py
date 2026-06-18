"""
photo_analysis.py

extracts personality signals from a photo using two approaches:
- deepface: dominant emotion -> F/T signal
- cv / numpy logic: solo vs group, eye contact, background, smile intensity -> E/I signals
"""

import numpy as np

def analyze_photo(image_path):
    """
    takes a photo path and returns signal nudges for E_I and T_F.
    returns a dict like {"E_I": float, "T_F": float} where values
    are in [-1, 1], negative = first key (E or T), positive = second (I or F).
    
    returns None if analysis fails or no image provided.
    """
    if image_path is None:
        return None

    results = {}

    # deepface: emotion -> T/F signal
    try:
        from deepface import DeepFace
        analysis = DeepFace.analyze(
            img_path=image_path,
            actions=["emotion"],
            enforce_detection=False,
            silent=True
        )

        if isinstance(analysis, list):
            analysis = analysis[0]

        dominant_emotion = analysis.get("dominant_emotion", "")
        emotion_scores = analysis.get("emotion", {})

        # F types tend toward warmer emotions, T types toward neutral/analytical
        # these are soft signals at best
        feeling_emotions = {"happy", "surprise", "fear", "sad", "disgust"}
        thinking_emotions = {"neutral", "angry"}

        feeling_score = sum(emotion_scores.get(e, 0) for e in feeling_emotions)
        thinking_score = sum(emotion_scores.get(e, 0) for e in thinking_emotions)
        total = feeling_score + thinking_score

        if total > 0:
            # positive = F lean, negative = T lean
            tf_val = (feeling_score - thinking_score) / total
            results["T_F"] = tf_val * 0.6  # scale down: emotion is a loose proxy

    except Exception as e:
        print(f"deepface failed: {e}")
        # don't crash the whole thing if deepface errors out

    # ----- cv logic for E/I signals -----
    try:
        import cv2

        img = cv2.imread(image_path)
        if img is None:
            return results if results else None

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        height, width = img.shape[:2]

        ei_signals = []

        # 1. solo vs group photo using face detection
        # more faces = more social = E lean
        try:
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
            face_count = len(faces)

            if face_count == 1:
                ei_signals.append(0.3)   # solo photo = mild I
            elif face_count >= 3:
                ei_signals.append(-0.5)  # group photo = E lean
            elif face_count == 2:
                ei_signals.append(-0.2)  # with one person = slight E lean
            # 0 faces detected = no signal

        except Exception:
            pass

        # 2. eye contact with camera 
        # (check if biggest face has eyes roughly centered toward camera)
        # this is a rough heuristic, not perfect
        try:
            eye_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_eye.xml"
            )
            if len(faces) >= 1:
                # look at the biggest face
                biggest_face = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
                fx, fy, fw, fh = biggest_face
                face_roi = gray[fy:fy+fh, fx:fx+fw]
                eyes = eye_cascade.detectMultiScale(face_roi, scaleFactor=1.1, minNeighbors=3)

                if len(eyes) >= 2:
                    # eyes detected facing camera = slightly more E (direct, present)
                    ei_signals.append(-0.15)

        except Exception:
            pass

        # 3. background context: busy/social setting vs alone/nature
        # crude approach: check color diversity in the background region
        # lots of varied colors = busy/social, uniform = solitary
        try:
            # use top 30% and sides as "background"
            bg_region = img_rgb[:int(height * 0.3), :]
            bg_colors = bg_region.reshape(-1, 3).astype(float)

            # standard deviation across color channels as proxy for busyness
            color_std = np.std(bg_colors, axis=0).mean()

            if color_std > 60:
                ei_signals.append(-0.2)  # busy background = mild E lean
            elif color_std < 20:
                ei_signals.append(0.2)   # plain/nature background = mild I lean

        except Exception:
            pass

        # 4. smile intensity as soft F/T signal
        # this goes into T_F not E_I
        try:
            smile_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_smile.xml"
            )
            if len(faces) >= 1:
                biggest_face = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)[0]
                fx, fy, fw, fh = biggest_face
                face_roi = gray[fy:fy+fh, fx:fx+fw]
                smiles = smile_cascade.detectMultiScale(
                    face_roi, scaleFactor=1.8, minNeighbors=20
                )

                if len(smiles) > 0:
                    # has a big visible smile = mild F lean
                    results["T_F"] = results.get("T_F", 0) + 0.15

        except Exception:
            pass

        # average the E/I signals
        if ei_signals:
            results["E_I"] = np.mean(ei_signals)

    except ImportError:
        print("cv2 not available, skipping cv photo analysis")
    except Exception as e:
        print(f"cv analysis failed: {e}")

    return results if results else None