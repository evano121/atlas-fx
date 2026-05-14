import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TWELVE_API_KEY")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOLS = [
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "XAU/USD",
    "NAS100"
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


def get_price(symbol):

    url = (
        f"https://api.twelvedata.com/price"
        f"?symbol={symbol}"
        f"&apikey={API_KEY}"
    )

    response = requests.get(url).json()

    return response.get("price")


def scan():

    message = "ATLAS LIVE SCAN\n\n"

    for symbol in SYMBOLS:

        price = get_price(symbol)

        message += f"{symbol}: {price}\n"

    send_telegram(message)


scan()