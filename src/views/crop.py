"""Crop recommendation page."""

import streamlit as st

import icons
import ui
from crop_recommendation import CROP_PROFILES, recommend_crop


def _fit_table(crop: str, values: dict) -> str:
    profile = CROP_PROFILES.get(crop)
    if not profile:
        return ""
    rows = [
        ("Nitrogen (kg/ha)", "N", values["N"]), ("Phosphorus (kg/ha)", "P", values["P"]),
        ("Potassium (kg/ha)", "K", values["K"]), ("Soil pH", "ph", values["ph"]),
        ("Temperature (°C)", "temp", values["temperature"]), ("Humidity (%)", "humidity", values["humidity"]),
        ("Rainfall (mm)", "rainfall", values["rainfall"]),
    ]
    out = []
    for label, key, val in rows:
        lo, hi = profile[key]
        inside = lo <= val <= hi
        badge = ui.pill("Within range", "ok") if inside else ui.pill("Outside range", "warn")
        out.append(ui.row(label, f"Typical for {crop.title()}: {lo:g} to {hi:g}",
                          f'<div style="text-align:right"><div class="ka-row-title">{val:g}</div>{badge}</div>'))
    return '<div class="ka-list">' + "".join(out) + "</div>"


def render() -> None:
    ui.page_header("Crop recommendation",
                   "Enter your soil test and local climate values to see which crops suit your land best.",
                   icon="sprout")

    form_col, result_col = st.columns([1, 1.25], gap="large")

    with form_col:
        with st.form("crop_form"):
            ui.card_heading("Soil test", "From your latest soil health report")
            c1, c2 = st.columns(2)
            N = c1.number_input("Nitrogen, N (kg/ha)", 0.0, 200.0, 90.0)
            P = c2.number_input("Phosphorus, P (kg/ha)", 0.0, 200.0, 42.0)
            K = c1.number_input("Potassium, K (kg/ha)", 0.0, 250.0, 43.0)
            ph = c2.number_input("Soil pH", 0.0, 14.0, 6.5, step=0.1)
            st.write("")
            ui.card_heading("Climate", "Typical values for your growing season")
            c3, c4 = st.columns(2)
            temperature = c3.number_input("Temperature (°C)", -5.0, 50.0, 25.0)
            humidity = c4.number_input("Humidity (%)", 0.0, 100.0, 80.0)
            rainfall = st.number_input("Rainfall (mm)", 0.0, 500.0, 200.0)
            submitted = st.form_submit_button("Get recommendation", type="primary", width="stretch")

    with result_col:
        if not submitted:
            ui.empty_state("sprout", "Your recommendation will appear here",
                           "Fill in the soil and climate values, then choose Get recommendation.")
        else:
            results = recommend_crop(N, P, K, temperature, humidity, ph, rainfall, top_k=3)
            best = results[0]
            values = dict(N=N, P=P, K=K, ph=ph, temperature=temperature, humidity=humidity, rainfall=rainfall)
            with ui.card("crop1"):
                ui.html(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap">'
                    f'<div><div class="ka-card-sub" style="margin:0">Best match for your land</div>'
                    f'<h2 style="margin:0.1rem 0 0 0">{ui.esc(best["crop"].title())}</h2></div>'
                    f'{ui.pill(str(best["confidence"]) + "% confidence", "ok")}</div>'
                )
                ui.html("".join(
                    ui.meter(r["crop"].title(), f'{r["confidence"]}%', r["confidence"],
                             "primary" if i == 0 else "neutral")
                    for i, r in enumerate(results)))
            st.write("")
            with ui.card("crop2"):
                ui.card_heading(f"How your values compare with {best['crop'].title()}",
                                "Typical ranges come from the data the model was trained on")
                ui.html(_fit_table(best["crop"], values))

    with st.expander("About this model"):
        st.write(
            "A random forest classifier of 200 decision trees trained on soil (N, P, K, pH) and climate "
            "(temperature, humidity, rainfall) features. This build trains on a synthetic dataset with "
            "agronomically plausible ranges so it runs offline. Point `train_model()` at the public Kaggle "
            "Crop Recommendation dataset for real-world use; nothing else needs to change."
        )
