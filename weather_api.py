import requests
import config

URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo sends a WMO weather code; these are the ones that matter in Kolkata.
WEATHER_CODES = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
}

def current_weather(point):
    # Weather right now at one point. Free, no key needed.
    # If anything goes wrong the cells are left blank - weather must never stop traffic logging.
    blank = {"rain_mm": None, "temp_c": None, "weather": None}
    params = {
        "latitude": point["lat"],
        "longitude": point["lon"],
        "current": "temperature_2m,precipitation,weather_code",
        "timezone": config.TIMEZONE,
    }
    try:
        res = requests.get(URL, params=params, timeout=config.REQUEST_TIMEOUT)
        res.raise_for_status()
        now = res.json()["current"]
    except (requests.RequestException, ValueError, KeyError):
        return blank

    code = now.get("weather_code")
    return {
        "rain_mm": now.get("precipitation"),   # rain in the last 15 minutes
        "temp_c": now.get("temperature_2m"),
        "weather": WEATHER_CODES.get(code, f"code {code}" if code is not None else None),
    }
