"""
theme.py

Loads the KrishiAI stylesheet (static/krishiai.css) and injects it into the page.

Design direction
----------------
A light, calm interface for people who read it outdoors on a phone as often as
at a desk, so contrast is deliberately high (see the ratios documented in the
CSS and verified by tools/check_contrast.py).

  Palette   canopy green (#17603A) for actions and identity, on a faintly
            green-tinted white (#F5F8F3). A single supporting blue is used for
            weather / information, amber for warnings, red only for
            destructive actions and errors.
  Type      Bricolage Grotesque for headings, Figtree for everything else.
            Both are bundled locally, so the app looks the same offline.
  Layout    a light sidebar grouped by task (overview / farm intelligence /
            equipment / account), pages that open with a title + one-line
            purpose, and white bordered cards on the tinted page background.

Edit the colours in the :root block at the top of static/krishiai.css.
"""

import os

import streamlit as st

_CSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "krishiai.css")


@st.cache_resource
def _load_css() -> str:
    with open(_CSS_PATH, encoding="utf-8") as fh:
        return fh.read()


def inject() -> None:
    """Inject the stylesheet. Call once per run, right after set_page_config()."""
    st.html(f'<div class="ka-css-marker"></div><style>{_load_css()}</style>')


def hide_sidebar() -> None:
    """Used on the login screen, where there is nothing to navigate to yet."""
    st.html(
        '<div class="ka-css-marker"></div><style>'
        '[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] { display: none !important; }'
        "</style>"
    )


def mark_active_nav(href: str) -> None:
    """Highlight the sidebar link for the current page.

    Streamlit gives the active link an unstable, auto-generated class name, but
    its href is reliable (the default page's href is empty), so we target that.
    """
    selector = f'[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][href="{href}"]'
    st.html(
        '<div class="ka-css-marker"></div><style>'
        f"{selector} {{ background: var(--ka-primary-tint) !important; }}"
        f"{selector} p {{ font-weight: 650 !important; color: var(--ka-primary-ink) !important; }}"
        f"{selector} .ka-i, {selector} [data-testid=\"stIconMaterial\"] {{ color: var(--ka-primary-ink) !important; }}"
        "</style>"
    )
