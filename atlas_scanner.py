import os
import requests
import time
from mtf_engine import get_mtf_bias
from database import initialize_database, save_setup
from datetime import datetime
from alert_memory import can_send_alert
from news_engine import detect_news_risk
from dotenv import load_dotenv
from decision_engine import make_final_decision
from killzone_engine import detect_killzone
from session_engine import get_current_session
from liquidity_engine import analyze_liquidity
from score_engine import score_setup
from pdh_pdl_engine import (
    get_previous_day_levels,
    detect_pdh_pdl_sweep
)

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
        trade_plan = analysis["trade_plan"]
        retracement = analysis["retracement"]
        

        try:
          daily_levels = get_previous_day_levels(symbol)

          pdh = float(daily_levels["PDH"])
          pdl = float(daily_levels["PDL"])

          current_price = float(trade_plan["entry"])

          daily_liquidity = detect_pdh_pdl_sweep(
          current_price,
           pdh,
           pdl
         )

        except:
          current_price = "N/A"
          pdh = "N/A"
          pdl = "N/A"
          daily_liquidity = "NO DAILY DATA"

    
        mtf = get_mtf_bias(symbol)
        mtf_alignment = mtf["aligned"]
        killzone = detect_killzone()
        news_risk = detect_news_risk()
        sweep = analysis["sweep"]
        structure = analysis["structure"]
        crt = analysis["crt"]
        fvg = analysis["fvg"]
        ob = analysis["ob"]
        expansion_state = analysis["expansion_state"]
        premium_discount = analysis["premium_discount"]
        session_liquidity = analysis["session_liquidity"]

        score, grade, reasons = score_setup(
         session=session,
         sweep=sweep,
         structure=structure,
         crt=crt,
         fvg=fvg,
         ob=ob,
         killzone=killzone,
         news_risk=news_risk,
         mtf_alignment=mtf_alignment,
         daily_liquidity=daily_liquidity,
         session_liquidity=session_liquidity["session_event"],
         rr=trade_plan["rr"]
         )
        
        try:
         rr_value = float(trade_plan["rr"])
        except:
         rr_value = 0

        try:
         retracement_rr = float(retracement["expected_rr"])
        except:
         retracement_rr = 0

        final_decision = make_final_decision(
         score,
         rr_value,
         retracement_rr,
         premium_discount["zone"],
         structure
         )

        

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
        print(f"15M STRUCTURE: {mtf['15m']}")
        print(f"1H STRUCTURE: {mtf['1h']}")
        print(f"MTF ALIGNMENT: {mtf_alignment}")
        print(f"PDH: {pdh}")
        print(f"PDL: {pdl}")
        print(f"DAILY LIQUIDITY: {daily_liquidity}")
        print(f"FVG: {fvg}")
        print(f"ORDER BLOCK: {ob}")
        print(f"EXPANSION STATE: {expansion_state}")
        print(f"PRICE ZONE: {premium_discount['zone']}")
        print(f"EQUILIBRIUM: {premium_discount['equilibrium']}")
        print(f"ASIA HIGH: {session_liquidity['asia_high']}")
        print(f"ASIA LOW: {session_liquidity['asia_low']}")
        print(f"SESSION LIQUIDITY: {session_liquidity['session_event']}")
        print(f"ACTION: {direction}")
        print(f"ENTRY: {trade_plan['entry']}")
        print(f"SL: {trade_plan['stop_loss']}")
        print(f"TP1: {trade_plan['tp1']}")
        print(f"TP2: {trade_plan['tp2']}")
        print(f"RR: {trade_plan['rr']}")
        print(f"RETRACE TYPE: {retracement['type']}")
        print(f"RETRACE ZONE: {retracement['zone']}")
        print(f"RETRACE ENTRY: {retracement['suggested_entry']}")
        print(f"RETRACE EXPECTED RR: {retracement['expected_rr']}")
        print(f"FINAL DECISION: {final_decision['decision']}")
        print(f"DECISION REASON: {final_decision['reason']}")

        rr_value = trade_plan["rr"]
        try:
         rr_value = float(rr_value)
        except:
         rr_value = 0


        if rr_value < 1:
         print("RR FILTER: FAILED — below 1:1")
        elif rr_value < 2:
         print("RR FILTER: ACCEPTABLE — between 1:1 and 2:1")
        else:
         print("RR FILTER: ELITE — 2:1 or better")

        if rr_value < 1:
         print("ENTRY QUALITY: BAD — price too close to target")
         print("ACTION DETAIL: Wait for retracement before entry")

        elif rr_value < 2:
         print("ENTRY QUALITY: ACCEPTABLE")

        else:
         print("ENTRY QUALITY: ELITE") 

        print("-" * 30)

        setup_data = {
         "timestamp": datetime.now().isoformat(),
         "pair_name": symbol,
         "session": session,
         "killzone": killzone,
         "news_risk": news_risk,

         "retracement_zone": retracement["zone"],
         "retracement_rr": retracement["expected_rr"],

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
         "rr": trade_plan["rr"],
         "final_decision": final_decision["decision"],
         }

        save_setup(setup_data)

        time.sleep(8)
        
        setup_key = f"{sweep}_{structure}_{crt}_{fvg}_{ob}"


        high_quality = (
          sweep != "NO SWEEP"
         and crt in ["BULLISH EXPANSION", "BEARISH EXPANSION"]
         and fvg != "NO FVG"
         and ob != "NO OB"
         and rr_value >= 1
         and mtf_alignment
         )

        alert_allowed = final_decision["decision"] in [
         "VALID SETUP — ENTRY POSSIBLE",
         "WAIT FOR RETRACEMENT",
         "WATCHLIST — WAIT FOR RETRACEMENT"
         ]

        safe_news = "HIGH NEWS RISK" not in news_risk

        if (
         high_quality
         and alert_allowed
         and score >= 80
         and safe_news
         and can_send_alert(symbol, setup_key)
         ):
        
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
RETRACE TYPE: {retracement['type']}
RETRACE ZONE: {retracement['zone']}
RETRACE ENTRY: {retracement['suggested_entry']}
RETRACE EXPECTED RR: {retracement['expected_rr']}
FINAL DECISION: {final_decision['decision']}
REASON: {final_decision['reason']}

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