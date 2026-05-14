from liquidity_engine import get_candles
from smt_engine import detect_smt

eurusd = get_candles("EUR/USD")
gbpusd = get_candles("GBP/USD")

result = detect_smt(eurusd, gbpusd)

print(f"SMT RESULT: {result}")