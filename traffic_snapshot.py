# The logger. One run = one snapshot of traffic around Jadavpur, from TomTom only:
#   routes     -> data/routes_YYYY-MM.csv            (8 routes)
#   locations  -> data/locations_YYYY-MM.csv         (6 points)
#   incidents  -> data/incident_summary_YYYY-MM.csv  (1 row every run: counts)
#                 data/incidents_YYYY-MM.csv         (full list, once per hour)
# Every row also gets the run context: IST time, weekday, weekend, holiday, weather.
#
#   python traffic_snapshot.py
import time
import config
import context
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

def build_route_row(route, key, ctx):
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
        "status": "ok",
        "error_msg": "",
    }
    try:
        t = call_with_retry(tomtom_api.route, route, key)
    except RuntimeError as e:
        row["status"] = "error"
        row["error_msg"] = str(e)[:200]
        return row

    live, usual, empty, km = t["live_min"], t["historic_min"], t["no_traffic_min"], t["distance_km"]
    row.update({"distance_km": km, "live_min": live, "usual_min": usual,
                "no_traffic_min": empty, "jam_sections": t["jam_sections"]})
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

def build_location_row(point, key, ctx):
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
        "status": "ok",
        "error_msg": "",
    }
    try:
        f = call_with_retry(tomtom_api.location_flow, point, key)
    except RuntimeError as e:
        row["status"] = "error"
        row["error_msg"] = str(e)[:200]
        return row

    row.update(f)
    if f["current_speed_kmh"] and f["free_flow_speed_kmh"]:
        row["speed_ratio"] = round(f["current_speed_kmh"] / f["free_flow_speed_kmh"], 3)
    return row

def collect_incidents(key, ctx):
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
        "status": "ok",
        "error_msg": "",
    }
    try:
        incidents = call_with_retry(tomtom_api.area_incidents, config.AREA_BOX, key)
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
    })

    # Full list: only if nothing has been saved yet during this hour.
    month, hour = ctx["run_time_ist"][:7], ctx["run_time_ist"][:13]
    if incidents and not storage.has_rows_starting("incidents", month, hour):
        summary["full_list_saved"] = True
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

def main():
    key = tomtom_api.get_key()
    ctx = context.get_run_context()

    route_rows = [build_route_row(route, key, ctx) for route in config.ROUTES]
    location_rows = [build_location_row(point, key, ctx) for point in config.LOCATIONS]
    summary, incident_rows = collect_incidents(key, ctx)

    storage.save("routes", route_rows)
    storage.save("locations", location_rows)
    storage.save("incident_summary", [summary])
    storage.save("incidents", incident_rows)

    print_report(ctx, route_rows, location_rows, summary)

if __name__ == "__main__":
    main()
