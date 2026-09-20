"""Leaf disease detection page."""

import json
import os
import uuid

import streamlit as st
from PIL import Image

import database
import ui
from disease_detection import analyze_leaf_image

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "uploads")
ALLOWED_EXT = {".jpg", ".jpeg", ".png"}

TONE = {"healthy": "ok", "nutrient_deficiency": "warn", "pest_damage": "warn", "fungal_risk": "bad"}
BACKGROUND = {"ok": "#E1F3E8", "warn": "#FDF0D5", "bad": "#FDE8E6"}
INK = {"ok": "#0F5A32", "warn": "#7A4700", "bad": "#A11B12"}
BREAKDOWN = [("green_%", "Healthy green", "primary"), ("yellow_%", "Yellowing", "warn"),
             ("brown_%", "Browning", "warn"), ("dark_spot_%", "Dark spots", "bad")]


def _save_once(user: dict, uploaded, image: Image.Image, result: dict) -> None:
    """Persist the photo and diagnosis a single time per uploaded file.

    Streamlit re-runs this script on every interaction; without this guard each
    rerun would save the same photo again and fill My Uploads with duplicates.
    """
    if st.session_state.get("_last_saved_upload") == uploaded.file_id:
        return
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(uploaded.name)[1].lower()
    ext = ext if ext in ALLOWED_EXT else ".jpg"
    path = os.path.join(UPLOAD_DIR, f"{user['id']}_{uuid.uuid4().hex}{ext}")
    image.convert("RGB").save(path)
    database.save_uploaded_file(user["id"], "disease_detection", uploaded.name, path, json.dumps(result))
    st.session_state["_last_saved_upload"] = uploaded.file_id


def render() -> None:
    user = st.session_state["user"]
    ui.page_header("Disease detection",
                   "Upload a clear photo of a single leaf to get a first assessment and a suggested next step.",
                   icon="scan-line")

    left, right = st.columns([1, 1.2], gap="large")
    with left:
        uploaded = st.file_uploader("Leaf photo", type=["jpg", "jpeg", "png"],
                                    help="JPG or PNG. Use daylight and fill the frame with the leaf.")
        if uploaded is not None:
            image = Image.open(uploaded)
            st.image(image, width="stretch")

    with right:
        if uploaded is None:
            ui.empty_state("scan-line", "No photo yet",
                           "Choose a leaf photo on the left and the assessment will appear here.")
        else:
            result = analyze_leaf_image(image)
            tone = TONE.get(result["condition"], "warn")
            label = result["condition"].replace("_", " ").title()
            ui.html(
                f'<div class="ka-diagnosis" style="background:{BACKGROUND[tone]};color:{INK[tone]}">'
                f'{ui.pill(str(result["confidence"]) + "% confidence", tone)}'
                f'<h3 style="color:{INK[tone]} !important">{ui.esc(label)}</h3>'
                f'<p style="color:{INK[tone]} !important">{ui.esc(result["description"])}</p></div>'
            )
            st.write("")
            with ui.card("disease1"):
                ui.card_heading("Suggested next step")
                st.write(result["advice"])
            with ui.card("disease2"):
                ui.card_heading("Colour analysis", "Share of the image in each colour group")
                ui.html("".join(ui.meter(name, f'{result["color_breakdown"][key]}%',
                                         result["color_breakdown"][key], t) for key, name, t in BREAKDOWN))
            _save_once(user, uploaded, image, result)
            st.caption("Saved to your account. Find it later under My uploads.")

    with st.expander("About this analysis"):
        st.write(
            "This build measures the proportion of green, yellow, brown and dark pixels in the photo and "
            "applies explainable rules. It is a first screening, not a laboratory diagnosis. "
            "`disease_detection.py` documents how to swap in a MobileNetV2 model trained on the PlantVillage "
            "dataset while keeping the same function signature."
        )
