def detect_smt(pair1_data, pair2_data):

    p1_latest_high = float(pair1_data.iloc[0]["high"])
    p1_previous_high = float(pair1_data.iloc[1]["high"])

    p2_latest_high = float(pair2_data.iloc[0]["high"])
    p2_previous_high = float(pair2_data.iloc[1]["high"])

    # Bearish SMT
    if (
        p1_latest_high > p1_previous_high
        and p2_latest_high <= p2_previous_high
    ):
        return "BEARISH SMT"

    # Bullish SMT
    if (
        p1_latest_high < p1_previous_high
        and p2_latest_high >= p2_previous_high
    ):
        return "BULLISH SMT"

    return "NO SMT"