import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, date
from pathlib import Path

st.set_page_config(page_title="Betting Dashboard", layout="wide")

FILE_NAME = "bets.xlsx"

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

def normalise_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.rename(columns={
        "Profit": "Profit/Loss",
        "Exchange odds": "Exchange Odds",
        "CLV": "CLV %",
        "Edge": "Edge %",
    })
    return df

def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    needed = [
        "Bet ID", "Date", "Time", "Day of Week", "Track", "Account", "Bookmaker",
        "Event", "Odds Taken", "Exchange Odds", "BSP", "Stake", "Result",
        "Profit/Loss", "CLV %", "Edge %", "Notes"
    ]
    for col in needed:
        if col not in df.columns:
            df[col] = None
    return df[needed]

def generate_bet_id(df: pd.DataFrame) -> int:
    if df.empty or df["Bet ID"].dropna().empty:
        return 1
    return int(pd.to_numeric(df["Bet ID"], errors="coerce").max()) + 1

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

def load_data() -> pd.DataFrame:
    path = Path(FILE_NAME)
    if not path.exists():
        empty = pd.DataFrame(columns=[
            "Bet ID", "Date", "Time", "Day of Week", "Track", "Account", "Bookmaker",
            "Event", "Odds Taken", "Exchange Odds", "BSP", "Stake", "Result",
            "Profit/Loss", "CLV %", "Edge %", "Notes"
        ])
        empty.to_excel(FILE_NAME, index=False)

    df = pd.read_excel(FILE_NAME)
    df = normalise_columns(df)
    df = ensure_required_columns(df)

    df["Bet ID"] = pd.to_numeric(df["Bet ID"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Stake"] = pd.to_numeric(df["Stake"], errors="coerce").fillna(0)
    df["Profit/Loss"] = pd.to_numeric(df["Profit/Loss"], errors="coerce").fillna(0)
    df["Odds Taken"] = pd.to_numeric(df["Odds Taken"], errors="coerce")
    df["Exchange Odds"] = pd.to_numeric(df["Exchange Odds"], errors="coerce")
    df["BSP"] = pd.to_numeric(df["BSP"], errors="coerce")
    df["CLV %"] = pd.to_numeric(df["CLV %"], errors="coerce")
    df["Edge %"] = pd.to_numeric(df["Edge %"], errors="coerce")

    for col in ["Day of Week", "Track", "Account", "Bookmaker", "Event", "Result", "Notes"]:
        df[col] = df[col].fillna("").astype(str)

    df["Time"] = df["Time"].fillna("").astype(str)
    df = df.dropna(subset=["Date"]).copy()
    df["Day of Week"] = df["Date"].dt.day_name()

    missing_mask = df["Bet ID"].isna()
    if missing_mask.any():
        next_id = 1
        existing = set(pd.to_numeric(df.loc[~missing_mask, "Bet ID"], errors="coerce").dropna().astype(int).tolist())
        new_ids = []
        for _ in range(missing_mask.sum()):
            while next_id in existing:
                next_id += 1
            new_ids.append(next_id)
            existing.add(next_id)
            next_id += 1
        df.loc[missing_mask, "Bet ID"] = new_ids

    df["Bet ID"] = df["Bet ID"].astype(int)
    df = df.sort_values(["Date", "Time", "Bet ID"]).reset_index(drop=True)
    df["Cumulative P/L"] = df["Profit/Loss"].cumsum()
    return df

def save_data(df: pd.DataFrame) -> None:
    output = df.copy()
    for col in ["Cumulative P/L", "Bankroll", "Day"]:
        if col in output.columns:
            output = output.drop(columns=[col])
    if "Date" in output.columns:
        output["Date"] = pd.to_datetime(output["Date"], errors="coerce")
        output["Day of Week"] = output["Date"].dt.day_name()
    output.to_excel(FILE_NAME, index=False)

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
    new_date = pd.to_datetime(bet_date)
    new_row = {
        "Bet ID": generate_bet_id(df),
        "Date": new_date,
        "Time": bet_time.strftime("%H:%M:%S"),
        "Day of Week": new_date.day_name(),
        "Track": track.strip(),
        "Account": account.strip(),
        "Bookmaker": bookmaker.strip(),
        "Event": event.strip(),
        "Odds Taken": odds_taken,
        "Exchange Odds": exchange_odds,
        "BSP": bsp,
        "Stake": stake,
        "Result": result,
        "Profit/Loss": calculate_profit(odds_taken, stake, result),
        "CLV %": calculate_clv(odds_taken, bsp),
        "Edge %": calculate_edge(odds_taken, exchange_odds),
        "Notes": notes.strip(),
    }
    updated_df = pd.concat([df.drop(columns=["Cumulative P/L"], errors="ignore"), pd.DataFrame([new_row])], ignore_index=True)
    save_data(updated_df)
    st.sidebar.success("Bet saved.")
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
            marker_color=[
                "#22c55e" if x >= 0 else "#ef4444"
                for x in daily_df["Profit/Loss"]
            ],
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
