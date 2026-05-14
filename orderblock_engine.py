def detect_order_block(candles):

    latest = candles.iloc[0]
    previous = candles.iloc[1]

    latest_open = float(latest["open"])
    latest_close = float(latest["close"])

    previous_open = float(previous["open"])
    previous_close = float(previous["close"])

    # Bullish Order Block
    if previous_close < previous_open and latest_close > latest_open:
        return "BULLISH OB"

    # Bearish Order Block
    if previous_close > previous_open and latest_close < latest_open:
        return "BEARISH OB"

    return "NO OB"