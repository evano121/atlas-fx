import csv
from datetime import datetime, timedelta
import pytz

riyadh = pytz.timezone("Asia/Riyadh")


def detect_news_risk():
    now = datetime.now(riyadh)

    try:
        with open("news_calendar.csv", "r") as file:
            reader = csv.DictReader(file)

            for row in reader:
                if row["impact"] != "HIGH":
                    continue

                news_time = riyadh.localize(
                    datetime.strptime(
                        row["date"] + " " + row["time"],
                        "%Y-%m-%d %H:%M"
                    )
                )

                window_start = news_time - timedelta(minutes=30)
                window_end = news_time + timedelta(minutes=30)

                if window_start <= now <= window_end:
                    return f"HIGH NEWS RISK — {row['currency']} {row['event']}"

        return "LOW NEWS RISK"

    except Exception as e:
        return f"NEWS DATA ERROR: {e}"