"""
database.py
Handles all SQLite persistence for KrishiAI:
- users (farmers / equipment owners, with authentication credentials)
- equipment (rental inventory)
- bookings (rental transactions)
- iot_logs (simulated sensor readings per equipment)
- uploaded_files (persisted leaf images + their diagnosis, per user)
- weather_advisories (saved advisories with full create / read / update / delete)
"""

import json
import os
import sqlite3
from pathlib import Path

# Resolve base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Set database path (supports custom KRISHI_DB_PATH environment variable if provided)
env_db_path = os.environ.get("KRISHI_DB_PATH")
if env_db_path:
    DB_PATH = Path(env_db_path)
else:
    DB_PATH = BASE_DIR / "data" / "krishiai.db"

# Automatically create the parent directory (data/) if it does not exist
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_connection():
    # timeout: wait briefly if another process holds a write lock
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't already exist, and seed sample equipment."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('farmer', 'owner')),
            phone TEXT,
            location TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            owner_name TEXT,
            location TEXT,
            price_per_day REAL NOT NULL,
            status TEXT DEFAULT 'available' CHECK(status IN ('available', 'rented', 'maintenance')),
            description TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER NOT NULL,
            farmer_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            total_cost REAL,
            status TEXT DEFAULT 'confirmed' CHECK(status IN ('confirmed', 'completed', 'cancelled')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(equipment_id) REFERENCES equipment(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS iot_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id INTEGER NOT NULL,
            fuel_level REAL,
            engine_temp REAL,
            latitude REAL,
            longitude REAL,
            health_status TEXT,
            logged_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(equipment_id) REFERENCES equipment(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            module TEXT NOT NULL,
            original_filename TEXT,
            stored_path TEXT NOT NULL,
            result_json TEXT,
            uploaded_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather_advisories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            city TEXT NOT NULL,
            temperature REAL NOT NULL,
            humidity REAL NOT NULL,
            condition TEXT NOT NULL,
            rainfall_mm REAL NOT NULL DEFAULT 0,
            wind_speed REAL NOT NULL DEFAULT 0,
            crop TEXT,
            severity TEXT NOT NULL CHECK(severity IN ('info', 'watch', 'warning')),
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'resolved')),
            tips_json TEXT NOT NULL,
            notes TEXT,
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()

    # Seed sample equipment only if table is empty
    cur.execute("SELECT COUNT(*) as c FROM equipment")
    if cur.fetchone()["c"] == 0:
        sample_equipment = [
            ("Mahindra 575 DI Tractor", "Tractor", "Ravi Kumar", "Belagavi", 1200.0, "available",
             "45 HP tractor, good for ploughing and tilling."),
            ("Combine Harvester CH-200", "Harvester", "Suresh Patil", "Belagavi", 3500.0, "available",
             "Self-propelled combine harvester for wheat and paddy."),
            ("Seed Drill Sower", "Seed Sower", "Ravi Kumar", "Hubballi", 600.0, "available",
             "Multi-crop seed drill, row spacing adjustable."),
            ("Drip Irrigation Kit", "Irrigation", "Anita Deshmukh", "Dharwad", 400.0, "available",
             "Covers up to 2 acres, includes pump and pipes."),
            ("Rotavator RV-6", "Tillage", "Suresh Patil", "Belagavi", 800.0, "maintenance",
             "6-feet rotavator for secondary tillage."),
            ("Power Sprayer PS-100", "Sprayer", "Anita Deshmukh", "Hubballi", 300.0, "available",
             "Battery powered knapsack sprayer, 16L tank."),
        ]
        cur.executemany("""
            INSERT INTO equipment (name, category, owner_name, location, price_per_day, status, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, sample_equipment)
        conn.commit()

    conn.close()


# --------------------------------------------------------------- USERS ----

def create_user(username, password_hash, salt, name, role, phone="", location=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (username, password_hash, salt, name, role, phone, location)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (username, password_hash, salt, name, role, phone, location))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_user_by_username(username):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_by_id(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


# ------------------------------------------------------------ EQUIPMENT ----

def get_all_equipment(status=None):
    conn = get_connection()
    cur = conn.cursor()
    if status:
        cur.execute("SELECT * FROM equipment WHERE status = ?", (status,))
    else:
        cur.execute("SELECT * FROM equipment")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def add_equipment(name, category, owner_name, location, price_per_day, description=""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO equipment (name, category, owner_name, location, price_per_day, status, description)
        VALUES (?, ?, ?, ?, ?, 'available', ?)
    """, (name, category, owner_name, location, price_per_day, description))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def book_equipment(equipment_id, farmer_name, start_date, end_date, total_cost):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO bookings (equipment_id, farmer_name, start_date, end_date, total_cost, status)
        VALUES (?, ?, ?, ?, ?, 'confirmed')
    """, (equipment_id, farmer_name, start_date, end_date, total_cost))
    cur.execute("UPDATE equipment SET status = 'rented' WHERE id = ?", (equipment_id,))
    conn.commit()
    booking_id = cur.lastrowid
    conn.close()
    return booking_id


def get_bookings():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT bookings.*, equipment.name as equipment_name
        FROM bookings JOIN equipment ON bookings.equipment_id = equipment.id
        ORDER BY bookings.created_at DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def release_equipment(equipment_id):
    """Mark equipment available again (e.g. booking completed)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE equipment SET status = 'available' WHERE id = ?", (equipment_id,))
    conn.commit()
    conn.close()


def complete_booking(booking_id):
    """Mark a booking as completed AND make its equipment available again."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT equipment_id FROM bookings WHERE id = ? AND status = 'confirmed'", (booking_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False
    cur.execute("UPDATE bookings SET status = 'completed' WHERE id = ?", (booking_id,))
    cur.execute("UPDATE equipment SET status = 'available' WHERE id = ?", (row["equipment_id"],))
    conn.commit()
    conn.close()
    return True


def log_iot_reading(equipment_id, fuel_level, engine_temp, latitude, longitude, health_status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO iot_logs (equipment_id, fuel_level, engine_temp, latitude, longitude, health_status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (equipment_id, fuel_level, engine_temp, latitude, longitude, health_status))
    conn.commit()
    conn.close()


def get_latest_iot_reading(equipment_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM iot_logs WHERE equipment_id = ? ORDER BY logged_at DESC, id DESC LIMIT 1
    """, (equipment_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_iot_history(equipment_id, limit=20):
    """Most recent readings for one machine, oldest first (ready for charting)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM iot_logs WHERE equipment_id = ? ORDER BY logged_at DESC, id DESC LIMIT ?
    """, (equipment_id, limit))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return list(reversed(rows))


# ------------------------------------------------------------- UPLOADS ----

def save_uploaded_file(user_id, module, original_filename, stored_path, result_json=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO uploaded_files (user_id, module, original_filename, stored_path, result_json)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, module, original_filename, stored_path, result_json))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_user_uploads(user_id, module=None):
    conn = get_connection()
    cur = conn.cursor()
    if module:
        cur.execute("""
            SELECT * FROM uploaded_files WHERE user_id = ? AND module = ? ORDER BY uploaded_at DESC
        """, (user_id, module))
    else:
        cur.execute("""
            SELECT * FROM uploaded_files WHERE user_id = ? ORDER BY uploaded_at DESC
        """, (user_id,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


# ------------------------------------------------- WEATHER ADVISORIES ------

_ADVISORY_COLUMNS = (
    "city", "temperature", "humidity", "condition", "rainfall_mm", "wind_speed",
    "crop", "severity", "status", "tips", "notes", "source",
)


def _advisory_row(row):
    d = dict(row)
    d["tips"] = json.loads(d.pop("tips_json"))
    return d


def create_advisory(user_id, data):
    """INSERT a new advisory. `data` holds the keys in _ADVISORY_COLUMNS."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO weather_advisories
            (user_id, city, temperature, humidity, condition, rainfall_mm, wind_speed,
             crop, severity, status, tips_json, notes, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, data["city"], data["temperature"], data["humidity"], data["condition"],
        data["rainfall_mm"], data["wind_speed"], data.get("crop"), data["severity"],
        data["status"], json.dumps(data["tips"]), data.get("notes"), data["source"],
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_advisory(advisory_id, user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM weather_advisories WHERE id = ? AND user_id = ?", (advisory_id, user_id))
    row = cur.fetchone()
    conn.close()
    return _advisory_row(row) if row else None


def list_advisories(user_id, city=None, severity=None, status=None, limit=50, offset=0):
    """Return (rows, total_matching) for the user, newest first."""
    where, params = ["user_id = ?"], [user_id]
    if city:
        where.append("LOWER(city) LIKE ?")
        params.append(f"%{city.strip().lower()}%")
    if severity:
        where.append("severity = ?")
        params.append(severity)
    if status:
        where.append("status = ?")
        params.append(status)
    clause = " AND ".join(where)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) AS c FROM weather_advisories WHERE {clause}", params)
    total = cur.fetchone()["c"]
    cur.execute(
        f"SELECT * FROM weather_advisories WHERE {clause} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
        params + [limit, offset],
    )
    rows = [_advisory_row(r) for r in cur.fetchall()]
    conn.close()
    return rows, total


def update_advisory(advisory_id, user_id, fields):
    """UPDATE only the supplied columns. Returns True if a row was changed."""
    sets, params = [], []
    for key, value in fields.items():
        if key not in _ADVISORY_COLUMNS:
            continue
        if key == "tips":
            sets.append("tips_json = ?")
            params.append(json.dumps(value))
        else:
            sets.append(f"{key} = ?")
            params.append(value)
    if not sets:
        return False
    sets.append("updated_at = CURRENT_TIMESTAMP")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"UPDATE weather_advisories SET {', '.join(sets)} WHERE id = ? AND user_id = ?",
        params + [advisory_id, user_id],
    )
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def delete_advisory(advisory_id, user_id):
    """DELETE one advisory. Returns True if a row was removed."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM weather_advisories WHERE id = ? AND user_id = ?", (advisory_id, user_id))
    conn.commit()
    removed = cur.rowcount > 0
    conn.close()
    return removed