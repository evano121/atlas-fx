import sqlite3

DB_NAME = "atlas.db"


def initialize_database():

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS setups (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        timestamp TEXT,
        pair_name TEXT,
        session TEXT,
        killzone TEXT,
        news_risk TEXT,

        sweep TEXT,
        structure TEXT,
        crt TEXT,
        fvg TEXT,
        ob_type TEXT,

        score INTEGER,
        grade TEXT,

        direction TEXT,

        entry REAL,
        stop_loss REAL,
        tp1 REAL,
        tp2 REAL,
        rr REAL
    )
    """)

    conn.commit()
    conn.close()


def save_setup(data):

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO setups (

        timestamp,
        pair_name,
        session,
        killzone,
        news_risk,

        sweep,
        structure,
        crt,
        fvg,
        ob_type,

        score,
        grade,

        direction,

        entry,
        stop_loss,
        tp1,
        tp2,
        rr

    )

    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        data["timestamp"],
        data["pair_name"],
        data["session"],
        data["killzone"],
        data["news_risk"],

        data["sweep"],
        data["structure"],
        data["crt"],
        data["fvg"],
        data["ob_type"],

        data["score"],
        data["grade"],

        data["direction"],

        data["entry"],
        data["stop_loss"],
        data["tp1"],
        data["tp2"],
        data["rr"]
    ))

    conn.commit()
    conn.close()