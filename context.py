from datetime import datetime
from zoneinfo import ZoneInfo
import holidays
import config
import weather_api
_official_holidays = holidays.India(subdiv="WB")

def holiday_name(day):
    return config.FESTIVAL_DAYS.get(day.isoformat()) or _official_holidays.get(day) or ""

def get_run_context():
    now = datetime.now(ZoneInfo(config.TIMEZONE))
    holiday = holiday_name(now.date())
    ctx = {
        "run_time_ist": now.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": now.strftime("%A"),
        "is_weekend": now.weekday() >= 5,
        "is_holiday": bool(holiday),
        "holiday_name": holiday,
    }
    ctx.update(weather_api.current_weather(config.WEATHER_POINT))
    return ctx
