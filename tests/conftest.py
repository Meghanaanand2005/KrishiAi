"""Shared test fixtures: a throw-away SQLite database and two registered users."""
import os
import sys
import tempfile

# Must be set BEFORE database.py is imported anywhere.
_TMP = tempfile.mkdtemp(prefix="krishi_test_")
os.environ["KRISHI_DB_PATH"] = os.path.join(_TMP, "test.db")
os.environ.pop("OPENWEATHER_API_KEY", None)  # tests must never hit the network

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pytest
from fastapi.testclient import TestClient

import auth
import database


@pytest.fixture(scope="session")
def client():
    from api import app
    with TestClient(app) as c:  # runs the lifespan -> init_db()
        yield c


@pytest.fixture(scope="session", autouse=True)
def users(client):
    ok1, _ = auth.signup("alice", "alice-pass-1", "Alice Farmer", "farmer")
    ok2, _ = auth.signup("bob", "bob-pass-22", "Bob Owner", "owner")
    assert ok1 and ok2
    return {"alice": ("alice", "alice-pass-1"), "bob": ("bob", "bob-pass-22")}


@pytest.fixture()
def alice(users):
    return users["alice"]


@pytest.fixture()
def bob(users):
    return users["bob"]


@pytest.fixture(autouse=True)
def clean_advisories():
    conn = database.get_connection()
    conn.execute("DELETE FROM weather_advisories")
    conn.commit()
    conn.close()
    yield
