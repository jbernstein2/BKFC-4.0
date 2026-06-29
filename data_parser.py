import pandas as pd
import re

# ── STAT DEFINITIONS ────────────────────────────────────────────────────────
# col = 0-indexed column number in the Wyscout export
STATS = [
    {"label": "Goals",                        "col": 6,   "category": "attack"},
    {"label": "xG (Expected Goals)",          "col": 7,   "category": "attack"},
    {"label": "Shots",                        "col": 8,   "category": "attack"},
    {"label": "Shots on Target",              "col": 9,   "category": "attack"},
    {"label": "Shot Accuracy %",              "col": 10,  "category": "attack"},
    {"label": "Possession %",                 "col": 14,  "category": "attack"},
    {"label": "Passes",                       "col": 11,  "category": "attack"},
    {"label": "Pass Accuracy %",              "col": 13,  "category": "attack"},
    {"label": "Positional Attacks",           "col": 29,  "category": "attack"},
    {"label": "Positional Attacks w/ Shots",  "col": 30,  "category": "attack"},
    {"label": "Counterattacks",               "col": 32,  "category": "attack"},
    {"label": "Corners",                      "col": 38,  "category": "attack"},
    {"label": "Set Pieces w/ Shots",          "col": 36,  "category": "attack"},
    {"label": "Crosses",                      "col": 47,  "category": "attack"},
    {"label": "Cross Accuracy %",             "col": 49,  "category": "attack"},
    {"label": "Touches in Penalty Area",      "col": 55,  "category": "attack"},
    {"label": "Offensive Duels Won %",        "col": 58,  "category": "attack"},
    {"label": "Defensive Duels Won %",        "col": 66,  "category": "defense"},
    {"label": "Aerial Duels Won %",           "col": 69,  "category": "defense"},
    {"label": "Interceptions",                "col": 73,  "category": "defense"},
    {"label": "Clearances",                   "col": 74,  "category": "defense"},
    {"label": "Shots Against",                "col": 61,  "category": "defense"},
    {"label": "PPDA",                         "col": 108, "category": "defense"},
    {"label": "Duels Won %",                  "col": 25,  "category": "defense"},
    {"label": "Fouls",                        "col": 75,  "category": "discipline"},
    {"label": "Yellow Cards",                 "col": 76,  "category": "discipline"},
]

# ── ATTACKING PHASE STATS (for dedicated slide) ──────────────────────────────
ATTACK_STATS = [
    {"label": "Positional Attacks",          "col": 29},
    {"label": "Positional Attacks w/ Shots", "col": 30},
    {"label": "Counterattacks",              "col": 32},
    {"label": "Counterattacks w/ Shots",     "col": 33},
    {"label": "Set Pieces",                  "col": 35},
    {"label": "Set Pieces w/ Shots",         "col": 36},
    {"label": "Touches in Penalty Area",     "col": 55},
    {"label": "Deep Completed Crosses",      "col": 50},
    {"label": "Deep Completed Passes",       "col": 51},
]

# ── DEFENSIVE PHASE STATS (for dedicated slide) ──────────────────────────────
DEFENSE_STATS = [
    {"label": "PPDA",                   "col": 108},
    {"label": "Interceptions",          "col": 73},
    {"label": "Clearances",             "col": 74},
    {"label": "Defensive Duels Won %",  "col": 66},
    {"label": "Aerial Duels Won %",     "col": 69},
    {"label": "Shots Against",          "col": 61},
    {"label": "Shots on Target Against","col": 62},
    {"label": "Sliding Tackles",        "col": 70},
]

# ── HEAD-TO-HEAD SUMMARY STATS (for comparison slide) ────────────────────────
H2H_STATS = [
    {"label": "Goals",               "col": 6},
    {"label": "xG",                  "col": 7},
    {"label": "Shots",               "col": 8},
    {"label": "Shots on Target",     "col": 9},
    {"label": "Possession %",        "col": 14},
    {"label": "Pass Accuracy %",     "col": 13},
    {"label": "Positional Attacks",  "col": 29},
    {"label": "Counterattacks",      "col": 32},
    {"label": "Duels Won %",         "col": 25},
    {"label": "Interceptions",       "col": 73},
    {"label": "PPDA",                "col": 108},
    {"label": "Touches in Box",      "col": 55},
]


def _safe_numeric(series):
    return pd.to_numeric(series, errors='coerce')


def _parse_score_and_opponent(match_title: str, home_team: str = "Brooklyn"):
    """Extract score string and opponent name from a Wyscout match title."""
    score = ""
    m = re.search(r"\d+:\d+", match_title)
    if m:
        score = m.group()

    # Remove score from title then strip team names
    clean = match_title.replace(score, "").strip(" -–")
    parts = [p.strip() for p in re.split(r"\s*-\s*", clean) if p.strip()]
    opponent = next((p for p in parts if home_team.lower() not in p.lower()), parts[-1] if parts else "Unknown")
    return score, opponent


