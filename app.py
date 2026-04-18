import sqlite3
from pathlib import Path
from datetime import datetime, date

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="Betting Dashboard", layout="wide")

DB_FILE = "bets.db"

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #09090b 0%, #111827 55%, #0f172a 100%);
    }

    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 1450px;
    }

    h1, h2, h3 {
        color: #f8fafc;
        letter-spacing: -0.02em;
    }

    div[data-testid="stMetric"] {
        background: rgba(17, 24, 39, 0.72);
        border: 1px solid rgba(148, 163, 184, 0.12);
        border-radius: 18px;
        padding: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.22);
    }

    div[data-testid="stMetricLabel"] {
        color: #94a3b8;
        font-size: 0.9rem;
    }

    div[data-testid="stMetricValue"] {
        color: #f8fafc;
        font-weight: 700;
    }

    .section-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #e2e8f0;
        margin-bottom: 0.6rem;
    }

    .subtle-text {
        color: #94a3b8;
        font-size: 0.95rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bets (
            bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            bet_date TEXT NOT NULL,
            bet_time TEXT,
            day_of_week TEXT,
            track TEXT,
            account TEXT,
            bookmaker TEXT,
            event TEXT,
            odds_taken REAL,
            exchange_odds REAL,
            bsp REAL,
            stake REAL,
            result TEXT,
            profit_loss REAL,
            clv_pct REAL,
            edge_pct REAL,
            notes TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def calculate_profit(odds_taken: float, stake: float, result: str) -> float:
    if result == "Win":
        return round((odds_taken - 1) * stake, 2)
    return round(-stake, 2)


def calculate_edge(odds_taken: float, exchange_odds: float):
    if pd.notna(exchange_odds) and exchange_odds > 0:
        return round((odds_taken / exchange_odds - 1) * 100, 2)
    return None


def calculate_clv(odds_taken: float, bsp: float):
    if pd.notna(bsp) and bsp > 0:
        return round((odds_taken / bsp - 1) * 100, 2)
    return None


def insert_bet(
    bet_date: date,
    bet_time: str,
    track: str,
    account: str,
    bookmaker: str,
    event: str,
    odds_taken: float,
    exchange_odds: float,
    bsp: float,
    stake: float,
    result: str,
    notes: str,
) -> None:
    day_of_week = pd.to_datetime(bet_date).day_name()
    profit_loss = calculate_profit(odds_taken, stake, result)
    clv_pct = calculate_clv(odds_taken, bsp)
    edge_pct = calculate_edge(odds_taken, exchange_odds)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO bets (
            bet_date, bet_time, day_of_week, track, account, bookmaker, event,
            odds_taken, exchange_odds, bsp, stake, result, profit_loss, clv_pct, edge_pct, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(bet_date),
            bet_time,
            day_of_week,
            track.strip(),
            account.strip(),
            bookmaker.strip(),
            event.strip(),
            odds_taken,
            exchange_odds,
            bsp,
            stake,
            result,
            profit_loss,
            clv_pct,
            edge_pct,
            notes.strip(),
        ),
    )
    conn.commit()
    conn.close()


def update_bet(
    bet_id: int,
    bet_date: date,
    bet_time: str,
    track: str,
    account: str,
    bookmaker: str,
    event: str,
    odds_taken: float,
    exchange_odds: float,
    bsp: float,
    stake: float,
    result: str,
    notes: str,
) -> None:
    day_of_week = pd.to_datetime(bet_date).day_name()
    profit_loss = calculate_profit(odds_taken, stake, result)
    clv_pct = calculate_clv(odds_taken, bsp)
    edge_pct = calculate_edge(odds_taken, exchange_odds)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE bets
        SET bet_date = ?, bet_time = ?, day_of_week = ?, track = ?, account = ?, bookmaker = ?,
            event = ?, odds_taken = ?, exchange_odds = ?, bsp = ?, stake = ?, result = ?,
            profit_loss = ?, clv_pct = ?, edge_pct = ?, notes = ?
        WHERE bet_id = ?
        """,
        (
            str(bet_date),
            bet_time,
            day_of_week,
            track.strip(),
            account.strip(),
            bookmaker.strip(),
            event.strip(),
            odds_taken,
            exchange_odds,
            bsp,
            stake,
            result,
            profit_loss,
            clv_pct,
            edge_pct,
            notes.strip(),
            bet_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_bet(bet_id: int) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM bets WHERE bet_id = ?", (bet_id,))
    conn.commit()
    conn.close()


def delete_last_bet() -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM bets
        WHERE bet_id = (
            SELECT bet_id
            FROM bets
            ORDER BY bet_date DESC, bet_time DESC, bet_id DESC
            LIMIT 1
        )
        """
    )
    conn.commit()
    conn.close()


