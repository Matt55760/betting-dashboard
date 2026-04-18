import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
from pathlib import Path

st.set_page_config(page_title="Betting Dashboard", layout="wide")

FILE_NAME = "bets.xlsx"

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    div[data-testid="stMetric"] {
        background-color: #111827;
        border: 1px solid #1f2937;
        padding: 15px;
        border-radius: 14px;
    }
    div[data-testid="stMetricLabel"] {
        color: #9ca3af;
    }
    div[data-testid="stMetricValue"] {
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Betting Dashboard")
st.caption("Profit, bankroll, and account performance")


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

    # derive day automatically from date
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

    # keep day derived from date for consistency
    if "Date" in output.columns:
        output["Date"] = pd.to_datetime(output["Date"], errors="coerce")
        output["Day of Week"] = output["Date"].dt.day_name()

    output.to_excel(FILE_NAME, index=False)


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


def format_bet_label(row: pd.Series) -> str:
    bet_date = row["Date"].strftime("%Y-%m-%d") if pd.notna(row["Date"]) else "No Date"
    return (
        f'#{int(row["Bet ID"])} | {bet_date} {row["Time"]} | '
        f'{row["Bookmaker"]} | {row["Track"]} | {row["Event"]} | '
        f'{row["Result"]} | £{row["Profit/Loss"]:.2f}'
    )


df = load_data()

# -------- SIDEBAR: ADD NEW BET --------
st.sidebar.header("Add New Bet")

with st.sidebar.form("new_bet_form", clear_on_submit=False):
    bet_date = st.date_input("Date", value=date.today(), key="add_date")
    bet_time = st.time_input(
        "Time",
        value=datetime.now().time().replace(second=0, microsecond=0),
        key="add_time"
    )
    track = st.text_input("Track", value="", key="add_track")
    account = st.text_input("Account", value="", key="add_account")
    bookmaker = st.text_input("Bookmaker", value="", key="add_bookmaker")
    event = st.text_input("Event", value="", key="add_event")

    odds_taken = st.number_input("Odds Taken", min_value=1.01, value=2.00, step=0.01, format="%.2f", key="add_odds")
    exchange_odds = st.number_input("Exchange Odds", min_value=1.01, value=1.80, step=0.01, format="%.2f", key="add_exch")
    bsp = st.number_input("BSP", min_value=1.01, value=1.90, step=0.01, format="%.2f", key="add_bsp")
    stake = st.number_input("Stake (£)", min_value=0.0, value=50.0, step=1.0, format="%.2f", key="add_stake")

    result = st.selectbox("Result", ["Win", "Lose"], key="add_result")
    notes = st.text_input("Notes", value="", key="add_notes")

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

# -------- SIDEBAR: DELETE LAST BET --------
st.sidebar.header("Quick Actions")

if st.sidebar.button("Delete Last Bet"):
    if not df.empty:
        latest_df = df.sort_values(["Date", "Time", "Bet ID"]).iloc[:-1].copy()
        save_data(latest_df)
        st.sidebar.success("Last bet deleted.")
        st.rerun()
    else:
        st.sidebar.warning("No bets to delete.")

# -------- SIDEBAR: SELECT BET --------
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
        updated_df = df[df["Bet ID"] != selected_bet_id].copy()
        save_data(updated_df)
        st.sidebar.success("Selected bet deleted.")
        st.rerun()

    with st.sidebar.expander("Edit Selected Bet", expanded=False):
        with st.form("edit_bet_form"):
            edit_date = st.date_input(
                "Edit Date",
                value=selected_row["Date"].date(),
                key="edit_date"
            )

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
                "Edit Odds Taken",
                min_value=1.01,
                value=float(selected_row["Odds Taken"]) if pd.notna(selected_row["Odds Taken"]) else 2.00,
                step=0.01,
                format="%.2f",
                key="edit_odds"
            )
            edit_exchange = st.number_input(
                "Edit Exchange Odds",
                min_value=1.01,
                value=float(selected_row["Exchange Odds"]) if pd.notna(selected_row["Exchange Odds"]) else 1.80,
                step=0.01,
                format="%.2f",
                key="edit_exchange"
            )
            edit_bsp = st.number_input(
                "Edit BSP",
                min_value=1.01,
                value=float(selected_row["BSP"]) if pd.notna(selected_row["BSP"]) else 1.90,
                step=0.01,
                format="%.2f",
                key="edit_bsp"
            )
            edit_stake = st.number_input(
                "Edit Stake (£)",
                min_value=0.0,
                value=float(selected_row["Stake"]) if pd.notna(selected_row["Stake"]) else 0.0,
                step=1.0,
                format="%.2f",
                key="edit_stake"
            )
            edit_result = st.selectbox(
                "Edit Result",
                ["Win", "Lose"],
                index=0 if selected_row["Result"] == "Win" else 1,
                key="edit_result"
            )
            edit_notes = st.text_input("Edit Notes", value=selected_row["Notes"], key="edit_notes")

            edit_submitted = st.form_submit_button("Save Changes")

        if edit_submitted:
            df_edit = df.drop(columns=["Cumulative P/L"], errors="ignore").copy()
            mask = df_edit["Bet ID"] == selected_bet_id
            new_edit_date = pd.to_datetime(edit_date)

            df_edit.loc[mask, "Date"] = new_edit_date
            df_edit.loc[mask, "Time"] = edit_time.strftime("%H:%M:%S")
            df_edit.loc[mask, "Day of Week"] = new_edit_date.day_name()
            df_edit.loc[mask, "Track"] = edit_track.strip()
            df_edit.loc[mask, "Account"] = edit_account.strip()
            df_edit.loc[mask, "Bookmaker"] = edit_bookmaker.strip()
            df_edit.loc[mask, "Event"] = edit_event.strip()
            df_edit.loc[mask, "Odds Taken"] = edit_odds
            df_edit.loc[mask, "Exchange Odds"] = edit_exchange
            df_edit.loc[mask, "BSP"] = edit_bsp
            df_edit.loc[mask, "Stake"] = edit_stake
            df_edit.loc[mask, "Result"] = edit_result
            df_edit.loc[mask, "Profit/Loss"] = calculate_profit(edit_odds, edit_stake, edit_result)
            df_edit.loc[mask, "CLV %"] = calculate_clv(edit_odds, edit_bsp)
            df_edit.loc[mask, "Edge %"] = calculate_edge(edit_odds, edit_exchange)
            df_edit.loc[mask, "Notes"] = edit_notes.strip()

            save_data(df_edit)
            st.success("Bet updated.")
            st.rerun()

