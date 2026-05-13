"""
KrushiAI — Predictor
- Loads the Keras CNN model once and caches it
- Returns (label, confidence_percent)
- Returns ("Invalid Image", confidence) if below threshold or model missing
"""

import numpy as np
from PIL import Image
import streamlit as st

MODEL_PATH  = "models/pomegranate_model.h5"
LABELS      = ["Alternaria", "Anthracnose", "Bacterial Blight", "Cercospora", "Healthy"]
IMG_SIZE    = (224, 224)
THRESHOLD   = 55.0   # % — below this, image is considered unrecognized


@st.cache_resource(show_spinner="Loading AI model…")
def _load_model():
    import os
    if not os.path.exists(MODEL_PATH):
        return None
    import tensorflow as tf
    return tf.keras.models.load_model(MODEL_PATH)


def predict_disease(image: Image.Image) -> tuple[str, float]:
    """
    Returns (disease_label, confidence_percent).
    Possible labels: 'Alternaria', 'Anthracnose', 'Bacterial Blight',
                     'Healthy', 'Invalid Image'
    """
    model = _load_model()

    if model is None:
        st.warning("⚠️ Model file not found at `models/pomegranate_model.h5`.")
        return "Invalid Image", 0.0

    try:
        # Pre-process — must match training pipeline
        img        = image.convert("RGB").resize(IMG_SIZE)
        img_array  = np.array(img, dtype=np.float32) / 255.0
        img_array  = np.expand_dims(img_array, axis=0)

        predictions = model.predict(img_array, verbose=0)
        idx         = int(np.argmax(predictions))
        confidence  = float(np.max(predictions) * 100)

        label = LABELS[idx] if confidence >= THRESHOLD else "Invalid Image"
        return label, round(confidence, 2)

    except Exception as e:
        st.error(f"Prediction error: {e}")
        return "Invalid Image", 0.0
