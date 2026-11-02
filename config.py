# Final routes: 4 main roads around Jadavpur, both directions.
# start / via / end are on the correct side of the road for that direction (from OpenStreetMap).
# via = a point in the middle that keeps the route on this road (no side-street shortcuts).
# ref_distance_km = normal length of the route, checked on the map (used later to spot detours).
ROUTES = [
    {
        "name": "RSC_Mullick_Gariahat_to_Jadavpur", "road": "Raja S.C. Mullick Road", "direction": "southbound",
        "start": {"lat": 22.51340, "lon": 88.36723},  # near Gariahat / Golpark
        "via":   {"lat": 22.50650, "lon": 88.36719},  # Dhakuria
        "end":   {"lat": 22.49962, "lon": 88.36954},  # Jadavpur (JU gates)
        "ref_distance_km": 1.59,
    },
    {
        "name": "RSC_Mullick_Jadavpur_to_Gariahat", "road": "Raja S.C. Mullick Road", "direction": "northbound",
        "start": {"lat": 22.49958, "lon": 88.36944},  # Jadavpur (JU gates)
        "via":   {"lat": 22.50644, "lon": 88.36710},  # Dhakuria
        "end":   {"lat": 22.51333, "lon": 88.36716},  # near Gariahat / Golpark
        "ref_distance_km": 1.58,
    },
    {
        "name": "RSC_Mullick_8B_to_Baghajatin", "road": "Raja S.C. Mullick Road", "direction": "southbound",
        "start": {"lat": 22.49551, "lon": 88.37094},  # 8B
        "via":   {"lat": 22.49140, "lon": 88.37240},  # Sulekha
        "end":   {"lat": 22.48412, "lon": 88.37543},  # Baghajatin
        "ref_distance_km": 1.45,
    },
    {
        "name": "RSC_Mullick_Baghajatin_to_8B", "road": "Raja S.C. Mullick Road", "direction": "northbound",
        "start": {"lat": 22.48410, "lon": 88.37543},  # Baghajatin
        "via":   {"lat": 22.49140, "lon": 88.37232},  # Sulekha
        "end":   {"lat": 22.49548, "lon": 88.37086},  # 8B
        "ref_distance_km": 1.38,
    },
    {
        "name": "Prince_Anwar_Shah_Tollygunge_to_Jadavpur", "road": "Prince Anwar Shah Road", "direction": "eastbound",
        "start": {"lat": 22.50148, "lon": 88.35197},  # Tollygunge end
        "via":   {"lat": 22.50217, "lon": 88.36000},  # middle
        "end":   {"lat": 22.50292, "lon": 88.36723},  # Jadavpur end
        "ref_distance_km": 1.69,
    },
    {
        "name": "Prince_Anwar_Shah_Jadavpur_to_Tollygunge", "road": "Prince Anwar Shah Road", "direction": "westbound",
        "start": {"lat": 22.50285, "lon": 88.36724},  # Jadavpur end
        "via":   {"lat": 22.50208, "lon": 88.36001},  # middle
        "end":   {"lat": 22.50140, "lon": 88.35200},  # Tollygunge end
        "ref_distance_km": 1.7,
    },
    {
        "name": "EM_Bypass_Ruby_to_Mukundapur", "road": "EM Bypass", "direction": "southbound",
        "start": {"lat": 22.51301, "lon": 88.40206},  # near Ruby
        "via":   {"lat": 22.50401, "lon": 88.40091},  # Kalikapur
        "end":   {"lat": 22.49391, "lon": 88.39769},  # before Mukundapur flyover
        "ref_distance_km": 2.18,
    },
    {
        "name": "EM_Bypass_Mukundapur_to_Ruby", "road": "EM Bypass", "direction": "northbound",
        "start": {"lat": 22.49398, "lon": 88.39755},  # before Mukundapur flyover
        "via":   {"lat": 22.50406, "lon": 88.40066},  # Kalikapur
        "end":   {"lat": 22.51299, "lon": 88.40176},  # near Ruby
        "ref_distance_km": 2.17,
    },
]

# Final points for TomTom Traffic Flow ("how fast is traffic right here?").
LOCATIONS = [
    {"name": "RSC_Mullick_Jadavpur",  "lat": 22.49880, "lon": 88.36980},  # her "Jadavpur_Stn" point (near JU gates 3/4)
    {"name": "8B",                    "lat": 22.49551, "lon": 88.37094},  # moved onto Raja S.C. Mullick Rd
    {"name": "Sulekha",               "lat": 22.49140, "lon": 88.37240},  # moved onto Raja S.C. Mullick Rd
    {"name": "RSC_Mullick_Dhakuria",  "lat": 22.50499, "lon": 88.36720},
    {"name": "Prince_Anwar_Shah_mid", "lat": 22.50217, "lon": 88.35999},
    {"name": "EM_Bypass_Kalikapur",   "lat": 22.50498, "lon": 88.40112},
]

# Box for the TomTom incidents search: the 4 roads plus ~300 m around them.
AREA_BOX = {"min_lat": 22.481, "min_lon": 88.348, "max_lat": 22.517, "max_lon": 88.405}

ROUTE_CHANGE_TOLERANCE = 0.05   # a reading more than 5% longer/shorter than ref_distance_km = route changed

# West Bengal festival days that the `holidays` package does not know (Durga Puja, Kali Puja ...).
# Fill in from your teammates, one line per day:   "YYYY-MM-DD": "name",
FESTIVAL_DAYS = {
    # "2026-10-18": "Durga Puja - Saptami",
}

# Where the weather is read from (Jadavpur).
WEATHER_POINT = {"lat": 22.4970, "lon": 88.3720}

# Logger: wait between TomTom calls (seconds), to stay under TomTom's rate limit.
TOMTOM_PAUSE = 0.3

TIMEZONE = "Asia/Kolkata"
DATA_DIR = "data"
REQUEST_TIMEOUT = 10
RETRIES = 1
RETRY_WAIT_SECONDS = 3
