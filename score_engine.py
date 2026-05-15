def score_setup(
    session,
    sweep,
    structure=None,
    rr=None,
    crt=None,
    fvg=None,
    ob=None,
    killzone=None,
    news_risk=None,
    mtf_alignment=False,
    daily_liquidity=None,
    session_liquidity=None
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
    if "HIGH NEWS RISK" in str(news_risk):
      score -= 40
      reasons.append(f"High-impact news risk detected: {news_risk}")

    elif news_risk == "LOW NEWS RISK":
      score += 5
      reasons.append("No major news risk")

    # Multi-timeframe alignment
    if mtf_alignment:
        score += 20
        reasons.append("15M and 1H aligned") 

     # Daily liquidity
    if daily_liquidity in ["PDH SWEPT", "PDL SWEPT"]:
        score += 15
        reasons.append(f"Daily liquidity event: {daily_liquidity}")  
    if session_liquidity in ["ASIA HIGH SWEPT", "ASIA LOW SWEPT"]:
        score += 15
        reasons.append(f"Session liquidity event: {session_liquidity}")

    # Ranging market penalty
    if structure == "RANGING":
        score -= 25
        reasons.append("Ranging market penalty")

    # No sweep penalty
    if sweep == "NO SWEEP":
        score -= 15
        reasons.append("No liquidity sweep")

    # No FVG and no OB penalty
    if fvg == "NO FVG" and ob == "NO OB":
        score -= 40
        reasons.append("No FVG or order block confirmation")

    # RR penalty
    try:
        rr_value = float(rr)
    except:
        rr_value = 0

    if rr_value < 1:
        score -= 80
        reasons.append("Poor RR")

    elif rr_value < 2:
        score -= 25
        reasons.append("Average RR")    

    score = max(score, 0)
    score = min(score, 100)     

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