from liquidity_engine import get_candles
from market_structure import detect_market_structure


def get_mtf_bias(symbol):

    candles_15m = get_candles(symbol, "15min")
    candles_1h = get_candles(symbol, "1h")

    structure_15m = detect_market_structure(candles_15m)
    structure_1h = detect_market_structure(candles_1h)

    aligned = structure_15m == structure_1h

    return {
        "15m": structure_15m,
        "1h": structure_1h,
        "aligned": aligned
    }