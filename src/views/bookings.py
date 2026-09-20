"""Bookings overview and completion."""

import pandas as pd
import streamlit as st

import database
import ui


def render() -> None:
    ui.page_header("Bookings", "Every equipment rental on the platform, and a way to close out finished ones.",
                   icon="calendar-check")
    bookings = database.get_bookings()
    if not bookings:
        ui.empty_state("calendar-check", "No bookings yet", "Bookings made in the rental marketplace will be listed here.")
        return

    active = [b for b in bookings if b["status"] == "confirmed"]
    done = [b for b in bookings if b["status"] == "completed"]
    value = sum(b["total_cost"] or 0 for b in bookings if b["status"] != "cancelled")
    ui.stat_grid([
        ui.stat_tile("calendar-check", len(bookings), "Total bookings", "primary"),
        ui.stat_tile("clock", len(active), "Active", "info"),
        ui.stat_tile("circle-check", len(done), "Completed", "ok"),
        ui.stat_tile("gauge", f"₹{value:,.0f}", "Booked value", "warn"),
    ])

    df = pd.DataFrame(bookings)[["id", "equipment_name", "farmer_name", "start_date", "end_date", "total_cost", "status"]]
    df["status"] = df["status"].str.title()
    st.dataframe(
        df, hide_index=True, width="stretch",
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "equipment_name": "Equipment", "farmer_name": "Booked for",
            "start_date": "Start", "end_date": "End",
            "total_cost": st.column_config.NumberColumn("Total", format="₹%d"),
            "status": "Status",
        },
    )

    with ui.card("bookings1"):
        ui.card_heading("Complete a booking", "Marks the booking as completed and makes the machine available again.")
        if active:
            options = {f"#{b['id']}  {b['equipment_name']} ({b['farmer_name']})": b for b in active}
            c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
            choice = c1.selectbox("Active booking", list(options))
            if c2.button("Mark as completed", type="primary", width="stretch"):
                b = options[choice]
                database.complete_booking(b["id"])
                ui.flash(f"Booking #{b['id']} completed. {b['equipment_name']} is available again.")
                st.rerun()
        else:
            st.caption("There are no active bookings to complete.")