def get_available_matches(bkfc_file) -> list[dict]:
    """
    Returns a list of all matches in the BKFC file, newest first.
    Each entry: {"label": <display string>, "match_title": <raw title>, "date": <str>}
    """
    df = pd.read_excel(bkfc_file, header=None, engine="openpyxl")
    data_rows = df.iloc[3:]  # skip header row, bkfc-avg label, opp-avg label
    bkfc_rows = data_rows[data_rows.index % 2 == 1]  # odd indices = Brooklyn rows

    matches = []
    for _, row in bkfc_rows.iterrows():
        date  = str(row[0])
        title = str(row[1])
        comp  = str(row[2])
        score, opponent = _parse_score_and_opponent(title)
        matches.append({
            "label":       f"{date}  |  {title}  ({comp.split('.')[-1].strip()})",
            "match_title": title,
            "date":        date,
            "competition": comp,
            "score":       score,
            "opponent":    opponent,
        })
    return matches


def load_match_data(bkfc_file, opp_file, match_title: str) -> dict:
    """
    Parse both Wyscout Excel exports and return a unified data dict for
    the specified match_title.

    Data layout (0-indexed rows):
        Row 0  — column headers
        Row 1  — "Brooklyn" label  (no numeric data; averages computed here)
        Row 2  — "Opponents" label (no numeric data; averages computed here)
        Row 3,5,7,…  — Brooklyn match rows   (odd index, starting at 3)
        Row 4,6,8,…  — Opponent match rows   (even index, starting at 4)

    The opponent file has the same layout but centred on the opponent team.
    Row 1 there carries the opponent's team name label.
    """
    bkfc_df = pd.read_excel(bkfc_file, header=None, engine="openpyxl")
    opp_df  = pd.read_excel(opp_file,  header=None, engine="openpyxl")

    numeric_cols = list(range(6, 109))

    # ── Split BKFC file into Brooklyn rows vs opponent rows ──────────────────
    bkfc_data = bkfc_df.iloc[3:]
    bkfc_team_rows = bkfc_data[bkfc_data.index % 2 == 1]   # Brooklyn
    bkfc_opp_rows  = bkfc_data[bkfc_data.index % 2 == 0]   # Their opponents

    # ── Find the specific match ──────────────────────────────────────────────
    match_bkfc_df = bkfc_team_rows[bkfc_team_rows[1] == match_title]
    match_opp_df  = bkfc_opp_rows[bkfc_opp_rows[1]  == match_title]

    if match_bkfc_df.empty:
        raise ValueError(f"Match not found in BKFC file: '{match_title}'")
    if match_opp_df.empty:
        raise ValueError(f"Opponent row not found for match: '{match_title}'")

    match_bkfc = match_bkfc_df.iloc[0]
    match_opp  = match_opp_df.iloc[0]

    # ── Compute BKFC season averages (exclude the selected match) ────────────
    bkfc_excl = bkfc_team_rows[bkfc_team_rows[1] != match_title]
    bkfc_season_avg = (
        bkfc_excl[numeric_cols]
        .apply(_safe_numeric)
        .mean()
    )

    # ── Compute all-opponent averages from BKFC file (exclude selected match) -
    opp_excl = bkfc_opp_rows[bkfc_opp_rows[1] != match_title]
    all_opp_avg = (
        opp_excl[numeric_cols]
        .apply(_safe_numeric)
        .mean()
    )

    # ── Opponent season average from their own file ──────────────────────────
    # Row 1 in opp_df contains the opponent team's name label
    opp_team_name_label = str(opp_df.iloc[1, 0])

    opp_file_data = opp_df.iloc[3:]
    # Opponent team rows are the odd-indexed rows in their own file
    opp_file_team_rows = opp_file_data[opp_file_data.index % 2 == 1]
    # Exclude the match vs Brooklyn from their own averages too
    opp_file_excl = opp_file_team_rows[opp_file_team_rows[1] != match_title]
    opp_season_avg = (
        opp_file_excl[numeric_cols]
        .apply(_safe_numeric)
        .mean()
    )

    # ── Extract match metadata ───────────────────────────────────────────────
    score, opponent_name = _parse_score_and_opponent(str(match_bkfc[1]))
    match_date  = str(match_bkfc[0])
    competition = str(match_bkfc[2])

    return {
        "match_title":     str(match_bkfc[1]),
        "match_date":      match_date,
        "competition":     competition,
        "score":           score,
        "opponent_name":   opponent_name,
        "match_bkfc":      match_bkfc,
        "match_opp":       match_opp,
        "bkfc_season_avg": bkfc_season_avg,
        "all_opp_avg":     all_opp_avg,
        "opp_season_avg":  opp_season_avg,
    }
