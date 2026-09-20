"""
Weather advisory page.

Tab 1  Current conditions   look up weather + generated advice, save it (POST)
Tab 2  Advisory records     list, edit (PUT), quick status change (PATCH), delete (DELETE)
Tab 3  REST API             endpoint reference and a live request console

The record operations call advisory_service, the same layer the REST API uses,
so the page and the API always follow the same rules.
"""

import json
import os
import time

import pandas as pd
import requests
import streamlit as st
from pydantic import ValidationError

import advisory_service as service
import icons
import ui
from schemas import SEVERITIES, STATUSES, AdvisoryCreate, AdvisoryPatch, AdvisoryReplace

DEFAULT_CITY = "Belagavi"
API_URL = os.environ.get("KRISHI_API_URL", "http://127.0.0.1:8000")


def _errors(exc: ValidationError) -> str:
    """Turn a pydantic error into one readable line per problem."""
    lines = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err["loc"]) or "form"
        msg = err["msg"].replace("Value error, ", "")
        lines.append(f"{field}: {msg}" if field != "form" else msg)
    return "  \n".join(lines)


# ============================================================ tab 1: check ==

def _readings_tiles(w: dict) -> None:
    ui.stat_grid([
        ui.stat_tile("thermometer", f'{w["temperature"]:.1f}°C', "Temperature", "warn"),
        ui.stat_tile("droplets", f'{w["humidity"]:.0f}%', "Humidity", "info"),
        ui.stat_tile("cloud", w["condition"], "Condition", "primary"),
        ui.stat_tile("cloud-rain", f'{w["rainfall_mm"]:.1f} mm', "Rainfall", "info"),
        ui.stat_tile("wind", f'{w["wind_speed"]:.1f} m/s', "Wind", "neutral"),
    ])


def _tab_current(user: dict) -> None:
    c1, c2, c3 = st.columns([1.2, 1.2, 0.8], vertical_alignment="bottom")
    city = c1.text_input("City or district", value=(user.get("location") or "").strip() or DEFAULT_CITY, key="wx_city")
    api_key = c2.text_input("OpenWeatherMap API key (optional)", type="password", key="wx_key",
                            help="Leave blank to use simulated weather. You can also set OPENWEATHER_API_KEY.")
    if c3.button("Get advisory", type="primary", width="stretch"):
        if not city.strip():
            st.error("Enter a city or district.")
        else:
            st.session_state["wx_current"] = service.current_conditions(city.strip(), api_key.strip() or None)

    cur = st.session_state.get("wx_current")
    if not cur:
        ui.empty_state("cloud-sun", "Check the weather for your farm",
                       "Enter a place above. You will get the current readings and advice you can act on today.")
        return

    st.write("")
    ui.html(f'<div style="display:flex;gap:.7rem;align-items:center;margin-bottom:.8rem">'
            f'<h3 style="margin:0">{ui.esc(cur["city"])}</h3>{ui.severity_pill(cur["severity"])}'
            f'<span class="ka-row-sub">Source: {ui.esc(cur["source"])}</span></div>')
    _readings_tiles(cur)

    left, right = st.columns([1.3, 1], gap="medium")
    with left:
        with ui.card("weather1"):
            ui.card_heading("Farming advice", "Rules applied to the readings above")
            ui.html('<ul style="margin:0;padding-left:1.1rem">' +
                    "".join(f'<li style="margin:.3rem 0">{ui.esc(t)}</li>' for t in cur["tips"]) + "</ul>")
    with right:
        with st.form("save_advisory_form"):
            ui.card_heading("Keep this advisory", "Save it to your records to edit or share later.")
            crop = st.text_input("Crop (optional)", placeholder="e.g. Sugarcane")
            notes = st.text_area("Notes (optional)", height=80, max_chars=500)
            if st.form_submit_button("Save advisory", type="primary", width="stretch"):
                try:
                    payload = AdvisoryCreate(
                        city=cur["city"], temperature=cur["temperature"], humidity=cur["humidity"],
                        condition=cur["condition"], rainfall_mm=cur["rainfall_mm"], wind_speed=cur["wind_speed"],
                        severity=cur["severity"], tips=cur["tips"], crop=crop or None, notes=notes or None)
                except ValidationError as exc:
                    st.error(_errors(exc))
                else:
                    saved = service.create_advisory(user["id"], payload, source=cur["source"])
                    st.session_state["adv_table_v"] = st.session_state.get("adv_table_v", 0) + 1
                    ui.flash(f'Advisory #{saved["id"]} saved for {saved["city"]}.')
                    st.rerun()


