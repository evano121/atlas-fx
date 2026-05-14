def detect_crt(candles):

    latest = candles.iloc[0]

    open_price = float(latest["open"])
    close_price = float(latest["close"])
    high = float(latest["high"])
    low = float(latest["low"])

    candle_range = high - low
    body = abs(close_price - open_price)

    body_ratio = body / candle_range if candle_range != 0 else 0

    if body_ratio > 0.7:

        if close_price > open_price:
            return "BULLISH EXPANSION"

        else:
            return "BEARISH EXPANSION"

    if body_ratio < 0.3:
        return "MANIPULATION"

    return "NORMAL"