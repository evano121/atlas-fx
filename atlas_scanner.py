import os
import requests
import time
from database import initialize_database, save_setup
from datetime import datetime
from alert_memory import can_send_alert
from news_engine import detect_news_risk
from dotenv import load_dotenv
from killzone_engine import detect_killzone
from session_engine import get_current_session
from liquidity_engine import analyze_liquidity
from score_engine import score_setup

load_dotenv()
initialize_database()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = [

    # Majors
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "AUD/USD",
    "USD/CAD",
    "NZD/USD",

    # Crosses
    "EUR/JPY",
    "GBP/JPY",
    "EUR/GBP",

    # Metals
    "XAU/USD",
    "XAG/USD"
]


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(
        url,
        json={
            "chat_id": CHAT_ID,
            "text": message
        }
    )


def run_scan():
    session = get_current_session()

    print(f"\nATLAS SCAN | SESSION: {session}\n")

    for symbol in SYMBOLS:
        analysis = analyze_liquidity(symbol)
        killzone = detect_killzone()
        news_risk = detect_news_risk()
        sweep = analysis["sweep"]
        structure = analysis["structure"]
        crt = analysis["crt"]
        fvg = analysis["fvg"]
        ob = analysis["ob"]
        score, grade, reasons = score_setup(
         session=session,
         sweep=sweep,
         structure=structure,
         crt=crt,
         fvg=fvg,
         ob=ob,
         killzone=killzone,
         news_risk=news_risk
       )

        trade_plan = analysis["trade_plan"]

        direction = "WAIT"

        if structure == "BEARISH":
         direction = "WAIT FOR SELL SETUP"

        elif structure == "BULLISH":
         direction = "WAIT FOR BUY SETUP"

        print(f"PAIR: {symbol}")
        print(f"SESSION: {session}")
        print(f"KILLZONE: {killzone}")
        print(f"NEWS RISK: {news_risk}")
        print(f"SWEEP: {sweep}")
        print(f"STRUCTURE: {structure}")
        print(f"CRT: {crt}")
        print(f"SCORE: {score}/100")
        print(f"GRADE: {grade}")
        print(f"BIAS: {structure}")
        print(f"FVG: {fvg}")
        print(f"ORDER BLOCK: {ob}")
        print(f"ACTION: {direction}")
        print(f"ENTRY: {trade_plan['entry']}")
        print(f"SL: {trade_plan['stop_loss']}")
        print(f"TP1: {trade_plan['tp1']}")
        print(f"TP2: {trade_plan['tp2']}")
        print(f"RR: {trade_plan['rr']}")
        print("-" * 30)

        setup_data = {
         "timestamp": datetime.now().isoformat(),
         "pair_name": symbol,
         "session": session,
         "killzone": killzone,
         "news_risk": news_risk,

         "sweep": sweep,
         "structure": structure,
          "crt": crt,
          "fvg": fvg,
         "ob_type": ob,

         "score": score,
         "grade": grade,

         "direction": trade_plan["direction"],

         "entry": trade_plan["entry"],
         "stop_loss": trade_plan["stop_loss"],
         "tp1": trade_plan["tp1"],
         "tp2": trade_plan["tp2"],
         "rr": trade_plan["rr"]
         }

        save_setup(setup_data)

        time.sleep(8)
        
        setup_key = f"{sweep}_{structure}_{crt}_{fvg}_{ob}"
        high_quality = (
         sweep != "NO SWEEP"
         and crt in ["BULLISH EXPANSION", "BEARISH EXPANSION"]
         and fvg != "NO FVG"
         and ob != "NO OB"
         )

        if high_quality and score >= 80 and can_send_alert(symbol, setup_key):
        
            message = f"""   
🚨 ATLAS {grade} SETUP

PAIR: {symbol}
SESSION: {session}
EVENT: {sweep}
STRUCTURE: {structure}
CRT: {crt}
KILLZONE: {killzone}
NEWS RISK: {news_risk}
TIMEFRAME: 15M
SCORE: {score}/100
BIAS: {structure}
ACTION: {direction}
ENTRY: {trade_plan['entry']}
SL: {trade_plan['stop_loss']}
TP1: {trade_plan['tp1']}
TP2: {trade_plan['tp2']}
RR: {trade_plan['rr']}

WHY:
{chr(10).join("- " + r for r in reasons)}

NEXT ACTION:
Wait for 15M–1H entry confirmation.
Use CRT / FVG / OB.
Risk only 0.5% to 1%.
Do not enter blindly.
"""
            send_telegram(message)


while True:

    try:
        run_scan()

    except Exception as e:
        print(f"ERROR: {e}")

    print("\nWaiting 5 minutes for next scan...\n")

    time.sleep(300)