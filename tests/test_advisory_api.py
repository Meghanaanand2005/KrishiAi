"""
Tests for the Weather Advisory REST API (POST / GET / PUT / PATCH / DELETE).

Run from the project root:   pytest -v
"""
BASE = "/api/v1/advisories"

MANUAL = {
    "city": "Hubballi", "temperature": 27.5, "humidity": 84, "condition": "Light Rain",
    "rainfall_mm": 7.2, "wind_speed": 4.1, "crop": "Maize",
}


def make(client, auth, **overrides):
    r = client.post(BASE, json={**MANUAL, **overrides}, auth=auth)
    assert r.status_code == 201, r.text
    return r.json()


# --------------------------------------------------------------------- auth --

def test_health_is_public(client):
    assert client.get("/health").json()["status"] == "ok"


def test_requires_credentials(client):
    r = client.get(BASE)
    assert r.status_code == 401
    assert "Basic" in r.headers["www-authenticate"]


def test_rejects_wrong_password_and_unknown_user_identically(client):
    wrong_pw = client.get(BASE, auth=("alice", "nope-nope"))
    unknown = client.get(BASE, auth=("ghost", "whatever1"))
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()  # doesn't reveal which usernames exist


# --------------------------------------------------------------------- POST --

def test_post_city_only_fetches_weather_and_generates_advice(client, alice):
    r = client.post(BASE, json={"city": "Belagavi"}, auth=alice)
    assert r.status_code == 201
    body = r.json()
    assert r.headers["location"] == f"{BASE}/{body['id']}"
    assert body["city"] == "Belagavi"
    assert body["source"].startswith("simulated")
    assert body["severity"] in ("info", "watch", "warning")
    assert len(body["tips"]) >= 1
    assert body["status"] == "active"
    assert body["created_at"].endswith("Z")


def test_post_manual_readings_derives_severity_and_tips(client, alice):
    body = make(client, alice)
    assert body["source"] == "manual"
    assert body["severity"] == "watch"          # light rain, 7.2 mm
    assert any("irrigation" in t.lower() for t in body["tips"])
    assert body["crop"] == "Maize"


def test_post_respects_explicit_severity_tips_and_notes(client, alice):
    body = make(client, alice, severity="warning", tips=["Harvest today."], notes="Custom")
    assert body["severity"] == "warning"
    assert body["tips"] == ["Harvest today."]
    assert body["notes"] == "Custom"


def test_post_rejects_partial_readings(client, alice):
    r = client.post(BASE, json={"city": "Dharwad", "temperature": 30}, auth=alice)
    assert r.status_code == 422


def test_post_rejects_out_of_range_and_unknown_fields(client, alice):
    assert client.post(BASE, json={**MANUAL, "humidity": 150}, auth=alice).status_code == 422
    assert client.post(BASE, json={**MANUAL, "temprature": 1}, auth=alice).status_code == 422
    assert client.post(BASE, json={"city": "   "}, auth=alice).status_code == 422
    assert client.post(BASE, json={**MANUAL, "severity": "panic"}, auth=alice).status_code == 422


# ---------------------------------------------------------------------- GET --

def test_get_one_and_404(client, alice):
    created = make(client, alice)
    r = client.get(f"{BASE}/{created['id']}", auth=alice)
    assert r.status_code == 200 and r.json() == created
    assert client.get(f"{BASE}/999999", auth=alice).status_code == 404
    assert client.get(f"{BASE}/0", auth=alice).status_code == 422  # ids start at 1


def test_list_filters_and_pagination(client, alice):
    make(client, alice, city="Belagavi", severity="info")
    make(client, alice, city="Belagavi", severity="warning")
    make(client, alice, city="Dharwad", severity="info", status="resolved")

    everything = client.get(BASE, auth=alice).json()
    assert everything["total"] == 3 and len(everything["items"]) == 3

    assert client.get(BASE, params={"city": "belag"}, auth=alice).json()["total"] == 2
    assert client.get(BASE, params={"severity": "warning"}, auth=alice).json()["total"] == 1
    assert client.get(BASE, params={"status": "resolved"}, auth=alice).json()["total"] == 1

    page = client.get(BASE, params={"limit": 2, "offset": 2}, auth=alice).json()
    assert page["total"] == 3 and len(page["items"]) == 1
    assert client.get(BASE, params={"severity": "bogus"}, auth=alice).status_code == 422


# ---------------------------------------------------------------------- PUT --

PUT_BODY = {
    "city": "Belagavi", "temperature": 31.0, "humidity": 48, "condition": "Clear",
    "rainfall_mm": 0, "wind_speed": 3.2, "crop": "Sugarcane", "severity": "info",
    "status": "active", "tips": ["Conditions are favorable."], "notes": "Reviewed",
}


