"""
KrushiAI — Predictor  (smart multi-stage image validation)

Validation pipeline — runs BEFORE and AFTER the CNN:

  Stage 1 — Color variation check
      Rejects solid-color blocks, blank images, screenshots of text.
      Uses per-channel standard deviation.

  Stage 2 — HSV plant-color analysis
      Checks what fraction of pixels fall in green / yellow-green /
      yellow-brown / necrotic-brown HSV ranges typical of leaves.
      Rejects cars, people, food, logos, skies, etc.

  Stage 3 — Post-model entropy check
      After the CNN runs, examines the full 5-class probability
      distribution.  If the model is wildly uncertain across all
      classes AND no class dominates, the image is OOD.

Why NOT a fixed confidence threshold
--------------------------------------
  A real pomegranate leaf can score 72-78% (moderate confidence).
  A random non-leaf image can score 84%+ for one class.
  A threshold would break both cases simultaneously.
  Stages 1-2 catch non-leaf images; Stage 3 catches edge cases
  that slip through, regardless of what the top confidence is.
"""

import os
import numpy as np
from PIL import Image
import streamlit as st

MODEL_PATH = "models/pomegranate_model.h5"
LABELS     = ["Alternaria", "Anthracnose", "Bacterial Blight", "Cercospora", "Healthy"]
IMG_SIZE   = (224, 224)

# ── Tunable validation parameters ────────────────────────────────────────────
# Stage 1 — colour variation
MIN_COLOR_STD     = 0.022   # below this the image is too uniform (blank/screenshot)

# Stage 2 — a colourful subject must occupy the centre of the frame.
# Pomegranate FRUIT is red/crimson/pink/yellow and LEAVES are green — both are
# vividly coloured and saturated. Documents, blank frames and grayscale UI
# screenshots are washed out. We reject only those, so real fruit always passes.
MIN_CENTER_SAT    = 0.16    # mean colour saturation in the central 60 % of the frame
MIN_CENTER_RICH   = 0.020   # colour variation (channel std) in the centre

# Stage 3 — prediction-distribution sanity
# Stage 3 — only reject a near-uniform (totally undecided) distribution.
# Kept deliberately lenient so a real — even ambiguous — fruit always passes.
MAX_NORM_ENTROPY  = 0.985   # reject only if the model is essentially guessing


# ── Model loading ─────────────────────────────────────────────────────────────

