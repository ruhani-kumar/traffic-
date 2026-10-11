import os
import folium
import config
import mapbox_api
import tomtom_api

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
MAP_FILE = os.path.join("maps", "routes_map.html")
SAME_ROUTE_TOLERANCE = 0.10   

def speed_colour(current, free_flow):
    if not current or not free_flow:
        return "gray"
    ratio = current / free_flow
    return "green" if ratio >= 0.8 else "orange" if ratio >= 0.5 else "red"

def popup(title, lines):
    body = "<br>".join(f"{k}: <b>{v}</b>" for k, v in lines.items())
    return folium.Popup(f"<b>{title}</b><br>{body}", max_width=320)


def draw_routes(m, mapbox_token, tomtom_key):
    print(f"{'ROUTE':42} {'Mapbox km':>9} {'TomTom km':>9}  NOTE")
    for route in config.ROUTES + config.CANDIDATE_ROUTES:
        layer = folium.FeatureGroup(name=f"Route: {route['name']}")
        km = {}

        try:
            mb = mapbox_api.get_route(route, mapbox_token, with_shape=True)
            km["mapbox"] = mb["distance_km"]
            folium.PolyLine(mb["shape"], color="blue", weight=6, opacity=0.5,
                            tooltip=f"Mapbox: {route['name']}",
                            popup=popup(f"Mapbox - {route['name']}", {
                                "distance km": mb["distance_km"], "live min": mb["live_min"],
                                "typical min": mb["typical_min"], "no-data share": mb["unknown_share"]})
                            ).add_to(layer)
        except RuntimeError as e:
            print(f"   ! Mapbox failed for {route['name']}: {e}")

        try:
            tt = tomtom_api.route(route, tomtom_key, with_shape=True)
            km["tomtom"] = tt["distance_km"]
            folium.PolyLine(tt["shape"], color="purple", weight=3, dash_array="8",
                            tooltip=f"TomTom: {route['name']}",
                            popup=popup(f"TomTom - {route['name']}", {
                                "distance km": tt["distance_km"], "live min": tt["live_min"],
                                "usual min": tt["historic_min"], "empty-road min": tt["no_traffic_min"],
                                "jam sections": tt["jam_sections"]})
                            ).add_to(layer)
        except RuntimeError as e:
            print(f"   ! TomTom failed for {route['name']}: {e}")

        for spot, colour in (("start", "green"), ("end", "red")):
            p = route[spot]
            folium.CircleMarker((p["lat"], p["lon"]), radius=6, color=colour, fill=True, fill_opacity=1,
                                tooltip=f"{route['name']} - {spot}").add_to(layer)
        layer.add_to(m)

        note = ""
        if len(km) == 2 and abs(km["mapbox"] - km["tomtom"]) > SAME_ROUTE_TOLERANCE * max(km.values()):
            note = "<- different paths? check on the map"
        print(f"{route['name']:42} {km.get('mapbox', '-'):>9} {km.get('tomtom', '-'):>9}  {note}")

def draw_points(m, tomtom_key):
    layer = folium.FeatureGroup(name="Points (TomTom Traffic Flow)")
    print(f"\n{'POINT':26} {'speed':>5} {'normal':>6} {'snap m':>6}  NOTE")
    for point in config.CANDIDATE_POINTS:
        here = (point["lat"], point["lon"])
        try:
            f = tomtom_api.location_flow(point, tomtom_key, with_shape=True)
        except RuntimeError as e:
            print(f"{point['name']:26} FAILED: {e}")
            continue

        colour = speed_colour(f["current_speed_kmh"], f["free_flow_speed_kmh"])
        info = {"speed now km/h": f["current_speed_kmh"], "normal km/h": f["free_flow_speed_kmh"],
                "confidence": f["confidence"], "road class": f["road_class"],
                "distance to road m": f["snapped_m"], "closed": f["road_closed"]}
        if f["shape"]:
            folium.PolyLine(f["shape"], color=colour, weight=8, opacity=0.8,
                            tooltip=f"Road TomTom measured for {point['name']}",
                            popup=popup(point["name"], info)).add_to(layer)
        folium.CircleMarker(here, radius=5, color="black", fill=True, fill_opacity=1,
                            tooltip=point["name"], popup=popup(point["name"], info)).add_to(layer)

        note = "<- TomTom measured a road away from this point" if (f["snapped_m"] or 0) > 30 else ""
        print(f"{point['name']:26} {str(f['current_speed_kmh']):>5} {str(f['free_flow_speed_kmh']):>6} "
              f"{str(f['snapped_m']):>6}  {note}")
    layer.add_to(m)

def draw_incidents(m, tomtom_key):
    layer = folium.FeatureGroup(name="Incidents (TomTom)")
    try:
        incidents = tomtom_api.area_incidents(config.AREA_BOX, tomtom_key)
    except RuntimeError as e:
        print(f"\nIncidents failed: {e}")
        return
    for i in incidents:
        info = {"severity": i["severity"], "delay s": i["delay_s"], "length m": i["length_m"],
                "from": i["from"], "to": i["to"], "details": i["description"]}
        if len(i["shape"]) > 1:
            folium.PolyLine(i["shape"], color="darkred", weight=4).add_to(layer)
        if i["lat"] is None:
            continue
        folium.Marker((i["lat"], i["lon"]), tooltip=i["type"], popup=popup(i["type"], info),
                      icon=folium.Icon(color="red", icon="exclamation-sign")).add_to(layer)
    layer.add_to(m)
    print(f"\nIncidents in the area right now: {len(incidents)}")

def add_legend(m):
    html = """
    <div style="position:fixed; bottom:20px; left:20px; z-index:9999; background:white;
                padding:8px 12px; border:1px solid #999; border-radius:6px; font-size:13px;">
      <b>Routes</b><br>
      <span style="color:blue">&#9644;</span> Mapbox &nbsp;
      <span style="color:purple">- - -</span> TomTom<br>
      <b>Points</b> (road TomTom measured)<br>
      <span style="color:green">&#9644;</span> flowing &nbsp;
      <span style="color:orange">&#9644;</span> slow &nbsp;
      <span style="color:red">&#9644;</span> jammed<br>
      <span style="color:red">&#9679;</span> incident &nbsp; dashed box = search area
    </div>"""
    m.get_root().html.add_child(folium.Element(html))

def main():
    mapbox_token = mapbox_api.get_token()
    tomtom_key = tomtom_api.get_key()
    box = config.AREA_BOX

    m = folium.Map(location=((box["min_lat"] + box["max_lat"]) / 2, (box["min_lon"] + box["max_lon"]) / 2),
                   zoom_start=14, tiles="OpenStreetMap")
    folium.Rectangle([(box["min_lat"], box["min_lon"]), (box["max_lat"], box["max_lon"])],
                     color="gray", weight=1, dash_array="5", fill=False,
                     tooltip="Incident search area").add_to(m)

    draw_routes(m, mapbox_token, tomtom_key)
    draw_points(m, tomtom_key)
    draw_incidents(m, tomtom_key)
    add_legend(m)
    folium.LayerControl(collapsed=False).add_to(m)

    os.makedirs("maps", exist_ok=True)
    m.save(MAP_FILE)
    print(f"\nMap saved to {MAP_FILE} - open it in your browser.")

if __name__ == "__main__":
    main()
