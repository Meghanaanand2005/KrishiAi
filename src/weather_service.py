"""
weather_service.py

Weather-based farming advisory.

Uses the free OpenWeatherMap API (https://openweathermap.org/api) when an
API key is provided. If no key is available (or the request fails / no
internet), falls back to a seeded pseudo-random weather simulator so the
rest of the app keeps working offline/for demos.

To go live: sign up for a free OpenWeatherMap API key and either pass it
into get_weather(city, api_key=...) or set the OPENWEATHER_API_KEY
environment variable.
"""

import os
import random
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None


def _simulate_weather(city, reason="no API key / offline"):
    """Deterministic-ish fallback weather generator (seeded by city+day)."""
    seed = sum(ord(c) for c in city) + datetime.now().timetuple().tm_yday
    rng = random.Random(seed)
    condition = rng.choice(["Clear", "Partly Cloudy", "Cloudy", "Light Rain", "Thunderstorm"])
    return {
        "city": city,
        "temperature": round(rng.uniform(20, 36), 1),
        "humidity": round(rng.uniform(35, 90), 1),
        "condition": condition,
        "rainfall_mm": round(rng.uniform(0, 20), 1) if "Rain" in condition or "Thunder" in condition else 0.0,
        "wind_speed": round(rng.uniform(2, 18), 1),
        "source": f"simulated ({reason})",
    }


def get_weather(city, api_key=None):
    """Fetch current weather for a city. Falls back to simulation on any failure."""
    api_key = api_key or os.environ.get("OPENWEATHER_API_KEY")
    reason = "no API key / offline"

    if api_key and requests is not None:
        try:
            url = "https://api.openweathermap.org/data/2.5/weather"
            params = {"q": city, "appid": api_key, "units": "metric"}
            resp = requests.get(url, params=params, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "city": city,
                    "temperature": data["main"]["temp"],
                    "humidity": data["main"]["humidity"],
                    "condition": data["weather"][0]["main"],
                    "rainfall_mm": data.get("rain", {}).get("1h", 0.0),
                    "wind_speed": data["wind"]["speed"],
                    "source": "OpenWeatherMap (live)",
                }
            reason = f"live lookup failed, HTTP {resp.status_code}"
        except Exception:
            reason = "live lookup failed, network error"
        # fall through to simulation

    return _simulate_weather(city, reason)


def get_farming_advisory(weather):
    """Rule-based farming tips derived from current weather conditions."""
    tips = []
    condition = weather["condition"].lower()
    temp = weather["temperature"]
    humidity = weather["humidity"]
    rainfall = weather["rainfall_mm"]

    if "rain" in condition or "thunder" in condition or rainfall > 5:
        tips.append("Delay irrigation and pesticide spraying - rainfall may wash them away.")
        tips.append("Ensure field drainage channels are clear to prevent waterlogging.")
    elif temp > 33 and humidity < 45:
        tips.append("Hot and dry conditions - schedule irrigation for early morning or evening to reduce evaporation loss.")
        tips.append("Consider mulching to retain soil moisture.")
    elif humidity > 80:
        tips.append("High humidity increases fungal disease risk - inspect crops closely and ensure good airflow.")
    else:
        tips.append("Conditions are favorable for routine field operations (sowing, spraying, harvesting).")

    if temp < 15:
        tips.append("Low temperature - protect sensitive seedlings with mulch or row covers.")

    if weather.get("wind_speed", 0) >= 12:
        tips.append("Strong wind - avoid spraying, as drift wastes product and can damage neighbouring plots.")

    return tips


def derive_severity(weather):
    """Classify current conditions as 'info', 'watch' or 'warning'.

    warning - conditions that can damage crops or make field work unsafe
    watch   - conditions worth planning around
    info    - routine
    """
    condition = weather["condition"].lower()
    temp = weather["temperature"]
    humidity = weather["humidity"]
    rainfall = weather["rainfall_mm"]
    wind = weather.get("wind_speed", 0)

    if "thunder" in condition or rainfall >= 15 or temp >= 38 or temp <= 8 or wind >= 20:
        return "warning"
    if "rain" in condition or rainfall > 5 or (temp > 33 and humidity < 45) or humidity > 80 or temp < 15 or wind >= 12:
        return "watch"
    return "info"


if __name__ == "__main__":
    w = get_weather("Belagavi")
    print("Weather:", w)
    print("Advisory:", get_farming_advisory(w))
