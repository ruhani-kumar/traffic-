import time
import config
import context
import mapbox_api
import storage
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def fetch_with_retry(route, token):
    for attempt in range(config.RETRIES + 1):
        try:
            return mapbox_api.get_route(route, token)
        except RuntimeError as e:
            last_error = e
            if attempt < config.RETRIES:
                time.sleep(config.RETRY_WAIT_SECONDS)
    raise last_error

def build_route_row(route, token, ctx):
    row = {
        **ctx,
        "source": "mapbox",
        "route_name": route["name"],
        "distance_km": None,
        "live_min": None,
        "typical_min": None,
        "delay_min": None,
        "ratio": None,
        "avg_speed_kmh": None,
        "heavy_share": None,
        "unknown_share": None,
        "status": "ok",
        "error_msg": "",
    }
    try:
        row.update(fetch_with_retry(route, token))
        if row["typical_min"]:
            row["delay_min"] = round(row["live_min"] - row["typical_min"], 2)
            row["ratio"] = round(row["live_min"] / row["typical_min"], 3)
    except RuntimeError as e:
        row["status"] = "error"
        row["error_msg"] = str(e)[:200]
    return row

def main():
    token = mapbox_api.get_token()
    ctx = context.get_run_context()
    rows = [build_route_row(route, token, ctx) for route in config.ROUTES]
    storage.save("routes", rows)
    for r in rows:
        if r["status"] == "ok":
            print(f"[{r['run_time_ist']}] {r['route_name']}: live {r['live_min']} min, "
                  f"typical {r['typical_min']} min, ratio {r['ratio']}, heavy {r['heavy_share']}")
        else:
            print(f"[{r['run_time_ist']}] {r['route_name']}: FAILED - {r['error_msg']}")

if __name__ == "__main__":
    main()
