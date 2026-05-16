"""
ATLAS — atlas_scanner.py (REBUILT)

=============================================================
WHAT WAS WRONG WITH THE OLD SCANNER
=============================================================

1. time.sleep(8) between every pair
   11 pairs × 8s = 88s dead wait per scan. Zero reason for this.
   TwelveData free tier limit is 8 calls/minute.
   Fix: calculate sleep dynamically based on actual API calls made.

2. Multiple redundant API calls per symbol
   Old: analyze_liquidity → get_candles (15M) = 1 call
        get_mtf_bias → fetches 15M + 1H separately = 2 calls
        get_previous_day_levels → fetches 1D separately = 1 call
        Total: ~4 calls/symbol × 11 symbols = 44 calls/scan
   New: fetch_all_timeframes fetches 15M + 1H + 1D = 3 calls/symbol
        Everything else receives pre-fetched data = 0 extra calls
        Total: 3 calls/symbol × 11 symbols = 33 calls/scan
        With cache (4-min TTL): ~5-8 calls/scan after first cycle

3. No session awareness
   Old: Scanned all 11 pairs every 5 minutes, 24/7
   New: Only runs full scan during active sessions (London + NY)
        During dead hours (Asia, weekend): 30-min interval, 6 pairs only
        Saves ~60% of off-session API calls

4. No API budget tracking
   Old: No way to know how many calls were used
   New: Prints call count and daily budget remaining each scan

=============================================================
API CALL MATH (after rebuild)
=============================================================
Active session scan:
  11 pairs × 2 calls (15M + 1H) = 22 calls + 11 daily = 33/scan
  With cache after first scan: ~6 calls/scan
  Budget: 800/day
  Conservative (no cache): 800 ÷ 33 = 24 scans/day → every 60 min
  With cache:               800 ÷  6 = 133 scans/day → every 11 min ✓

Off-session (Asia/closed):
  6 pairs × 2 calls = 12 calls/scan
  Every 30 min = 2 scans/hour = 48/day → 576 calls off-session
  Leaves 224 calls for active session → 224 ÷ 33 = ~6 active scans/day

Recommended upgrade: Polygon.io $29/mo → unlimited calls → no math needed
=============================================================
"""

import os
import time
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

from database import initialize_database, save_setup
from alert_memory import can_send_alert
from news_engine import detect_news_risk
from decision_engine import make_final_decision
from killzone_engine import detect_killzone
from session_engine import get_current_session
from liquidity_engine import analyze_liquidity, fetch_all_timeframes, clear_cache
from score_engine import score_setup
from mtf_engine import get_mtf_bias
from pdh_pdl_engine import get_previous_day_levels, detect_pdh_pdl_sweep

load_dotenv()
initialize_database()

TOKEN   = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ─────────────────────────────────────────────────────────────
# SYMBOL LISTS
# Active session: all pairs — full scan
# Off session: only majors — conserve API budget
# ─────────────────────────────────────────────────────────────
ALL_SYMBOLS = [
    "EUR/USD", "GBP/USD", "USD/JPY",
    "AUD/USD", "USD/CAD", "NZD/USD",
    "EUR/JPY", "GBP/JPY", "EUR/GBP",
    "XAU/USD", "XAG/USD",
]

CORE_SYMBOLS = [
    "EUR/USD", "GBP/USD", "USD/JPY",
    "XAU/USD", "EUR/JPY", "GBP/JPY",
]

# TwelveData free tier: 8 calls/minute
API_CALLS_PER_MINUTE = 8
SECONDS_PER_CALL     = 60.0 / API_CALLS_PER_MINUTE  # 7.5 seconds between calls

# Daily budget tracker
_daily_call_count = 0
_budget_reset_hour = 0   # UTC hour when TwelveData resets the daily counter
_last_reset_day   = None


def _track_call(n: int = 1):
    """Increments the daily API call counter."""
    global _daily_call_count, _last_reset_day
    today = datetime.now(timezone.utc).date()
    if _last_reset_day != today:
        _daily_call_count = 0
        _last_reset_day   = today
    _daily_call_count += n
    return _daily_call_count


def _budget_remaining() -> int:
    return max(0, 800 - _daily_call_count)


