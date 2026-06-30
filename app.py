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

from pdf_parser import parse_pdf

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

    # Automatically switch text color for dark backgrounds
    text_color = "#FFFFFF" if color == "DARK_GRAY" else "#000000"

    st.markdown(
        f"""
        <div style="
            background-color:{hex_color};
            padding:12px;
            border-radius:8px;
            color:{text_color};
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
    pdf_file = st.file_uploader("Wyscout Match Report (.pdf)", type=["pdf"])
    st.markdown("---")

# ───────────────────────────────────────────────────────────────
# LOAD PDF DATA (optional)
# ───────────────────────────────────────────────────────────────
pdf_data = None
if pdf_file:
    pdf_data = parse_pdf(pdf_file)

# ───────────────────────────────────────────────────────────────
# TABS
# ───────────────────────────────────────────────────────────────
tabs = st.tabs([
    "Match Summary (XLSX)",
    "Team Stats (XLSX)",
    "Advanced Insights (PDF)",
    "Player Dashboards (PDF)"
])

# ───────────────────────────────────────────────────────────────
# TAB 1 — MATCH SUMMARY (XLSX)
# ───────────────────────────────────────────────────────────────
with tabs[0]:

    if bkfc_file and opp_file:

        matches = get_available_matches(bkfc_file)
        match_labels = [m["label"] for m in matches]

        selected_label = st.selectbox("Select Match", match_labels)
        match_title = next(m["match_title"] for m in matches if m["label"] == selected_label)

        st.markdown("#### Optional: Compare with another match")
        compare_label = st.selectbox("Select comparison match (optional)", ["None"] + match_labels)
        compare_title = None
        if compare_label != "None":
            compare_title = next(m["match_title"] for m in matches if m["label"] == compare_label)

        data = load_match_data_cached(bkfc_file, opp_file, match_title)

        st.success(f"Loaded match: BKFC vs {data['opponent_name']} ({data['match_date']})")

        # Opponent Profile stays — useful and will expand with PDF insights later
        with st.sidebar:
            st.header("Opponent Profile")
            bkfc_card("Opponent", data["opponent_name"], color="GOLD")
            bkfc_card("PPDA (Season Avg)", f"{data['opp_season_avg'][108]:.2f}", color="SILVER")
            bkfc_card("Shots Against (Season Avg)", f"{data['opp_season_avg'][61]:.2f}", color="DARK_GRAY")
            bkfc_card("Touches in Box (Season Avg)", f"{data['opp_season_avg'][55]:.2f}", color="GREEN")

        st.markdown("### Match Performance Overview")

        summary_metrics = [
            ("Goals", 6),
            ("xG (Exp. Goals)", 7),
            ("Shots", 8),
            ("Shots on Target", 9),
            ("Possession %", 14),
            ("Pass Accuracy %", 13),
            ("PPDA", 108),
        ]

        # ⭐ FIXED ROUNDING HERE
        rows = []
        for label, col in summary_metrics:
            rows.append({
                "Metric": label,
                "BKFC": f"{float(data['match_bkfc'][col]):.2f}",
                data["opponent_name"]: f"{float(data['match_opp'][col]):.2f}",
            })
        st.table(rows)

        st.markdown("### Head-to-Head Comparison")

        labels = [m[0] for m in summary_metrics]
        bkfc_vals = np.array([float(data["match_bkfc"][m[1]]) for m in summary_metrics])
        opp_vals  = np.array([float(data["match_opp"][m[1]]) for m in summary_metrics])

        fig, ax = plt.subplots(figsize=(8, 4))
        x = np.arange(len(labels))
        w = 0.35

        ax.bar(x - w/2, bkfc_vals, w, label="BKFC", color="#" + COLORS["GOLD"])
        ax.bar(x + w/2, opp_vals,  w, label=data["opponent_name"], color="#" + COLORS["DARK_GRAY"])

        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.grid(True, linestyle="--", alpha=0.3, color="#" + COLORS["GRID"])
        ax.legend()
        st.pyplot(fig)

        st.markdown("### Strategic Insights")

        stats_list = [
            {
                "label": s["label"],
                "match": data["match_bkfc"][s["col"]],
                "season": data["bkfc_season_avg"][s["col"]],
            }
            for s in STATS
        ]
        insights = generate_insights(stats_list)

        with st.expander("View key deviations vs season baseline"):
            for text in insights:
                st.info(text)

        st.markdown("### Per-Metric Deep Dive")

        stat_label = st.selectbox("Choose a metric", [s["label"] for s in STATS])
        stat_def = next(s for s in STATS if s["label"] == stat_label)
        col_idx = stat_def["col"]

        bkfc_match_val = float(data["match_bkfc"][col_idx])
        opp_match_val  = float(data["match_opp"][col_idx])
        bkfc_season    = float(data["bkfc_season_avg"][col_idx])
        league_avg     = float(data["all_opp_avg"][col_idx])
        opp_season     = float(data["opp_season_avg"][col_idx])

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("This Match")
            bkfc_card("BKFC", f"{bkfc_match_val:.2f}", color="GOLD")
            bkfc_card(data["opponent_name"], f"{opp_match_val:.2f}", color="DARK_GRAY")

        with c2:
            st.subheader("Season Context")
            bkfc_card("BKFC Avg", f"{bkfc_season:.2f}", color="GOLD")
            bkfc_card("Opp Avg", f"{league_avg:.2f}", color="SILVER")
            bkfc_card(f"{data['opponent_name']} Avg", f"{opp_season:.2f}", color="DARK_GRAY")

        st.markdown("### Season Trends (Interactive)")

        TREND_STATS = {s["label"]: s["col"] for s in STATS}

        selected_trend_stats = st.multiselect(
            "Choose metrics to visualize over the season",
            list(TREND_STATS.keys()),
            default=["xG (Expected Goals)", "PPDA"]
        )

        bkfc_season_df = load_bkfc_season_df(bkfc_file)

        trend_df = pd.DataFrame({"Date": bkfc_season_df[0].astype(str)})

        for label in selected_trend_stats:
            col = TREND_STATS[label]
            trend_df[label] = _safe_numeric(bkfc_season_df[col])

        trend_df = trend_df.sort_values("Date").set_index("Date")
        st.line_chart(trend_df)

        if compare_title:
            st.markdown("### Match Comparison")

            data_cmp = load_match_data_cached(bkfc_file, opp_file, compare_title)

            comp_cols = [6, 7, 8, 14, 13, 108]
            comp_labels = ["Goals", "xG", "Shots", "Possession %", "Pass Acc %", "PPDA"]

            rows_cmp = []
            for label, col in zip(comp_labels, comp_cols):
                rows_cmp.append({
                    "Metric": label,
                    "Match A (selected)": float(data["match_bkfc"][col]),
                    "Match B (comparison)": float(data_cmp["match_bkfc"][col]),
                })
            st.table(rows_cmp)

        st.markdown("---")
        confirm = st.checkbox("Verify data profiles match and charts look correct")

        if confirm:
            if st.button("Compile Match Report (PowerPoint)", use_container_width=True):
                with st.spinner("Generating PowerPoint report..."):
                    report_stream = generate_report(data)
                    clean_opp_name = data['opponent_name'].replace(" ", "_")
                    output_filename = f"BKFC_vs_{clean_opp_name}_Match_Report.pptx"

                st.success("Report ready!")
                st.download_button(
                    label="Download PowerPoint",
                    data=report_stream,
                    file_name=output_filename,
                    mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                    use_container_width=True
                )

    else:
        st.info("Upload both BKFC and opponent Wyscout season files to begin.")

# ───────────────────────────────────────────────────────────────
# TAB 2 — TEAM STATS (XLSX)
# ───────────────────────────────────────────────────────────────
with tabs[1]:
    st.header("Team Stats (from XLSX)")
    if not (bkfc_file and opp_file):
        st.info("Upload both BKFC and opponent Wyscout season files to view team stats.")
    else:
        st.write("Team stats are shown in the Match Summary tab.")

# ───────────────────────────────────────────────────────────────
# TAB 3 — ADVANCED INSIGHTS (PDF)
# ───────────────────────────────────────────────────────────────
with tabs[2]:
    st.header("Advanced Tactical Insights (from PDF)")

    if pdf_data:

        st.subheader("xG Timeline")

        xg = pdf_data["xg_timeline"]

        st.write("### Player xG Contribution")
        st.bar_chart(pd.DataFrame.from_dict(
            xg["player_xg"], orient="index", columns=["xG"]
        ))

        st.write("### First Half vs Second Half xG")
        st.json(xg["half_split"])

        st.write("### Defensive xCG Timeline")
        st.line_chart(pd.DataFrame([
            {"minute": s["minute"], "xCG": s["xCG_cumulative"]}
            for s in xg["defensive_timeline"]
        ]))

        st.write("### Shots Against (xCG)")
        st.dataframe(pd.DataFrame(xg["shots_against"]))

        st.markdown("---")
        st.info("More tactical modules coming soon: PPDA, Passing Network, Defensive Shot Map, Transition Map, Set Pieces, Duel Efficiency, etc.")

    else:
        st.info("Upload a Wyscout Match Report PDF to view tactical insights.")

# ───────────────────────────────────────────────────────────────
# TAB 4 — PLAYER DASHBOARDS (PDF)
# ───────────────────────────────────────────────────────────────
with tabs[3]:
    st.header("Player Dashboards (from PDF)")

    if pdf_data:
        st.info("Player dashboards will be added after team tactical modules.")
    else:
        st.info("Upload a Wyscout Match Report PDF to view player dashboards.")
