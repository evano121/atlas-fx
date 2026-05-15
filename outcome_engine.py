"""
ATLAS — outcome_engine.py (NEW)

This is your #1 missing piece.
Without outcome tracking, ATLAS cannot:
  - Know if its signals actually work
  - Build win rate statistics
  - Identify which setups perform best
  - Feed data into adaptive scoring (future)

This engine:
  - Stores trade outcomes against ATLAS-generated setups
  - Calculates running win rate, expectancy, profit factor
  - Tracks performance by pair, session, setup type, grade
  - Integrates with SQLite (drop-in, no migration needed)
  - Provides data for dashboard and Telegram weekly summary
"""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional


DB_PATH = "atlas.db"


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────────────────────────────────────

def initialize_outcome_table():
    """
    Creates the trade_outcomes table if it doesn't exist.
    Safe to run multiple times — uses IF NOT EXISTS.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS trade_outcomes (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            setup_id          INTEGER,           -- links to setups table (optional)
            timestamp_opened  TEXT NOT NULL,
            timestamp_closed  TEXT,
            pair_name         TEXT NOT NULL,
            direction         TEXT,              -- LONG / SHORT
            session           TEXT,
            killzone          TEXT,
            structure         TEXT,
            setup_type        TEXT,              -- CRT+OB, FVG, Sweep, etc.
            grade             TEXT,              -- A+, A, B, C
            score             REAL,
            entry_price       REAL,
            stop_loss         REAL,
            tp1               REAL,
            tp2               REAL,
            rr_planned        REAL,              -- RR at entry
            exit_price        REAL,
            rr_achieved       REAL,              -- actual RR achieved
            pips_result       REAL,              -- pips gained/lost
            result            TEXT,              -- WIN / LOSS / BREAKEVEN / RUNNING
            notes             TEXT,
            created_at        TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# WRITE OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

def log_trade_open(
    pair_name: str,
    direction: str,
    entry_price: float,
    stop_loss: float,
    tp1: float,
    tp2: float,
    rr_planned: float,
    session: str = None,
    killzone: str = None,
    structure: str = None,
    setup_type: str = None,
    grade: str = None,
    score: float = None,
    setup_id: int = None,
    notes: str = None
) -> int:
    """
    Logs a new trade when it opens.
    Returns the outcome ID for later update when trade closes.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO trade_outcomes (
            setup_id, timestamp_opened, pair_name, direction,
            session, killzone, structure, setup_type, grade, score,
            entry_price, stop_loss, tp1, tp2, rr_planned,
            result, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        setup_id,
        datetime.now().isoformat(),
        pair_name, direction,
        session, killzone, structure, setup_type, grade, score,
        entry_price, stop_loss, tp1, tp2, rr_planned,
        "RUNNING", notes
    ))
    conn.commit()
    outcome_id = c.lastrowid
    conn.close()
    print(f"[OUTCOME] Trade opened: {pair_name} {direction} @ {entry_price} | ID: {outcome_id}")
    return outcome_id