def load_data() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        """
        SELECT
            bet_id AS "Bet ID",
            bet_date AS "Date",
            bet_time AS "Time",
            day_of_week AS "Day of Week",
            track AS "Track",
            account AS "Account",
            bookmaker AS "Bookmaker",
            event AS "Event",
            odds_taken AS "Odds Taken",
            exchange_odds AS "Exchange Odds",
            bsp AS "BSP",
            stake AS "Stake",
            result AS "Result",
            profit_loss AS "Profit/Loss",
            clv_pct AS "CLV %",
            edge_pct AS "Edge %",
            notes AS "Notes"
        FROM bets
        ORDER BY bet_date ASC, bet_time ASC, bet_id ASC
        """,
        conn,
    )
    conn.close()

    if df.empty:
        return pd.DataFrame(
            columns=[
                "Bet ID", "Date", "Time", "Day of Week", "Track", "Account", "Bookmaker",
                "Event", "Odds Taken", "Exchange Odds", "BSP", "Stake", "Result",
                "Profit/Loss", "CLV %", "Edge %", "Notes"
            ]
        )

    # force proper types
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Stake"] = pd.to_numeric(df["Stake"], errors="coerce").fillna(0)
    df["Profit/Loss"] = pd.to_numeric(df["Profit/Loss"], errors="coerce").fillna(0)
    df["Odds Taken"] = pd.to_numeric(df["Odds Taken"], errors="coerce")
    df["Exchange Odds"] = pd.to_numeric(df["Exchange Odds"], errors="coerce")
    df["BSP"] = pd.to_numeric(df["BSP"], errors="coerce")
    df["CLV %"] = pd.to_numeric(df["CLV %"], errors="coerce")
    df["Edge %"] = pd.to_numeric(df["Edge %"], errors="coerce")

    for col in ["Day of Week", "Track", "Account", "Bookmaker", "Event", "Result", "Notes", "Time"]:
        df[col] = df[col].fillna("").astype(str)

    # remove bad dates
    df = df.dropna(subset=["Date"]).copy()

    # rebuild day name from actual date
    df["Day of Week"] = df["Date"].dt.day_name()

    df = df.sort_values(["Date", "Time", "Bet ID"]).reset_index(drop=True)
    df["Cumulative P/L"] = df["Profit/Loss"].cumsum()
    return df

    if df.empty:
        return pd.DataFrame(
            columns=[
                "Bet ID", "Date", "Time", "Day of Week", "Track", "Account", "Bookmaker",
                "Event", "Odds Taken", "Exchange Odds", "BSP", "Stake", "Result",
                "Profit/Loss", "CLV %", "Edge %", "Notes"
            ]
        )

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Stake"] = pd.to_numeric(df["Stake"], errors="coerce").fillna(0)
    df["Profit/Loss"] = pd.to_numeric(df["Profit/Loss"], errors="coerce").fillna(0)
    df["Odds Taken"] = pd.to_numeric(df["Odds Taken"], errors="coerce")
    df["Exchange Odds"] = pd.to_numeric(df["Exchange Odds"], errors="coerce")
    df["BSP"] = pd.to_numeric(df["BSP"], errors="coerce")
    df["CLV %"] = pd.to_numeric(df["CLV %"], errors="coerce")
    df["Edge %"] = pd.to_numeric(df["Edge %"], errors="coerce")

    for col in ["Day of Week", "Track", "Account", "Bookmaker", "Event", "Result", "Notes", "Time"]:
        df[col] = df[col].fillna("").astype(str)

    df = df.dropna(subset=["Date"]).sort_values(["Date", "Time", "Bet ID"]).reset_index(drop=True)
    df["Cumulative P/L"] = df["Profit/Loss"].cumsum()
    return df


