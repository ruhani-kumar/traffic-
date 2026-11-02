# The logger. One run = one snapshot of traffic around Jadavpur, from TomTom only:
#   routes            8 routes
#   locations         6 points
#   incident_summary  1 row every run: counts
#   incidents         full list, once per hour
#   raw_responses     TomTom's full JSON reply for each of the above
# Everything goes to MongoDB (the main store) and to monthly CSV files in data/ (the backup).
# Every row also gets the run context: IST time, weekday, weekend, holiday, weather.
#
#   python traffic_snapshot.py
import sys
import time
from pymongo.errors import PyMongoError
import config
import context
import mongodb_storage
import storage
import tomtom_api

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def call_with_retry(func, *args):
    # Call a TomTom function; if it fails, wait a little and try again.
    for attempt in range(config.RETRIES + 1):
        try:
            result = func(*args)
            time.sleep(config.TOMTOM_PAUSE)
            return result
        except RuntimeError as e:
            last_error = e
            if attempt < config.RETRIES:
                time.sleep(config.RETRY_WAIT_SECONDS)
    raise last_error

def raw_doc(ctx, api, name, data, size):
    return {"run_time_ist": ctx["run_time_ist"], "source": "tomtom", "api": api, "name": name,
            **size, "response": data}

def build_route_row(route, key, ctx, raw_docs):
    row = {
        **ctx,
        "source": "tomtom",
        "route_name": route["name"],
        "road": route.get("road"),
        "direction": route.get("direction"),
        "distance_km": None,
        "live_min": None,
        "usual_min": None,
        "no_traffic_min": None,
        "delay_vs_usual_min": None,   # live - usual; negative = faster than usual
        "ratio_vs_usual": None,       # live / usual; 1.3 = 30% slower than normal for this hour
        "ratio_vs_empty": None,       # live / empty road = Travel Time Index; 2.0 = twice as long
        "avg_speed_kmh": None,
        "jam_sections": None,
        "route_changed": None,
        "response_ms": None,
        "response_kb": None,
        "status": "ok",
        "error_msg": "",
    }
    try:
        t = call_with_retry(tomtom_api.route, route, key, False, True)
    except RuntimeError as e:
        row["status"] = "error"
        row["error_msg"] = str(e)[:200]
        return row

    live, usual, empty, km = t["live_min"], t["historic_min"], t["no_traffic_min"], t["distance_km"]
    row.update({"distance_km": km, "live_min": live, "usual_min": usual,
                "no_traffic_min": empty, "jam_sections": t["jam_sections"],
                "response_ms": t["response_ms"], "response_kb": t["response_kb"]})
    raw_docs.append(raw_doc(ctx, "routing", route["name"], t["raw"],
                            {"response_ms": t["response_ms"], "response_kb": t["response_kb"]}))
    if live and usual:
        row["delay_vs_usual_min"] = round(live - usual, 2)
        row["ratio_vs_usual"] = round(live / usual, 3)
    if live and empty:
        row["ratio_vs_empty"] = round(live / empty, 3)
    if live:
        row["avg_speed_kmh"] = round(km / (live / 60), 1)
    ref = route.get("ref_distance_km")
    if ref:
        row["route_changed"] = abs(km - ref) > config.ROUTE_CHANGE_TOLERANCE * ref
    return row

def build_location_row(point, key, ctx, raw_docs):
    row = {
        **ctx,
        "source": "tomtom",
        "location": point["name"],
        "current_speed_kmh": None,
        "free_flow_speed_kmh": None,
        "speed_ratio": None,          # current / normal; 0.5 = moving at half the normal speed
        "current_travel_s": None,
        "free_flow_travel_s": None,
        "confidence": None,
        "road_class": None,
        "road_closed": None,
        "snapped_m": None,
        "response_ms": None,
        "response_kb": None,
        "status": "ok",
        "error_msg": "",
    }
    try:
        f = call_with_retry(tomtom_api.location_flow, point, key, False, True)
    except RuntimeError as e:
        row["status"] = "error"
        row["error_msg"] = str(e)[:200]
        return row

    raw_docs.append(raw_doc(ctx, "flow", point["name"], f.pop("raw"),
                            {"response_ms": f["response_ms"], "response_kb": f["response_kb"]}))
    row.update(f)
    if f["current_speed_kmh"] and f["free_flow_speed_kmh"]:
        row["speed_ratio"] = round(f["current_speed_kmh"] / f["free_flow_speed_kmh"], 3)
    return row

def full_list_due(ctx):
    # Only if nothing has been saved yet during this hour. This asks MongoDB, not the CSV,
    # because on GitHub each run starts on a fresh machine with no earlier CSV rows.
    try:
        return not mongodb_storage.has_rows_starting("incidents", ctx["run_time_ist"][:13])
    except (PyMongoError, RuntimeError):
        return True

