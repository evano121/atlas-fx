def detect_expansion_state(candles):

    latest = candles.iloc[0]

    latest_high = float(latest["high"])
    latest_low = float(latest["low"])

    latest_range = latest_high - latest_low

    previous = candles.iloc[1:10]

    avg_range = (
        previous["high"].astype(float) -
        previous["low"].astype(float)
    ).mean()

    expansion_ratio = latest_range / avg_range if avg_range != 0 else 0

    if expansion_ratio >= 2:
        return "OVEREXTENDED"

    if expansion_ratio >= 1.2:
        return "HEALTHY EXPANSION"

    return "NORMAL"