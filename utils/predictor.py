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

import numpy as np
from PIL import Image
import streamlit as st

MODEL_PATH = "models/pomegranate_model.h5"
LABELS     = ["Alternaria", "Anthracnose", "Bacterial Blight", "Cercospora", "Healthy"]
IMG_SIZE   = (224, 224)

# ── Tunable validation parameters ────────────────────────────────────────────
# Stage 1
MIN_COLOR_STD   = 0.025   # images with lower std are "too uniform"

# Stage 2
MIN_PLANT_RATIO = 0.18    # need ≥18 % plant-coloured pixels

# Stage 3
MAX_NORM_ENTROPY = 0.90   # normalised entropy upper bound  (0=certain, 1=max uncertain)
MIN_TOP_PROB     = 0.38   # top class must be at least this confident for OOD rejection
                          # (only applied when entropy is also high)


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

def _plant_pixel_ratio(arr: np.ndarray) -> float:
    """
    Return the fraction of pixels that fall in plant-like HSV colour ranges.
    arr: (H, W, 3) float32 normalised to [0, 1].

    Covered ranges:
      • Fresh green (healthy leaf)         hue  55–165°, sat >0.12, val >0.07
      • Yellow-green (mild chlorosis)      hue  40– 75°, sat >0.15, val >0.15
      • Yellow-brown (disease lesions)     hue  15– 55°, sat >0.15, val 0.10–0.80
      • Dark necrotic/brown tissue         low sat, dark val, reddish tone
    """
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    cmax  = np.maximum(np.maximum(r, g), b)
    delta = cmax - np.minimum(np.minimum(r, g), b)
    eps   = 1e-8

    # Saturation and Value
    sat = np.where(cmax > eps, delta / cmax, 0.0)
    val = cmax

    # Hue (0–360 °)
    hue   = np.zeros_like(r)
    m_r   = (cmax == r)
    m_g   = (cmax == g) & ~m_r
    m_b   = ~m_r & ~m_g

    hue[m_r] = (60.0 * ((g[m_r] - b[m_r]) / (delta[m_r] + eps))) % 360
    hue[m_g] =  60.0 * ((b[m_g] - r[m_g]) / (delta[m_g] + eps)) + 120.0
    hue[m_b] =  60.0 * ((r[m_b] - g[m_b]) / (delta[m_b] + eps)) + 240.0
    hue      =  hue % 360

    fresh_green   = (hue >= 55)  & (hue <= 165) & (sat > 0.12) & (val > 0.07)
    yellow_green  = (hue >= 40)  & (hue <= 75)  & (sat > 0.15) & (val > 0.15)
    yellow_brown  = (hue >= 15)  & (hue <= 55)  & (sat > 0.15) & (val > 0.10) & (val < 0.80)
    dark_necrotic = (sat < 0.40) & (val > 0.05) & (val < 0.55) & (r >= g * 0.80) & (g >= b * 1.02)

    plant_px = np.sum(fresh_green | yellow_green | yellow_brown | dark_necrotic)
    return float(plant_px) / (arr.shape[0] * arr.shape[1])


# ── Stage 1 + 2: Pre-model validation ────────────────────────────────────────

def _validate_pre_model(arr: np.ndarray) -> tuple[bool, str]:
    """
    Returns (is_valid, rejection_reason).
    Called before the CNN to avoid wasting inference on obvious non-leaf images.
    """
    # Stage 1 — color variation
    channel_std = float(arr.std(axis=(0, 1)).mean())
    if channel_std < MIN_COLOR_STD:
        return False, (
            "The image appears to be blank, a solid colour, or a screenshot. "
            "Please upload a clear photo of a pomegranate leaf."
        )

    # Stage 2 — HSV plant ratio
    ratio = _plant_pixel_ratio(arr)
    if ratio < MIN_PLANT_RATIO:
        return False, (
            f"The image does not appear to contain a leaf "
            f"(plant-like content detected: {ratio:.0%}). "
            f"Please upload a pomegranate leaf image with good lighting."
        )

    return True, "OK"


# ── Stage 3: Post-model entropy check ────────────────────────────────────────

def _validate_post_model(probs: np.ndarray) -> tuple[bool, str]:
    """
    Examines the shape of the full probability distribution.

    A real pomegranate leaf produces a peaked distribution
    (one or two dominant classes) even at moderate confidence.

    A non-leaf image that somehow passed Stage 1/2 often produces
    a nearly flat distribution — high entropy — where the model
    can't commit to any class.  We only reject when BOTH entropy
    is very high AND the top probability is low, so we never
    penalise genuine leaves with moderate confidence.
    """
    entropy      = float(-np.sum(probs * np.log(probs + 1e-8)))
    max_entropy  = float(np.log(len(probs)))          # log(5) ≈ 1.609
    norm_entropy = entropy / max_entropy               # 0 → certain, 1 → max uncertain
    top_prob     = float(np.max(probs))

    if norm_entropy > MAX_NORM_ENTROPY and top_prob < MIN_TOP_PROB:
        return False, (
            f"The model cannot confidently identify this as a pomegranate leaf "
            f"(top confidence: {top_prob*100:.1f}%, uncertainty: {norm_entropy:.0%}). "
            f"Please try a clearer, well-lit leaf image."
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
