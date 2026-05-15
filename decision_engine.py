"""
ATLAS — decision_engine.py (FIXED)

Old version problems:
  - Only 48 lines — no nuance
  - RR threshold of 1.0 was the only quality gate
  - No differentiation between marginal and elite setups
  - Premium/discount logic was the only secondary check

Fixed version:
  - Uses rr_quality_filter() from score_engine (RR scored separately)
  - Score threshold enforced (structural quality gate)
  - Premium/discount logic preserved and improved
  - 6 decision states with clear reasoning
  - Returns full context for dashboard and Telegram
"""

from score_engine import rr_quality_filter


# Minimum structural score to consider any entry
MIN_SCORE_FOR_ENTRY = 70        # Below this = NO TRADE regardless of RR
MIN_SCORE_FOR_WATCHLIST = 55    # Below this = not even on watchlist


def make_final_decision(
    score: float,
    rr,
    retracement_rr=0,
    premium_discount: str = None,
    structure: str = None,
    killzone: str = None,
    news_risk: str = None
) -> dict:
    """
    Final gating logic for ATLAS.

    Decision hierarchy (in order):
    1. News risk gate — hard block
    2. Score gate — structural quality minimum
    3. Premium/discount location check
    4. RR quality gate — is the current entry worth taking?
    5. Retracement quality — is there a better entry coming?
    6. Final decision
    """

    try:
        rr_val = float(rr)
    except (TypeError, ValueError):
        rr_val = 0.0

    try:
        ret_rr = float(retracement_rr)
    except (TypeError, ValueError):
        ret_rr = 0.0

    # ── GATE 1: HARD NEWS BLOCK ───────────────────────────────────────────
    if "HIGH NEWS RISK" in str(news_risk):
        return {
            "decision": "NO TRADE — HIGH NEWS RISK",
            "reason": f"High-impact news event active. ATLAS blocks all entries. Wait for market to stabilize. ({news_risk})",
            "quality": "BLOCKED",
            "score_gate": "BLOCKED",
            "rr_gate": "BLOCKED"
        }

    # ── GATE 2: STRUCTURAL QUALITY ────────────────────────────────────────
    if score < MIN_SCORE_FOR_WATCHLIST:
        return {
            "decision": "NO TRADE — WEAK SETUP",
            "reason": f"Structural score {score}/100 is below minimum threshold ({MIN_SCORE_FOR_WATCHLIST}). Setup lacks enough ICT/SMC confluence.",
            "quality": "LOW",
            "score_gate": "FAILED",
            "rr_gate": "NOT EVALUATED"
        }

    # ── GATE 3: PRICE LOCATION ────────────────────────────────────────────
    wrong_zone = (
        (structure == "BEARISH" and premium_discount == "DISCOUNT") or
        (structure == "BULLISH" and premium_discount == "PREMIUM")
    )

    if wrong_zone:
        if ret_rr >= 2.0:
            return {
                "decision": "WAIT — BAD PRICE LOCATION",
                "reason": (
                    f"Bias is {structure} but price is in {premium_discount} zone — wrong location for entry. "
                    f"Retracement to correct zone offers {ret_rr}R. Wait for price to reach the OB/FVG zone."
                ),
                "quality": "LOCATION INVALID",
                "score_gate": "PASSED",
                "rr_gate": "WAIT FOR LOCATION"
            }
        return {
            "decision": "WAIT — BAD PRICE LOCATION",
            "reason": f"Bias is {structure} but price is in {premium_discount} zone. Do not chase. Wait for retracement.",
            "quality": "LOCATION INVALID",
            "score_gate": "PASSED",
            "rr_gate": "NOT EVALUATED"
        }

    # ── GATE 4: RR QUALITY ────────────────────────────────────────────────
    rr_result = rr_quality_filter(rr_val, ret_rr)

    # ── GATE 5: FINAL DECISION ────────────────────────────────────────────

    # A: High score + passing RR → Valid entry
    if score >= MIN_SCORE_FOR_ENTRY and rr_result["passes"]:
        quality_label = _quality_label(score, rr_val)
        return {
            "decision": "VALID SETUP — ENTRY POSSIBLE",
            "reason": (
                f"Score {score}/100, {rr_result['label']} ({rr_val}R). "
                f"{rr_result['recommendation']}. "
                f"Structure: {structure}. Zone: {premium_discount}."
            ),
            "quality": quality_label,
            "score_gate": "PASSED",
            "rr_gate": "PASSED"
        }

    # B: High score + poor current RR + good retracement RR → Wait
    if score >= MIN_SCORE_FOR_ENTRY and not rr_result["passes"] and ret_rr >= 1.5:
        return {
            "decision": "WAIT FOR RETRACEMENT",
            "reason": (
                f"Setup quality is strong (score {score}/100) but current entry RR is poor ({rr_val}R). "
                f"Retracement entry offers {ret_rr}R. Wait for price to pull back to the OB/FVG zone."
            ),
            "quality": "WAIT",
            "score_gate": "PASSED",
            "rr_gate": "WAITING FOR RETRACEMENT"
        }

    # C: Moderate score + good retracement → Watchlist
    if score >= MIN_SCORE_FOR_WATCHLIST and ret_rr >= 1.5:
        return {
            "decision": "WATCHLIST — WAIT FOR RETRACEMENT",
            "reason": (
                f"Setup on radar (score {score}/100). Current entry not ideal ({rr_val}R). "
                f"If price retraces to OB/FVG zone, retracement RR improves to {ret_rr}R. Monitor closely."
            ),
            "quality": "WATCHLIST",
            "score_gate": "PARTIAL",
            "rr_gate": "RETRACEMENT ONLY"
        }

    # D: Killzone active but setup incomplete → Alert
    if killzone in ("SILVER BULLET WINDOW", "LONDON KILLZONE", "NY AM KILLZONE"):
        if score >= MIN_SCORE_FOR_WATCHLIST:
            return {
                "decision": "KILLZONE ACTIVE — MONITOR FOR ENTRY",
                "reason": (
                    f"Active killzone ({killzone}) with score {score}/100. "
                    f"Setup not yet confirmed but timing is prime. "
                    f"Watch for CRT sweep + FVG/OB to form entry signal."
                ),
                "quality": "MONITOR",
                "score_gate": "PARTIAL",
                "rr_gate": "NOT MET"
            }

    # E: Default fallback
    return {
        "decision": "NO TRADE",
        "reason": (
            f"Setup does not meet entry criteria. "
            f"Score: {score}/100 (need {MIN_SCORE_FOR_ENTRY}+). "
            f"RR: {rr_val}R (need 1.0+ or retracement {ret_rr}R need 1.5+). "
            f"Review confluence and wait for better setup."
        ),
        "quality": "LOW",
        "score_gate": "FAILED" if score < MIN_SCORE_FOR_ENTRY else "PASSED",
        "rr_gate": "FAILED"
    }


def _quality_label(score: float, rr: float) -> str:
    """Combined quality label for dashboard display."""
    if score >= 90 and rr >= 3.0:
        return "A+ ELITE"
    elif score >= 80 and rr >= 2.0:
        return "A STRONG"
    elif score >= 70 and rr >= 1.5:
        return "B ACCEPTABLE"
    return "B MARGINAL"
