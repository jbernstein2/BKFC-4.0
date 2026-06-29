import streamlit as st
from data_parser import load_match_data, get_available_matches, STATS
from report_generator import generate_report

st.set_page_config(
    page_title="BKFC Match Report",
    page_icon="⚽",
    layout="wide"
)

@st.cache_data
def load_match_data_cached(bkfc_file, opp_file, match_title):
    return load_match_data(bkfc_file, opp_file, match_title)
st.title("⚽ Brooklyn FC")
st.subheader("Match Analysis & Report Generator")
st.markdown("---")

# ── SIDEBAR: FILES + OPPONENT PROFILE + REPORT CONTROLS ─────────────────────
with st.sidebar:
    st.header("Data Inputs")
    bkfc_file = st.file_uploader("BKFC Wyscout Season (.xlsx)", type=["xlsx"])
    opp_file = st.file_uploader("Opponent Wyscout Season (.xlsx)", type=["xlsx"])

    st.markdown("---")
    st.header("Report Controls")

# ── MAIN: ONLY CONTINUE WHEN BOTH FILES ARE PRESENT ─────────────────────────
if bkfc_file and opp_file:
    # Get all matches from BKFC file
    matches = get_available_matches(bkfc_file)
    match_labels = [m["label"] for m in matches]

    # Single-match selection
    selected_label = st.selectbox("Select Match", match_labels)
    match_title = next(m["match_title"] for m in matches if m["label"] == selected_label)

    # Optional: second match for comparison
    st.markdown("#### Optional: Compare with another match")
    compare_label = st.selectbox(
        "Select comparison match (optional)",
        ["None"] + match_labels,
        index=0
    )
    compare_title = None
    if compare_label != "None":
        compare_title = next(m["match_title"] for m in matches if m["label"] == compare_label)

    # Load main match data (cached)
    data = load_match_data_cached(bkfc_file, opp_file, match_title)

    st.success(f"Loaded match: BKFC vs {data['opponent_name']} ({data['match_date']})")

    # ── OPPONENT PROFILE IN SIDEBAR ──────────────────────────────────────────
    with st.sidebar:
        st.header("Opponent Profile")
        st.write(data["opponent_name"])
        st.metric("PPDA (season avg)", f"{data['opp_season_avg'][108]:.2g}")
        st.metric("Shots Against (season avg)", f"{data['opp_season_avg'][61]:.2g}")
        st.metric("Touches in Box (season avg)", f"{data['opp_season_avg'][55]:.2g}")

    # ── MAIN DASHBOARD SECTIONS ──────────────────────────────────────────────

    # 1) Match summary table
    st.markdown("### Match Performance Overview")
    summary_metrics = [
        ("Goals",           6),
        ("xG (Exp. Goals)", 7),
        ("Shots",           8),
        ("Shots on Target", 9),
        ("Possession %",    14),
        ("Pass Accuracy %", 13),
        ("PPDA",            108),
    ]

    rows = []
    for label, col in summary_metrics:
        bkfc_val = float(data["match_bkfc"][col])
        opp_val  = float(data["match_opp"][col])
        rows.append({
            "Metric": label,
            "BKFC": bkfc_val,
            data["opponent_name"]: opp_val,
        })
    st.table(rows)

    # 2) Head-to-head chart (reuse logic conceptually)
    st.markdown("### Head-to-Head Comparison (Key Metrics)")
    import matplotlib.pyplot as plt
    import numpy as np

    h2h_cols = [m[1] for m in summary_metrics]
    labels   = [m[0] for m in summary_metrics]
    bkfc_vals = np.array([float(data["match_bkfc"][c]) for c in h2h_cols])
    opp_vals  = np.array([float(data["match_opp"][c]) for c in h2h_cols])

    fig, ax = plt.subplots(figsize=(8, 4))
    x = np.arange(len(labels))
    w = 0.35
    ax.bar(x - w/2, bkfc_vals, w, label="BKFC")
    ax.bar(x + w/2, opp_vals,  w, label=data["opponent_name"])
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right")
    ax.legend()
    st.pyplot(fig)

    # 3) Strategic insights (same engine as PPTX)
    from insights import generate_insights
    from data_parser import STATS as ALL_STATS

    st.markdown("### Strategic Insights")
    stats_list = [
        {
            "label":  s["label"],
            "match":  data["match_bkfc"][s["col"]],
            "season": data["bkfc_season_avg"][s["col"]],
        }
        for s in ALL_STATS
    ]
    insights = generate_insights(stats_list)

    with st.expander("View key deviations vs season baseline"):
        for text in insights:
            st.info(text)

    # 4) Per-stat deep dive explorer
    st.markdown("### Per-Metric Deep Dive")
    stat_label = st.selectbox("Choose a metric", [s["label"] for s in ALL_STATS])
    stat_def   = next(s for s in ALL_STATS if s["label"] == stat_label)
    col_idx    = stat_def["col"]

    bkfc_match_val = float(data["match_bkfc"][col_idx])
    opp_match_val  = float(data["match_opp"][col_idx])
    bkfc_season    = float(data["bkfc_season_avg"][col_idx])
    league_avg     = float(data["all_opp_avg"][col_idx])
    opp_season     = float(data["opp_season_avg"][col_idx])

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("This Match")
        st.metric("BKFC", f"{bkfc_match_val:.2g}")
        st.metric(data["opponent_name"], f"{opp_match_val:.2g}")
    with c2:
        st.subheader("Season Context")
        st.metric("BKFC Avg", f"{bkfc_season:.2g}")
        st.metric("League Avg", f"{league_avg:.2g}")
        st.metric(f"{data['opponent_name']} Avg", f"{opp_season:.2g}")

    # 5) Season trend charts (simple example for xG and PPDA)
    st.markdown("### Season Trends (BKFC)")
    import pandas as pd

    # Build a small season dataframe from bkfc_team_rows via data_parser logic
    # Here we reuse bkfc_file directly for a quick trend view
    from data_parser import _safe_numeric  # or reimplement inline

    df_bkfc = pd.read_excel(bkfc_file, header=None, engine="openpyxl")
    data_rows = df_bkfc.iloc[3:]
    bkfc_team_rows = data_rows[data_rows.index % 2 == 1]
    trend_df = pd.DataFrame({
        "Date": bkfc_team_rows[0].astype(str),
        "MatchTitle": bkfc_team_rows[1].astype(str),
        "xG": _safe_numeric(bkfc_team_rows[7]),
        "PPDA": _safe_numeric(bkfc_team_rows[108]),
    })

    trend_df = trend_df.sort_values("Date")
    st.line_chart(trend_df.set_index("Date")[["xG", "PPDA"]])

    # 6) Optional multi-match comparison
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
