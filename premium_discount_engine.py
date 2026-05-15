def detect_premium_discount(candles):
    recent = candles.iloc[0:20]

    high = float(recent["high"].max())
    low = float(recent["low"].min())

    equilibrium = (high + low) / 2

    latest_close = float(candles.iloc[0]["close"])

    if latest_close > equilibrium:
        return {
            "zone": "PREMIUM",
            "equilibrium": round(equilibrium, 5)
        }

    if latest_close < equilibrium:
        return {
            "zone": "DISCOUNT",
            "equilibrium": round(equilibrium, 5)
        }

    return {
        "zone": "EQUILIBRIUM",
        "equilibrium": round(equilibrium, 5)
    }