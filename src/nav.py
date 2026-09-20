"""nav.py - lets any page render a link to another page (pages are registered in app.py)."""

import streamlit as st


def register(pages: dict) -> None:
    st.session_state["_pages"] = pages


def link(key: str, label: str, icon: str) -> None:
    st.page_link(st.session_state["_pages"][key], label=label, icon=icon)
