def build_trade_plan(candles, structure, sweep, crt, fvg, ob):
    latest = candles.iloc[0]
    previous = candles.iloc[1:15]

    high = float(latest["high"])
    low = float(latest["low"])
    close = float(latest["close"])

    previous_high = float(previous["high"].max())
    previous_low = float(previous["low"].min())

    candle_range = high - low

    if structure == "BEARISH":
        direction = "SELL"

        entry = close

        # SL above current candle high / buy-side liquidity
        stop_loss = max(high, previous_high) + (candle_range * 0.15)

        # TP targets sell-side liquidity
        tp1 = previous_low
        tp2 = close - ((stop_loss - close) * 2)

    elif structure == "BULLISH":
        direction = "BUY"

        entry = close

        # SL below current candle low / sell-side liquidity
        stop_loss = min(low, previous_low) - (candle_range * 0.15)

        # TP targets buy-side liquidity
        tp1 = previous_high
        tp2 = close + ((close - stop_loss) * 2)

    else:
        return {
            "direction": "WAIT",
            "entry": "N/A",
            "stop_loss": "N/A",
            "tp1": "N/A",
            "tp2": "N/A",
            "rr": "N/A"
        }

    risk = abs(entry - stop_loss)
    reward = abs(tp1 - entry)

    rr = round(reward / risk, 2) if risk != 0 else "N/A"

    return {
        "direction": direction,
        "entry": round(entry, 5),
        "stop_loss": round(stop_loss, 5),
        "tp1": round(tp1, 5),
        "tp2": round(tp2, 5),
        "rr": rr
    }