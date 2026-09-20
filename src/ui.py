"""
ui.py - small reusable interface components used by every page.

Each helper returns or renders a piece of HTML styled by static/krishiai.css.
Anything that comes from the database or a user is passed through esc() first.
"""

from html import escape as esc
from typing import Optional

import streamlit as st

import icons

# ------------------------------------------------------------ status maps ---

SEVERITY_TONE = {"info": "info", "watch": "warn", "warning": "bad"}
SEVERITY_LABEL = {"info": "Routine", "watch": "Watch", "warning": "Warning"}

EQUIPMENT_TONE = {"available": "ok", "rented": "info", "maintenance": "warn"}
BOOKING_TONE = {"confirmed": "info", "completed": "ok", "cancelled": "neutral"}
HEALTH_TONE = {"normal": "ok", "caution": "warn", "warning": "bad"}
ADVISORY_STATUS_TONE = {"active": "ok", "resolved": "neutral"}
METHOD_TONE = {"GET": "info", "POST": "ok", "PUT": "warn", "PATCH": "violet", "DELETE": "bad"}


# ------------------------------------------------------------- primitives ---

def card(name: str):
    """A white bordered card. `name` must be unique on the page: it becomes the
    container key, which the stylesheet uses (.st-key-card_*) to paint the card."""
    return st.container(border=True, key=f"card_{name}")


def html(markup: str) -> None:
    st.html(markup)


def pill(text: str, tone: str = "neutral", dot: bool = True) -> str:
    plain = "" if dot else " ka-pill--plain"
    return f'<span class="ka-pill ka-tone-{tone}{plain}">{esc(str(text))}</span>'


def severity_pill(severity: str) -> str:
    return pill(SEVERITY_LABEL.get(severity, severity), SEVERITY_TONE.get(severity, "neutral"))


def status_pill(status: str, tones: dict) -> str:
    return pill(str(status).replace("_", " ").title(), tones.get(status, "neutral"))


def method_pill(method: str) -> str:
    return f'<span class="ka-pill ka-method ka-pill--plain ka-tone-{METHOD_TONE[method]}">{method}</span>'


def meter(label: str, value_text: str, pct: float, tone: str = "primary") -> str:
    """A labelled horizontal bar. `pct` is 0-100."""
    pct = max(0.0, min(100.0, float(pct)))
    fill = "" if tone == "primary" else f" ka-fill-{tone}"
    return (
        '<div class="ka-meter">'
        f'<div class="ka-meter-row"><span class="ka-meter-label">{esc(label)}</span>'
        f'<span class="ka-meter-value">{esc(value_text)}</span></div>'
        f'<div class="ka-meter-track" role="progressbar" aria-label="{esc(label)}" aria-valuemin="0" '
        f'aria-valuemax="100" aria-valuenow="{pct:.0f}"><div class="ka-meter-fill{fill}" style="width:{pct:.1f}%"></div></div>'
        "</div>"
    )


def stat_tile(icon: str, value, label: str, tone: str = "primary") -> str:
    return (
        '<div class="ka-stat">'
        f'<div class="ka-stat-icon ka-tone-{tone}">{icons.svg(icon, 22)}</div>'
        f'<div><div class="ka-stat-value">{esc(str(value))}</div><div class="ka-stat-label">{esc(label)}</div></div>'
        "</div>"
    )


def stat_grid(tiles: list) -> None:
    html('<div class="ka-stats">' + "".join(tiles) + "</div>")


def page_header(title: str, subtitle: str, icon: Optional[str] = None, aside: str = "") -> None:
    icon_html = f'<div class="ka-pagehead-icon">{icons.svg(icon, 24)}</div>' if icon else ""
    aside_html = f"<div>{aside}</div>" if aside else ""
    html(
        '<div class="ka-pagehead"><div class="ka-pagehead-title">'
        f'{icon_html}<div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p></div></div>{aside_html}</div>'
    )


def card_heading(title: str, subtitle: str = "") -> None:
    sub = f'<p class="ka-card-sub">{esc(subtitle)}</p>' if subtitle else ""
    html(f'<div class="ka-card-title">{esc(title)}</div>{sub}')


def empty_state(icon: str, title: str, body: str) -> None:
    html(
        '<div class="ka-empty">'
        f'<div class="ka-empty-icon ka-tone-primary">{icons.svg(icon, 24)}</div>'
        f"<h4>{esc(title)}</h4><p>{esc(body)}</p></div>"
    )


def chip(icon: str, text: str) -> str:
    return f'<span class="ka-chip">{icons.svg(icon, 16)}{esc(text)}</span>'


def row(title: str, sub: str = "", right: str = "") -> str:
    return (
        '<div class="ka-row"><div class="ka-row-main">'
        f'<div class="ka-row-title">{esc(title)}</div><div class="ka-row-sub">{esc(sub)}</div></div>{right}</div>'
    )


# ---------------------------------------------------------- flash toasts ---
# st.rerun() wipes anything shown before it, so confirmations ("Advisory
# saved") are stored in session state and shown as a toast after the rerun.

def flash(message: str, icon: str = ":material/check_circle:") -> None:
    st.session_state.setdefault("_flash", []).append((message, icon))


def show_flash() -> None:
    for message, icon in st.session_state.pop("_flash", []):
        st.toast(message, icon=icon)


# ----------------------------------------------------------------- misc ----

def initials(name: str) -> str:
    parts = [p for p in (name or "").split() if p]
    if not parts:
        return "?"
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def first_name(name: str) -> str:
    return (name or "there").split()[0]
