import sqlite3
import pandas as pd

DB_NAME = "atlas.db"

conn = sqlite3.connect(DB_NAME)

query = """
SELECT
    id,
    pair_name,
    session,
    grade,
    score,
    rr
FROM setups
"""

df = pd.read_sql(query, conn)

conn.close()

print("\n===== ATLAS STATS =====\n")

print(df.tail(20))

print("\nAverage Score:")
print(df["score"].mean())

print("\nAverage RR:")
print(df["rr"].mean())

print("\nGrade Counts:")
print(df["grade"].value_counts())

print("\nBest Pairs:")
print(df.groupby("pair_name")["score"].mean())