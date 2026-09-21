"""Login and sign-up screen."""

import streamlit as st

import auth
import icons
import ui

FEATURES = [
    ("sprout", "Crop recommendation", "A machine-learning model reads soil and climate values and suggests what to plant."),
    ("scan-line", "Leaf disease check", "Upload a leaf photo and get a first assessment with the next step to take."),
    ("cloud-sun", "Weather advisories", "Current conditions turned into plain farming advice you can save and manage."),
    ("tractor", "Equipment rental", "List, find and book machinery, with live status readings from each machine."),
]


def render() -> None:
    brand, form = st.columns([1.1, 1], gap="large", vertical_alignment="center")

    with brand:
        items = "".join(
            f'<li><div class="ka-feat-icon">{icons.svg(icon, 18)}</div>'
            f"<div><strong>{title}</strong><span>{text}</span></div></li>"
            for icon, title, text in FEATURES
        )
        ui.html(
            '<div class="ka-auth-brand">'
            '<div class="ka-brand" style="padding:0">'
            f'<div class="ka-brand-mark">{icons.svg("sprout", 22, stroke=2)}</div>'
            '<div><div class="ka-brand-name">KrishiAI</div>'
            '<div class="ka-brand-tag">AI and IoT powered smart agriculture</div></div></div>'
            "<h1>Decisions for the field, backed by data</h1>"
            "<p>Everything a farm needs in one place: what to grow, how the crop is doing, "
            "what the weather means for the week, and the machinery to get the work done.</p>"
            f'<ul class="ka-auth-features">{items}</ul>'
            '<div class="ka-auth-foot">Developed by Meghana A, Ruthu S, Pragathi PG,Pallavi TG<br>Guided by Prof. Sangeetha</div>'
            "</div>"
        )

    with form:
        tab_login, tab_signup = st.tabs(["Log in", "Create account"])

        with tab_login:
            ui.html('<div class="ka-auth-formhead"><h2>Welcome back</h2><p>Log in to continue to your dashboard.</p></div>')
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="e.g. ravi.kumar")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", type="primary", width="stretch")
            if submitted:
                user, message = auth.login(username, password)
                if user:
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.error(message)

        with tab_signup:
            ui.html('<div class="ka-auth-formhead"><h2>Create your account</h2>'
                    "<p>Farmers rent equipment. Owners list equipment for rent.</p></div>")
            with st.form("signup_form"):
                name = st.text_input("Full name")
                role = st.selectbox("I am a", ["farmer", "owner"], format_func=str.title)
                username = st.text_input("Choose a username")
                password = st.text_input("Choose a password", type="password", help="At least 6 characters.")
                c1, c2 = st.columns(2)
                phone = c1.text_input("Phone (optional)")
                location = c2.text_input("Village or town (optional)", help="Used for the weather on your dashboard.")
                submitted = st.form_submit_button("Create account", type="primary", width="stretch")
            if submitted:
                ok, message = auth.signup(username, password, name, role, phone, location)
                if ok:
                    st.success("Account created. Switch to the Log in tab to sign in.")
                else:
                    st.error(message)
