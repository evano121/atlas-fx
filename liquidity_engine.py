import os
import requests
import pandas as pd
from fvg_engine import detect_fvg
from dotenv import load_dotenv
from orderblock_engine import detect_order_block
from market_structure import detect_market_structure
from crt_engine import detect_crt
from trade_plan_engine import build_trade_plan
load_dotenv()

API_KEY = os.getenv("TWELVE_API_KEY")


def get_candles(symbol):
    url = (
        f"https://api.twelvedata.com/time_series"
        f"?symbol={symbol}"
        f"&interval=15min"
        f"&outputsize=20"
        f"&apikey={API_KEY}"
    )

    data = requests.get(url).json()

    if "values" not in data:
        print(f"ERROR for {symbol}: {data}")
        return None

    candles = pd.DataFrame(data["values"])

    candles["open"] = candles["open"].astype(float)
    candles["high"] = candles["high"].astype(float)
    candles["low"] = candles["low"].astype(float)
    candles["close"] = candles["close"].astype(float)

    return candles


def analyze_liquidity(symbol):
    candles = get_candles(symbol)

    if candles is None:
        return {
            "symbol": symbol,
            "sweep": "DATA ERROR",
            "structure": "UNKNOWN",
            "crt": "UNKNOWN",
            "fvg": "UNKNOWN",
            "ob": "UNKNOWN"
        }

    latest = candles.iloc[0]
    previous = candles.iloc[1:10]

    previous_high = previous["high"].max()
    previous_low = previous["low"].min()

    structure = detect_market_structure(candles)
    crt = detect_crt(candles)
    fvg = detect_fvg(candles)
    ob = detect_order_block(candles)
    

    if latest["high"] > previous_high:
        sweep = "BUY SIDE LIQUIDITY TAKEN"
    elif latest["low"] < previous_low:
        sweep = "SELL SIDE LIQUIDITY TAKEN"
    else:
        sweep = "NO SWEEP"
    
    trade_plan = build_trade_plan(candles, structure, sweep, crt, fvg, ob)
    return {
        "symbol": symbol,
        "sweep": sweep,
        "structure": structure,
        "crt": crt,
        "fvg": fvg,
        "ob": ob,
        "trade_plan": trade_plan
    }


def detect_liquidity_sweep(symbol):
    result = analyze_liquidity(symbol)
    return result["sweep"]


if __name__ == "__main__":
    result = analyze_liquidity("XAU/USD")

    print(f"Symbol: {result['symbol']}")
    print(f"Market Structure: {result['structure']}")
    print(f"CRT: {result['crt']}")
    print(f"Sweep: {result['sweep']}")