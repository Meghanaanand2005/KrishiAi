"""
crop_recommendation.py

AI-based crop recommendation using a RandomForest classifier trained on
soil (N, P, K, pH) and climate (temperature, humidity, rainfall) features.

NOTE ON DATA: For the actual project submission you should train this on the
real "Crop Recommendation Dataset" (22 crops, ~2200 rows - widely available
on Kaggle: https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset).
Since this sandbox has no internet access, this file generates a synthetic
dataset with realistic agronomic ranges per crop so the whole pipeline is
runnable end-to-end offline. Swap `generate_synthetic_dataset()` for
`pd.read_csv("Crop_recommendation.csv")` once you download the real dataset -
the training/prediction code does not need to change.
"""

import os
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import LabelEncoder
import joblib

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
MODEL_PATH = os.path.join(DATA_DIR, "crop_model.pkl")
ENCODER_PATH = os.path.join(DATA_DIR, "crop_label_encoder.pkl")
DATASET_PATH = os.path.join(DATA_DIR, "crop_dataset.csv")

# Approximate agronomic ranges (N, P, K in kg/ha; temp in C; humidity in %;
# ph 0-14; rainfall in mm). These are illustrative, not lab-verified values.
CROP_PROFILES = {
    "rice":        dict(N=(80, 120), P=(40, 60),  K=(40, 60),  temp=(22, 32), humidity=(70, 90), ph=(5.5, 7.0), rainfall=(150, 300)),
    "maize":       dict(N=(60, 100), P=(35, 55),  K=(15, 25),  temp=(18, 27), humidity=(55, 75), ph=(5.5, 7.5), rainfall=(60, 110)),
    "chickpea":    dict(N=(20, 45),  P=(55, 75),  K=(75, 95),  temp=(15, 25), humidity=(15, 35), ph=(6.0, 8.0), rainfall=(60, 100)),
    "kidneybeans": dict(N=(15, 40),  P=(55, 75),  K=(15, 25),  temp=(15, 24), humidity=(18, 25), ph=(5.5, 6.5), rainfall=(60, 150)),
    "pigeonpeas":  dict(N=(15, 40),  P=(55, 75),  K=(15, 25),  temp=(18, 36), humidity=(30, 70), ph=(4.5, 7.0), rainfall=(90, 200)),
    "banana":      dict(N=(90, 120), P=(70, 95),  K=(45, 55),  temp=(25, 35), humidity=(75, 90), ph=(5.5, 6.5), rainfall=(90, 220)),
    "mango":       dict(N=(15, 40),  P=(15, 40),  K=(25, 40),  temp=(24, 36), humidity=(45, 60), ph=(4.5, 7.0), rainfall=(60, 120)),
    "grapes":      dict(N=(0, 30),   P=(115, 145),K=(190, 210),temp=(8, 42),  humidity=(80, 90), ph=(5.5, 6.5), rainfall=(60, 90)),
    "watermelon":  dict(N=(90, 110), P=(0, 20),   K=(45, 55),  temp=(24, 30), humidity=(50, 70), ph=(6.0, 7.0), rainfall=(40, 60)),
    "cotton":      dict(N=(100, 140),P=(35, 65),  K=(15, 25),  temp=(22, 32), humidity=(65, 85), ph=(5.5, 8.0), rainfall=(60, 110)),
    "coffee":      dict(N=(90, 120), P=(15, 35),  K=(25, 35),  temp=(20, 28), humidity=(50, 70), ph=(6.0, 7.5), rainfall=(150, 220)),
    "jute":        dict(N=(60, 100), P=(35, 55),  K=(35, 45),  temp=(23, 30), humidity=(70, 90), ph=(6.0, 7.5), rainfall=(150, 200)),
    "coconut":     dict(N=(15, 40),  P=(0, 30),   K=(25, 35),  temp=(25, 32), humidity=(90, 100),ph=(5.0, 6.5), rainfall=(120, 220)),
    "sugarcane":   dict(N=(90, 130), P=(35, 65),  K=(15, 45),  temp=(24, 35), humidity=(70, 90), ph=(6.0, 7.5), rainfall=(120, 200)),
    "muskmelon":   dict(N=(90, 110), P=(0, 20),   K=(45, 55),  temp=(24, 32), humidity=(85, 95), ph=(6.0, 7.0), rainfall=(30, 50)),
    "wheat":       dict(N=(50, 90),  P=(30, 55),  K=(15, 30),  temp=(11, 25), humidity=(50, 65), ph=(6.0, 7.5), rainfall=(40, 90)),
    "groundnut":   dict(N=(15, 40),  P=(35, 65),  K=(15, 30),  temp=(24, 32), humidity=(50, 75), ph=(5.5, 7.0), rainfall=(50, 100)),
    "soybean":     dict(N=(20, 50),  P=(55, 80),  K=(15, 25),  temp=(20, 30), humidity=(60, 80), ph=(6.0, 7.0), rainfall=(60, 120)),
}


