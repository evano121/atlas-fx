from datetime import datetime
import pytz


riyadh = pytz.timezone("Asia/Riyadh")


def get_current_session():

    now = datetime.now(riyadh)

    hour = now.hour

    if 0 <= hour < 8:
        return "ASIA"

    elif 8 <= hour < 16:
        return "LONDON"

    elif 16 <= hour < 24:
        return "NEW_YORK"

    return "UNKNOWN"


if __name__ == "__main__":
    print(get_current_session())