def test_put_replaces_every_field(client, alice):
    created = make(client, alice, notes="to be wiped")
    r = client.put(f"{BASE}/{created['id']}", json=PUT_BODY, auth=alice)
    assert r.status_code == 200
    body = r.json()
    for key, value in PUT_BODY.items():
        assert body[key] == value
    assert body["id"] == created["id"]
    assert client.get(f"{BASE}/{created['id']}", auth=alice).json() == body  # persisted


def test_put_without_optional_fields_clears_them(client, alice):
    created = make(client, alice, notes="to be wiped")
    minimal = {k: v for k, v in PUT_BODY.items() if k not in ("crop", "notes")}
    body = client.put(f"{BASE}/{created['id']}", json=minimal, auth=alice).json()
    assert body["crop"] is None and body["notes"] is None


def test_put_requires_full_body_and_ignores_readonly_fields(client, alice):
    created = make(client, alice)
    incomplete = {k: v for k, v in PUT_BODY.items() if k != "tips"}
    assert client.put(f"{BASE}/{created['id']}", json=incomplete, auth=alice).status_code == 422
    # A GET -> edit -> PUT round trip (which includes id / timestamps) must work.
    roundtrip = {**created, **PUT_BODY}
    assert client.put(f"{BASE}/{created['id']}", json=roundtrip, auth=alice).status_code == 200


def test_put_404(client, alice):
    assert client.put(f"{BASE}/424242", json=PUT_BODY, auth=alice).status_code == 404


# -------------------------------------------------------------------- PATCH --

def test_patch_changes_only_sent_fields(client, alice):
    created = make(client, alice)
    r = client.patch(f"{BASE}/{created['id']}", json={"status": "resolved"}, auth=alice)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "resolved"
    for key in ("city", "temperature", "humidity", "condition", "tips", "severity", "crop"):
        assert body[key] == created[key]


def test_patch_can_clear_nullable_fields(client, alice):
    created = make(client, alice, notes="temp")
    body = client.patch(f"{BASE}/{created['id']}", json={"crop": None, "notes": None}, auth=alice).json()
    assert body["crop"] is None and body["notes"] is None


def test_patch_validation(client, alice):
    created = make(client, alice)
    url = f"{BASE}/{created['id']}"
    assert client.patch(url, json={}, auth=alice).status_code == 422                      # nothing to update
    assert client.patch(url, json={"temperature": None}, auth=alice).status_code == 422   # can't null a required field
    assert client.patch(url, json={"humidity": -5}, auth=alice).status_code == 422
    assert client.patch(url, json={"nonsense": 1}, auth=alice).status_code == 422
    assert client.patch(f"{BASE}/424242", json={"status": "resolved"}, auth=alice).status_code == 404


def test_editing_readings_of_a_fetched_record_updates_its_source_label(client, alice):
    fetched = client.post(BASE, json={"city": "Belagavi"}, auth=alice).json()
    assert fetched["source"].startswith("simulated")
    same = client.patch(f"{BASE}/{fetched['id']}", json={"notes": "just a note"}, auth=alice).json()
    assert same["source"] == fetched["source"]                       # notes don't touch the readings
    edited = client.patch(f"{BASE}/{fetched['id']}", json={"temperature": 12.3}, auth=alice).json()
    assert edited["source"] == "manual (edited)"


# ------------------------------------------------------------------- DELETE --

def test_delete_then_gone(client, alice):
    created = make(client, alice)
    url = f"{BASE}/{created['id']}"
    r = client.delete(url, auth=alice)
    assert r.status_code == 204 and r.content == b""
    assert client.get(url, auth=alice).status_code == 404
    assert client.delete(url, auth=alice).status_code == 404        # second delete
    assert client.get(BASE, auth=alice).json()["total"] == 0


# ---------------------------------------------------------------- ownership --

def test_users_cannot_see_or_change_each_others_advisories(client, alice, bob):
    mine = make(client, alice)
    url = f"{BASE}/{mine['id']}"

    assert client.get(BASE, auth=bob).json()["total"] == 0
    assert client.get(url, auth=bob).status_code == 404
    assert client.put(url, json=PUT_BODY, auth=bob).status_code == 404
    assert client.patch(url, json={"status": "resolved"}, auth=bob).status_code == 404
    assert client.delete(url, auth=bob).status_code == 404

    still = client.get(url, auth=alice).json()                        # untouched
    assert still == mine


# ------------------------------------------------------------------ weather --

def test_weather_endpoint_returns_readings_and_advice_without_saving(client, alice):
    r = client.get("/api/v1/weather", params={"city": "Belagavi"}, auth=alice)
    assert r.status_code == 200
    body = r.json()
    assert body["severity"] in ("info", "watch", "warning") and body["tips"]
    assert client.get(BASE, auth=alice).json()["total"] == 0
    assert client.get("/api/v1/weather", auth=alice).status_code == 422   # city is required