# ======================================================== tab 2: records ====

def _clear_editor_state() -> None:
    for key in [k for k in st.session_state if k.startswith("edit_")]:
        del st.session_state[key]


def _bump_table() -> None:
    st.session_state["adv_table_v"] = st.session_state.get("adv_table_v", 0) + 1


@st.dialog("New advisory", width="large")
def _new_dialog(user: dict) -> None:
    st.caption("Fetch today's weather for a place, or type in readings you measured yourself.")
    mode = st.radio("Readings", ["Fetch current weather", "Enter readings manually"], horizontal=True,
                    label_visibility="collapsed")
    c1, c2 = st.columns(2)
    city = c1.text_input("City or district", value=(user.get("location") or "").strip() or DEFAULT_CITY, key="new_city")
    crop = c2.text_input("Crop (optional)", key="new_crop")
    data = {}
    if mode == "Enter readings manually":
        r1, r2, r3 = st.columns(3)
        data = dict(
            temperature=r1.number_input("Temperature (°C)", -50.0, 60.0, 28.0, key="new_temp"),
            humidity=r2.number_input("Humidity (%)", 0.0, 100.0, 60.0, key="new_hum"),
            condition=r3.text_input("Condition", value="Clear", key="new_cond"),
            rainfall_mm=r1.number_input("Rainfall (mm)", 0.0, 1000.0, 0.0, key="new_rain"),
            wind_speed=r2.number_input("Wind (m/s)", 0.0, 150.0, 3.0, key="new_wind"),
        )
    notes = st.text_area("Notes (optional)", max_chars=500, key="new_notes")
    st.caption("Severity and tips are generated from the readings. You can change them after saving.")

    if st.button("Create advisory", type="primary", key="new_submit"):
        try:
            payload = AdvisoryCreate(city=city, crop=crop or None, notes=notes or None, **data)
        except ValidationError as exc:
            st.error(_errors(exc))
            return
        saved = service.create_advisory(user["id"], payload)
        _bump_table()
        ui.flash(f'Advisory #{saved["id"]} created for {saved["city"]}.')
        st.rerun()


@st.dialog("Delete this advisory?")
def _delete_dialog(user: dict, adv: dict) -> None:
    st.write(f'Advisory **#{adv["id"]}** for **{adv["city"]}** will be permanently removed. This cannot be undone.')
    c1, c2 = st.columns(2)
    if c1.button("Delete advisory", key="dangersolid_confirm", width="stretch"):
        service.delete_advisory(user["id"], adv["id"])
        _clear_editor_state()
        _bump_table()
        ui.flash(f'Advisory #{adv["id"]} deleted.', ":material/delete:")
        st.rerun()
    if c2.button("Keep it", key="keep_advisory", width="stretch"):
        st.rerun()


# Editor callbacks run before the page re-renders, which is the only safe place
# to change the value of a widget that already exists.

def _cb_save(user_id: int, adv_id: int) -> None:
    s = st.session_state
    try:
        payload = AdvisoryReplace(
            city=s["edit_city"], temperature=s["edit_temp"], humidity=s["edit_hum"], condition=s["edit_cond"],
            rainfall_mm=s["edit_rain"], wind_speed=s["edit_wind"], crop=s["edit_crop"] or None,
            severity=s["edit_sev"], status=s["edit_status"],
            tips=[t for t in s["edit_tips"].splitlines() if t.strip()], notes=s["edit_notes"] or None)
    except ValidationError as exc:
        s["_edit_error"] = _errors(exc)
        return
    service.replace_advisory(user_id, adv_id, payload)  # PUT
    ui.flash(f"Advisory #{adv_id} updated.")


def _cb_set_status(user_id: int, adv_id: int, status: str) -> None:
    service.patch_advisory(user_id, adv_id, AdvisoryPatch(status=status))  # PATCH
    st.session_state["edit_status"] = status
    ui.flash(f"Advisory #{adv_id} marked as {status}.")


