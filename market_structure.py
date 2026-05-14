import pandas as pd


def detect_market_structure(candles):

    highs = candles["high"].astype(float).tolist()
    lows = candles["low"].astype(float).tolist()

    recent_highs = highs[:5]
    recent_lows = lows[:5]

    bullish = recent_highs[0] > recent_highs[-1] and recent_lows[0] > recent_lows[-1]

    bearish = recent_highs[0] < recent_highs[-1] and recent_lows[0] < recent_lows[-1]

    if bullish:
        return "BULLISH"

    if bearish:
        return "BEARISH"

    return "RANGING"