def format_bet_label(row: pd.Series) -> str:
    bet_date = row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "No Date"
    return (
        f'#{int(row["Bet ID"])} | {bet_date} {row["Time"]} | '
        f'{row["Bookmaker"]} | {row["Track"]} | {row["Event"]} | '
        f'{row["Result"]} | £{row["Profit/Loss"]:.2f}'
    )


init_db()
df = load_data()

st.sidebar.header("Add New Bet")

with st.sidebar.form("new_bet_form", clear_on_submit=False):
    bet_date = st.date_input("Date", value=date.today())
    bet_time = st.time_input("Time", value=datetime.now().time().replace(second=0, microsecond=0))
    track = st.text_input("Track", value="")
    account = st.text_input("Account", value="")
    bookmaker = st.text_input("Bookmaker", value="")
    event = st.text_input("Event", value="")
    odds_taken = st.number_input("Odds Taken", min_value=1.01, value=2.00, step=0.01, format="%.2f")
    exchange_odds = st.number_input("Exchange Odds", min_value=1.01, value=1.80, step=0.01, format="%.2f")
    bsp = st.number_input("BSP", min_value=1.01, value=1.90, step=0.01, format="%.2f")
    stake = st.number_input("Stake (£)", min_value=0.0, value=50.0, step=1.0, format="%.2f")
    result = st.selectbox("Result", ["Win", "Lose"])
    notes = st.text_input("Notes", value="")
    submitted = st.form_submit_button("Save Bet")

if submitted:
    insert_bet(
        bet_date=bet_date,
        bet_time=bet_time.strftime("%H:%M:%S"),
        track=track,
        account=account,
        bookmaker=bookmaker,
        event=event,
        odds_taken=odds_taken,
        exchange_odds=exchange_odds,
        bsp=bsp,
        stake=stake,
        result=result,
        notes=notes,
    )
    st.sidebar.success("Bet saved.")
    st.rerun()

st.sidebar.header("Quick Actions")

if st.sidebar.button("Delete Last Bet"):
    if not df.empty:
        delete_last_bet()
        st.sidebar.success("Last bet deleted.")
        st.rerun()
    else:
        st.sidebar.warning("No bets to delete.")

st.sidebar.header("Edit / Delete Selected Bet")

if df.empty:
    selected_bet_id = None
    selected_row = None
else:
    selectable_df = df.sort_values(["Date", "Time", "Bet ID"], ascending=False).copy()
    labels = {format_bet_label(row): int(row["Bet ID"]) for _, row in selectable_df.iterrows()}
    selected_label = st.sidebar.selectbox("Select bet", list(labels.keys()))
    selected_bet_id = labels[selected_label]
    selected_row = df[df["Bet ID"] == selected_bet_id].iloc[0]

