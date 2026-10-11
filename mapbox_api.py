import os
import requests
import config
BASE_URL = "https://api.mapbox.com/directions/v5/mapbox/driving-traffic/"

def get_token():
    token = os.environ.get("MAPBOX_TOKEN")
    if not token:
        raise SystemExit(
            "MAPBOX_TOKEN is not set."
        )
    return token

def get_route(route, token, with_shape=False):
    points = [route["start"], route["end"]]
    coords = ";".join(f"{p['lon']},{p['lat']}" for p in points)

    params = {
        "access_token": token,
        "overview": "full",                    
        "annotations": "congestion,distance",
        "geometries": "geojson",  
    }

    try:
        res = requests.get(BASE_URL + coords, params=params, timeout=config.REQUEST_TIMEOUT)
        data = res.json()
    except requests.RequestException as e:
        raise RuntimeError(f"Network error ({type(e).__name__})") from None
    except ValueError:
        raise RuntimeError(f"Mapbox sent a non-JSON reply (HTTP {res.status_code})") from None

    if data.get("code") != "Ok" or not data.get("routes"):
        raise RuntimeError(f"Mapbox error: {data.get('code')} {data.get('message', '')}".strip())

    r = data["routes"][0]

    levels, lengths = [], []
    for leg in r["legs"]:
        ann = leg.get("annotation", {})
        levels += ann.get("congestion", [])
        lengths += ann.get("distance", [])

    total = sum(lengths) or 1
    heavy_m = sum(l for c, l in zip(levels, lengths) if c in ("heavy", "severe"))
    unknown_m = sum(l for c, l in zip(levels, lengths) if c == "unknown")

    live_s = r["duration"]
    typical_s = r.get("duration_typical") 

    result = {
        "distance_km": round(r["distance"] / 1000, 2),
        "live_min": round(live_s / 60, 2),
        "typical_min": round(typical_s / 60, 2) if typical_s else None,
        "avg_speed_kmh": round((r["distance"] / 1000) / (live_s / 3600), 1) if live_s else None,
        "heavy_share": round(heavy_m / total, 2),     
        "unknown_share": round(unknown_m / total, 2),  
    }
    if with_shape:
        result["shape"] = [(lat, lon) for lon, lat in r["geometry"]["coordinates"]]
    return result