def log_trade_close(
    outcome_id: int,
    exit_price: float,
    result: str,          # "WIN", "LOSS", "BREAKEVEN"
    notes: str = None
):
    """
    Updates an existing trade when it closes.
    Calculates actual pips and RR achieved.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Fetch the original trade to calculate actuals
    row = c.execute("""
        SELECT entry_price, stop_loss, direction, pair_name, rr_planned
        FROM trade_outcomes WHERE id = ?
    """, (outcome_id,)).fetchone()

    if not row:
        print(f"[OUTCOME] ERROR: No trade found with ID {outcome_id}")
        conn.close()
        return

    entry_price, stop_loss, direction, pair_name, rr_planned = row

    # Calculate pips (multiply by 10000 for standard pairs, 100 for JPY)
    multiplier = 100 if "JPY" in str(pair_name).upper() else 10000
    if direction == "LONG":
        pips_result = round((exit_price - entry_price) * multiplier, 1)
    else:
        pips_result = round((entry_price - exit_price) * multiplier, 1)

    # Calculate actual RR achieved
    risk_pips = abs(entry_price - stop_loss) * multiplier
    rr_achieved = round(pips_result / risk_pips, 2) if risk_pips > 0 else 0

    c.execute("""
        UPDATE trade_outcomes
        SET timestamp_closed = ?,
            exit_price = ?,
            pips_result = ?,
            rr_achieved = ?,
            result = ?,
            notes = COALESCE(notes || ' | ' || ?, notes, ?)
        WHERE id = ?
    """, (
        datetime.now().isoformat(),
        exit_price,
        pips_result,
        rr_achieved,
        result,
        notes, notes,
        outcome_id
    ))
    conn.commit()
    conn.close()
    print(f"[OUTCOME] Trade closed: ID {outcome_id} | {result} | {pips_result} pips | {rr_achieved}R")


# ─────────────────────────────────────────────────────────────────────────────
# READ / ANALYTICS OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

def get_overall_stats(days: int = 30) -> dict:
    """
    Returns overall performance statistics for the last N days.
    Used by dashboard and weekly Telegram summary.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    since = (datetime.now() - timedelta(days=days)).isoformat()

    rows = c.execute("""
        SELECT result, rr_achieved, pips_result, pair_name, session, grade, setup_type
        FROM trade_outcomes
        WHERE result IN ('WIN', 'LOSS', 'BREAKEVEN')
        AND timestamp_opened >= ?
    """, (since,)).fetchall()

    conn.close()

    if not rows:
        return {"error": "No completed trades in period", "days": days}

    total = len(rows)
    wins = [r for r in rows if r[0] == "WIN"]
    losses = [r for r in rows if r[0] == "LOSS"]
    breakevens = [r for r in rows if r[0] == "BREAKEVEN"]

    win_rate = round(len(wins) / total * 100, 1) if total > 0 else 0

    total_pips = sum(r[2] or 0 for r in rows)
    gross_win_rr = sum(r[1] or 0 for r in wins)
    gross_loss_rr = abs(sum(r[1] or 0 for r in losses))
    profit_factor = round(gross_win_rr / gross_loss_rr, 2) if gross_loss_rr > 0 else float("inf")

    avg_win_rr = round(gross_win_rr / len(wins), 2) if wins else 0
    avg_loss_rr = round(gross_loss_rr / len(losses), 2) if losses else 0
    expectancy = round((win_rate / 100) * avg_win_rr - (1 - win_rate / 100) * avg_loss_rr, 2)

    return {
        "period_days": days,
        "total_trades": total,
        "wins": len(wins),
        "losses": len(losses),
        "breakevens": len(breakevens),
        "win_rate_pct": win_rate,
        "total_pips": round(total_pips, 1),
        "profit_factor": profit_factor,
        "avg_win_rr": avg_win_rr,
        "avg_loss_rr": avg_loss_rr,
        "expectancy_r": expectancy,
        "gross_win_rr": round(gross_win_rr, 2),
        "gross_loss_rr": round(gross_loss_rr, 2),
    }


def get_stats_by_pair(days: int = 30) -> list:
    """Win rate and pips broken down by currency pair."""
    return _get_stats_by_field("pair_name", days)


def get_stats_by_session(days: int = 30) -> list:
    """Win rate broken down by session (London, NY, Asia, etc.)."""
    return _get_stats_by_field("session", days)


def get_stats_by_grade(days: int = 30) -> list:
    """Win rate broken down by ATLAS grade (A+, A, B, C)."""
    return _get_stats_by_field("grade", days)


def get_stats_by_setup(days: int = 30) -> list:
    """Win rate broken down by setup type."""
    return _get_stats_by_field("setup_type", days)


