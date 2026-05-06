import tensorflow as tf
import numpy as np
from PIL import Image
import streamlit as st

@st.cache_resource
def load_cnn_model():
    """Loads the model from the models folder."""
    return tf.keras.models.load_model('models/pomegranate_model.h5')

def predict_disease(image):
    """Processes image and returns prediction only if confidence is high."""
    model = load_cnn_model()
    
    # 1. Preprocessing (Ensure this matches your training 224x224)
    img = image.resize((224, 224))
    img_array = np.array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    
    # 2. Get Raw Predictions
    predictions = model.predict(img_array)
    
    # 3. Class labels
    labels = ['Alternaria', 'Anthracnose', 'Bacterial Blight', 'Healthy']
    
    # 4. Extract Confidence and Index
    idx = np.argmax(predictions)
    confidence = float(np.max(predictions) * 100)
    
    # --- THE FIX: Confidence Threshold ---
    # If the model is less than 85% sure, it's likely a non-leaf image.
    THRESHOLD = 55.0 
    
    if confidence < THRESHOLD:
        label = "Invalid Image / Not Recognized"
    else:
        label = labels[idx]
    
    return label, confidence