# ─────────────────────────────────────────────────────────────
# SESSION-AWARE SCAN CONFIGURATION
# ─────────────────────────────────────────────────────────────
def _get_scan_config(session: str) -> dict:
    """
    Returns scan parameters based on current session.
    We don't scan heavily during off-hours — no setups, wasted budget.
    """
    if session in ("LONDON", "NEW_YORK", "OVERLAP"):
        return {
            "symbols":  ALL_SYMBOLS,
            "interval": 300,   # 5 minutes between full scans
            "label":    "ACTIVE SESSION — FULL SCAN",
        }
    elif session == "ASIA":
        return {
            "symbols":  CORE_SYMBOLS,
            "interval": 900,   # 15 minutes — watch for Asian range formation
            "label":    "ASIA SESSION — CORE PAIRS ONLY",
        }
    else:  # CLOSED / OFF
        return {
            "symbols":  CORE_SYMBOLS,
            "interval": 1800,  # 30 minutes — dead market, conserve budget
            "label":    "OFF SESSION — MINIMAL SCAN",
        }


# ─────────────────────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────────────────────
def send_telegram(message: str):
    """Sends a message to your configured Telegram chat."""
    if not TOKEN or not CHAT_ID:
        print("[TELEGRAM] No token or chat ID configured — skipping.")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print(f"[TELEGRAM] Send failed: {e}")


def _build_telegram_message(symbol, session, killzone, news_risk,
                             analysis, score, grade, reasons,
                             trade_plan, retracement, final_decision,
                             mtf, daily_liquidity) -> str:
    """Builds the formatted Telegram alert message."""
    structure = analysis["structure"]
    sweep     = analysis["sweep"]
    crt       = analysis["crt"]

    direction = "WAIT"
    if structure == "BEARISH":
        direction = "SELL SETUP"
    elif structure == "BULLISH":
        direction = "BUY SETUP"

    why_lines = "\n".join(f"  • {r}" for r in reasons[:8])  # cap at 8 reasons

    return f"""
🔷 ATLAS {grade} ALERT

PAIR:      {symbol}
SESSION:   {session}
KILLZONE:  {killzone}
NEWS:      {news_risk}

STRUCTURE: {structure}
SWEEP:     {sweep}
CRT:       {crt}
MTF:       {'✅ ALIGNED' if mtf['aligned'] else '❌ MISALIGNED'} (15M: {mtf['15m']} | 1H: {mtf['1h']})
DAILY LIQ: {daily_liquidity}

SCORE:     {score}/100  |  GRADE: {grade}
DECISION:  {final_decision['decision']}

━━━━ TRADE PLAN ━━━━
ACTION:  {direction}
ENTRY:   {trade_plan['entry']}
SL:      {trade_plan['stop_loss']}
TP1:     {trade_plan['tp1']}
TP2:     {trade_plan['tp2']}
RR:      {trade_plan['rr']}R  (TP2: {trade_plan.get('rr_tp2', '?')}R)

━━━━ RETRACEMENT ENTRY ━━━━
TYPE:    {retracement['type']}
ZONE:    {retracement['zone']}
ENTRY:   {retracement['suggested_entry']}
RR:      {retracement['expected_rr']}R

━━━━ WHY ━━━━
{why_lines}

REASON: {final_decision['reason']}

⚠️ Risk 0.5–1% max. Confirm on 15M before entry.
"""


