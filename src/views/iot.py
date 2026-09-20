"""IoT equipment monitor (simulated telemetry)."""

import pandas as pd
import streamlit as st

import advisory_service
import database
import icons
import ui
from iot_simulator import generate_reading


def _fuel_tone(v):
    return "bad" if v < 15 else "warn" if v < 30 else "primary"


def _temp_tone(v):
    return "bad" if v > 98 else "warn" if v > 90 else "primary"


def render() -> None:
    ui.page_header("IoT monitor", "Live-style readings from each machine: fuel, engine temperature, location and health.",
                   icon="radio-tower")
    equipment = database.get_all_equipment()
    if not equipment:
        ui.empty_state("tractor", "No equipment yet", "List a machine in the rental marketplace to monitor it here.")
        return

    options = {f"{e['name']} (#{e['id']})": e["id"] for e in equipment}
    c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
    choice = c1.selectbox("Machine", list(options))
    eq_id = options[choice]
    if c2.button("Take a new reading", type="primary", icon=":material/refresh:", width="stretch"):
        prev = database.get_latest_iot_reading(eq_id)
        r = generate_reading(eq_id, previous_fuel=prev["fuel_level"] if prev else None)
        database.log_iot_reading(eq_id, r["fuel_level"], r["engine_temp"], r["latitude"], r["longitude"], r["health_status"])
        st.rerun()

    latest = database.get_latest_iot_reading(eq_id)
    if not latest:
        ui.empty_state("radio-tower", "No readings yet", "Choose Take a new reading to record the first one.")
        st.caption("Simulated telemetry. iot_simulator.py explains how to connect real sensors.")
        return

    left, right = st.columns([1, 1.2], gap="medium")
    with left:
        with ui.card("iot1"):
            ui.card_heading("Current readings", f"Updated {advisory_service.format_ist(advisory_service.to_iso(latest['logged_at']))}")
            ui.html(
                f'<div style="margin-bottom:.4rem">{ui.status_pill(latest["health_status"], ui.HEALTH_TONE)}</div>'
                + ui.meter("Fuel level", f'{latest["fuel_level"]}%', latest["fuel_level"], _fuel_tone(latest["fuel_level"]))
                + ui.meter("Engine temperature", f'{latest["engine_temp"]}°C', min(latest["engine_temp"] / 120 * 100, 100),
                           _temp_tone(latest["engine_temp"]))
                + f'<div class="ka-row-sub" style="margin-top:.8rem;display:flex;gap:.4rem;align-items:center">'
                  f'{icons.svg("map-pin", 15)}{latest["latitude"]}, {latest["longitude"]}</div>'
            )
    with right:
        with ui.card("iot2"):
            ui.card_heading("Location")
            st.map(pd.DataFrame([{"lat": latest["latitude"], "lon": latest["longitude"]}]), size=140, color="#17603A", height=250)

    history = database.get_iot_history(eq_id, 20)
    if len(history) >= 2:
        with ui.card("iot3"):
            ui.card_heading("Trend", f"Last {len(history)} readings")
            df = pd.DataFrame(history).rename(columns={"fuel_level": "Fuel (%)", "engine_temp": "Engine temp (°C)"})
            df["Reading"] = range(1, len(df) + 1)
            st.line_chart(df.set_index("Reading")[["Fuel (%)", "Engine temp (°C)"]], color=["#17603A", "#C77D0A"], height=240)
    st.caption("Simulated telemetry. iot_simulator.py explains how to connect real sensors.")