if selected_bet_id is not None:
    if st.sidebar.button("Delete Selected Bet"):
        delete_bet(selected_bet_id)
        st.sidebar.success("Selected bet deleted.")
        st.rerun()

    with st.sidebar.expander("Edit Selected Bet", expanded=False):
        with st.form("edit_bet_form"):
            edit_date = st.date_input("Edit Date", value=selected_row["Date"].date(), key="edit_date")

            try:
                edit_time_default = datetime.strptime(selected_row["Time"], "%H:%M:%S").time()
            except Exception:
                try:
                    edit_time_default = datetime.strptime(selected_row["Time"], "%H:%M").time()
                except Exception:
                    edit_time_default = datetime.now().time().replace(second=0, microsecond=0)

            edit_time = st.time_input("Edit Time", value=edit_time_default, key="edit_time")
            edit_track = st.text_input("Edit Track", value=selected_row["Track"], key="edit_track")
            edit_account = st.text_input("Edit Account", value=selected_row["Account"], key="edit_account")
            edit_bookmaker = st.text_input("Edit Bookmaker", value=selected_row["Bookmaker"], key="edit_bookmaker")
            edit_event = st.text_input("Edit Event", value=selected_row["Event"], key="edit_event")
            edit_odds = st.number_input(
                "Edit Odds Taken", min_value=1.01,
                value=float(selected_row["Odds Taken"]) if pd.notna(selected_row["Odds Taken"]) else 2.00,
                step=0.01, format="%.2f", key="edit_odds"
            )
            edit_exchange = st.number_input(
                "Edit Exchange Odds", min_value=1.01,
                value=float(selected_row["Exchange Odds"]) if pd.notna(selected_row["Exchange Odds"]) else 1.80,
                step=0.01, format="%.2f", key="edit_exchange"
            )
            edit_bsp = st.number_input(
                "Edit BSP", min_value=1.01,
                value=float(selected_row["BSP"]) if pd.notna(selected_row["BSP"]) else 1.90,
                step=0.01, format="%.2f", key="edit_bsp"
            )
            edit_stake = st.number_input(
                "Edit Stake (£)", min_value=0.0,
                value=float(selected_row["Stake"]) if pd.notna(selected_row["Stake"]) else 0.0,
                step=1.0, format="%.2f", key="edit_stake"
            )
            edit_result = st.selectbox(
                "Edit Result", ["Win", "Lose"],
                index=0 if selected_row["Result"] == "Win" else 1,
                key="edit_result"
            )
            edit_notes = st.text_input("Edit Notes", value=selected_row["Notes"], key="edit_notes")
            edit_submitted = st.form_submit_button("Save Changes")

        if edit_submitted:
            update_bet(
                bet_id=selected_bet_id,
                bet_date=edit_date,
                bet_time=edit_time.strftime("%H:%M:%S"),
                track=edit_track,
                account=edit_account,
                bookmaker=edit_bookmaker,
                event=edit_event,
                odds_taken=edit_odds,
                exchange_odds=edit_exchange,
                bsp=edit_bsp,
                stake=edit_stake,
                result=edit_result,
                notes=edit_notes,
            )
            st.success("Bet updated.")
            st.rerun()

st.sidebar.header("Filters")

starting_bankroll = st.sidebar.number_input(
    "Starting bankroll (£)",
    min_value=0.0,
    value=2000.0,
    step=100.0
)

min_date = df["Date"].min().date() if not df.empty else date.today()
max_date = df["Date"].max().date() if not df.empty else date.today()