def _get_stats_by_field(field: str, days: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    since = (datetime.now() - timedelta(days=days)).isoformat()

    rows = c.execute(f"""
        SELECT {field}, result, rr_achieved, pips_result
        FROM trade_outcomes
        WHERE result IN ('WIN', 'LOSS', 'BREAKEVEN')
        AND timestamp_opened >= ?
    """, (since,)).fetchall()
    conn.close()

    grouped = {}
    for row in rows:
        key = row[0] or "UNKNOWN"
        if key not in grouped:
            grouped[key] = {"wins": 0, "losses": 0, "total": 0, "pips": 0, "rr": 0}
        grouped[key]["total"] += 1
        grouped[key]["pips"] += row[3] or 0
        grouped[key]["rr"] += row[2] or 0
        if row[1] == "WIN":
            grouped[key]["wins"] += 1
        elif row[1] == "LOSS":
            grouped[key]["losses"] += 1

    results = []
    for key, v in grouped.items():
        wr = round(v["wins"] / v["total"] * 100, 1) if v["total"] > 0 else 0
        results.append({
            "label": key,
            "total": v["total"],
            "wins": v["wins"],
            "losses": v["losses"],
            "win_rate_pct": wr,
            "total_pips": round(v["pips"], 1),
            "avg_rr": round(v["rr"] / v["total"], 2) if v["total"] > 0 else 0
        })

    return sorted(results, key=lambda x: x["win_rate_pct"], reverse=True)


def get_recent_trades(limit: int = 20) -> list:
    """Returns the most recent completed trades for dashboard display."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("""
        SELECT id, timestamp_opened, pair_name, direction, grade,
               setup_type, session, entry_price, exit_price,
               rr_planned, rr_achieved, pips_result, result, notes
        FROM trade_outcomes
        WHERE result IN ('WIN', 'LOSS', 'BREAKEVEN', 'RUNNING')
        ORDER BY timestamp_opened DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()

    keys = ["id", "opened", "pair", "direction", "grade", "setup_type",
            "session", "entry", "exit", "rr_planned", "rr_achieved",
            "pips", "result", "notes"]
    return [dict(zip(keys, r)) for r in rows]


def get_running_trades() -> list:
    """Returns all trades currently marked as RUNNING."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("""
        SELECT id, timestamp_opened, pair_name, direction, entry_price,
               stop_loss, tp1, tp2, rr_planned, grade
        FROM trade_outcomes
        WHERE result = 'RUNNING'
        ORDER BY timestamp_opened DESC
    """).fetchall()
    conn.close()
    keys = ["id", "opened", "pair", "direction", "entry", "sl", "tp1", "tp2", "rr_planned", "grade"]
    return [dict(zip(keys, r)) for r in rows]


def generate_weekly_summary() -> str:
    """
    Generates a formatted Telegram-ready weekly performance summary.
    Call this every Sunday or on demand.
    """
    stats = get_overall_stats(days=7)
    by_pair = get_stats_by_pair(days=7)
    by_session = get_stats_by_session(days=7)

    if "error" in stats:
        return "📊 ATLAS WEEKLY SUMMARY\n\nNo completed trades this week."

    best_pair = by_pair[0] if by_pair else {"label": "N/A", "win_rate_pct": 0}
    best_session = by_session[0] if by_session else {"label": "N/A", "win_rate_pct": 0}

    summary = f"""
📊 ATLAS WEEKLY PERFORMANCE REPORT

Period: Last 7 days
Total Trades: {stats['total_trades']}
Wins: {stats['wins']} | Losses: {stats['losses']} | BE: {stats['breakevens']}

Win Rate: {stats['win_rate_pct']}%
Profit Factor: {stats['profit_factor']}x
Expectancy: {stats['expectancy_r']}R per trade
Total Pips: {stats['total_pips']}

Best Pair: {best_pair['label']} ({best_pair['win_rate_pct']}% WR)
Best Session: {best_session['label']} ({best_session['win_rate_pct']}% WR)

Avg Win: {stats['avg_win_rr']}R
Avg Loss: {stats['avg_loss_rr']}R

━━━━━━━━━━━━━━━━━━━━━━━━━━━
ATLAS | Institutional Intelligence
"""
    return summary.strip()


# Run table initialization on import
initialize_outcome_table()
