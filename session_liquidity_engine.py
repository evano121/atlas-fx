from datetime import datetime


def detect_session_liquidity(candles):
    candles = candles.copy()

    candles["high"] = candles["high"].astype(float)
    candles["low"] = candles["low"].astype(float)

    candles["datetime"] = candles["datetime"].astype(str)
    candles["hour"] = candles["datetime"].apply(
        lambda x: datetime.fromisoformat(x).hour
    )

    asia = candles[(candles["hour"] >= 0) & (candles["hour"] < 8)]

    latest = candles.iloc[0]
    latest_high = float(latest["high"])
    latest_low = float(latest["low"])

    if asia.empty:
        return {
            "asia_high": "N/A",
            "asia_low": "N/A",
            "session_event": "NO ASIA DATA"
        }

    asia_high = float(asia["high"].max())
    asia_low = float(asia["low"].min())

    if latest_high > asia_high:
        session_event = "ASIA HIGH SWEPT"

    elif latest_low < asia_low:
        session_event = "ASIA LOW SWEPT"

    else:
        session_event = "ASIA RANGE INTACT"

    return {
        "asia_high": round(asia_high, 5),
        "asia_low": round(asia_low, 5),
        "session_event": session_event
    }