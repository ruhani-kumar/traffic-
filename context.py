from datetime import datetime
from zoneinfo import ZoneInfo
import config
def get_run_context():
    now = datetime.now(ZoneInfo(config.TIMEZONE))
    return {
        "run_time_ist": now.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": now.strftime("%A"),
    }
