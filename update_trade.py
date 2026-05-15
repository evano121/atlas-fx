import sqlite3

conn = sqlite3.connect("atlas.db")

cursor = conn.cursor()

trade_id = input("Trade ID: ")
outcome = input("Outcome (WIN / LOSS / BE): ")
profit = float(input("Profit amount: "))

cursor.execute("""
UPDATE setups
SET outcome = ?, profit = ?
WHERE id = ?
""", (outcome, profit, trade_id))

conn.commit()
conn.close()

print("Trade updated.")