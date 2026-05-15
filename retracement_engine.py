def build_retracement_entry(candles, structure):
    latest = candles.iloc[0]
    previous = candles.iloc[1:15]

    high = float(latest["high"])
    low = float(latest["low"])

    previous_high = float(previous["high"].max())
    previous_low = float(previous["low"].min())

    candle_range = high - low

    if structure == "BEARISH":
        entry_low = low + (candle_range * 0.50)
        entry_high = low + (candle_range * 0.75)

        suggested_entry = entry_high
        stop_loss = max(high, previous_high) + (candle_range * 0.15)
        tp1 = previous_low

        risk = abs(stop_loss - suggested_entry)
        reward = abs(suggested_entry - tp1)

        expected_rr = round(reward / risk, 2) if risk != 0 else "N/A"

        return {
            "zone": f"{round(entry_low, 5)} - {round(entry_high, 5)}",
            "type": "SELL RETRACEMENT ZONE",
            "suggested_entry": round(suggested_entry, 5),
            "expected_rr": expected_rr
        }

    if structure == "BULLISH":
        entry_low = high - (candle_range * 0.75)
        entry_high = high - (candle_range * 0.50)

        suggested_entry = entry_low
        stop_loss = min(low, previous_low) - (candle_range * 0.15)
        tp1 = previous_high

        risk = abs(suggested_entry - stop_loss)
        reward = abs(tp1 - suggested_entry)

        expected_rr = round(reward / risk, 2) if risk != 0 else "N/A"

        return {
            "zone": f"{round(entry_low, 5)} - {round(entry_high, 5)}",
            "type": "BUY RETRACEMENT ZONE",
            "suggested_entry": round(suggested_entry, 5),
            "expected_rr": expected_rr
        }

    return {
        "zone": "N/A",
        "type": "WAIT",
        "suggested_entry": "N/A",
        "expected_rr": "N/A"
    }