"""
ATLAS — expansion_engine.py (FIXED)

=============================================================
PROBLEMS WITH THE OLD VERSION (25 lines)
=============================================================

Old output: "HEALTHY EXPANSION", "OVEREXTENDED", "NORMAL"
  - No direction. Score engine checks for "BULLISH EXPANSION"
    or "BEARISH EXPANSION" but expansion_engine never returned those.
  - Result: CRT score always 0 in score_engine → setups always
    penalized for missing CRT even when expansion was present.

Old logic: only compared latest candle range to 9-candle average.
  - 9 candles = 2.25 hours on 15M. Too short to detect session expansion.
  - Didn't check direction — expansion could be up or down.
  - "OVEREXTENDED" was never used by any other engine.

=============================================================
HOW THE FIX WORKS
=============================================================

New logic:
  1. Calculate ATR over 14 candles (real volatility baseline)
  2. Measure latest candle range vs ATR
  3. Check latest candle DIRECTION (bullish or bearish close)
  4. Check if body is dominant (>50% of range) — displacement signal
  5. Combine: direction + expansion ratio → ICT-compatible label

New outputs:
  "BULLISH EXPANSION"   → price expanding upward with momentum
  "BEARISH EXPANSION"   → price expanding downward with momentum
  "BULLISH CONSOLIDATION" → upward but weak body, below expansion threshold
  "BEARISH CONSOLIDATION" → downward but weak body, below expansion threshold
  "RANGING"             → no clear direction, avoid entries
  "OVEREXTENDED"        → expansion ratio > 2.5, wait for pullback

These labels are EXACTLY what score_engine.py checks for.
score_engine now correctly awards 15pts for CRT confirmation.
=============================================================
"""


def detect_expansion_state(candles) -> str:
    """
    Detects CRT expansion state with directional context.

    Returns one of:
        "BULLISH EXPANSION"       → Strong upward displacement
        "BEARISH EXPANSION"       → Strong downward displacement
        "BULLISH CONSOLIDATION"   → Weak upward, wait for expansion
        "BEARISH CONSOLIDATION"   → Weak downward, wait for expansion
        "RANGING"                 → No clear directional bias
        "OVEREXTENDED"            → Too extended, wait for pullback
        "INSUFFICIENT DATA"       → Not enough candles to assess

    ICT context:
        Expansion = price moving away from an OB/FVG with momentum.
        This is the "delivery" phase of the CRT model.
        High-quality entries happen at the START of expansion,
        after a sweep and retracement to the OB/FVG zone.
    """
    if len(candles) < 16:
        return "INSUFFICIENT DATA"

    latest = candles.iloc[0]
    latest_open  = float(latest["open"])
    latest_high  = float(latest["high"])
    latest_low   = float(latest["low"])
    latest_close = float(latest["close"])
    latest_range = latest_high - latest_low

    # ── ATR BASELINE (14 periods) ─────────────────────────────────────
    # Use candles 1–15 (exclude current) for ATR calculation
    atr_candles = candles.iloc[1:16]
    true_ranges = []
    for i in range(len(atr_candles) - 1):
        h  = float(atr_candles.iloc[i]["high"])
        lo = float(atr_candles.iloc[i]["low"])
        pc = float(atr_candles.iloc[i + 1]["close"])
        tr = max(h - lo, abs(h - pc), abs(lo - pc))
        true_ranges.append(tr)

    if not true_ranges:
        return "INSUFFICIENT DATA"

    atr = sum(true_ranges) / len(true_ranges)

    # ── EXPANSION RATIO ───────────────────────────────────────────────
    # How much larger is the current candle vs average volatility?
    # > 2.5 = overextended (don't chase)
    # >= 1.3 = expansion (institutional displacement)
    # < 1.3  = consolidation (wait)
    if atr == 0:
        return "RANGING"

    expansion_ratio = latest_range / atr

    # ── DIRECTION ─────────────────────────────────────────────────────
    # Bullish = closed above open
    # Bearish = closed below open
    is_bullish = latest_close > latest_open
    is_bearish = latest_close < latest_open

    # ── BODY DOMINANCE ────────────────────────────────────────────────
    # Body = |close - open|
    # Wick  = range - body
    # Strong candle: body > 50% of range (institutional displacement)
    # Weak candle:   body < 50% of range (indecision/noise)
    body = abs(latest_close - latest_open)
    body_ratio = body / latest_range if latest_range > 0 else 0
    strong_body = body_ratio >= 0.50

    # ── RECENT TREND CONFIRMATION ─────────────────────────────────────
    # Check last 5 candles for directional consistency
    recent = candles.iloc[1:6]
    recent_bullish = (recent["close"] > recent["open"]).sum()
    recent_bearish = (recent["close"] < recent["open"]).sum()
    trend_bullish = recent_bullish >= 3   # 3 of last 5 bullish
    trend_bearish = recent_bearish >= 3   # 3 of last 5 bearish

    # ── CLASSIFY ──────────────────────────────────────────────────────

    # Overextended: too far too fast — wait for retracement
    if expansion_ratio >= 2.5:
        return "OVEREXTENDED"

    # Genuine expansion: large candle + strong body + trend agreement
    if expansion_ratio >= 1.3:
        if is_bullish and strong_body and trend_bullish:
            return "BULLISH EXPANSION"
        if is_bearish and strong_body and trend_bearish:
            return "BEARISH EXPANSION"
        # Large candle but body weak or trend disagrees
        if is_bullish:
            return "BULLISH CONSOLIDATION"
        if is_bearish:
            return "BEARISH CONSOLIDATION"

    # Below expansion threshold
    if is_bullish and trend_bullish:
        return "BULLISH CONSOLIDATION"
    if is_bearish and trend_bearish:
        return "BEARISH CONSOLIDATION"

    # No clear directional conviction
    return "RANGING"


def get_expansion_context(candles) -> dict:
    """
    Extended version returning full expansion context for dashboard display.
    Returns the state plus supporting metrics for debugging/review.
    """
    if len(candles) < 16:
        return {
            "state":          "INSUFFICIENT DATA",
            "expansion_ratio": 0,
            "body_ratio":      0,
            "atr":             0,
            "candle_range":    0,
        }

    latest       = candles.iloc[0]
    latest_open  = float(latest["open"])
    latest_high  = float(latest["high"])
    latest_low   = float(latest["low"])
    latest_close = float(latest["close"])
    latest_range = latest_high - latest_low

    atr_candles  = candles.iloc[1:16]
    true_ranges  = []
    for i in range(len(atr_candles) - 1):
        h  = float(atr_candles.iloc[i]["high"])
        lo = float(atr_candles.iloc[i]["low"])
        pc = float(atr_candles.iloc[i + 1]["close"])
        tr = max(h - lo, abs(h - pc), abs(lo - pc))
        true_ranges.append(tr)

    atr = sum(true_ranges) / len(true_ranges) if true_ranges else 0
    expansion_ratio = round(latest_range / atr, 2) if atr > 0 else 0
    body = abs(latest_close - latest_open)
    body_ratio = round(body / latest_range, 2) if latest_range > 0 else 0

    return {
        "state":           detect_expansion_state(candles),
        "expansion_ratio": expansion_ratio,
        "body_ratio":      body_ratio,
        "atr":             round(atr, 5),
        "candle_range":    round(latest_range, 5),
    }
