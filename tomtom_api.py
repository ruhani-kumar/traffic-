import math
import os
import requests
import config

ROUTING_URL = "https://api.tomtom.com/routing/1/calculateRoute/"
FLOW_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
INCIDENTS_URL = "https://api.tomtom.com/traffic/services/5/incidentDetails"

def get_key():
    key = os.environ.get("TOMTOM_KEY")
    if not key:
        raise SystemExit("TOMTOM_KEY is not set.")
    return key

def _get_json(url, params):
    try:
        res = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
    except requests.RequestException as e:
        raise RuntimeError(f"Network error ({type(e).__name__})") from None
    try:
        data = res.json()
    except ValueError:
        raise RuntimeError(f"Non-JSON reply (HTTP {res.status_code})") from None
    if res.status_code != 200:
        err = data.get("error") or data.get("detailedError") or {}
        msg = err.get("description") or err.get("message") or str(data)[:100]
        raise RuntimeError(f"TomTom error (HTTP {res.status_code}): {msg}")
    return data

def route(route, key, with_shape=False):
    points = [route["start"], route["end"]]
    coords = ":".join(f"{p['lat']},{p['lon']}" for p in points)

    params = {
        "key": key,
        "traffic": "true",                 
        "travelMode": "car",
        "computeTravelTimeFor": "all",     
        "sectionType": "traffic",         
    }
    data = _get_json(f"{ROUTING_URL}{coords}/json", params)
    if not data.get("routes"):
        raise RuntimeError("TomTom returned no route")

    r = data["routes"][0]
    s = r["summary"]
    jams = [sec for sec in r.get("sections", []) if sec.get("sectionType") == "TRAFFIC"]

    def minutes(field):
        return round(s[field] / 60, 2) if s.get(field) is not None else None

    result = {
        "distance_km": round(s["lengthInMeters"] / 1000, 2),
        "live_min": minutes("travelTimeInSeconds"),
        "historic_min": minutes("historicTrafficTravelTimeInSeconds"),
        "no_traffic_min": minutes("noTrafficTravelTimeInSeconds"),
        "delay_min": round(s.get("trafficDelayInSeconds", 0) / 60, 2),
        "jam_sections": len(jams),         
    }
    if with_shape:
        result["shape"] = [(p["latitude"], p["longitude"]) for leg in r["legs"] for p in leg["points"]]
    return result

def location_flow(point, key, with_shape=False):
    params = {"key": key, "point": f"{point['lat']},{point['lon']}", "unit": "KMPH"}
    f = _get_json(FLOW_URL, params)["flowSegmentData"]
    road = [(c["latitude"], c["longitude"]) for c in f.get("coordinates", {}).get("coordinate", [])]
    snapped_m = _distance_to_road_m(point["lat"], point["lon"], road)

    result = {
        "road_class": f.get("frc"),#FRC0 is a motorway, FRC6 a small local road
        "current_speed_kmh": f.get("currentSpeed"),
        "free_flow_speed_kmh": f.get("freeFlowSpeed"),
        "current_travel_s": f.get("currentTravelTime"),
        "free_flow_travel_s": f.get("freeFlowTravelTime"),
        "confidence": f.get("confidence"),
        "road_closed": f.get("roadClosure"),
        "snapped_m": round(snapped_m) if snapped_m is not None else None,
    }
    if with_shape:
        result["shape"] = road
    return result

INCIDENT_TYPES = {
    0: "Unknown", 1: "Accident", 2: "Fog", 3: "Dangerous conditions", 4: "Rain", 5: "Ice",
    6: "Jam", 7: "Lane closed", 8: "Road closed", 9: "Road works", 10: "Wind",
    11: "Flooding", 14: "Broken-down vehicle",
}
DELAY_SIZES = {0: "Unknown", 1: "Minor", 2: "Moderate", 3: "Major", 4: "Undefined"}

def area_incidents(box, key):
    fields = ("{incidents{type,geometry{type,coordinates},properties{id,iconCategory,magnitudeOfDelay,"
              "events{description},startTime,endTime,from,to,length,delay,roadNumbers,"
              "probabilityOfOccurrence,lastReportTime}}}")
    params = {
        "key": key,
        "bbox": f"{box['min_lon']},{box['min_lat']},{box['max_lon']},{box['max_lat']}",
        "fields": fields,
        "language": "en-GB",
        "timeValidityFilter": "present",
    }
    incidents = []
    for item in _get_json(INCIDENTS_URL, params).get("incidents", []):
        p = item.get("properties", {})
        geom = item.get("geometry", {})
        coords = geom.get("coordinates", [])
        if geom.get("type") == "LineString":
            shape = [(c[1], c[0]) for c in coords]
        elif coords:
            shape = [(coords[1], coords[0])]
        else:
            shape = []
        mid = shape[len(shape) // 2] if shape else (None, None)
        incidents.append({
            "incident_id": p.get("id"),
            "type": INCIDENT_TYPES.get(p.get("iconCategory"), "Unknown"),
            "severity": DELAY_SIZES.get(p.get("magnitudeOfDelay"), "Unknown"),
            "description": "; ".join(e.get("description", "") for e in p.get("events") or []),
            "from": p.get("from"),
            "to": p.get("to"),
            "length_m": round(p["length"]) if p.get("length") is not None else None,
            "delay_s": p.get("delay"),
            "roads": ", ".join(p.get("roadNumbers") or []),
            "start_time": p.get("startTime"),
            "end_time": p.get("endTime"),
            "probability": p.get("probabilityOfOccurrence"),
            "last_report": p.get("lastReportTime"),
            "lat": round(mid[0], 5) if mid[0] is not None else None,
            "lon": round(mid[1], 5) if mid[1] is not None else None,
            "shape": shape,
        })
    return incidents

def _distance_to_road_m(lat, lon, road):
    if not road:
        return None
    m_per_deg_lat = 111320
    m_per_deg_lon = 111320 * math.cos(math.radians(lat))
    xy = [((lo - lon) * m_per_deg_lon, (la - lat) * m_per_deg_lat) for la, lo in road]
    if len(xy) == 1:
        return math.hypot(*xy[0])
    best = float("inf")
    for (x1, y1), (x2, y2) in zip(xy, xy[1:]):
        dx, dy = x2 - x1, y2 - y1
        length_sq = dx * dx + dy * dy
        t = 0 if length_sq == 0 else max(0, min(1, -(x1 * dx + y1 * dy) / length_sq))
        best = min(best, math.hypot(x1 + t * dx, y1 + t * dy))
    return best