"""
ATLAS — score_engine.py (FIXED)

Root cause of scoring problem:
  - Old version: rr < 1 → score -= 80 inside the score function
  - This DESTROYED the score on otherwise perfect setups
  - Because RR was broken (retracement_engine bug), not the setup itself
  - Even after fixing RR, mixing RR into structure score is wrong:
      Structure quality and RR quality are SEPARATE dimensions

Fix:
  - score_setup() now scores STRUCTURE QUALITY only (max 100)
  - RR is evaluated separately by rr_quality_filter()
  - decision_engine combines both — structure score + RR filter
  - This correctly separates "is the setup valid" from "is the entry good"

Scoring weights (total 100):
  - Liquidity sweep:        25 pts  (essential — no sweep = no setup)
  - Session quality:        15 pts  (London/NY vs off-session)
  - CRT confirmation:       15 pts  (expansion state)
  - FVG + OB confluence:    15 pts  (institutional confirmation)
  - Market structure:       10 pts  (BOS/CHoCH direction)
  - Killzone alignment:     10 pts  (timing quality)
  - MTF alignment:          10 pts  (15M + 1H agree)
  - Daily liquidity event:   5 pts  (PDH/PDL sweep)
  - Session liquidity:       5 pts  (Asia range used)
  - Penalties applied last (ranging, no confirmation, high news)
"""


def score_setup(
    session,
    sweep,
    structure=None,
    rr=None,           # kept for backward compat — no longer penalized here
    crt=None,
    fvg=None,
    ob=None,
    killzone=None,
    news_risk=None,
    mtf_alignment=False,
    daily_liquidity=None,
    session_liquidity=None
):
    """
    Returns (score, grade, reasons).
    Score reflects STRUCTURAL QUALITY of the setup, not RR.
    RR is filtered separately in rr_quality_filter().
    """
    score = 0
    reasons = []

    # ── LIQUIDITY SWEEP (25 pts) ──────────────────────────────────────────
    # Most important signal. No sweep = no institutional interest.
    if sweep not in ("NO SWEEP", "DATA ERROR", None):
        score += 25
        reasons.append(f"Liquidity sweep: {sweep}")
    else:
        score -= 15
        reasons.append("No liquidity sweep — setup quality reduced")

    # ── SESSION QUALITY (15 pts) ──────────────────────────────────────────
    if session == "LONDON":
        score += 15
        reasons.append("London session — high institutional volume")
    elif session == "NEW_YORK":
        score += 15
        reasons.append("New York session — high institutional volume")
    elif session == "OVERLAP":
        score += 12
        reasons.append("London-NY overlap — elevated volatility")
    elif session == "ASIA":
        score += 3
        reasons.append("Asia session — low volume, range formation only")
    else:
        score += 0
        reasons.append("Off-session — avoid entries")

    # ── CRT CONFIRMATION (15 pts) ─────────────────────────────────────────
    if crt in ("BULLISH EXPANSION", "BEARISH EXPANSION"):
        score += 15
        reasons.append(f"CRT expansion confirmed: {crt}")
    elif crt in ("BULLISH CONSOLIDATION", "BEARISH CONSOLIDATION"):
        score += 5
        reasons.append(f"CRT consolidating — wait for expansion: {crt}")

    # ── FVG + OB CONFLUENCE (15 pts combined) ─────────────────────────────
    fvg_score = 0
    ob_score = 0

    if fvg in ("BULLISH FVG", "BEARISH FVG"):
        fvg_score = 8
        reasons.append(f"FVG present: {fvg}")
    else:
        reasons.append("No FVG — reduced confluence")

    if ob in ("BULLISH OB", "BEARISH OB"):
        ob_score = 7
        reasons.append(f"Order block: {ob}")
    else:
        reasons.append("No OB — reduced confluence")

    score += fvg_score + ob_score

    # Both missing = heavy penalty
    if fvg not in ("BULLISH FVG", "BEARISH FVG") and ob not in ("BULLISH OB", "BEARISH OB"):
        score -= 20
        reasons.append("No FVG and no OB — major confluence missing")

    # Full alignment bonus
    bearish_full = (
        structure == "BEARISH"
        and crt == "BEARISH EXPANSION"
        and fvg == "BEARISH FVG"
        and ob == "BEARISH OB"
    )
    bullish_full = (
        structure == "BULLISH"
        and crt == "BULLISH EXPANSION"
        and fvg == "BULLISH FVG"
        and ob == "BULLISH OB"
    )
    if bearish_full or bullish_full:
        score += 10
        reasons.append("Full institutional alignment — all signals agree")

    # ── MARKET STRUCTURE (10 pts) ─────────────────────────────────────────
    if structure in ("BULLISH", "BEARISH"):
        score += 10
        reasons.append(f"Clear market structure: {structure}")
    elif structure == "RANGING":
        score -= 20
        reasons.append("Ranging market — no directional bias, avoid")

    # ── KILLZONE TIMING (10 pts) ──────────────────────────────────────────
    if killzone == "SILVER BULLET WINDOW":
        score += 10
        reasons.append("Silver Bullet window — highest timing quality")
    elif killzone in ("LONDON KILLZONE", "NY AM KILLZONE"):
        score += 8
        reasons.append(f"Active killzone: {killzone}")
    elif killzone == "NY PM KILLZONE":
        score += 4
        reasons.append("NY PM killzone — reduced probability")
    else:
        reasons.append("No killzone active — off timing")

    # ── MTF ALIGNMENT (10 pts) ────────────────────────────────────────────
    if mtf_alignment:
        score += 10
        reasons.append("15M and 1H structure aligned")
    else:
        reasons.append("MTF misaligned — 15M and 1H disagree")

    # ── DAILY LIQUIDITY (5 pts) ───────────────────────────────────────────
    if daily_liquidity in ("PDH SWEPT", "PDL SWEPT"):
        score += 5
        reasons.append(f"Daily liquidity event: {daily_liquidity}")

    # ── SESSION LIQUIDITY (5 pts) ─────────────────────────────────────────
    if session_liquidity in ("ASIA HIGH SWEPT", "ASIA LOW SWEPT"):
        score += 5
        reasons.append(f"Session liquidity swept: {session_liquidity}")

    # ── NEWS RISK PENALTY ─────────────────────────────────────────────────
    if "HIGH NEWS RISK" in str(news_risk):
        score -= 35
        reasons.append(f"HIGH NEWS RISK — setup heavily penalized: {news_risk}")
    elif "MEDIUM NEWS RISK" in str(news_risk):
        score -= 10
        reasons.append(f"Medium news risk — caution: {news_risk}")
    elif news_risk == "LOW NEWS RISK":
        score += 3
        reasons.append("Clean news environment")

    # ── CLAMP AND GRADE ───────────────────────────────────────────────────
    score = max(0, min(100, score))

    if score >= 90:
        grade = "A+"
    elif score >= 75:
        grade = "A"
    elif score >= 55:
        grade = "B"
    else:
        grade = "C"

    return score, grade, reasons


