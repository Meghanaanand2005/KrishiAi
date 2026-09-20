"""
disease_detection.py

Leaf health / disease-risk analysis from an uploaded leaf image.

IMPORTANT - HONEST SCOPE NOTE FOR YOUR REPORT:
A production-grade disease detector is a Convolutional Neural Network (CNN)
trained on a large labeled dataset such as PlantVillage (~54,000 images,
38 disease classes) - typically using transfer learning on
MobileNetV2/ResNet with TensorFlow/Keras. That requires downloading a
multi-GB dataset and GPU training time, which isn't possible in this
offline sandbox.

What this module does instead: a colour/texture-based heuristic (pure
PIL + NumPy, no training data needed) that inspects the ratio of green,
yellow/brown, and dark-spot pixels in the leaf image and flags a likely
condition. It's a legitimate, explainable image-processing technique
(similar to early plant-pathology vegetation-index methods) and is good
enough to demo the pipeline end-to-end.

TO UPGRADE FOR YOUR FINAL SUBMISSION:
1. Download the PlantVillage dataset (Kaggle: "plantvillage-dataset").
2. Fine-tune a MobileNetV2 with Keras (~20-30 lines, transfer learning).
3. Replace `analyze_leaf_image()`'s body with `model.predict(img_array)`
   and keep the same function signature - the Streamlit UI won't need
   to change at all.
"""

import numpy as np
from PIL import Image


CONDITIONS = {
    "healthy": {
        "description": "Leaf appears healthy - predominantly green with no significant discoloration.",
        "advice": "Continue current watering and fertilization schedule. Monitor weekly.",
    },
    "nutrient_deficiency": {
        "description": "High yellowing detected (possible nitrogen/iron deficiency - chlorosis pattern).",
        "advice": "Consider soil testing and a balanced NPK or micronutrient foliar spray.",
    },
    "fungal_risk": {
        "description": "Dark/brown spotting detected, consistent with fungal leaf-spot disease.",
        "advice": "Isolate affected plants, improve airflow, and consider a fungicide after lab confirmation.",
    },
    "pest_damage": {
        "description": "Irregular patchy discoloration detected, consistent with possible pest/insect damage.",
        "advice": "Inspect undersides of leaves for pests; consider neem-oil or targeted pesticide treatment.",
    },
}


def _classify_pixel_ratios(green_ratio, yellow_ratio, brown_ratio, dark_spot_ratio):
    """Simple rule-based classifier over colour-composition ratios."""
    if dark_spot_ratio > 0.08:
        return "fungal_risk"
    if yellow_ratio > 0.30:
        return "nutrient_deficiency"
    if brown_ratio > 0.15:
        return "pest_damage"
    if green_ratio > 0.55:
        return "healthy"
    # fallback - whichever non-green signal is strongest
    candidates = {"nutrient_deficiency": yellow_ratio, "pest_damage": brown_ratio, "fungal_risk": dark_spot_ratio}
    return max(candidates, key=candidates.get)


def analyze_leaf_image(image: Image.Image):
    """
    Analyze a PIL Image of a leaf and return a diagnosis dict:
    { condition, description, advice, confidence, color_breakdown }
    """
    img = image.convert("RGB").resize((200, 200))
    arr = np.asarray(img).astype(np.float32) / 255.0

    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    # Simple HSV-ish heuristics using RGB relationships
    green_mask = (g > r) & (g > b) & (g > 0.25)
    yellow_mask = (r > 0.4) & (g > 0.4) & (b < 0.35) & (~green_mask)
    brown_mask = (r > 0.25) & (r < 0.6) & (g < r) & (b < r * 0.7)
    dark_mask = (r + g + b) / 3 < 0.20

    total_pixels = arr.shape[0] * arr.shape[1]
    green_ratio = float(green_mask.sum()) / total_pixels
    yellow_ratio = float(yellow_mask.sum()) / total_pixels
    brown_ratio = float(brown_mask.sum()) / total_pixels
    dark_spot_ratio = float(dark_mask.sum()) / total_pixels

    condition = _classify_pixel_ratios(green_ratio, yellow_ratio, brown_ratio, dark_spot_ratio)
    info = CONDITIONS[condition]

    # crude confidence: how dominant the deciding ratio is
    ratios = {"healthy": green_ratio, "nutrient_deficiency": yellow_ratio,
              "pest_damage": brown_ratio, "fungal_risk": dark_spot_ratio}
    confidence = round(min(95.0, 50 + ratios[condition] * 150), 1)

    return {
        "condition": condition,
        "description": info["description"],
        "advice": info["advice"],
        "confidence": confidence,
        "color_breakdown": {
            "green_%": round(green_ratio * 100, 1),
            "yellow_%": round(yellow_ratio * 100, 1),
            "brown_%": round(brown_ratio * 100, 1),
            "dark_spot_%": round(dark_spot_ratio * 100, 1),
        },
    }


if __name__ == "__main__":
    # Quick self-test with a synthetic green image
    test_img = Image.new("RGB", (200, 200), (40, 140, 40))
    result = analyze_leaf_image(test_img)
    print("Synthetic healthy-green test:", result["condition"], result["confidence"])

    test_img2 = Image.new("RGB", (200, 200), (180, 170, 40))
    result2 = analyze_leaf_image(test_img2)
    print("Synthetic yellow test:", result2["condition"], result2["confidence"])