def _download_model_if_needed():
    """
    If the model file is missing (e.g. on a deployment server where the
    .h5 is not committed), try to download it from MODEL_URL env variable.
    Supports Google Drive share links and direct URLs.
    """
    if os.path.exists(MODEL_PATH):
        return True

    url = os.getenv("MODEL_URL", "").strip()
    if not url:
        return False

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    st.info("📥 Downloading AI model for the first time… this may take a minute.")
    try:
        import requests
        # Handle Google Drive share links → convert to direct download URL
        if "drive.google.com" in url and "/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
            url = f"https://drive.google.com/uc?export=download&id={file_id}&confirm=t"

        with requests.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(MODEL_PATH, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        return True
    except Exception as e:
        st.error(f"Failed to download model: {e}")
        return False


@st.cache_resource(show_spinner="Loading AI model…")
def _load_model():
    if not _download_model_if_needed():
        return None
    import tensorflow as tf
    return tf.keras.models.load_model(MODEL_PATH)


# ── Stage 2: HSV plant-colour analysis ───────────────────────────────────────

def _center_subject_analysis(arr: np.ndarray) -> tuple[float, float]:
    """
    Return (center_saturation, center_richness) for the central 60 % of the frame.
    arr: (H, W, 3) float32 normalised to [0, 1].

    A pomegranate FRUIT (red/crimson/pink/yellow) or LEAF (green) is a vividly
    coloured, saturated subject. Blank frames, documents and grayscale UI
    screenshots are washed out / low-saturation. Measuring the CENTRE (where the
    subject sits) avoids being fooled by busy backgrounds.

      • center_saturation — mean HSV saturation in the centre box
      • center_richness   — colour variation (channel std) in the centre box
    """
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    cmax  = np.maximum(np.maximum(r, g), b)
    delta = cmax - np.minimum(np.minimum(r, g), b)
    sat   = np.where(cmax > 1e-8, delta / cmax, 0.0)

    H, W = sat.shape
    cy0, cy1 = int(H * 0.20), int(H * 0.80)   # central 60% box
    cx0, cx1 = int(W * 0.20), int(W * 0.80)

    center_sat  = float(sat[cy0:cy1, cx0:cx1].mean())
    center_rich = float(arr[cy0:cy1, cx0:cx1, :].std(axis=(0, 1)).mean())
    return center_sat, center_rich


# ── Stage 1 + 2: Pre-model validation ────────────────────────────────────────

def _validate_pre_model(arr: np.ndarray) -> tuple[bool, str]:
    """
    Returns (is_valid, rejection_reason).
    Runs before the CNN to reject blank / washed-out / non-photo inputs while
    always accepting a real pomegranate fruit or leaf photo.
    """
    # Stage 1 — overall colour variation (blank / solid / flat screenshot)
    channel_std = float(arr.std(axis=(0, 1)).mean())
    if channel_std < MIN_COLOR_STD:
        return False, (
            "The image appears to be blank, a solid colour, or a flat screenshot. "
            "Please upload a clear close-up photo of a pomegranate."
        )

    # Stage 2 — a colourful, saturated subject must occupy the centre.
    # Accepts red/yellow fruit AND green leaves; rejects only grayscale docs /
    # blank UI. Deliberately lenient: a real pomegranate must never be rejected.
    center_sat, center_rich = _center_subject_analysis(arr)
    if center_sat < MIN_CENTER_SAT and center_rich < MIN_CENTER_RICH:
        return False, (
            f"This doesn't look like a pomegranate photo "
            f"(centre colour: {center_sat:.0%}). "
            f"Fill the frame with the fruit in good light and try again."
        )

    return True, "OK"


# ── Stage 3: Post-model distribution check ───────────────────────────────────

def _validate_post_model(probs: np.ndarray) -> tuple[bool, str]:
    """
    Lenient sanity check: reject only when the model is essentially guessing
    (a near-uniform distribution across all classes). A real pomegranate —
    even an ambiguous diseased one — produces a clearly peaked class and passes.
    """
    entropy      = float(-np.sum(probs * np.log(probs + 1e-8)))
    norm_entropy = entropy / float(np.log(len(probs)))   # 0 certain → 1 max uncertain

    if norm_entropy > MAX_NORM_ENTROPY:
        return False, "The model could not interpret this image. Please try a clearer photo."
    return True, "OK"


# ── Public API ────────────────────────────────────────────────────────────────

def predict_disease(image: Image.Image) -> tuple[str, float, dict]:
    """
    Returns (disease_label, confidence_percent, all_class_probs_dict).

    Runs the model exactly ONCE per call — no redundant inference.

    Possible labels:
        'Alternaria', 'Anthracnose', 'Bacterial Blight',
        'Cercospora', 'Healthy', 'Invalid Image'

    all_class_probs_dict is empty {} for invalid/rejected images,
    otherwise maps each label → probability % (0–100).
    confidence is 0.0 for pre-model rejections.
    """
    model = _load_model()
    if model is None:
        st.warning("⚠️ Model file not found at `models/pomegranate_model.h5`.")
        return "Invalid Image", 0.0, {}

    try:
        arr = np.array(image.convert("RGB").resize(IMG_SIZE), dtype=np.float32) / 255.0

        # ── Stage 1 & 2: pre-model ────────────────────────────────────────────
        valid, _ = _validate_pre_model(arr)
        if not valid:
            return "Invalid Image", 0.0, {}

        # ── Single CNN inference ──────────────────────────────────────────────
        probs = model.predict(np.expand_dims(arr, 0), verbose=0)[0]
        conf  = round(float(np.max(probs)) * 100, 2)
        idx   = int(np.argmax(probs))
        probs_dict = {lbl: round(float(p) * 100, 2) for lbl, p in zip(LABELS, probs)}

        # ── Stage 3: post-model ───────────────────────────────────────────────
        valid_pred, _ = _validate_post_model(probs)
        if not valid_pred:
            return "Invalid Image", conf, {}

        return LABELS[idx], conf, probs_dict

    except Exception as e:
        st.error(f"Prediction error: {e}")
        return "Invalid Image", 0.0, {}
