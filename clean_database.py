import sqlite3

conn = sqlite3.connect("atlas.db")

cursor = conn.cursor()

cursor.execute("""
DELETE FROM setups
WHERE score > 100
""")

conn.commit()
conn.close()

print("Old invalid setups removed.")