def _cb_recalculate() -> None:
    s = st.session_state
    weather = dict(temperature=s["edit_temp"], humidity=s["edit_hum"], condition=s["edit_cond"] or "Clear",
                   rainfall_mm=s["edit_rain"], wind_speed=s["edit_wind"])
    advice = service.generate_advice(weather)
    s["edit_tips"] = "\n".join(advice["tips"])
    s["edit_sev"] = advice["severity"]
    ui.flash("Advice recalculated from the readings. Save changes to keep it.", ":material/calculate:")


def _editor(user: dict, adv: dict) -> None:
    s = st.session_state
    if s.get("_editing_id") != adv["id"]:  # a different record was picked: start from its stored values
        _clear_editor_state()
        s["_editing_id"] = adv["id"]

    with ui.card("weather2"):
        ui.html(
            f'<div style="display:flex;justify-content:space-between;align-items:center;gap:1rem;flex-wrap:wrap">'
            f'<div><div class="ka-card-title">Advisory #{adv["id"]}, {ui.esc(adv["city"])}</div>'
            f'<div class="ka-row-sub">Created {service.format_ist(adv["created_at"])}. '
            f'Last updated {service.format_ist(adv["updated_at"])}. Source: {ui.esc(adv["source"])}</div></div>'
            f'<div>{ui.severity_pill(adv["severity"])} {ui.status_pill(adv["status"], ui.ADVISORY_STATUS_TONE)}</div></div>')
        st.write("")

        a, b, c = st.columns(3)
        a.text_input("City or district", value=adv["city"], key="edit_city", max_chars=80)
        b.text_input("Crop", value=adv["crop"] or "", key="edit_crop", max_chars=60)
        c.text_input("Condition", value=adv["condition"], key="edit_cond", max_chars=40)
        d, e, f, g = st.columns(4)
        d.number_input("Temperature (°C)", -50.0, 60.0, float(adv["temperature"]), key="edit_temp")
        e.number_input("Humidity (%)", 0.0, 100.0, float(adv["humidity"]), key="edit_hum")
        f.number_input("Rainfall (mm)", 0.0, 1000.0, float(adv["rainfall_mm"]), key="edit_rain")
        g.number_input("Wind (m/s)", 0.0, 150.0, float(adv["wind_speed"]), key="edit_wind")
        h, i = st.columns(2)
        h.selectbox("Severity", SEVERITIES, index=SEVERITIES.index(adv["severity"]), key="edit_sev",
                    format_func=lambda v: ui.SEVERITY_LABEL[v])
        i.selectbox("Status", STATUSES, index=STATUSES.index(adv["status"]), key="edit_status", format_func=str.title)
        st.text_area("Tips (one per line)", value="\n".join(adv["tips"]), key="edit_tips", height=130)
        st.text_area("Notes", value=adv["notes"] or "", key="edit_notes", height=80, max_chars=500)

        b1, b2, b3, b4 = st.columns(4)
        b1.button("Save changes", type="primary", icon=":material/save:", width="stretch",
                  on_click=_cb_save, args=(user["id"], adv["id"]))
        b2.button("Recalculate advice", icon=":material/calculate:", width="stretch", on_click=_cb_recalculate,
                  help="Regenerate severity and tips from the readings above")
        if adv["status"] == "active":
            b3.button("Mark resolved", icon=":material/task_alt:", width="stretch",
                      on_click=_cb_set_status, args=(user["id"], adv["id"], "resolved"))
        else:
            b3.button("Reopen", icon=":material/undo:", width="stretch",
                      on_click=_cb_set_status, args=(user["id"], adv["id"], "active"))
        if b4.button("Delete", key="danger_open", icon=":material/delete:", width="stretch"):
            _delete_dialog(user, adv)

        if err := s.pop("_edit_error", None):
            st.error(err)


