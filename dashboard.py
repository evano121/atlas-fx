from flask import Flask, render_template_string
import sqlite3
import pandas as pd

app = Flask(__name__)

DB_NAME = "atlas.db"


HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>ATLAS Dashboard</title>
    <meta http-equiv="refresh" content="15">
    <style>
        body {
            background: #0b0f19;
            color: #e5e7eb;
            font-family: Arial, sans-serif;
            padding: 30px;
        }

        h1 {
            color: #38bdf8;
            margin-bottom: 5px;
        }

        .subtitle {
            color: #9ca3af;
            margin-bottom: 30px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 25px;
        }

        .card {
            background: #111827;
            padding: 20px;
            border-radius: 14px;
            border: 1px solid #1f2937;
        }

        .metric {
            font-size: 28px;
            font-weight: bold;
            color: #38bdf8;
        }

        .label {
            color: #9ca3af;
            font-size: 14px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            background: #111827;
            border-radius: 14px;
            overflow: hidden;
            font-size: 13px;
        }

        th, td {
            padding: 10px;
            border-bottom: 1px solid #374151;
            text-align: left;
        }

        th {
            background: #1f2937;
            color: #93c5fd;
        }

        tr:hover {
            background: #1e293b;
        }

        .grade-Aplus {
            color: #22c55e;
            font-weight: bold;
        }

        .grade-A {
            color: #84cc16;
            font-weight: bold;
        }

        .grade-B {
            color: #facc15;
            font-weight: bold;
        }

        .grade-C {
            color: #f87171;
            font-weight: bold;
        }

        .decision-good {
            color: #22c55e;
            font-weight: bold;
        }

        .decision-watch {
            color: #facc15;
            font-weight: bold;
        }

        .decision-bad {
            color: #f87171;
            font-weight: bold;
        }

        .section-title {
            margin-top: 30px;
            color: #e5e7eb;
        }
    </style>
</head>
<body>

    <h1>ATLAS Private Trading Dashboard</h1>
    <p class="subtitle">Institutional-style scanner | Auto-refresh every 15 seconds</p>

    <div class="grid">
        <div class="card">
            <div class="metric">{{ total_setups }}</div>
            <div class="label">Total Setups Stored</div>
        </div>

        <div class="card">
            <div class="metric">{{ avg_score }}</div>
            <div class="label">Average Score</div>
        </div>

        <div class="card">
            <div class="metric">{{ avg_rr }}</div>
            <div class="label">Average RR</div>
        </div>

        <div class="card">
            <div class="metric">{{ aplus_count }}</div>
            <div class="label">A+ Setups</div>
        </div>
    </div>

    <div class="card">
        <h2>Latest / Best Setup Full Details</h2>
        {{ best_setup | safe }}
    </div>

    <h2 class="section-title">Latest Market Scans</h2>
    <div class="card">
        {{ table | safe }}
    </div>

</body>
</html>
"""


def load_data():
    conn = sqlite3.connect(DB_NAME)

    query = """
    SELECT *
    FROM setups
    WHERE score <= 100
    ORDER BY id DESC
    LIMIT 100
    """

    df = pd.read_sql(query, conn)
    conn.close()

    return df


def style_grade(value):
    if value == "A+":
        return '<span class="grade-Aplus">A+</span>'
    if value == "A":
        return '<span class="grade-A">A</span>'
    if value == "B":
        return '<span class="grade-B">B</span>'
    return '<span class="grade-C">C</span>'


def make_table(df):
    if df.empty:
        return "<p>No setups saved yet.</p>"

    display_cols = [
        "timestamp",
        "pair_name",
        "session",
        "killzone",
        "news_risk",
        "sweep",
        "structure",
        "crt",
        "fvg",
        "ob_type",
        "score",
        "grade",
        "direction",
        "entry",
        "stop_loss",
        "tp1",
        "tp2",
        "rr"
    ]

    df = df[display_cols].copy()

    df["grade"] = df["grade"].apply(style_grade)

    return df.to_html(index=False, escape=False)


def get_best_setup(df):
    if df.empty:
        return "<p>No setup yet.</p>"

    df["rr_numeric"] = pd.to_numeric(df["rr"], errors="coerce")

    valid_df = df[
        (df["score"] <= 100) &
        (df["rr_numeric"] >= 1)
    ]

    if valid_df.empty:
        latest = df.iloc[0]
    else:
        latest = valid_df.sort_values(
            by=["score", "rr_numeric"],
            ascending=False
        ).iloc[0]

    return f"""
    <p><strong>Timestamp:</strong> {latest.get('timestamp')}</p>
    <p><strong>Pair:</strong> {latest.get('pair_name')}</p>
    <p><strong>Timeframe:</strong> {latest.get('timeframe', '15M')}</p>
    <p><strong>Session:</strong> {latest.get('session')}</p>
    <p><strong>Killzone:</strong> {latest.get('killzone')}</p>
    <p><strong>News Risk:</strong> {latest.get('news_risk')}</p>

    <hr>

    <p><strong>Sweep:</strong> {latest.get('sweep')}</p>
    <p><strong>Structure:</strong> {latest.get('structure')}</p>
    <p><strong>CRT:</strong> {latest.get('crt')}</p>
    <p><strong>FVG:</strong> {latest.get('fvg')}</p>
    <p><strong>Order Block:</strong> {latest.get('ob_type')}</p>

    <hr>

    <p><strong>Grade:</strong> {style_grade(latest.get('grade'))}</p>
    <p><strong>Score:</strong> {latest.get('score')}/100</p>
    <p><strong>Direction:</strong> {latest.get('direction')}</p>

    <hr>

    <p><strong>Entry:</strong> {latest.get('entry')}</p>
    <p><strong>SL:</strong> {latest.get('stop_loss')}</p>
    <p><strong>TP1:</strong> {latest.get('tp1')}</p>
    <p><strong>TP2:</strong> {latest.get('tp2')}</p>
    <p><strong>RR:</strong> {latest.get('rr')}</p>
    """


@app.route("/")
def home():
    df = load_data()

    if df.empty:
        total_setups = 0
        avg_score = 0
        avg_rr = 0
        aplus_count = 0
    else:
        total_setups = len(df)
        avg_score = round(df["score"].mean(), 2)

        df["rr_numeric"] = pd.to_numeric(df["rr"], errors="coerce")
        avg_rr = round(df["rr_numeric"].mean(), 2)

        aplus_count = len(df[df["grade"] == "A+"])

    table = make_table(df)
    best_setup = get_best_setup(df)

    return render_template_string(
        HTML,
        total_setups=total_setups,
        avg_score=avg_score,
        avg_rr=avg_rr,
        aplus_count=aplus_count,
        table=table,
        best_setup=best_setup
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)