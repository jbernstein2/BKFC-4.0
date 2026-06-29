import pdfplumber
import re

# ---------------------------------------------------------
# Load PDF
# ---------------------------------------------------------
def load_pdf(pdf_file):
    return pdfplumber.open(pdf_file)

# ---------------------------------------------------------
# Extract Match Metadata
# ---------------------------------------------------------
def extract_metadata(pages):
    text = pages[0].extract_text()

    # Match header line example:
    # "UNITED STATES. USL CHAMPIONSHIP (21.06.2026)\nBrooklyn 0 - 2 Tampa Bay Rowdies"
    competition = re.search(r"(USL Championship|USL CHAMPIONSHIP)", text)
    date = re.search(r"\((\d{2}\.\d{2}\.\d{4})\)", text)
    teams = re.search(r"(.+?)\s+0\s+-\s+2\s+(.+)", text)

    return {
        "competition": competition.group(1) if competition else None,
        "date": date.group(1) if date else None,
        "home_team": teams.group(1).strip() if teams else None,
        "away_team": teams.group(2).strip() if teams else None,
        "score": "0 - 2"
    }

# ---------------------------------------------------------
# Extract xG Timeline
# ---------------------------------------------------------
def extract_xg_timeline(pages):
    xg_data = []
    player_xg = {}
    half_split = {}
    shots_against = []

    for page in pages:
        text = page.extract_text()

        # -----------------------------
        # 1. Find the xG table section
        # -----------------------------
        if "Opportunities (xG)" in text:
            table = page.extract_tables()[0]

            # Table structure:
            # Team / Total / 1st half / 2nd half
            for row in table[1:]:
                name = row[0]
                total = row[1]
                first = row[2]
                second = row[3]

                # Team totals
                if name.lower() in ["brooklyn", "tampa bay rowdies"]:
                    half_split[name] = {
                        "1H": float(first),
                        "2H": float(second)
                    }

                # Player rows
                else:
                    try:
                        player_xg[name] = float(total)
                    except:
                        pass

        # -----------------------------
        # 2. Shot-by-shot xCG (GK page)
        # -----------------------------
        if "Shots against" in text:
            tables = page.extract_tables()
            for t in tables:
                if len(t) > 1 and t[0] == ["#", "Player", "Time", "xCG"]:
                    for row in t[1:]:
                        shots_against.append({
                            "player": row[1],
                            "minute": int(row[2].replace("'", "")),
                            "xCG": float(row[3])
                        })

    # -----------------------------
    # Build cumulative xG timeline
    # -----------------------------
    cumulative = {
        "Brooklyn": [],
        "Tampa Bay Rowdies": []
    }

    # Build from player_xg (no timestamps in Wyscout PDF)
    # We use shot-by-shot xCG for defensive timeline
    # Offensive timeline is cumulative by player contribution
    brooklyn_total = 0
    tampa_total = 0

    for player, xg in player_xg.items():
        # Assign players to teams based on metadata later
        # For now, accumulate globally
        brooklyn_total += xg
        cumulative["Brooklyn"].append(brooklyn_total)

    # Defensive timeline from xCG
    tampa_total = 0
    defensive_timeline = []
    for shot in shots_against:
        tampa_total += shot["xCG"]
        defensive_timeline.append({
            "minute": shot["minute"],
            "xCG_cumulative": tampa_total
        })

    return {
        "player_xg": player_xg,
        "half_split": half_split,
        "shots_against": shots_against,
        "cumulative": cumulative,
        "defensive_timeline": defensive_timeline
    }

# ---------------------------------------------------------
# Master Parser
# ---------------------------------------------------------
def parse_pdf(pdf_file):
    pdf = load_pdf(pdf_file)
    pages = pdf.pages

    data = {
        "metadata": extract_metadata(pages),
        "xg_timeline": extract_xg_timeline(pages),
        # Future modules will be added here:
        # "ppda": extract_ppda_timeline(pages),
        # "attack_momentum": extract_attack_momentum(pages),
        # ...
    }

    pdf.close()
    return data
