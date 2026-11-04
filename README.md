<div align="center">

<img src="assets/images/logo.png" alt="KrushiAI Logo" width="90" style="border-radius:16px"/>

# KrushiAI

**AI-Powered Pomegranate Fruit Disease Detection Platform**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.51%2B-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.13%2B-FF6F00?style=flat-square&logo=tensorflow&logoColor=white)](https://tensorflow.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=flat-square&logo=mongodb&logoColor=white)](https://mongodb.com/atlas)
[![License](https://img.shields.io/badge/License-MIT-10b981?style=flat-square)](LICENSE)

*Detect pomegranate fruit diseases instantly using deep learning — upload a photo or use your camera and get an AI diagnosis with treatment recommendations in seconds.*

</div>

---

## Overview

KrushiAI is a full-stack web application that helps farmers and agronomists identify pomegranate fruit diseases early using a trained Convolutional Neural Network (CNN). The platform provides real-time diagnostics, historical scan tracking, and data-driven field health insights through an intuitive dark-themed dashboard.

### Detected Diseases

| Disease | Type | Severity |
|---|---|---|
| **Alternaria** | Fungal Infection | Medium Risk |
| **Anthracnose** | Fungal Pathogen | High Risk |
| **Bacterial Blight** | Bacterial Pathogen | High Risk |
| **Cercospora** | Fungal Spot | Medium Risk |
| **Healthy** | No Disease | No Risk |

---

## Features

- **AI Diagnostic Scanner** — image checks before and after the CNN (face detection, colour variation, centre colour, prediction entropy) reject non-fruit photos; returns per-class confidence bars
- **Camera Support** — Scan fruit directly using your device's webcam, no upload required
- **Treatment Plans** — Each diagnosis includes 3 actionable treatment steps tailored to the identified disease
- **Interactive Dashboard** — Stats overview, recent scans, and quick-action cards
- **Scan History** — Full scan log with Plotly charts (disease breakdown donut + scans-over-time line), search, and delete
- **Weather & Disease Risk** — Live weather via OpenWeatherMap + High/Medium/Low pomegranate disease risk scoring
- **Crop Advisor** — Rule-based recommendation engine scoring 13 Indian crops by soil × season × water × region
- **Government Schemes** — Searchable database of 10 central schemes (PM-KISAN, PMFBY, KCC, PMKSY, and more)
- **Agri Hub** — Live agricultural news (NewsAPI, cached 1hr) + 15 rotating daily farming tips
- **Multilingual** — Full UI in English, Hindi (हिंदी), and Marathi (मराठी) via sidebar switcher
- **Secure Authentication** — PBKDF2-HMAC-SHA256 password hashing, rate limiting (5 attempts → 15-min lockout), XSS prevention
- **User Profiles** — Update display name, change password, view personal stats
- **MongoDB Atlas** — Cloud-hosted database with aggregation pipelines and TTL-based auto-expiring rate-limit records

---

## Screenshots

> Dashboard · Scanner · History · Profile

*(Add screenshots to `assets/images/screenshots/` and link them here)*

---

## Project Structure

```
KrushiAI/
├── app.py                     # Main Streamlit application (all pages & routing)
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (not committed)
│
├── models/
│   └── pomegranate_model.h5   # Trained MobileNetV2 weights — 5-class, input (224,224,3)
│
├── utils/
│   ├── predictor.py           # Model inference + image validation
│   ├── database.py            # MongoDB Atlas — CRUD, aggregation pipeline, TTL indexes
│   ├── auth.py                # Authentication, rate limiting, password policy, XSS prevention
│   ├── i18n.py                # Translations — English, Hindi (हिंदी), Marathi (मराठी)
│   ├── weather.py             # OpenWeatherMap API + disease risk scoring
│   ├── crop_advisor.py        # Rule-based crop recommendation engine (13 crops)
│   ├── schemes.py             # Government schemes database (10 central schemes)
│   └── news.py                # NewsAPI integration + rotating farming tips
│
└── assets/
    ├── css/
    │   └── style.css          # Custom dark navy/emerald design system
    └── images/
        ├── logo.png
        ├── login_bg.jpg
        └── hero_banner.jpg
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher (the code uses `str | None` type hints, so Python 3.9 will not start it)
- A [MongoDB Atlas](https://mongodb.com/atlas) account (free tier works)
- The trained model file `pomegranate_model.h5` placed in the `models/` directory

### 1. Clone the repository

```bash
git clone https://github.com/PrathameshShinde24/KrushiAI.git
cd KrushiAI
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy `.env.example` to `.env` in the project root and fill in your values:

```env
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?appName=KrushiAI
MONGODB_DB=krushiai

# Optional
OPENWEATHER_API_KEY=<your OpenWeatherMap key>   # Weather page
NEWS_API_KEY=<your NewsAPI key>                 # Agri Hub news
MODEL_URL=<direct or Google Drive link to the .h5>  # downloads the model if models/ is empty
```

> **Never commit your `.env` file.** It is already listed in `.gitignore`.

### 4. Add the trained model

Place your trained model at:

```
models/pomegranate_model.h5
```

Or set `MODEL_URL` in `.env` and the app downloads it on first run.

The file must hold weights for a MobileNetV2 base + GlobalAveragePooling2D + Dropout(0.3) + Dense(5, softmax) head, with input shape `(224, 224, 3)` and the 5 classes in this order:

```
["Alternaria", "Anthracnose", "Bacterial Blight", "Cercospora", "Healthy"]
```

### 5. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit, custom CSS (Inter font, dark navy/emerald tokens) |
| **AI Model** | TensorFlow / Keras CNN — input `(224,224,3)`, 5-class softmax |
| **Database** | MongoDB Atlas via PyMongo — aggregation pipelines, TTL indexes |
| **Auth** | PBKDF2-HMAC-SHA256 (260k iterations), rate limiting, XSS prevention |
| **Charts** | Plotly (donut pie + spline line, dark-themed) |
| **Image Input** | PIL (upload) + `st.camera_input()` (webcam) |
| **Config** | python-dotenv for secret management |

---

## Security

KrushiAI implements several security layers:

- **Password hashing** — PBKDF2-HMAC-SHA256 with a random 16-byte salt and 260,000 iterations (stdlib `hashlib`, no external deps)
- **Rate limiting** — After 5 failed login attempts, the account is locked for 15 minutes. Stored in MongoDB with a TTL index that auto-expires records — survives server restarts
- **XSS prevention** — All user-supplied strings are HTML-escaped via `html.escape()` in the `LocalUser` constructor before any template injection
- **Strong password policy** — Minimum 8 characters, at least one uppercase letter, one digit, and one special character
- **No plaintext passwords** — Legacy accounts without a salt are blocked at login
- **Secrets management** — MongoDB URI is loaded from `.env` and never shipped to the frontend or committed to version control

---

## Model Information

The CNN (`pomegranate_model.h5`) is a MobileNetV2 transfer-learning model trained to classify pomegranate fruit images into 5 categories. The app rebuilds the architecture and loads only the weights, so a Keras version difference between training and runtime doesn't break loading. During inference:

1. The input image is resized to `224×224` pixels
2. The image is checked (no faces, enough colour variation, a colourful subject in the centre); failing photos return `"Invalid Image"`
3. Pixels are scaled to `[-1, 1]` with MobileNetV2's `preprocess_input`
4. The model outputs a softmax probability distribution over 5 classes
5. If the probabilities are almost uniform (the model is guessing), the result is `"Invalid Image"`
6. Otherwise the class with the highest probability is returned as the diagnosis along with its confidence score
7. All 5 class probabilities are shown as visual bars in the result card

If the model file is missing, the app gracefully handles the error and returns `"Invalid Image"`.

---

## Database Schema

### `users` collection
```json
{
  "_id": ObjectId,
  "name": "string",
  "email": "string (unique, indexed)",
  "password": "string (PBKDF2 hex hash)",
  "salt": "string (hex)",
  "created_at": "datetime (UTC)"
}
```

### `scans` collection
```json
{
  "_id": ObjectId,
  "user_id": "ObjectId (ref: users, indexed)",
  "disease_type": "string",
  "confidence": "float",
  "image_name": "string | null",
  "created_at": "datetime (UTC, indexed DESC)"
}
```

### `login_attempts` collection
```json
{
  "_id": ObjectId,
  "email": "string (unique, indexed)",
  "attempts": "int",
  "last_attempt": "datetime (TTL index: auto-expires after 900s)"
}
```

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

