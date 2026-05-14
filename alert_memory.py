import json
import os
from datetime import datetime, timedelta

MEMORY_FILE = "alert_memory.json"


def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}

    with open(MEMORY_FILE, "r") as file:
        return json.load(file)


def save_memory(memory):
    with open(MEMORY_FILE, "w") as file:
        json.dump(memory, file, indent=4)


def can_send_alert(symbol, setup_key, cooldown_minutes=60):
    memory = load_memory()

    alert_id = f"{symbol}_{setup_key}"

    now = datetime.now()

    if alert_id in memory:
        last_time = datetime.fromisoformat(memory[alert_id])

        if now - last_time < timedelta(minutes=cooldown_minutes):
            return False

    memory[alert_id] = now.isoformat()
    save_memory(memory)

    return True