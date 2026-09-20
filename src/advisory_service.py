"""
advisory_service.py

Business logic for weather advisories, shared by the REST API (api.py) and the
Streamlit interface (views/weather.py). Neither of them touches SQL directly;
they both go through here, so the rules below apply no matter which door a
request comes in through.

    api.py / views/weather.py  ->  advisory_service.py  ->  database.py

Every function takes `user_id` first and only ever sees that user's records.
"""

from datetime import datetime, timedelta, timezone

import database
import weather_service
from schemas import AdvisoryCreate, AdvisoryPatch, AdvisoryReplace

IST = timezone(timedelta(hours=5, minutes=30))  # India has no DST, so a fixed offset is exact

READING_FIELDS = ("temperature", "humidity", "condition", "rainfall_mm", "wind_speed")


class AdvisoryNotFound(Exception):
    """Raised when an advisory doesn't exist or belongs to someone else."""


# ---------------------------------------------------------------- helpers ---

def to_iso(sqlite_ts):
    """'2026-09-20 08:15:00' (UTC, from SQLite) -> '2026-09-20T08:15:00Z'."""
    return sqlite_ts.replace(" ", "T") + "Z" if sqlite_ts and "T" not in sqlite_ts else sqlite_ts


def format_ist(ts):
    """Human-readable local time for the UI, e.g. '20 Sep 2026, 13:45 IST'."""
    if not ts:
        return "-"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00").replace(" ", "T"))
    except ValueError:
        return ts
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(IST).strftime("%d %b %Y, %H:%M IST")


def _public(row):
    """Database row -> API-safe dict (no user_id, ISO timestamps)."""
    out = {k: v for k, v in row.items() if k != "user_id"}
    out["created_at"] = to_iso(out["created_at"])
    out["updated_at"] = to_iso(out["updated_at"])
    return out


def generate_advice(weather):
    """Run the rule engine over a weather dict -> {'severity': ..., 'tips': [...]}."""
    return {
        "severity": weather_service.derive_severity(weather),
        "tips": weather_service.get_farming_advisory(weather),
    }


def current_conditions(city, api_key=None):
    """Current weather for a city plus generated advice. Nothing is stored."""
    weather = weather_service.get_weather(city, api_key=api_key)
    return {**weather, **generate_advice(weather)}


# ------------------------------------------------------------------- CRUD ---

def create_advisory(user_id, payload: AdvisoryCreate, source=None):
    """POST: create an advisory, fetching weather and generating advice as needed.

    `source` lets trusted in-process callers (the web UI) record where readings
    they already fetched came from. The REST API never passes it, so API clients
    can't spoof a source label.
    """
    if payload.temperature is None:
        weather = weather_service.get_weather(payload.city)
        readings = {f: weather[f] for f in READING_FIELDS}
        source = weather["source"]
    else:
        readings = {
            "temperature": payload.temperature,
            "humidity": payload.humidity,
            "condition": payload.condition,
            "rainfall_mm": payload.rainfall_mm or 0.0,
            "wind_speed": payload.wind_speed or 0.0,
        }
        source = source or "manual"

    advice = generate_advice(readings)
    new_id = database.create_advisory(user_id, {
        "city": payload.city,
        **readings,
        "crop": payload.crop,
        "severity": payload.severity or advice["severity"],
        "status": payload.status,
        "tips": payload.tips or advice["tips"],
        "notes": payload.notes,
        "source": source,
    })
    return get_advisory(user_id, new_id)


def get_advisory(user_id, advisory_id):
    """GET one."""
    row = database.get_advisory(advisory_id, user_id)
    if not row:
        raise AdvisoryNotFound(advisory_id)
    return _public(row)


def list_advisories(user_id, city=None, severity=None, status=None, limit=50, offset=0):
    """GET many, newest first. Returns {'items', 'total', 'limit', 'offset'}."""
    rows, total = database.list_advisories(user_id, city, severity, status, limit, offset)
    return {"items": [_public(r) for r in rows], "total": total, "limit": limit, "offset": offset}


def _apply_update(user_id, advisory_id, fields):
    existing = database.get_advisory(advisory_id, user_id)
    if not existing:
        raise AdvisoryNotFound(advisory_id)

    # If the readings themselves were edited, the record no longer reflects
    # what the weather source reported -- say so instead of leaving a stale label.
    readings_changed = any(f in fields and fields[f] != existing[f] for f in READING_FIELDS)
    if readings_changed and not existing["source"].startswith("manual"):
        fields = {**fields, "source": "manual (edited)"}

    database.update_advisory(advisory_id, user_id, fields)
    return get_advisory(user_id, advisory_id)


def replace_advisory(user_id, advisory_id, payload: AdvisoryReplace):
    """PUT: replace every writable field."""
    return _apply_update(user_id, advisory_id, payload.model_dump())


def patch_advisory(user_id, advisory_id, payload: AdvisoryPatch):
    """PATCH: change only the fields the client actually sent."""
    return _apply_update(user_id, advisory_id, payload.model_dump(exclude_unset=True))


def delete_advisory(user_id, advisory_id):
    """DELETE. Raises AdvisoryNotFound if there was nothing to delete."""
    if not database.delete_advisory(advisory_id, user_id):
        raise AdvisoryNotFound(advisory_id)
