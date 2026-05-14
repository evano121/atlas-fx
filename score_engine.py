def score_setup(
    session,
    sweep,
    structure=None,
    crt=None,
    fvg=None,
    ob=None,
    killzone=None,
    news_risk=None
):

    score = 0
    reasons = []

    # Liquidity
    if sweep != "NO SWEEP" and sweep != "DATA ERROR":
        score += 35
        reasons.append("Liquidity sweep detected")

    # Sessions
    if session in ["LONDON", "NEW_YORK"]:
        score += 25
        reasons.append("High-volume session")

    if session == "NEW_YORK":
        score += 10
        reasons.append("NY continuation/reversal potential")

    # CRT
    if crt in ["BULLISH EXPANSION", "BEARISH EXPANSION"]:
        score += 20
        reasons.append(f"CRT confirmation: {crt}")

    # Structure
    if structure in ["BULLISH", "BEARISH"]:
        score += 10
        reasons.append(f"Market structure: {structure}")

    # FVG
    if fvg in ["BULLISH FVG", "BEARISH FVG"]:
        score += 15
        reasons.append(f"FVG detected: {fvg}")

    # Order Block
    if ob in ["BULLISH OB", "BEARISH OB"]:
        score += 15
        reasons.append(f"Order block detected: {ob}")

    # Alignment bonus
    bearish_alignment = (
        structure == "BEARISH"
        and crt == "BEARISH EXPANSION"
        and fvg == "BEARISH FVG"
        and ob == "BEARISH OB"
    )

    bullish_alignment = (
        structure == "BULLISH"
        and crt == "BULLISH EXPANSION"
        and fvg == "BULLISH FVG"
        and ob == "BULLISH OB"
    )

    if bearish_alignment or bullish_alignment:
        score += 25
        reasons.append("Full institutional alignment")
     
    # Killzone
    if killzone in ["LONDON KILLZONE", "NY AM KILLZONE"]:
        score += 20
        reasons.append(f"Active killzone: {killzone}")

    if killzone == "SILVER BULLET WINDOW":
        score += 30
        reasons.append("Silver Bullet timing window")
    
    # News Risk
    if news_risk == "HIGH NEWS RISK":
        score -= 25
        reasons.append("High-impact news risk detected")

    elif news_risk == "LOW NEWS RISK":
        score += 5
        reasons.append("No major news risk")
    # Grade
    if score >= 90:
        grade = "A+"

    elif score >= 75:
        grade = "A"

    elif score >= 55:
        grade = "B"

    else:
        grade = "C"

    return score, grade, reasons