def collect_incidents(key, ctx, raw_docs):
    # Returns (one summary row, full incident rows). The full list is only kept once per hour.
    summary = {
        **ctx,
        "source": "tomtom",
        "incidents_total": None,
        "jams": None,
        "major_jams": None,
        "road_closures": None,
        "accidents": None,
        "road_works": None,
        "other": None,
        "total_delay_min": None,      # sum of the delays TomTom reports for all incidents
        "full_list_saved": False,
        "response_ms": None,
        "response_kb": None,
        "status": "ok",
        "error_msg": "",
    }
    try:
        incidents, raw, size = call_with_retry(tomtom_api.area_incidents_full, config.AREA_BOX, key)
    except RuntimeError as e:
        summary["status"] = "error"
        summary["error_msg"] = str(e)[:200]
        return summary, []

    types = [i["type"] for i in incidents]
    jams = types.count("Jam")
    closures = types.count("Road closed") + types.count("Lane closed")
    accidents = types.count("Accident")
    works = types.count("Road works")
    summary.update({
        "incidents_total": len(incidents),
        "jams": jams,
        "major_jams": sum(1 for i in incidents if i["type"] == "Jam" and i["severity"] == "Major"),
        "road_closures": closures,
        "accidents": accidents,
        "road_works": works,
        "other": len(incidents) - jams - closures - accidents - works,
        "total_delay_min": round(sum(i["delay_s"] or 0 for i in incidents) / 60, 1),
        **size,
    })

    if incidents and full_list_due(ctx):
        summary["full_list_saved"] = True
        raw_docs.append(raw_doc(ctx, "incidents", "area", raw, size))
        return summary, [{**ctx, **{k: v for k, v in i.items() if k != "shape"}} for i in incidents]
    return summary, []

def _s(value):
    return "-" if value is None else str(value)

def print_report(ctx, route_rows, location_rows, summary):
    holiday = f", holiday: {ctx['holiday_name']}" if ctx["is_holiday"] else ""
    weather = f"{ctx['weather']}, {ctx['temp_c']} C, rain {ctx['rain_mm']} mm" if ctx["weather"] else "weather unavailable"
    print(f"\n[{ctx['run_time_ist']}] {ctx['weekday']}{holiday} | {weather}\n")

    print(f"{'ROUTE':42} {'live':>5} {'usual':>6} {'empty':>6} {'vs usual':>9}  NOTE")
    for r in route_rows:
        if r["status"] != "ok":
            print(f"{r['route_name']:42} FAILED - {r['error_msg']}")
            continue
        note = "route changed!" if r["route_changed"] else ""
        print(f"{r['route_name']:42} {_s(r['live_min']):>5} {_s(r['usual_min']):>6} "
              f"{_s(r['no_traffic_min']):>6} {_s(r['ratio_vs_usual']):>9}  {note}")

    print(f"\n{'LOCATION':24} {'speed':>5} {'normal':>6} {'ratio':>6}")
    for p in location_rows:
        if p["status"] != "ok":
            print(f"{p['location']:24} FAILED - {p['error_msg']}")
            continue
        print(f"{p['location']:24} {_s(p['current_speed_kmh']):>5} {_s(p['free_flow_speed_kmh']):>6} "
              f"{_s(p['speed_ratio']):>6}")

    if summary["status"] != "ok":
        print(f"\nIncidents FAILED - {summary['error_msg']}")
    else:
        saved = " (full list saved this hour)" if summary["full_list_saved"] else ""
        print(f"\nIncidents: {summary['incidents_total']} total - {summary['jams']} jams "
              f"({summary['major_jams']} major), {summary['road_closures']} closures, "
              f"{summary['accidents']} accidents, {summary['road_works']} road works{saved}")

def save_to_mongodb(kind, rows):
    # Returns False if MongoDB refused; the run carries on so the other data still gets saved.
    try:
        mongodb_storage.save(kind, rows)
        return True
    except (PyMongoError, RuntimeError) as e:
        print(f"MongoDB save FAILED for {kind}: {type(e).__name__}: {str(e)[:200]}")
        return False

def main():
    key = tomtom_api.get_key()
    ctx = context.get_run_context()

    raw_docs = []
    route_rows = [build_route_row(route, key, ctx, raw_docs) for route in config.ROUTES]
    location_rows = [build_location_row(point, key, ctx, raw_docs) for point in config.LOCATIONS]
    summary, incident_rows = collect_incidents(key, ctx, raw_docs)

    # CSVs first: they are the backup if MongoDB is unreachable.
    storage.save("routes", route_rows)
    storage.save("locations", location_rows)
    storage.save("incident_summary", [summary])
    storage.save("incidents", incident_rows)

    saved = [save_to_mongodb("routes", route_rows),
             save_to_mongodb("locations", location_rows),
             save_to_mongodb("incident_summary", [summary]),
             save_to_mongodb("incidents", incident_rows),
             save_to_mongodb("raw_responses", raw_docs)]

    print_report(ctx, route_rows, location_rows, summary)
    print(f"\nSaved to MongoDB: {'yes' if all(saved) else 'NO - see the errors above'}")

    # A failed exit makes the GitHub run show red (and keeps the CSVs as a download).
    all_routes_failed = all(r["status"] != "ok" for r in route_rows)
    if not all(saved) or all_routes_failed:
        sys.exit(1)

if __name__ == "__main__":
    main()