def _tab_records(user: dict) -> None:
    f1, f2, f3, f4 = st.columns([1.4, 1, 1, 1], vertical_alignment="bottom")
    city = f1.text_input("Search by city", placeholder="Type part of a name", key="flt_city")
    severity = f2.selectbox("Severity", ["All"] + list(SEVERITIES), key="flt_sev",
                            format_func=lambda v: v if v == "All" else ui.SEVERITY_LABEL[v])
    status = f3.selectbox("Status", ["All"] + list(STATUSES), key="flt_status", format_func=str.title)
    if f4.button("New advisory", type="primary", icon=":material/add:", width="stretch"):
        _new_dialog(user)

    result = service.list_advisories(
        user["id"], city=city or None, severity=None if severity == "All" else severity,
        status=None if status == "All" else status, limit=200)
    items = result["items"]

    if not items:
        st.write("")
        if result["total"] == 0 and not (city or severity != "All" or status != "All"):
            ui.empty_state("cloud-sun", "You have no advisories yet",
                           "Create one with New advisory, or save one from the Current conditions tab.")
        else:
            ui.empty_state("search", "No advisories match these filters", "Change or clear the filters above.")
        return

    st.caption(f'{result["total"]} advisor{"y" if result["total"] == 1 else "ies"}. Select a row to edit or delete it.')
    df = pd.DataFrame([{
        "ID": a["id"], "City": a["city"], "Crop": a["crop"] or "", "Condition": a["condition"],
        "Temp (°C)": a["temperature"], "Severity": ui.SEVERITY_LABEL[a["severity"]],
        "Status": a["status"].title(), "Updated": service.format_ist(a["updated_at"]),
    } for a in items])
    event = st.dataframe(
        df, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
        key=f'adv_table_{st.session_state.get("adv_table_v", 0)}',
        column_config={"ID": st.column_config.NumberColumn(width="small"),
                       "Temp (°C)": st.column_config.NumberColumn(format="%.1f")})

    rows = event.selection.rows
    if rows and rows[0] < len(items):
        st.write("")
        _editor(user, items[rows[0]])
    else:
        st.session_state.pop("_editing_id", None)


# ========================================================= tab 3: REST API ==

ENDPOINTS = [
    ("GET", "/api/v1/advisories", "List your advisories. Filter with city, severity, status; page with limit and offset."),
    ("POST", "/api/v1/advisories", "Create an advisory. Send just a city to fetch weather and generate advice."),
    ("GET", "/api/v1/advisories/{id}", "Read one advisory."),
    ("PUT", "/api/v1/advisories/{id}", "Replace an advisory. Every writable field is required."),
    ("PATCH", "/api/v1/advisories/{id}", "Update only the fields you send, for example just the status."),
    ("DELETE", "/api/v1/advisories/{id}", "Delete an advisory. Returns 204 with no body."),
    ("GET", "/api/v1/weather?city=", "Current conditions and advice for a city. Nothing is saved."),
]

EXAMPLES = {
    "GET": ("/api/v1/advisories?severity=warning", ""),
    "POST": ("/api/v1/advisories", '{\n  "city": "Belagavi",\n  "crop": "Sugarcane",\n  "notes": "Created from the console"\n}'),
    "PUT": ("/api/v1/advisories/1", '{\n  "city": "Belagavi",\n  "temperature": 31.0,\n  "humidity": 48,\n  "condition": "Clear",\n'
            '  "rainfall_mm": 0,\n  "wind_speed": 3.2,\n  "crop": "Sugarcane",\n  "severity": "info",\n  "status": "active",\n'
            '  "tips": ["Conditions are favorable for routine field operations."],\n  "notes": "Reviewed"\n}'),
    "PATCH": ("/api/v1/advisories/1", '{\n  "status": "resolved"\n}'),
    "DELETE": ("/api/v1/advisories/1", ""),
}


def _cb_method_changed() -> None:
    path, body = EXAMPLES[st.session_state["con_method"]]
    st.session_state["con_path"], st.session_state["con_body"] = path, body


def _curl(method: str, base: str, path: str, body: str, username: str) -> str:
    parts = [f"curl -X {method} '{base}{path}'", f"-u {username or 'USERNAME'}:PASSWORD"]
    if body.strip() and method in ("POST", "PUT", "PATCH"):
        parts += ["-H 'Content-Type: application/json'", "-d '" + " ".join(body.split()) + "'"]
    return " \\\n  ".join(parts)