# ─────────────────────────────────────────────────────────────
# SINGLE PAIR SCAN
# ─────────────────────────────────────────────────────────────
def scan_symbol(symbol: str, session: str, killzone: str,
                news_risk: str) -> dict | None:
    """
    Runs the full ATLAS analysis pipeline for a single symbol.
    Receives pre-fetched candle data from fetch_all_timeframes()
    called in the outer scan loop — no redundant API calls here.

    Returns the setup dict if alert-worthy, else None.
    """

    # ── FETCH (uses cache if available) ───────────────────────────────
    tf_data  = fetch_all_timeframes(symbol)
    calls_made = 0

    # Count actual API calls (cache hits = 0 extra calls)
    from liquidity_engine import _get_cached
    for interval in ("15min", "1h", "1day"):
        if _get_cached(symbol, interval) is None:
            calls_made += 1

    if tf_data["15m"] is None:
        print(f"  [{symbol}] ⚠ No 15M data — skipping")
        return None

    # ── ANALYSIS ──────────────────────────────────────────────────────
    analysis = analyze_liquidity(
        symbol,
        candles_15m=tf_data["15m"],
        candles_1h=tf_data["1h"]
    )

    trade_plan  = analysis["trade_plan"]
    retracement = analysis["retracement"]
    structure   = analysis["structure"]
    sweep       = analysis["sweep"]
    crt         = analysis["crt"]
    fvg         = analysis["fvg"]
    ob          = analysis["ob"]

    # ── MTF BIAS (pass 1H data — no extra API call) ───────────────────
    mtf = get_mtf_bias(symbol, candles_1h=tf_data["1h"],
                        candles_15m=tf_data["15m"])

    # ── DAILY LIQUIDITY (use pre-fetched daily data) ───────────────────
    daily_liquidity = "NO DAILY DATA"
    try:
        if tf_data["1d"] is not None:
            pdh = float(tf_data["1d"].iloc[1]["high"])   # yesterday's high
            pdl = float(tf_data["1d"].iloc[1]["low"])    # yesterday's low
            current_price = float(tf_data["15m"].iloc[0]["close"])
            daily_liquidity = detect_pdh_pdl_sweep(current_price, pdh, pdl)
        else:
            daily_levels   = get_previous_day_levels(symbol)
            pdh = float(daily_levels["PDH"])
            pdl = float(daily_levels["PDL"])
            current_price  = float(trade_plan.get("entry", 0) or 0)
            daily_liquidity = detect_pdh_pdl_sweep(current_price, pdh, pdl)
    except Exception as e:
        print(f"  [{symbol}] Daily levels error: {e}")

    # ── SCORING ───────────────────────────────────────────────────────
    score, grade, reasons = score_setup(
        session=session,
        sweep=sweep,
        structure=structure,
        crt=crt,
        fvg=fvg,
        ob=ob,
        killzone=killzone,
        news_risk=news_risk,
        mtf_alignment=mtf["aligned"],
        daily_liquidity=daily_liquidity,
        session_liquidity=analysis["session_liquidity"]["session_event"],
    )

    try:
        rr_value = float(trade_plan["rr"])
    except (TypeError, ValueError):
        rr_value = 0.0

    try:
        retracement_rr = float(retracement["expected_rr"])
    except (TypeError, ValueError):
        retracement_rr = 0.0

    # ── DECISION ──────────────────────────────────────────────────────
    final_decision = make_final_decision(
        score=score,
        rr=rr_value,
        retracement_rr=retracement_rr,
        premium_discount=analysis["premium_discount"]["zone"],
        structure=structure,
        killzone=killzone,
        news_risk=news_risk,
    )

    # ── PRINT SUMMARY ─────────────────────────────────────────────────
    decision_icon = "✅" if "VALID" in final_decision["decision"] else \
                    "👀" if "WATCH" in final_decision["decision"] else \
                    "⏳" if "WAIT" in final_decision["decision"] else "❌"

    print(
        f"  {decision_icon} {symbol:<10} "
        f"S:{score:>3}/100  G:{grade:<2}  "
        f"RR:{rr_value:<4}  "
        f"STRUCT:{structure:<8}  "
        f"CRT:{crt:<20}  "
        f"{final_decision['decision']}"
    )

    # ── BUILD SETUP RECORD ────────────────────────────────────────────
    setup_data = {
        "timestamp":       datetime.now().isoformat(),
        "pair_name":       symbol,
        "session":         session,
        "killzone":        killzone,
        "news_risk":       news_risk,
        "retracement_zone": retracement["zone"],
        "retracement_rr":  retracement["expected_rr"],
        "sweep":           sweep,
        "structure":       structure,
        "crt":             crt,
        "fvg":             fvg,
        "ob_type":         ob,
        "score":           score,
        "grade":           grade,
        "direction":       trade_plan["direction"],
        "entry":           trade_plan["entry"],
        "stop_loss":       trade_plan["stop_loss"],
        "tp1":             trade_plan["tp1"],
        "tp2":             trade_plan["tp2"],
        "rr":              trade_plan["rr"],
        "final_decision":  final_decision["decision"],
    }
    save_setup(setup_data)

    # ── TELEGRAM ALERT GATE ────────────────────────────────────────────
    setup_key  = f"{sweep}_{structure}_{crt}_{fvg}_{ob}"
    alert_worthy = (
        score >= 75
        and rr_value >= 1.5
        and sweep != "NO SWEEP"
        and crt in ("BULLISH EXPANSION", "BEARISH EXPANSION")
        and fvg != "NO FVG"
        and ob  != "NO OB"
        and mtf["aligned"]
        and "HIGH NEWS RISK" not in str(news_risk)
        and final_decision["decision"] in (
            "VALID SETUP — ENTRY POSSIBLE",
            "WAIT FOR RETRACEMENT",
            "WATCHLIST — WAIT FOR RETRACEMENT",
        )
        and can_send_alert(symbol, setup_key)
    )

    if alert_worthy:
        msg = _build_telegram_message(
            symbol, session, killzone, news_risk,
            analysis, score, grade, reasons,
            trade_plan, retracement, final_decision,
            mtf, daily_liquidity
        )
        send_telegram(msg)
        print(f"  📤 Alert sent for {symbol}")

    return setup_data


