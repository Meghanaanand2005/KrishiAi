"""Dashboard: today's field brief, equipment status and recent activity."""

from datetime import datetime

import streamlit as st

import advisory_service
import database
import icons
import nav
import ui

DEFAULT_CITY = "Belagavi"


@st.cache_data(ttl=900, show_spinner=False)
def _conditions(city: str) -> dict:
    return advisory_service.current_conditions(city)


def _greeting() -> str:
    hour = datetime.now(advisory_service.IST).hour
    return "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"


def _field_brief(city: str) -> str:
    w = _conditions(city)
    tips = "".join(f"<li>{ui.esc(t)}</li>" for t in w["tips"][:3])
    humidity = ui.chip("droplets", "Humidity %.0f%%" % w["humidity"])
    wind = ui.chip("wind", "Wind %.1f m/s" % w["wind_speed"])
    rain = ui.chip("cloud-rain", "Rain %.1f mm" % w["rainfall_mm"])
    return (
        '<div class="ka-brief">'
        '<div class="ka-brief-top"><div>'
        f'<div class="ka-brief-where">{icons.svg("map-pin", 17)}{ui.esc(city)}</div>'
        f'<div class="ka-brief-temp">{w["temperature"]:.0f}<small>&deg;C</small></div>'
        f'<div class="ka-brief-cond">{ui.esc(w["condition"])}</div></div>'
        f'<div>{ui.severity_pill(w["severity"])}</div></div>'
        '<div class="ka-brief-readings">'
        f"{humidity}{wind}{rain}"
        "</div>"
        f'<div class="ka-brief-advice"><h4>Advice for today</h4><ul>{tips}</ul></div>'
        "</div>"
    )


def render() -> None:
    user = st.session_state["user"]
    ui.page_header(
        f"{_greeting()}, {ui.first_name(user['name'])}",
        "Today's conditions, your equipment and your saved advisories at a glance.",
        icon="layout-dashboard",
    )

    equipment = database.get_all_equipment()
    bookings = database.get_bookings()
    advisories = advisory_service.list_advisories(user["id"], limit=4)
    active_bookings = [b for b in bookings if b["status"] == "confirmed"]
    by_status = {s: sum(1 for e in equipment if e["status"] == s) for s in ("available", "rented", "maintenance")}

    city = (user.get("location") or "").strip() or DEFAULT_CITY
    left, right = st.columns([1.7, 1], gap="medium")
    with left:
        ui.html(_field_brief(city))
        st.write("")
        nav.link("weather", "Open weather advisory", ":material/partly_cloudy_day:")
    with right:
        with ui.card("dashboard1"):
            ui.card_heading("Equipment status", f"{len(equipment)} machines listed on the marketplace")
            total = max(len(equipment), 1)
            ui.html(
                ui.meter("Available", str(by_status["available"]), by_status["available"] / total * 100, "primary")
                + ui.meter("On rent", str(by_status["rented"]), by_status["rented"] / total * 100, "info")
                + ui.meter("In maintenance", str(by_status["maintenance"]), by_status["maintenance"] / total * 100, "warn")
            )
            nav.link("equipment", "Browse equipment", ":material/agriculture:")

    st.write("")
    ui.stat_grid([
        ui.stat_tile("tractor", len(equipment), "Equipment listed", "primary"),
        ui.stat_tile("circle-check", by_status["available"], "Available now", "ok"),
        ui.stat_tile("calendar-check", len(active_bookings), "Active bookings", "info"),
        ui.stat_tile("cloud-sun", advisories["total"], "Your saved advisories", "warn"),
    ])

    col_adv, col_book = st.columns(2, gap="medium")
    with col_adv:
        with ui.card("dashboard2"):
            ui.card_heading("Recent advisories", "The latest weather advisories you saved")
            if advisories["items"]:
                ui.html('<div class="ka-list">' + "".join(
                    ui.row(a["city"], f'{a["condition"]}, {a["temperature"]:.0f}°C', ui.severity_pill(a["severity"]))
                    for a in advisories["items"]) + "</div>")
                nav.link("weather", "Manage advisories", ":material/edit_note:")
            else:
                ui.empty_state("cloud-sun", "No advisories saved yet",
                               "Check the weather for your farm and save the advice to keep a record.")
                nav.link("weather", "Check the weather", ":material/partly_cloudy_day:")

    with col_book:
        with ui.card("dashboard3"):
            ui.card_heading("Recent bookings", "The latest equipment rentals across the platform")
            if bookings:
                ui.html('<div class="ka-list">' + "".join(
                    ui.row(b["equipment_name"], f'{b["farmer_name"]}, {b["start_date"]} to {b["end_date"]}',
                           ui.status_pill(b["status"], ui.BOOKING_TONE))
                    for b in bookings[:4]) + "</div>")
                nav.link("bookings", "View all bookings", ":material/event_available:")
            else:
                ui.empty_state("calendar-check", "No bookings yet", "Book a machine from the rental marketplace to see it here.")
                nav.link("equipment", "Find equipment", ":material/agriculture:")
