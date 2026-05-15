def make_final_decision(score, rr, retracement_rr, premium_discount=None, structure=None):

    try:
        rr = float(rr)
    except:
        rr = 0

    try:
        retracement_rr = float(retracement_rr)
    except:
        retracement_rr = 0

    correct_zone = True

    if structure == "BEARISH" and premium_discount == "DISCOUNT":
        correct_zone = False

    if structure == "BULLISH" and premium_discount == "PREMIUM":
        correct_zone = False

    if not correct_zone:
        return {
            "decision": "WAIT — BAD PRICE LOCATION",
            "reason": "Bias is valid, but price is in the wrong premium/discount zone."
        }

    if score >= 80 and rr >= 1:
        return {
            "decision": "VALID SETUP — ENTRY POSSIBLE",
            "reason": "High score, acceptable RR, and correct price location."
        }

    if score >= 80 and rr < 1 and retracement_rr >= 1:
        return {
            "decision": "WAIT FOR RETRACEMENT",
            "reason": "Setup is strong, but current RR is weak. Retracement improves RR."
        }

    if retracement_rr >= 1 and rr < 1:
        return {
            "decision": "WATCHLIST — WAIT FOR RETRACEMENT",
            "reason": "Current entry RR is weak, but retracement entry offers acceptable RR."
        }

    return {
        "decision": "NO TRADE",
        "reason": "Setup does not meet quality, RR, or location requirements."
    }