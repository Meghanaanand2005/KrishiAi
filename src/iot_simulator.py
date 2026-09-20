"""
iot_simulator.py

Simulates IoT sensor telemetry (fuel level, engine temperature, GPS
location, health status) for rented agricultural equipment, since real
sensor hardware (Arduino/Raspberry Pi + GPS/fuel modules, per your
bibliography) isn't available in this environment.

TO GO LIVE: replace `generate_reading()`'s body with real sensor reads,
e.g. via an MQTT broker (paho-mqtt) publishing from an ESP32/Arduino unit
fitted to the machinery, or serial/GPIO reads on a Raspberry Pi. The
function signature and return shape can stay identical so `database.py`
and the Streamlit UI need no changes.
"""

import random
from datetime import datetime

# Rough bounding box around Belagavi / North Karnataka for demo GPS coordinates
LAT_RANGE = (15.7, 16.1)
LON_RANGE = (74.3, 74.7)


def generate_reading(equipment_id, previous_fuel=None):
    """Generate one simulated IoT sensor reading for a piece of equipment."""
    rng = random.Random(equipment_id * 7919 + int(datetime.now().timestamp()) // 30)

    if previous_fuel is None:
        fuel = rng.uniform(40, 100)
    else:
        # fuel drains gradually, occasionally refueled
        fuel = max(0, previous_fuel - rng.uniform(0, 3))
        if fuel < 10 and rng.random() < 0.3:
            fuel = rng.uniform(80, 100)  # simulated refuel

    engine_temp = rng.uniform(70, 105)
    latitude = rng.uniform(*LAT_RANGE)
    longitude = rng.uniform(*LON_RANGE)

    if engine_temp > 98 or fuel < 8:
        health_status = "warning"
    elif engine_temp > 90:
        health_status = "caution"
    else:
        health_status = "normal"

    return {
        "equipment_id": equipment_id,
        "fuel_level": round(fuel, 1),
        "engine_temp": round(engine_temp, 1),
        "latitude": round(latitude, 5),
        "longitude": round(longitude, 5),
        "health_status": health_status,
    }


if __name__ == "__main__":
    reading = generate_reading(equipment_id=1)
    print(reading)
