"""My uploads: history of analysed leaf photos."""

import json
import os

import streamlit as st

import advisory_service
import database
import ui
from views.disease import BREAKDOWN, TONE  # noqa: F401  (TONE reused below)


def render() -> None:
    user = st.session_state["user"]
    ui.page_header("My uploads", "Every leaf photo you have analysed, saved with its assessment.", icon="images")

    uploads = database.get_user_uploads(user["id"], module="disease_detection")
    if not uploads:
        ui.empty_state("images", "No uploads yet", "Photos you analyse under Disease detection are saved here automatically.")
        return

    st.caption(f"{len(uploads)} photo{'s' if len(uploads) != 1 else ''}, newest first")
    cols = st.columns(3, gap="medium")
    for i, u in enumerate(uploads):
        with cols[i % 3]:
            with ui.card(f"up_{u['id']}"):
                if os.path.exists(u["stored_path"]):
                    st.image(u["stored_path"], width="stretch")
                else:
                    st.caption("Image file is missing on disk.")
                if u["result_json"]:
                    r = json.loads(u["result_json"])
                    label = r["condition"].replace("_", " ").title()
                    ui.html(f'{ui.pill(label, TONE.get(r["condition"], "warn"))} '
                            f'<span class="ka-row-sub">&nbsp;{r["confidence"]}% confidence</span>')
                    st.write(r["advice"])
                st.caption(f'{u["original_filename"]}, {advisory_service.format_ist(advisory_service.to_iso(u["uploaded_at"]))}')
