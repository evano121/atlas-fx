from liquidity_engine import get_candles


def get_previous_day_levels(symbol):

    daily = get_candles(symbol, "1day")

    previous_day = daily.iloc[1]

    pdh = float(previous_day["high"])
    pdl = float(previous_day["low"])

    return {
        "PDH": pdh,
        "PDL": pdl
    }

def detect_pdh_pdl_sweep(current_price, pdh, pdl):

    if current_price > pdh:
        return "PDH SWEPT"

    if current_price < pdl:
        return "PDL SWEPT"

    return "INSIDE DAILY RANGE"