date_range = st.sidebar.date_input(
    "Date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = min_date, max_date

bookmakers = ["All"] + sorted([x for x in df["Bookmaker"].dropna().unique().tolist() if x != ""])
accounts = ["All"] + sorted([x for x in df["Account"].dropna().unique().tolist() if x != ""])
results = ["All"] + sorted([x for x in df["Result"].dropna().unique().tolist() if x != ""])
tracks = ["All"] + sorted([x for x in df["Track"].dropna().unique().tolist() if x != ""])

weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
available_days = [d for d in weekday_order if d in df["Day of Week"].dropna().unique().tolist()]
days_of_week = ["All"] + available_days

selected_bookmaker = st.sidebar.selectbox("Bookmaker", bookmakers)
selected_account = st.sidebar.selectbox("Account", accounts)
selected_result = st.sidebar.selectbox("Result", results)
selected_track = st.sidebar.selectbox("Track", tracks)
selected_day = st.sidebar.selectbox("Day of Week", days_of_week)

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
df = df.dropna(subset=["Date"]).copy()

filtered_df = df[
    (df["Date"].dt.date >= start_date) &
    (df["Date"].dt.date <= end_date)
].copy()

if selected_bookmaker != "All":
    filtered_df = filtered_df[filtered_df["Bookmaker"] == selected_bookmaker]
if selected_account != "All":
    filtered_df = filtered_df[filtered_df["Account"] == selected_account]
if selected_result != "All":
    filtered_df = filtered_df[filtered_df["Result"] == selected_result]
if selected_track != "All":
    filtered_df = filtered_df[filtered_df["Track"] == selected_track]
if selected_day != "All":
    filtered_df = filtered_df[filtered_df["Day of Week"] == selected_day]

filtered_df = filtered_df.sort_values(["Date", "Time", "Bet ID"]).reset_index(drop=True)

if filtered_df.empty:
    st.warning("No bets match your filters.")
    st.stop()

filtered_df["Cumulative P/L"] = filtered_df["Profit/Loss"].cumsum()
filtered_df["Bankroll"] = starting_bankroll + filtered_df["Cumulative P/L"]
filtered_df["Day"] = filtered_df["Date"].dt.normalize()

daily_curve_df = filtered_df.groupby("Day", as_index=False).tail(1).copy()
daily_df = filtered_df.groupby("Day", as_index=False)["Profit/Loss"].sum().sort_values("Day").reset_index(drop=True)
daily_df["Rolling 7D P/L"] = daily_df["Profit/Loss"].rolling(7, min_periods=1).sum()

daily_curve_df["Peak"] = daily_curve_df["Cumulative P/L"].cummax()
daily_curve_df["Drawdown"] = daily_curve_df["Cumulative P/L"] - daily_curve_df["Peak"]

st.title("Greyhound Betting Dashboard")
st.markdown('<div class="subtle-text">Focused Performance layout</div>', unsafe_allow_html=True)

total_bets = len(filtered_df)
total_staked = filtered_df["Stake"].sum()
total_profit = filtered_df["Profit/Loss"].sum()
roi = (total_profit / total_staked * 100) if total_staked != 0 else 0
ending_bankroll = filtered_df["Bankroll"].iloc[-1]
avg_edge = filtered_df["Edge %"].mean() if "Edge %" in filtered_df.columns else None
avg_clv = filtered_df["CLV %"].mean() if "CLV %" in filtered_df.columns else None

k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Bets", f"{total_bets}")
k2.metric("Staked", f"£{total_staked:,.2f}")
k3.metric("P/L", f"£{total_profit:,.2f}")
k4.metric("ROI", f"{roi:.2f}%")
k5.metric("Bankroll", f"£{ending_bankroll:,.2f}")
k6.metric("Avg CLV", f"{avg_clv:.2f}%" if pd.notna(avg_clv) else "N/A")

st.markdown('<div class="section-title">Performance Curve</div>', unsafe_allow_html=True)

fig_cum = go.Figure()
fig_cum.add_trace(
    go.Scatter(
        x=daily_curve_df["Day"],
        y=daily_curve_df["Cumulative P/L"],
        mode="lines",
        line=dict(width=4, color="#60a5fa"),
        fill="tozeroy",
        fillcolor="rgba(96,165,250,0.12)",
        hovertemplate="%{x|%d %b %Y}<br>P/L: £%{y:,.2f}<extra></extra>",
    )
)
fig_cum.update_layout(
    template="plotly_dark",
    height=520,
    margin=dict(l=20, r=20, t=20, b=20),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(17,24,39,0.35)",
    font=dict(color="#e5e7eb"),
    xaxis=dict(showgrid=False, title=""),
    yaxis=dict(title="Cumulative P/L (£)", gridcolor="rgba(148,163,184,0.15)"),
)
st.plotly_chart(fig_cum, use_container_width=True)

row1, row2 = st.columns([1.15, 0.85])

with row1:
    st.markdown('<div class="section-title">Daily Profit / Loss</div>', unsafe_allow_html=True)

    fig_daily = go.Figure()
    fig_daily.add_trace(
        go.Bar(
            x=daily_df["Day"],
            y=daily_df["Profit/Loss"],
            marker_color=["#22c55e" if x >= 0 else "#ef4444" for x in daily_df["Profit/Loss"]],
            hovertemplate="%{x|%d %b %Y}<br>Daily P/L: £%{y:,.2f}<extra></extra>",
        )
    )
    fig_daily.update_layout(
        template="plotly_dark",
        height=330,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(17,24,39,0.35)",
        font=dict(color="#e5e7eb"),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(title="Daily P/L (£)", gridcolor="rgba(148,163,184,0.15)"),
    )
    st.plotly_chart(fig_daily, use_container_width=True)

with row2:
    st.markdown('<div class="section-title">Performance Summary</div>', unsafe_allow_html=True)

    pos_days = int((daily_df["Profit/Loss"] > 0).sum())
    neg_days = int((daily_df["Profit/Loss"] < 0).sum())
    avg_day = daily_df["Profit/Loss"].mean() if not daily_df.empty else 0
    max_day = daily_df["Profit/Loss"].max() if not daily_df.empty else 0
    min_day = daily_df["Profit/Loss"].min() if not daily_df.empty else 0
    max_drawdown = daily_curve_df["Drawdown"].min() if not daily_curve_df.empty else 0

    s1, s2 = st.columns(2)
    s1.metric("Winning Days", pos_days)
    s2.metric("Losing Days", neg_days)

    s3, s4 = st.columns(2)
    s3.metric("Avg Day", f"£{avg_day:,.2f}")
    s4.metric("Best Day", f"£{max_day:,.2f}")

    st.metric("Worst Day", f"£{min_day:,.2f}")
    st.metric("Max Drawdown", f"£{max_drawdown:,.2f}")
    st.metric("Avg Edge", f"{avg_edge:.2f}%" if pd.notna(avg_edge) else "N/A")

c1, c2 = st.columns(2)

with c1:
    st.markdown('<div class="section-title">Drawdown</div>', unsafe_allow_html=True)

    fig_dd = go.Figure()
    fig_dd.add_trace(
        go.Scatter(
            x=daily_curve_df["Day"],
            y=daily_curve_df["Drawdown"],
            mode="lines",
            line=dict(width=3, color="#f43f5e"),
            fill="tozeroy",
            fillcolor="rgba(244,63,94,0.14)",
            hovertemplate="%{x|%d %b %Y}<br>Drawdown: £%{y:,.2f}<extra></extra>",
        )
    )
    fig_dd.update_layout(
        template="plotly_dark",
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(17,24,39,0.35)",
        font=dict(color="#e5e7eb"),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(title="Drawdown (£)", gridcolor="rgba(148,163,184,0.15)"),
    )
    st.plotly_chart(fig_dd, use_container_width=True)

with c2:
    st.markdown('<div class="section-title">Rolling 7-Day P/L</div>', unsafe_allow_html=True)

    fig_roll = go.Figure()
    fig_roll.add_trace(
        go.Scatter(
            x=daily_df["Day"],
            y=daily_df["Rolling 7D P/L"],
            mode="lines",
            line=dict(width=3, color="#a78bfa"),
            fill="tozeroy",
            fillcolor="rgba(167,139,250,0.12)",
            hovertemplate="%{x|%d %b %Y}<br>7D P/L: £%{y:,.2f}<extra></extra>",
        )
    )
    fig_roll.update_layout(
        template="plotly_dark",
        height=320,
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(17,24,39,0.35)",
        font=dict(color="#e5e7eb"),
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(title="Rolling 7D P/L (£)", gridcolor="rgba(148,163,184,0.15)"),
    )
    st.plotly_chart(fig_roll, use_container_width=True)

st.markdown('<div class="section-title">Bet Log</div>', unsafe_allow_html=True)

display_columns = [
    col for col in [
        "Bet ID",
        "Date",
        "Day of Week",
        "Time",
        "Track",
        "Account",
        "Bookmaker",
        "Event",
        "Odds Taken",
        "Exchange Odds",
        "BSP",
        "Stake",
        "Result",
        "Profit/Loss",
        "CLV %",
        "Edge %",
        "Notes",
    ]
    if col in filtered_df.columns
]

table_df = filtered_df[display_columns].sort_values(["Date", "Time", "Bet ID"], ascending=False)
st.dataframe(table_df, use_container_width=True, hide_index=True)