# -------- SIDEBAR: FILTERS --------
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

# -------- METRICS --------
total_bets = len(filtered_df)
total_staked = filtered_df["Stake"].sum()
total_profit = filtered_df["Profit/Loss"].sum()
roi = (total_profit / total_staked * 100) if total_staked != 0 else 0
avg_stake = filtered_df["Stake"].mean()
avg_edge = filtered_df["Edge %"].mean() if "Edge %" in filtered_df.columns else None
avg_clv = filtered_df["CLV %"].mean() if "CLV %" in filtered_df.columns else None
ending_bankroll = filtered_df["Bankroll"].iloc[-1]

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Bets", f"{total_bets}")
m2.metric("Staked", f"£{total_staked:,.2f}")
m3.metric("Profit", f"£{total_profit:,.2f}")
m4.metric("ROI", f"{roi:.2f}%")
m5.metric("Avg Stake", f"£{avg_stake:,.2f}")
m6.metric("Ending Bankroll", f"£{ending_bankroll:,.2f}")

m7, m8 = st.columns(2)
m7.metric("Avg Edge %", f"{avg_edge:.2f}%" if pd.notna(avg_edge) else "N/A")
m8.metric("Avg CLV %", f"{avg_clv:.2f}%" if pd.notna(avg_clv) else "N/A")

chart_template = "plotly_dark"

# -------- CHARTS --------
st.subheader("Cumulative P/L")
fig_cum = go.Figure()
fig_cum.add_trace(
    go.Scatter(
        x=daily_curve_df["Day"],
        y=daily_curve_df["Cumulative P/L"],
        mode="lines+markers",
        line=dict(width=3),
        marker=dict(size=7),
        fill="tozeroy"
    )
)
fig_cum.update_layout(
    template=chart_template,
    height=420,
    margin=dict(l=20, r=20, t=20, b=20),
    xaxis_title="Date",
    yaxis_title="Profit / Loss (£)",
)
st.plotly_chart(fig_cum, use_container_width=True)

st.subheader("Bankroll Curve")
fig_bankroll = go.Figure()
fig_bankroll.add_trace(
    go.Scatter(
        x=daily_curve_df["Day"],
        y=daily_curve_df["Bankroll"],
        mode="lines+markers",
        line=dict(width=3),
        marker=dict(size=7),
        fill="tozeroy"
    )
)
fig_bankroll.update_layout(
    template=chart_template,
    height=420,
    margin=dict(l=20, r=20, t=20, b=20),
    xaxis_title="Date",
    yaxis_title="Bankroll (£)",
)
st.plotly_chart(fig_bankroll, use_container_width=True)

st.subheader("Daily P/L")
daily_df = filtered_df.groupby("Day", as_index=False)["Profit/Loss"].sum()
fig_daily = px.bar(
    daily_df,
    x="Day",
    y="Profit/Loss",
    template=chart_template,
)
fig_daily.update_layout(
    height=380,
    margin=dict(l=20, r=20, t=20, b=20),
    xaxis_title="Date",
    yaxis_title="Daily Profit / Loss (£)",
)
st.plotly_chart(fig_daily, use_container_width=True)

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Profit by Bookmaker")
    bookmaker_df = (
        filtered_df.groupby("Bookmaker", as_index=False)["Profit/Loss"]
        .sum()
        .sort_values("Profit/Loss", ascending=False)
    )
    fig_book = px.bar(
        bookmaker_df,
        x="Bookmaker",
        y="Profit/Loss",
        template=chart_template,
    )
    fig_book.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Bookmaker",
        yaxis_title="Profit / Loss (£)",
    )
    st.plotly_chart(fig_book, use_container_width=True)

with right_col:
    st.subheader("Profit by Account")
    account_df = (
        filtered_df.groupby("Account", as_index=False)["Profit/Loss"]
        .sum()
        .sort_values("Profit/Loss", ascending=False)
    )
    fig_acc = px.bar(
        account_df,
        x="Account",
        y="Profit/Loss",
        template=chart_template,
    )
    fig_acc.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_title="Account",
        yaxis_title="Profit / Loss (£)",
    )
    st.plotly_chart(fig_acc, use_container_width=True)

# -------- TABLE --------
st.subheader("Bet Log")

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
