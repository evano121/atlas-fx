from datetime import datetime
import pytz


riyadh = pytz.timezone("Asia/Riyadh")


def detect_news_risk():

    now = datetime.now(riyadh)

    hour = now.hour

    # Simplified placeholders
    # Later we connect real economic calendar API

    high_risk_hours = [15, 16]

    if hour in high_risk_hours:
        return "HIGH NEWS RISK"

    return "LOW NEWS RISK"