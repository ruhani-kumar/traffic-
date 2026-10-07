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
TIMEZONE = "Asia/Kolkata"
DATA_DIR = "data"
REQUEST_TIMEOUT = 10
RETRIES = 1
RETRY_WAIT_SECONDS = 3
