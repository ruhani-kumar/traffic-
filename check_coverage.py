import csv
import glob
import os
import sys
import time
import config
import context
import mapbox_api
import storage
import tomtom_api

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MAPBOX_MAX_UNKNOWN = 0.3     
TOMTOM_MIN_CONFIDENCE = 0.7  
MIN_CHANGE = 0.10            
PAUSE = 0.3                  
def test_route(route, mapbox_token, tomtom_key, ctx):
    row = {**ctx, "route_name": route["name"]}
    try:
        m = mapbox_api.get_route(route, mapbox_token)
        row.update({
            "mapbox_distance_km": m["distance_km"],
            "mapbox_live_min": m["live_min"],
            "mapbox_typical_min": m["typical_min"],
            "mapbox_unknown_share": m["unknown_share"],
            "mapbox_heavy_share": m["heavy_share"],
            "mapbox_error": "",
        })
    except RuntimeError as e:
        row["mapbox_error"] = str(e)[:200]
    try:
        t = tomtom_api.route(route, tomtom_key)
        row.update({
            "tomtom_distance_km": t["distance_km"],
            "tomtom_live_min": t["live_min"],
            "tomtom_historic_min": t["historic_min"],
            "tomtom_no_traffic_min": t["no_traffic_min"],
            "tomtom_delay_min": t["delay_min"],
            "tomtom_jam_sections": t["jam_sections"],
            "tomtom_error": "",
        })
    except RuntimeError as e:
        row["tomtom_error"] = str(e)[:200]
    time.sleep(PAUSE)
    return row

def test_point(point, tomtom_key, ctx):
    row = {**ctx, "point_name": point["name"]}
    try:
        row.update(tomtom_api.location_flow(point, tomtom_key))
        row["error"] = ""
    except RuntimeError as e:
        row["error"] = str(e)[:200]
    time.sleep(PAUSE)
    return row

def run_test():
    mapbox_token = mapbox_api.get_token()
    tomtom_key = tomtom_api.get_key()
    ctx = context.get_run_context()
    routes = config.ROUTES + config.CANDIDATE_ROUTES
    route_rows = [test_route(r, mapbox_token, tomtom_key, ctx) for r in routes]
    point_rows = [test_point(p, tomtom_key, ctx) for p in config.CANDIDATE_POINTS]
    storage.save("coverage_routes", route_rows)
    storage.save("coverage_points", point_rows)
    print(f"\nTest run at {ctx['run_time_ist']} ({ctx['weekday']})\n")
    print(f"{'ROUTE':42} {'MB unknown':>10} {'MB live':>8} {'TT live':>8} {'TT usual':>8} {'TT empty':>8} {'TT jams':>7}")
    for r in route_rows:
        print(f"{r['route_name']:42} {_show(r.get('mapbox_unknown_share')):>10} {_show(r.get('mapbox_live_min')):>8} "
              f"{_show(r.get('tomtom_live_min')):>8} {_show(r.get('tomtom_historic_min')):>8} "
              f"{_show(r.get('tomtom_no_traffic_min')):>8} {_show(r.get('tomtom_jam_sections')):>7}")
        for side in ("mapbox", "tomtom"):
            if r.get(f"{side}_error"):
                print(f"   ! {side} failed: {r[f'{side}_error']}")

    print(f"\n{'POINT':26} {'speed':>6} {'normal':>6} {'confid.':>7} {'road':>5} {'snap m':>6}")
    for p in point_rows:
        if p["error"]:
            print(f"{p['point_name']:26} FAILED: {p['error']}")
        else:
            print(f"{p['point_name']:26} {_show(p['current_speed_kmh']):>6} {_show(p['free_flow_speed_kmh']):>6} "
                  f"{_show(p['confidence']):>7} {_show(p['road_class']):>5} {_show(p['snapped_m']):>6}")
    print("\nSaved to data/coverage_routes_*.csv and data/coverage_points_*.csv")

def summary():
    routes = _read_all("coverage_routes")
    points = _read_all("coverage_points")
    if not routes and not points:
        sys.exit("No test runs found yet.")
    runs = sorted({r["run_time_ist"] for r in routes + points})
    print(f"\n{len(runs)} test run(s): {', '.join(t[11:16] for t in runs)}")
    if len(runs) < 3:
        print("do at least 3 runs at different times of day before trusting the 'changes' column.\n")
    print(f"\n{'ROUTE':42} {'MB unknown':>10} {'MB live?':>8} {'TT change':>9} {'TT live?':>8}")
    for name in dict.fromkeys(r["route_name"] for r in routes):
        rows = [r for r in routes if r["route_name"] == name]
        unknown = _avg(r.get("mapbox_unknown_share") for r in rows)
        tt_change = _change(r.get("tomtom_live_min") for r in rows)
        mb_live = unknown is not None and unknown <= MAPBOX_MAX_UNKNOWN
        tt_live = tt_change is not None and tt_change >= MIN_CHANGE
        print(f"{name:42} {_show(unknown):>10} {_yes(mb_live):>8} {_pct(tt_change):>9} {_yes(tt_live):>8}")

    print(f"\n{'POINT':26} {'avg confid.':>11} {'speed change':>12} {'road':>5} {'snap m':>6} {'TT live?':>8}")
    for name in dict.fromkeys(p["point_name"] for p in points):
        rows = [p for p in points if p["point_name"] == name and not p["error"]]
        conf = _avg(p.get("confidence") for p in rows)
        change = _change(p.get("current_speed_kmh") for p in rows)
        live = conf is not None and conf >= TOMTOM_MIN_CONFIDENCE
        road = rows[-1]["road_class"] if rows else ""
        snap = rows[-1]["snapped_m"] if rows else ""
        print(f"{name:26} {_show(conf):>11} {_pct(change):>12} {road:>5} {snap:>6} {_yes(live):>8}")

    print("\nHow to read this:")
    print(f"  MB live?  yes = Mapbox has data on {100 - int(MAPBOX_MAX_UNKNOWN * 100)}%+ of the route")
    print(f"  TT change = how much TomTom's live time moved between runs (live data moves, guesses don't)")
    print(f"  TT live?  route: time changed {int(MIN_CHANGE * 100)}%+ | point: confidence >= {TOMTOM_MIN_CONFIDENCE}")
    print("  snap m    = how far TomTom's road is from your point (over ~30 m: it may have picked another road)")
def _read_all(kind):
    rows = []
    for path in sorted(glob.glob(os.path.join(config.DATA_DIR, f"{kind}_*.csv"))):
        with open(path, newline="", encoding="utf-8") as f:
            rows += list(csv.DictReader(f))
    return rows

def _numbers(values):
    out = []
    for v in values:
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            pass
    return out

def _avg(values):
    nums = _numbers(values)
    return round(sum(nums) / len(nums), 2) if nums else None

def _change(values):
    nums = _numbers(values)
    if len(nums) < 2 or min(nums) == 0:
        return None
    return (max(nums) - min(nums)) / min(nums)

def _show(v):
    return "-" if v is None or v == "" else str(v)
def _pct(v):
    return "-" if v is None else f"{v * 100:.0f}%"
def _yes(flag):
    return "yes" if flag else "no"
if __name__ == "__main__":
    if "--summary" in sys.argv:
        summary()
    else:
        run_test()