def rr_quality_filter(rr_value: float, retracement_rr: float = 0) -> dict:
    """
    Evaluates RR quality SEPARATELY from structural score.
    This is used by decision_engine to make the final call.

    Returns a dict with:
      - label: human-readable quality label
      - passes: whether this RR is acceptable for entry
      - recommendation: what to do
    """
    try:
        rr = float(rr_value)
    except (TypeError, ValueError):
        rr = 0.0

    try:
        ret_rr = float(retracement_rr)
    except (TypeError, ValueError):
        ret_rr = 0.0

    if rr >= 3.0:
        return {
            "label": "ELITE RR",
            "passes": True,
            "recommendation": "Enter at market — exceptional risk/reward",
            "rr": rr
        }
    elif rr >= 2.0:
        return {
            "label": "STRONG RR",
            "passes": True,
            "recommendation": "Valid entry — strong risk/reward",
            "rr": rr
        }
    elif rr >= 1.5:
        return {
            "label": "ACCEPTABLE RR",
            "passes": True,
            "recommendation": "Acceptable — confirm with killzone timing",
            "rr": rr
        }
    elif rr >= 1.0:
        return {
            "label": "MARGINAL RR",
            "passes": True,
            "recommendation": "Marginal entry — consider waiting for retracement",
            "rr": rr
        }
    elif ret_rr >= 1.5:
        return {
            "label": "WAIT FOR RETRACEMENT",
            "passes": False,
            "recommendation": f"Current RR poor ({rr}R). Retracement offers {ret_rr}R — wait for pullback",
            "rr": rr
        }
    else:
        return {
            "label": "POOR RR",
            "passes": False,
            "recommendation": "RR does not meet minimum threshold. No trade.",
            "rr": rr
        }
