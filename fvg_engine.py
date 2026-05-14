def detect_fvg(candles):

    if len(candles) < 3:
        return "NO FVG"

    c1 = candles.iloc[2]
    c2 = candles.iloc[1]
    c3 = candles.iloc[0]

    # Bullish FVG
    if float(c1["high"]) < float(c3["low"]):
        return "BULLISH FVG"

    # Bearish FVG
    if float(c1["low"]) > float(c3["high"]):
        return "BEARISH FVG"

    return "NO FVG"