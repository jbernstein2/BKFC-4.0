import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from branding import COLORS
from data_parser import (
    load_match_data,
    get_available_matches,
    STATS,
    _safe_numeric
)
from report_generator import generate_report
from insights import generate_insights

# ───────────────────────────────────────────────────────────────
# STREAMLIT CONFIG
# ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="BKFC Match Report",
    page_icon="⚽",
    layout="wide"
)

# ───────────────────────────────────────────────────────────────
# CACHING
# ───────────────────────────────────────────────────────────────
@st.cache_data
def load_match_data_cached(bkfc_file, opp_file, match_title):
    return load_match_data(bkfc_file, opp_file, match_title)

@st.cache_data
def load_bkfc_season_df(bkfc_file):
    df = pd.read_excel(bkfc_file, header=None, engine="openpyxl")
    data_rows = df.iloc[3:]
    bkfc_team_rows = data_rows[data_rows.index % 2 == 1]
    return bkfc_team_rows

# ───────────────────────────────────────────────────────────────
# BKFC BRAND CARD
# ───────────────────────────────────────────────────────────────
def bkfc_card(text, value, color="GOLD"):
    hex_color = "#" + COLORS[color]
    st.markdown(
        f"""
        <div style="
            background-color:{hex_color};
            padding:12px;
            border-radius:8px;
            color:#000;
            font-weight:bold;
            font-size:18px;
            text-align:center;
            margin-bottom:10px;">
            {text}: {value}
        </div>
        """,
        unsafe_allow_html=True
    )

# ───────────────────────────────────────────────────────────────
# UI HEADER
# ───────────────────────────────────────────────────────────────
st.title("⚽ Brooklyn FC")
st.subheader("Match Analysis & Report Generator")
st.markdown("---")

# ───────────────────────────────────────────────────────────────
# SIDEBAR INPUTS
# ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Data Inputs")
    bkfc_file = st.file_uploader("BKFC Wyscout Season (.xlsx)", type=["xlsx"])
    opp_file = st.file_uploader("Opponent Wyscout Season (.xlsx)", type=["xlsx"])
    st.markdown("---")
    st.header("Report Controls")

# ───────────────────────────────────────────────────────────────
# MAIN LOGIC — ONLY RUN WHEN BOTH FILES ARE PRESENT
# ───────────────────────────────────────────────────────────────
if bkfc_file and opp_file:

    # Load match list
    matches = get_available_matches(bkfc_file)
    match_labels = [m["label"] for m in matches]

    selected_label = st.selectbox("Select Match", match_labels)
    match_title = next(m["match_title"] for m in matches if m["label"] == selected_label)

    # Optional comparison match
    st.markdown("#### Optional: Compare with another match")
    compare_label = st.selectbox("Select comparison match (optional)", ["None"] + match_labels)
    compare_title = None
    if compare_label != "None":
        compare_title = next(m["match_title"] for m in matches if m["label"] == compare_label)

    # Load match data
    data = load_match_data_cached(bkfc_file, opp_file, match_title)

    st.success(f"Loaded match: BKFC vs {data['opponent_name']} ({data['match_date']})")

    # ───────────────────────────────────────────────────────────────
    # SIDEBAR — OPPONENT PROFILE
    # ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Opponent Profile")
        bkfc_card("Opponent", data["opponent_name"], color="GOLD")
        bkfc_card("PPDA
