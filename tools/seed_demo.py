"""
seed_demo.py - fill a fresh database with demo data for a viva or screenshots.

    python tools/seed_demo.py

Creates the account  demo / demo1234  with four saved weather advisories and
one booking. Safe to run more than once (it skips anything that exists).
This is for demonstrations only - don't use these credentials for real data.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import advisory_service
import auth
import database
from schemas import AdvisoryCreate


def main() -> None:
    database.init_db()
    ok, message = auth.signup("demo", "demo1234", "Ravi Kumar", "farmer", "9000000000", "Belagavi")
    print(message if ok else "demo user already exists")
    user = database.get_user_by_username("demo")

    if advisory_service.list_advisories(user["id"], limit=1)["total"] == 0:
        create = advisory_service.create_advisory
        create(user["id"], AdvisoryCreate(city="Belagavi", crop="Sugarcane"))
        create(user["id"], AdvisoryCreate(city="Hubballi", temperature=27.5, humidity=84, condition="Light Rain",
                                          rainfall_mm=7.2, wind_speed=4.1, crop="Maize"))
        create(user["id"], AdvisoryCreate(city="Dharwad", temperature=39, humidity=30, condition="Clear",
                                          wind_speed=6, crop="Groundnut", notes="Heat spell expected"))
        create(user["id"], AdvisoryCreate(city="Belagavi", temperature=24, humidity=88, condition="Thunderstorm",
                                          rainfall_mm=18, wind_speed=13, crop="Rice", status="resolved"))
        print("added 4 advisories")

    if not database.get_bookings():
        database.book_equipment(1, "Ravi Kumar", "2026-09-21", "2026-09-23", 2400.0)
        print("added 1 booking")
    print("done - log in as demo / demo1234")


if __name__ == "__main__":
    main()
