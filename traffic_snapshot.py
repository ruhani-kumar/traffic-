import csv
import os
import requests
from datetime import datetime

# Reads token securely from GitHub Secret
MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN")

ROUTES = {
    "Jadavpur_Stn_to_8B": "88.3698,22.4988;88.3691,22.4953",
    "8B_to_Sulekha":       "88.3691,22.4953;88.3712,22.4915",
    "Sulekha_to_8B":       "88.3712,22.4915;88.3691,22.4953",
}

CSV_FILE = "jadavpur_traffic_log.csv"
TIMEOUT = 10

def ensure_header():
    if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
        with open(CSV_FILE, "w", newline="") as f:
            csv.writer(f).writerow(
                ["Timestamp", "Route_Name", "Distance_km", "Live_Duration_min", "Typical_Duration_min", "Delay_min"]
            )

def fetch_duration(coords, profile):
    url = f"https://api.mapbox.com/directions/v5/mapbox/{profile}/{coords}?access_token={MAPBOX_TOKEN}"
    res = requests.get(url, timeout=TIMEOUT).json()
    if res.get("code") == "Ok" and res.get("routes"):
        r = res["routes"][0]
        return round(r["distance"] / 1000, 2), round(r["duration"] / 60, 2)
    raise ValueError(f"Bad response: {res.get('code', 'unknown error')}")

def log_route_traffic(route_name, coords):
    try:
        distance_km, live_min = fetch_duration(coords, "driving-traffic")
        _, typical_min = fetch_duration(coords, "driving")
        delay_min = max(0.0, round(live_min - typical_min, 2))
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(CSV_FILE, "a", newline="") as f:
            csv.writer(f).writerow([timestamp, route_name, distance_km, live_min, typical_min, delay_min])
        print(f"[{timestamp}] {route_name} -> Live: {live_min} | Typical: {typical_min} | Delay: {delay_min}")
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] FAILED {route_name}: {e}")

def main():
    ensure_header()
    for name, coords in ROUTES.items():
        log_route_traffic(name, coords)

if __name__ == "__main__":
    main()
