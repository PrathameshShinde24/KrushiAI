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
MIN_COLOR_STD     = 0.025   # below this the image is too uniform (blank/screenshot)

# Stage 2 — green dominance (leaf must be the subject)
MIN_CENTER_GREEN  = 0.22    # ≥22 % leaf-green in the central 60 % of the frame, OR
MIN_OVERALL_GREEN = 0.34    # ≥34 % leaf-green across the whole frame

# Stage 3 — prediction-distribution sanity
MAX_NORM_ENTROPY  = 0.88    # normalised entropy upper bound (0 certain → 1 max uncertain)
MIN_TOP_PROB      = 0.55    # a real leaf usually peaks above this
MIN_MARGIN        = 0.18    # top-1 must beat top-2 by this margin when confidence is low


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

def _green_analysis(arr: np.ndarray) -> tuple[float, float]:
    """
    Return (overall_green_ratio, center_green_ratio).
    arr: (H, W, 3) float32 normalised to [0, 1].

    "Green" = leaf-like pixels: hue 60–170°, with enough saturation and value.
    This deliberately EXCLUDES beige walls, skin, sky, and brown soil — which
    is what made the old broad "plant" heuristic let non-leaf photos through.

    A genuine leaf scan is green-dominated, and crucially green in the CENTER
    of the frame (the leaf is the subject). Background foliage in a snapshot
    only adds green at the edges, so the center ratio is the stronger signal.
    """
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    cmax  = np.maximum(np.maximum(r, g), b)
    delta = cmax - np.minimum(np.minimum(r, g), b)
    eps   = 1e-8
    sat   = np.where(cmax > eps, delta / cmax, 0.0)
    val   = cmax

    hue = np.zeros_like(r)
    m_r = (cmax == r)
    m_g = (cmax == g) & ~m_r
    m_b = ~m_r & ~m_g
    hue[m_r] = (60.0 * ((g[m_r] - b[m_r]) / (delta[m_r] + eps))) % 360
    hue[m_g] =  60.0 * ((b[m_g] - r[m_g]) / (delta[m_g] + eps)) + 120.0
    hue[m_b] =  60.0 * ((r[m_b] - g[m_b]) / (delta[m_b] + eps)) + 240.0
    hue = hue % 360

    # Leaf green (incl. yellow-green chlorosis), green channel must dominate.
    green = (hue >= 60) & (hue <= 170) & (sat > 0.18) & (val > 0.12) & (g > r) & (g > b)

    overall = float(green.mean())

    H, W = green.shape
    cy0, cy1 = int(H * 0.20), int(H * 0.80)   # central 60% box
    cx0, cx1 = int(W * 0.20), int(W * 0.80)
    center = float(green[cy0:cy1, cx0:cx1].mean())

    return overall, center


# ── Stage 1 + 2: Pre-model validation ────────────────────────────────────────

def _validate_pre_model(arr: np.ndarray) -> tuple[bool, str]:
    """
    Returns (is_valid, rejection_reason).
    Runs before the CNN to reject obvious non-leaf images.
    """
    # Stage 1 — colour variation (blank / solid / screenshot)
    channel_std = float(arr.std(axis=(0, 1)).mean())
    if channel_std < MIN_COLOR_STD:
        return False, (
            "The image appears to be blank, a solid colour, or a screenshot. "
            "Please upload a clear photo of a pomegranate leaf."
        )

    # Stage 2 — green dominance, center-weighted
    overall_green, center_green = _green_analysis(arr)

    # Accept only if the leaf is clearly present:
    #   • the center of the frame is green (leaf is the subject), OR
    #   • green fills a large share of the whole frame (leaf fills it).
    # Background foliage in a snapshot fails both (green only at the edges).
    if center_green < MIN_CENTER_GREEN and overall_green < MIN_OVERALL_GREEN:
        return False, (
            f"This doesn't look like a pomegranate leaf "
            f"(leaf-green in center: {center_green:.0%}, overall: {overall_green:.0%}). "
            f"Fill the frame with a single leaf in good light and try again."
        )

    return True, "OK"


# ── Stage 3: Post-model distribution check ───────────────────────────────────

def _validate_post_model(probs: np.ndarray) -> tuple[bool, str]:
    """
    Examines the probability distribution shape.

    Out-of-distribution images that slip past the colour gate often produce
    either a flat (high-entropy) distribution OR two near-tied top classes —
    the model can't commit. A genuine leaf yields a clearly peaked top class
    with a comfortable margin over the runner-up.
    """
    entropy      = float(-np.sum(probs * np.log(probs + 1e-8)))
    norm_entropy = entropy / float(np.log(len(probs)))   # 0 certain → 1 max uncertain
    top_prob     = float(np.max(probs))

    ordered = np.sort(probs)[::-1]
    margin  = float(ordered[0] - ordered[1])             # top-1 minus top-2

    # Reject if the model is broadly unsure, or top-1 and top-2 are near-tied.
    if (norm_entropy > MAX_NORM_ENTROPY and top_prob < MIN_TOP_PROB) or \
       (top_prob < MIN_TOP_PROB and margin < MIN_MARGIN):
        return False, (
            f"The model could not confidently identify this as a pomegranate leaf "
            f"(top confidence {top_prob*100:.0f}%, margin {margin*100:.0f}%). "
            f"Please try a clearer, well-lit close-up of a single leaf."
        )
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
