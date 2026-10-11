import config
import context
import storage
import tomtom_api

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main():
    key = tomtom_api.get_key()
    ctx = context.get_run_context()
    box = config.AREA_BOX

    try:
        incidents = tomtom_api.area_incidents(box, key)
    except RuntimeError as e:
        raise SystemExit(f"Incidents request failed: {e}")

    print(f"\nIncidents at {ctx['run_time_ist']} ({ctx['weekday']}) "
          f"in box lat {box['min_lat']}-{box['max_lat']}, lon {box['min_lon']}-{box['max_lon']}\n")

    if not incidents:
        print("TomTom reports no incidents in this area right now.")
        return

    print(f"{'TYPE':20} {'SEVERITY':10} {'DELAY':>6} {'LENGTH':>7}  WHERE")
    for i in incidents:
        delay = f"{i['delay_s']}s" if i["delay_s"] is not None else "-"
        length = f"{i['length_m']}m" if i["length_m"] is not None else "-"
        where = f"{i['from'] or '?'} -> {i['to'] or '?'}"
        print(f"{i['type']:20} {i['severity']:10} {delay:>6} {length:>7}  {where}")
        if i["description"]:
            print(f"{'':20} {i['description']}")

    rows = [{**ctx, **{k: v for k, v in i.items() if k != "shape"}} for i in incidents]
    storage.save("incidents", rows)
    print(f"\n{len(incidents)} incident(s) saved to data/incidents_{ctx['run_time_ist'][:7]}.csv")

if __name__ == "__main__":
    main()
