"""Rental marketplace: browse, filter, book, and list equipment."""

from datetime import date, timedelta

import streamlit as st

import database
import icons
import ui

CATEGORIES = ["Tractor", "Harvester", "Seed Sower", "Irrigation", "Tillage", "Sprayer", "Other"]


def _booking_popover(e: dict, user: dict) -> None:
    with st.popover("Book", type="primary", width="stretch"):
        name = st.text_input("Booked for", value=user["name"], key=f"bk_name_{e['id']}")
        start = st.date_input("Start date", value=date.today(), min_value=date.today(), key=f"bk_start_{e['id']}")
        end = st.date_input("End date", value=date.today() + timedelta(days=2), min_value=start, key=f"bk_end_{e['id']}")
        days = max((end - start).days, 1)
        cost = days * e["price_per_day"]
        st.markdown(f"**Total: ₹{cost:,.0f}** for {days} day{'s' if days != 1 else ''}")
        if st.button("Confirm booking", key=f"bk_ok_{e['id']}", type="primary", width="stretch"):
            if not name.strip():
                st.error("Enter a name for the booking.")
            else:
                database.book_equipment(e["id"], name.strip(), str(start), str(end), cost)
                ui.flash(f"{e['name']} booked for {days} day{'s' if days != 1 else ''}.")
                st.rerun()


def _card(e: dict, user: dict) -> None:
    with ui.card(f"eq_{e['id']}"):
        ui.html(
            f'<div style="display:flex;justify-content:space-between;gap:.8rem;align-items:flex-start">'
            f'<div><div class="ka-eq-title">{ui.esc(e["name"])}</div>'
            f'<div class="ka-eq-meta">{icons.svg("map-pin", 15)}{ui.esc(e["location"] or "Location not set")}</div></div>'
            f'{ui.status_pill(e["status"], ui.EQUIPMENT_TONE)}</div>'
            f'<div class="ka-eq-desc">{ui.esc(e["description"] or "")}</div>'
            f'<div style="display:flex;justify-content:space-between;align-items:flex-end;gap:1rem">'
            f'<div><div class="ka-price">₹{e["price_per_day"]:,.0f}<small> per day</small></div>'
            f'<div class="ka-row-sub">{ui.esc(e["category"])}, owned by {ui.esc(e["owner_name"] or "unknown")}</div></div></div>'
        )
        if e["status"] == "available":
            _booking_popover(e, user)
        else:
            st.button("Not available", key=f"na_{e['id']}", disabled=True, width="stretch")


def _browse(user: dict) -> None:
    equipment = database.get_all_equipment()
    f1, f2, f3 = st.columns([1, 1, 1.4])
    category = f1.selectbox("Category", ["All"] + sorted({e["category"] for e in equipment}))
    status = f2.selectbox("Availability", ["All", "Available", "Rented", "Maintenance"])
    query = f3.text_input("Search", placeholder="Name or location", key="eq_search")

    shown = [e for e in equipment
             if (category == "All" or e["category"] == category)
             and (status == "All" or e["status"] == status.lower())
             and (not query.strip() or query.strip().lower() in f'{e["name"]} {e["location"]}'.lower())]

    st.caption(f"Showing {len(shown)} of {len(equipment)} machines")
    if not shown:
        ui.empty_state("search", "Nothing matches these filters", "Try another category or clear the search box.")
        return
    cols = st.columns(2, gap="medium")
    for i, e in enumerate(shown):
        with cols[i % 2]:
            _card(e, user)


def _list_new(user: dict) -> None:
    left, _ = st.columns([1.4, 1])
    with left:
        with st.form("add_equipment_form"):
            ui.card_heading("List your equipment for rent", "It appears on the marketplace straight away.")
            name = st.text_input("Equipment name")
            c1, c2 = st.columns(2)
            category = c1.selectbox("Category", CATEGORIES)
            price = c2.number_input("Price per day (₹)", 0.0, 100000.0, 500.0, step=50.0)
            c3, c4 = st.columns(2)
            owner = c3.text_input("Owner name", value=user["name"])
            location = c4.text_input("Location")
            description = st.text_area("Description", height=90)
            submitted = st.form_submit_button("List equipment", type="primary")
        if submitted:
            if not name.strip() or not owner.strip():
                st.error("Equipment name and owner name are required.")
            elif price <= 0:
                st.error("Set a price per day greater than zero.")
            else:
                database.add_equipment(name.strip(), category, owner.strip(), location.strip(), price, description.strip())
                ui.flash(f"{name.strip()} is now listed.")
                st.rerun()


def render() -> None:
    user = st.session_state["user"]
    ui.page_header("Rental marketplace", "Find machinery near you, book it for the days you need, or list your own.",
                   icon="tractor")
    tab_browse, tab_list = st.tabs(["Browse and book", "List equipment"])
    with tab_browse:
        _browse(user)
    with tab_list:
        _list_new(user)