def _api_online(base: str) -> bool:
    try:
        return requests.get(f"{base}/health", timeout=1.5).status_code == 200
    except requests.RequestException:
        return False


def _tab_api(user: dict) -> None:
    base = st.text_input("API server address", value=API_URL, key="con_base").rstrip("/")
    online = _api_online(base)

    left, right = st.columns([1.5, 1], gap="medium")
    with left:
        with ui.card("weather3"):
            ui.card_heading("Endpoints", "HTTP Basic authentication with your KrishiAI username and password")
            ui.html("".join(
                f'<div class="ka-endpoint">{ui.method_pill(m)}<code>{ui.esc(p)}</code><span class="ka-ep-desc">{ui.esc(d)}</span></div>'
                for m, p, d in ENDPOINTS))
    with right:
        with ui.card("weather4"):
            ui.card_heading("Server status")
            ui.html(ui.pill("API online" if online else "API offline", "ok" if online else "bad"))
            if online:
                ui.html(f'<p class="ka-row-sub" style="margin-top:.7rem">Interactive documentation: '
                        f'<a href="{ui.esc(base)}/docs" target="_blank">{ui.esc(base)}/docs</a></p>')
            else:
                st.caption("Start it in a second terminal from the src folder:")
                st.code("uvicorn api:app --port 8000", language="bash")
                st.caption("Or run everything at once with `python run.py`.")

    st.write("")
    with ui.card("weather5"):
        ui.card_heading("Request console", "Send a real request to the API and inspect the response")
        c1, c2 = st.columns([1, 3])
        method = c1.selectbox("Method", list(EXAMPLES), key="con_method", on_change=_cb_method_changed)
        path = c2.text_input("Path", value=EXAMPLES["GET"][0], key="con_path")
        body_disabled = method in ("GET", "DELETE")
        body = st.text_area("JSON body", value=EXAMPLES["GET"][1], key="con_body", height=150, disabled=body_disabled,
                            help="Not used for GET and DELETE.")
        u1, u2, u3 = st.columns([1, 1, 1], vertical_alignment="bottom")
        username = u1.text_input("Username", value=user.get("username", ""), key="con_user")
        password = u2.text_input("Password", type="password", key="con_pass")
        send = u3.button("Send request", type="primary", icon=":material/send:", width="stretch", disabled=not online)

        st.caption("Equivalent command:")
        st.code(_curl(method, base, path, "" if body_disabled else body, username), language="bash")

        if send:
            if not path.startswith("/"):
                st.error("The path must start with /.")
            elif not username or not password:
                st.error("Enter your username and password. They are sent to the API as Basic authentication.")
            else:
                kwargs = {}
                if not body_disabled and body.strip():
                    try:
                        kwargs["json"] = json.loads(body)
                    except json.JSONDecodeError as exc:
                        st.error(f"The body is not valid JSON: {exc.msg} (line {exc.lineno}).")
                        return
                started = time.perf_counter()
                try:
                    resp = requests.request(method, base + path, auth=(username, password), timeout=10, **kwargs)
                except requests.RequestException as exc:
                    st.error(f"Could not reach the API: {exc}")
                    return
                ms = (time.perf_counter() - started) * 1000
                tone = "ok" if resp.status_code < 300 else "warn" if resp.status_code < 500 else "bad"
                ui.html(f'{ui.pill(f"{resp.status_code} {resp.reason}", tone)} '
                        f'<span class="ka-row-sub">&nbsp;{ms:.0f} ms</span>')
                if resp.content:
                    try:
                        st.code(json.dumps(resp.json(), indent=2), language="json")
                    except ValueError:
                        st.code(resp.text[:2000])
                else:
                    st.caption("The response has no body.")
                if method != "GET" and resp.status_code < 300:
                    _bump_table()


def render() -> None:
    user = st.session_state["user"]
    ui.page_header("Weather advisory",
                   "Check current conditions, keep a record of advisories, and manage them here or through the REST API.",
                   icon="cloud-sun")
    tab_now, tab_records, tab_api = st.tabs(["Current conditions", "Advisory records", "REST API"])
    with tab_now:
        _tab_current(user)
    with tab_records:
        _tab_records(user)
    with tab_api:
        _tab_api(user)
