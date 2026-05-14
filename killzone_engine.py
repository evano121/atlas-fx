from datetime import datetime
import pytz

riyadh = pytz.timezone("Asia/Riyadh")


def detect_killzone():
    now = datetime.now(riyadh)
    hour = now.hour
    minute = now.minute

    current_minutes = hour * 60 + minute

    # Times in Riyadh / AST UTC+3

    london_killzone_start = 9 * 60
    london_killzone_end = 12 * 60

    ny_am_killzone_start = 15 * 60 + 30
    ny_am_killzone_end = 18 * 60

    silver_bullet_1_start = 17 * 60
    silver_bullet_1_end = 18 * 60

    if london_killzone_start <= current_minutes <= london_killzone_end:
        return "LONDON KILLZONE"

    if ny_am_killzone_start <= current_minutes <= ny_am_killzone_end:
        return "NY AM KILLZONE"

    if silver_bullet_1_start <= current_minutes <= silver_bullet_1_end:
        return "SILVER BULLET WINDOW"

    return "OUTSIDE KILLZONE"