"""
ATLAS — retracement_engine.py (FIXED)

Root cause of small range bug:
  - Old version used single candle range for stop → 1–2 pip stops
  - Old version only looked back 14 candles for TP → 8–15 pip targets
  - Result: RR < 1 constantly → -80 score penalty → NO TRADE on everything

Fix:
  - Stop is now ATR-based (Average True Range over 14 periods)
  - TP target uses 50-candle swing high/low → realistic institutional target
  - Entry zone derived from OB/FVG logic (50–62% retracement of last move)
  - Minimum stop buffer enforced per pair type
"""

import numpy as np


# Minimum stop distance in price units per pair type
# Prevents unrealistically tight stops
MIN_STOP_PIPS = {
    "JPY": 0.060,    # 6 pips (JPY pairs — price ~150, 1 pip = 0.01)
    "XAU": 1.500,    # $1.50 for Gold
    "XAG": 0.050,    # 5 cents for Silver
    "DEFAULT": 0.00060  # 6 pips for standard pairs (EUR/USD etc.)
}


def get_min_stop(symbol: str) -> float:
    if "JPY" in symbol.upper():
        return MIN_STOP_PIPS["JPY"]
    if "XAU" in symbol.upper():
        return MIN_STOP_PIPS["XAU"]
    if "XAG" in symbol.upper():
        return MIN_STOP_PIPS["XAG"]
    return MIN_STOP_PIPS["DEFAULT"]


def calculate_atr(candles, period: int = 14) -> float:
    """
    True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    ATR = Average of TR over [period] candles.
    This gives a realistic measure of recent volatility — far better
    than using a single candle range.
    """
    if len(candles) < period + 1:
        # Fallback: use simple mean of high-low ranges
        return float((candles["high"] - candles["low"]).mean())

    trs = []
    for i in range(1, period + 1):
        high = float(candles.iloc[i]["high"])
        low = float(candles.iloc[i]["low"])
        prev_close = float(candles.iloc[i + 1]["close"]) if i + 1 < len(candles) else low
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)

    return float(np.mean(trs))


def get_swing_high(candles, lookback: int = 50) -> float:
    """
    Institutional swing high: highest high over [lookback] candles.
    This is where liquidity pools sit — the real TP target.
    """
    window = candles.iloc[1:lookback + 1]  # exclude current candle
    return float(window["high"].max())


def get_swing_low(candles, lookback: int = 50) -> float:
    """
    Institutional swing low: lowest low over [lookback] candles.
    Equal lows, sell stops, liquidity below — real TP target.
    """
    window = candles.iloc[1:lookback + 1]
    return float(window["low"].min())


def build_retracement_entry(candles, structure: str, symbol: str = "UNKNOWN") -> dict:
    """
    Builds a realistic institutional retracement entry zone.

    Logic (BULLISH example):
      - The last impulsive move UP defines our range
      - Entry zone = 50–62% retracement of that move (OB/FVG area)
      - Stop = ATR × 1.5 below entry (gives room for manipulation)
      - TP = swing high (liquidity pool above EQH)
      - RR is calculated on these realistic levels

    Why 50–62%? This maps to the ICT OB/FVG retracement zone.
    Price pulls back to fill the imbalance before continuing.
    """

    if len(candles) < 20:
        return _empty_result()

    latest = candles.iloc[0]
    current_high = float(latest["high"])
    current_low = float(latest["low"])

    # ATR for stop sizing — the key fix
    atr = calculate_atr(candles, period=14)
    min_stop = get_min_stop(symbol)

    # Enforce minimum stop distance
    stop_buffer = max(atr * 1.5, min_stop)

    # Swing levels for TP — look back 50 candles (institutional)
    swing_high = get_swing_high(candles, lookback=50)
    swing_low = get_swing_low(candles, lookback=50)

    # Determine the last impulsive move range
    # For BULLISH: measure from the recent swing low to current high
    # For BEARISH: measure from recent swing high to current low
    recent_high = get_swing_high(candles, lookback=15)
    recent_low = get_swing_low(candles, lookback=15)
    move_range = recent_high - recent_low

    if structure == "BULLISH":
        # Retracement entry zone: 50–62% pullback from recent high
        # This is where OBs and FVGs typically sit
        entry_high = recent_high - (move_range * 0.50)  # 50% retrace
        entry_low = recent_high - (move_range * 0.62)   # 62% retrace (deep OB)
        suggested_entry = round(entry_high, 5)

        # Stop: ATR below the entry zone (below OB + buffer)
        stop_loss = round(entry_low - stop_buffer, 5)

        # TP: previous swing high (liquidity above — equal highs)
        tp1 = round(swing_high, 5)

        # Second target: swing high + 50% of the move range extension
        tp2 = round(swing_high + (move_range * 0.50), 5)

        risk = abs(suggested_entry - stop_loss)
        reward_tp1 = abs(tp1 - suggested_entry)
        reward_tp2 = abs(tp2 - suggested_entry)

        expected_rr = _safe_rr(reward_tp1, risk)
        rr_tp2 = _safe_rr(reward_tp2, risk)

        return {
            "zone": f"{round(entry_low, 5)} - {round(entry_high, 5)}",
            "type": "BUY RETRACEMENT ZONE",
            "suggested_entry": suggested_entry,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "atr": round(atr, 5),
            "expected_rr": expected_rr,
            "rr_tp2": rr_tp2,
            "risk_pips": round(risk, 5),
        }

    if structure == "BEARISH":
        # Retracement entry zone: 50–62% pullback from recent low (upward retrace)
        entry_low = recent_low + (move_range * 0.50)   # 50% retrace up
        entry_high = recent_low + (move_range * 0.62)  # 62% retrace up (deep OB)
        suggested_entry = round(entry_low, 5)

        # Stop: ATR above the entry zone
        stop_loss = round(entry_high + stop_buffer, 5)

        # TP: previous swing low (liquidity below — equal lows)
        tp1 = round(swing_low, 5)

        # Second target: extension below swing low
        tp2 = round(swing_low - (move_range * 0.50), 5)

        risk = abs(stop_loss - suggested_entry)
        reward_tp1 = abs(suggested_entry - tp1)
        reward_tp2 = abs(suggested_entry - tp2)

        expected_rr = _safe_rr(reward_tp1, risk)
        rr_tp2 = _safe_rr(reward_tp2, risk)

        return {
            "zone": f"{round(entry_low, 5)} - {round(entry_high, 5)}",
            "type": "SELL RETRACEMENT ZONE",
            "suggested_entry": suggested_entry,
            "stop_loss": stop_loss,
            "tp1": tp1,
            "tp2": tp2,
            "atr": round(atr, 5),
            "expected_rr": expected_rr,
            "rr_tp2": rr_tp2,
            "risk_pips": round(risk, 5),
        }

    return _empty_result()


def _safe_rr(reward: float, risk: float) -> float:
    """Returns RR ratio. Returns 0 if risk is zero or negative."""
    if risk <= 0:
        return 0.0
    return round(reward / risk, 2)


def _empty_result() -> dict:
    return {
        "zone": "N/A",
        "type": "WAIT — INSUFFICIENT DATA",
        "suggested_entry": "N/A",
        "stop_loss": "N/A",
        "tp1": "N/A",
        "tp2": "N/A",
        "atr": "N/A",
        "expected_rr": 0,
        "rr_tp2": 0,
        "risk_pips": "N/A",
    }
