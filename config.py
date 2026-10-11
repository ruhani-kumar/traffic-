ROUTES = [
    {
        "name": "Jadavpur_Stn_to_8B",
        "start": {"lat": 22.4988, "lon": 88.3698},  # Jadavpur Station
        "end":   {"lat": 22.4953, "lon": 88.3691},  # 8B Bus Stand
    },
    {
        "name": "8B_to_Sulekha",
        "start": {"lat": 22.4953, "lon": 88.3691},  # 8B Bus Stand
        "end":   {"lat": 22.4915, "lon": 88.3712},  # Sulekha More
    },
    {
        "name": "Sulekha_to_8B",
        "start": {"lat": 22.4915, "lon": 88.3712},  # Sulekha More
        "end":   {"lat": 22.4953, "lon": 88.3691},  # 8B Bus Stand
    },
]

CANDIDATE_ROUTES = [
    {
        "name": "RSC_Mullick_Gariahat_to_Jadavpur",
        "start": {"lat": 22.51337, "lon": 88.36724},  # Raja S.C. Mullick Rd near Gariahat/Golpark
        "end":   {"lat": 22.49954, "lon": 88.36958},  # Raja S.C. Mullick Rd at Jadavpur
    },
    {
        "name": "RSC_Mullick_Jadavpur_to_Baghajatin",
        "start": {"lat": 22.49550, "lon": 88.37095},  # Raja S.C. Mullick Rd at 8B
        "end":   {"lat": 22.48412, "lon": 88.37543},  # Raja S.C. Mullick Rd at Baghajatin
    },
    {
        "name": "Prince_Anwar_Shah_Tollygunge_to_Jadavpur",
        "start": {"lat": 22.50140, "lon": 88.35198},  # Prince Anwar Shah Rd, Tollygunge end
        "end":   {"lat": 22.50303, "lon": 88.36758},  # Prince Anwar Shah Rd, Jadavpur end
    },
    {
        "name": "EM_Bypass_Ruby_to_Mukundapur",
        "start": {"lat": 22.51299, "lon": 88.40176},  # EM Bypass near Ruby
        "end":   {"lat": 22.48981, "lon": 88.39547},  # EM Bypass near Mukundapur
    },
]

CANDIDATE_POINTS = [
    {"name": "Jadavpur_Stn_point", "lat": 22.4988, "lon": 88.3698},   
    {"name": "8B_point",           "lat": 22.4953, "lon": 88.3691},
    {"name": "Sulekha_point",      "lat": 22.4915, "lon": 88.3712},
    {"name": "RSC_Mullick_Dhakuria",    "lat": 22.50499, "lon": 88.36720},
    {"name": "RSC_Mullick_Baghajatin",  "lat": 22.48993, "lon": 88.37211},
    {"name": "Prince_Anwar_Shah_mid",   "lat": 22.50217, "lon": 88.35999},
    {"name": "EM_Bypass_Kalikapur",     "lat": 22.50498, "lon": 88.40112},
]

# Box around Jadavpur used for the TomTom incidents search and the map.
AREA_BOX = {"min_lat": 22.478, "min_lon": 88.345, "max_lat": 22.520, "max_lon": 88.410}

TIMEZONE = "Asia/Kolkata"
DATA_DIR = "data"
REQUEST_TIMEOUT = 10
RETRIES = 1
RETRY_WAIT_SECONDS = 3
