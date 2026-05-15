import sqlite3

conn = sqlite3.connect("atlas.db")

cursor = conn.cursor()

try:
    cursor.execute("""
    ALTER TABLE setups
    ADD COLUMN outcome TEXT
    """)

    print("Outcome column added.")

except Exception as e:
    print(e)

try:
    cursor.execute("""
    ALTER TABLE setups
    ADD COLUMN profit REAL
    """)

    print("Profit column added.")

except Exception as e:
    print(e)

conn.commit()
conn.close()