def generate_synthetic_dataset(samples_per_crop=150, random_state=42):
    """Generate a synthetic but agronomically plausible dataset for offline training."""
    rng = np.random.default_rng(random_state)
    rows = []
    for crop, profile in CROP_PROFILES.items():
        for _ in range(samples_per_crop):
            row = {
                "N": rng.uniform(*profile["N"]),
                "P": rng.uniform(*profile["P"]),
                "K": rng.uniform(*profile["K"]),
                "temperature": rng.uniform(*profile["temp"]),
                "humidity": rng.uniform(*profile["humidity"]),
                "ph": rng.uniform(*profile["ph"]),
                "rainfall": rng.uniform(*profile["rainfall"]),
                "label": crop,
            }
            rows.append(row)
    df = pd.DataFrame(rows)
    df = df.sample(frac=1, random_state=random_state).reset_index(drop=True)  # shuffle
    return df


def train_model(force_retrain=False):
    """Train (or load cached) RandomForest crop classifier. Returns (model, encoder, accuracy)."""
    os.makedirs(DATA_DIR, exist_ok=True)

    if not force_retrain and os.path.exists(MODEL_PATH) and os.path.exists(ENCODER_PATH):
        model = joblib.load(MODEL_PATH)
        encoder = joblib.load(ENCODER_PATH)
        return model, encoder, None

    if os.path.exists(DATASET_PATH):
        df = pd.read_csv(DATASET_PATH)
    else:
        df = generate_synthetic_dataset()
        df.to_csv(DATASET_PATH, index=False)

    feature_cols = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
    X = df[feature_cols]
    encoder = LabelEncoder()
    y = encoder.fit_transform(df["label"])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    model = RandomForestClassifier(n_estimators=200, max_depth=12, random_state=42)
    model.fit(X_train, y_train)

    accuracy = accuracy_score(y_test, model.predict(X_test))

    joblib.dump(model, MODEL_PATH)
    joblib.dump(encoder, ENCODER_PATH)

    return model, encoder, accuracy


def recommend_crop(N, P, K, temperature, humidity, ph, rainfall, top_k=3):
    """Predict the top-k most suitable crops for given soil/climate conditions."""
    model, encoder, _ = train_model()
    features = pd.DataFrame([{
        "N": N, "P": P, "K": K,
        "temperature": temperature, "humidity": humidity,
        "ph": ph, "rainfall": rainfall,
    }])
    probs = model.predict_proba(features)[0]
    top_indices = np.argsort(probs)[::-1][:top_k]
    results = [
        {"crop": encoder.inverse_transform([idx])[0], "confidence": round(float(probs[idx]) * 100, 1)}
        for idx in top_indices
    ]
    return results


if __name__ == "__main__":
    model, encoder, acc = train_model(force_retrain=True)
    print(f"Model trained. Test accuracy: {acc:.3f}")
    sample = recommend_crop(N=90, P=42, K=43, temperature=25, humidity=80, ph=6.5, rainfall=200)
    print("Sample recommendation (should lean rice/jute-like conditions):")
    for r in sample:
        print(f"  {r['crop']}: {r['confidence']}%")