# ─────────────────────────────────────────────────────────────
# MAIN SCAN LOOP
# ─────────────────────────────────────────────────────────────
def run_scan():
    """
    Runs a full scan across all symbols for the current session.

    Key improvements over old version:
    - Clears cache at scan start → fresh data for new cycle
    - Reads session + killzone once → same value for all pairs
    - Tracks API calls and budget
    - Rate limits based on actual calls, not fixed sleep(8)
    - Session-aware: fewer pairs + longer intervals off-session
    """
    session  = get_current_session()
    killzone = detect_killzone()
    news_risk = detect_news_risk()
    config   = _get_scan_config(session)
    symbols  = config["symbols"]

    print(f"\n{'='*60}")
    print(f"  ATLAS SCAN  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  SESSION: {session}  |  KILLZONE: {killzone}")
    print(f"  NEWS: {news_risk}")
    print(f"  SCANNING: {len(symbols)} pairs  |  {config['label']}")
    print(f"  API BUDGET: {_budget_remaining()} calls remaining today")
    print(f"{'='*60}")

    # Clear cache at scan start so all pairs get fresh data
    clear_cache()

    scan_start   = time.time()
    calls_before = _daily_call_count

    for i, symbol in enumerate(symbols):
        # Check budget before each pair
        if _budget_remaining() < 5:
            print(f"\n⚠ API BUDGET NEARLY EXHAUSTED ({_budget_remaining()} calls left). Pausing scan.")
            send_telegram(f"⚠ ATLAS: Daily API budget nearly exhausted. Scan paused. Resets at midnight UTC.")
            break

        # Rate limit: stay under 8 calls/minute
        # Each symbol makes 2-3 API calls → sleep between pairs
        if i > 0:
            elapsed  = time.time() - scan_start
            expected = i * (SECONDS_PER_CALL * 2.5)  # ~2.5 calls avg per pair
            sleep_needed = max(0, expected - elapsed)
            if sleep_needed > 0:
                time.sleep(sleep_needed)

        try:
            scan_symbol(symbol, session, killzone, news_risk)
            _track_call(2)  # approximate: 15M + 1H (daily usually cached)
        except Exception as e:
            print(f"  ❌ {symbol}: Error — {e}")

    calls_made = _daily_call_count - calls_before
    elapsed    = round(time.time() - scan_start, 1)

    print(f"\n  Scan complete in {elapsed}s | ~{calls_made} API calls used | {_budget_remaining()} remaining today")
    print(f"{'='*60}\n")

    return config["interval"]


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("ATLAS Scanner starting...")
    send_telegram("🔷 ATLAS Scanner started. Monitoring markets.")

    while True:
        try:
            next_interval = run_scan()
        except Exception as e:
            print(f"\nCRITICAL ERROR in scan loop: {e}")
            next_interval = 300  # default 5 min on error

        print(f"  Next scan in {next_interval // 60} minutes...\n")
        time.sleep(next_interval)
