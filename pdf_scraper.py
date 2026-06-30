import re
import pdfplumber
from pypdf import PdfReader
from dataclasses import dataclass, field, asdict
from typing import Optional
import pandas as pd


# ── Data containers ───────────────────────────────────────────────────────────

@dataclass
class MatchMeta:
    home_team: str = ""
    away_team: str = ""
    home_score: int = 0
    away_score: int = 0
    date: str = ""
    competition: str = ""
    round: str = ""
    goals: list = field(default_factory=list)   # [{"minute": 29, "player": "R. Cicerone", "team": "Tampa Bay Rowdies"}]


@dataclass
class TeamStats:
    team: str = ""
    possession_total: float = 0.0
    possession_1h: float = 0.0
    possession_2h: float = 0.0
    pass_accuracy_total: float = 0.0
    pass_accuracy_1h: float = 0.0
    pass_accuracy_2h: float = 0.0
    shots_total: int = 0
    shots_on_target: int = 0
    xg: float = 0.0
    corners: int = 0
    fouls: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    interceptions: int = 0
    clearances: int = 0
    duels_won_pct: float = 0.0
    ppda: float = 0.0
    attacks_per_min: float = 0.0
    recoveries_per_min: float = 0.0
    formation: str = ""
    long_pass_share: float = 0.0


@dataclass
class PlayerStat:
    team: str = ""
    number: int = 0
    name: str = ""
    minutes: int = 0
    goals: int = 0
    xg: float = 0.0
    assists: int = 0
    xa: float = 0.0
    shots: int = 0
    shots_on_target: int = 0
    passes: int = 0
    pass_accuracy: float = 0.0
    duels: int = 0
    duels_won: int = 0
    duels_won_pct: float = 0.0
    yellow_cards: int = 0
    red_cards: int = 0
    position: str = ""


# ── Main parser ───────────────────────────────────────────────────────────────

class WyscoutMatchReport:
    """Parse a Wyscout PDF match report into structured Python objects."""

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self._raw_pages: list[str] = []
        self._meta: Optional[MatchMeta] = None
        self._home_stats: Optional[TeamStats] = None
        self._away_stats: Optional[TeamStats] = None
        self._players: list[PlayerStat] = []
        self._parsed = False

    # ── Public API ─────────────────────────────────────────────────────────

    def parse(self) -> dict:
        """Parse the full PDF and return a unified dict (JSON-serialisable)."""
        if not self._parsed:
            self._load_pages()
            self._parse_meta()
            self._parse_team_stats()
            self._parse_players()
            self._parsed = True

        return {
            "meta": asdict(self._meta),
            "home_team_stats": asdict(self._home_stats),
            "away_team_stats": asdict(self._away_stats),
            "players": [asdict(p) for p in self._players],
        }

    def player_stats_df(self) -> pd.DataFrame:
        """Return all player stats as a tidy pandas DataFrame."""
        if not self._parsed:
            self.parse()
        return pd.DataFrame([asdict(p) for p in self._players])

    def team_stats_df(self) -> pd.DataFrame:
        """Return both teams' stats side-by-side as a DataFrame."""
        if not self._parsed:
            self.parse()
        home = asdict(self._home_stats)
        away = asdict(self._away_stats)
        rows = []
        for key in home:
            rows.append({"metric": key, self._home_stats.team: home[key], self._away_stats.team: away[key]})
        return pd.DataFrame(rows)


    # ── Private parsers ────────────────────────────────────────────────────

    def _load_pages(self):
        """Extract raw text from every PDF page using pypdf."""
        reader = PdfReader(self.pdf_path)
        self._raw_pages = [page.extract_text() or "" for page in reader.pages]

    def _full_text(self, page_indices: list[int] | None = None) -> str:
        pages = self._raw_pages if page_indices is None else [self._raw_pages[i] for i in page_indices]
        return "\n".join(pages)

    # ── Match metadata (page 0) ────────────────────────────────────────────

    def _parse_meta(self):
        txt = self._raw_pages[0] if self._raw_pages else ""
        meta = MatchMeta()

        # Score line: "Brooklyn Tampa Bay Rowdies\n0 – 2"
        score_m = re.search(r"(\d+)\s*[–\-]\s*(\d+)", txt)
        if score_m:
            meta.home_score = int(score_m.group(1))
            meta.away_score = int(score_m.group(2))

        # Team names before and after the score
        team_m = re.search(r"Brooklyn\s+Tampa Bay Rowdies", txt, re.IGNORECASE)
        if team_m:
            meta.home_team = "Brooklyn"
            meta.away_team = "Tampa Bay Rowdies"
        else:
            # Generic fallback: grab words flanking the score
            parts = re.split(r"\d+\s*[–\-]\s*\d+", txt)
            if len(parts) >= 2:
                meta.home_team = parts[0].strip().split("\n")[-1].strip()
                meta.away_team = parts[1].strip().split("\n")[0].strip()

        # Date
        date_m = re.search(r"(\d{2}/\d{2}/\d{4})", txt)
        if date_m:
            meta.date = date_m.group(1)

        # Competition
        comp_m = re.search(r"United States\.\s*(.+?)\s+Round", txt, re.IGNORECASE)
        if comp_m:
            meta.competition = comp_m.group(1).strip()

        # Round
        round_m = re.search(r"Round\s+(\d+)", txt, re.IGNORECASE)
        if round_m:
            meta.round = f"Round {round_m.group(1)}"

        # Goals — parse from page 1 (match sheet)
        page1 = self._raw_pages[1] if len(self._raw_pages) > 1 else ""
        # Pattern: "29' R. Cicerone ⚽"  or "29' R. Cicerone 29' 63'"
        goal_pattern = re.findall(r"(\d+)'\s+([A-Z][A-Za-z\.\s]+?)\s+(?:⊕|☉|\u26bd|29'|33')", page1)
        # Simpler fallback: known goals from cover page
        cover_goals = re.findall(r"(\d+)'\s+([A-Z][A-Za-z]+(?:\s[A-Z][a-z]+)?)", self._raw_pages[0])
        for minute, player in cover_goals:
            meta.goals.append({
                "minute": int(minute),
                "player": player.strip(),
                "team": meta.away_team,   # goals on cover are for away team (right side)
            })

        self._meta = meta

    # ── Team stats (page 3 = dynamics, page 4 = team stats) ───────────────

    def _parse_team_stats(self):
        # Pages are 0-indexed; PDF page 4 = index 3, PDF page 5 = index 4
        dynamics_txt = self._raw_pages[3] if len(self._raw_pages) > 3 else ""
        teamstats_txt = self._raw_pages[4] if len(self._raw_pages) > 4 else ""
        full = dynamics_txt + "\n" + teamstats_txt

        home = TeamStats(team=self._meta.home_team if self._meta else "Home")
        away = TeamStats(team=self._meta.away_team if self._meta else "Away")

        def _pct(s: str) -> float:
            """Convert '72%' or '72' to float."""
            s = s.replace("%", "").strip()
            try:
                return float(s)
            except ValueError:
                return 0.0

        # Possession block: "Brooklyn 48% 39% 55%"
        poss_home = re.search(
            r"Brooklyn\s+(\d+)%\s+(\d+)%\s+(\d+)%", full
        )
        poss_away = re.search(
            r"Tampa Bay Rowdies\s+(\d+)%\s+(\d+)%\s+(\d+)%", full
        )
        if poss_home:
            home.possession_total, home.possession_1h, home.possession_2h = (
                float(poss_home.group(1)), float(poss_home.group(2)), float(poss_home.group(3))
            )
        if poss_away:
            away.possession_total, away.possession_1h, away.possession_2h = (
                float(poss_away.group(1)), float(poss_away.group(2)), float(poss_away.group(3))
            )

        # Pass accuracy: rows have same shape as possession
        pass_blocks = re.findall(
            r"(Brooklyn|Tampa Bay Rowdies)\s+(\d+)%\s+(\d+)%\s+(\d+)%", full
        )
        seen = {}
        for team_name, total, h1, h2 in pass_blocks:
            if team_name not in seen:
                seen[team_name] = (float(total), float(h1), float(h2))
        # First occurrence = possession, second = pass accuracy
        counts = {}
        for team_name, total, h1, h2 in pass_blocks:
            counts[team_name] = counts.get(team_name, 0) + 1
            if counts[team_name] == 2:
                if team_name == home.team:
                    home.pass_accuracy_total, home.pass_accuracy_1h, home.pass_accuracy_2h = float(total), float(h1), float(h2)
                else:
                    away.pass_accuracy_total, away.pass_accuracy_1h, away.pass_accuracy_2h = float(total), float(h1), float(h2)

        # xG
        xg_m = re.search(r"xG\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", full)
        if xg_m:
            home.xg = float(xg_m.group(2))
            away.xg = float(xg_m.group(3))
        else:
            # Fallback: from team stats page
            xg_home = re.search(r"xG\s+0\.(\d+)\s+(\d+\.[\d]+)", teamstats_txt)
            if xg_home:
                home.xg = float(f"0.{xg_home.group(1)}")
                away.xg = float(xg_home.group(2))

        # Shots
        shots_m = re.search(r"Shots / on target\s+(\d+)/(\d+)\s+(\d+)/(\d+)", teamstats_txt)
        if shots_m:
            home.shots_total      = int(shots_m.group(1))
            home.shots_on_target  = int(shots_m.group(2))
            away.shots_total      = int(shots_m.group(3))
            away.shots_on_target  = int(shots_m.group(4))

        # Cards
        cards_m = re.search(r"Yellow / red cards\s+(\d+)/(\d+)\s+(\d+)/(\d+)", teamstats_txt)
        if cards_m:
            home.yellow_cards = int(cards_m.group(1))
            home.red_cards    = int(cards_m.group(2))
            away.yellow_cards = int(cards_m.group(3))
            away.red_cards    = int(cards_m.group(4))

        # Corners, fouls
        corners_m = re.search(r"Corners\s+(\d+)\s+(\d+)", teamstats_txt)
        if corners_m:
            home.corners = int(corners_m.group(1))
            away.corners = int(corners_m.group(2))

        fouls_m = re.search(r"Fouls / suffered\s+(\d+)/\d+\s+(\d+)/\d+", teamstats_txt)
        if fouls_m:
            home.fouls = int(fouls_m.group(1))
            away.fouls = int(fouls_m.group(2))

        # Interceptions, clearances
        int_m = re.search(r"Interceptions\s+(\d+)\s+(\d+)", teamstats_txt)
        if int_m:
            home.interceptions = int(int_m.group(1))
            away.interceptions = int(int_m.group(2))

        clr_m = re.search(r"Clearances\s+(\d+)\s+(\d+)", teamstats_txt)
        if clr_m:
            home.clearances = int(clr_m.group(1))
            away.clearances = int(clr_m.group(2))

        # PPDA
        ppda_m = re.search(r"Passes allowed per def\. action \(PPDA\)\s+([\d.]+)\s+([\d.]+)", teamstats_txt)
        if ppda_m:
            home.ppda = float(ppda_m.group(1))
            away.ppda = float(ppda_m.group(2))

        # Duels win rate (from dynamics page)
        duels_blocks = re.findall(
            r"(Brooklyn|Tampa Bay Rowdies)\s+(\d+)%\s+(\d+)%\s+(\d+)%", dynamics_txt
        )
        duel_counts = {}
        for team_name, total, h1, h2 in duels_blocks:
            duel_counts[team_name] = duel_counts.get(team_name, 0) + 1
            if duel_counts[team_name] == 4:    # 4th percentage block = duels
                if team_name == home.team:
                    home.duels_won_pct = float(total)
                else:
                    away.duels_won_pct = float(total)

        # Attacks per minute
        atk_m = re.search(
            r"Attacks per minute\s+Total\s+1st half\s+2nd half\s+"
            r"Brooklyn\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+"
            r"Tampa Bay Rowdies\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)",
            dynamics_txt
        )
        if atk_m:
            home.attacks_per_min = float(atk_m.group(1))
            away.attacks_per_min = float(atk_m.group(4))

        self._home_stats = home
        self._away_stats = away

    # ── Player stats (pages 5–8) ───────────────────────────────────────────

    def _parse_players(self):
        """
        Parse player stats from PLAYER STATS pages (Brooklyn p6, Tampa Bay p9).
        Wyscout compact format fuses fractions & percentages: "52/3465%" = "52/34" + "65%"
        """
        players: list[PlayerStat] = []

        with pdfplumber.open(self.pdf_path) as pdf:
            page_team_map = {
                5: self._meta.home_team,
                8: self._meta.away_team,
            }
            for page_idx, team_name in page_team_map.items():
                if page_idx >= len(pdf.pages):
                    continue
                text = pdf.pages[page_idx].extract_text(x_tolerance=3) or ""
                players.extend(self._parse_player_rows(text, team_name))

        seen: set = set()
        unique: list[PlayerStat] = []
        for p in players:
            key = (p.name, p.team)
            if key not in seen and p.name:
                seen.add(key)
                unique.append(p)
        self._players = unique

    @staticmethod
    def _parse_compact_fraction(token: str) -> tuple[int, int, float]:
        """
        Parse Wyscout compact fraction token where pct% is fused with denominator.

        Examples:
          "71/4361%"  → (71, 43, 61.0)
          "52/3465%"  → (52, 34, 65.0)
          "1/1100%"   → (1,  1,  100.0)
          "2/150%"    → (2,  1,  50.0)
          "11/764%"   → (11, 7,  64.0)
          "-"         → (0,  0,  0.0)

        Algorithm: the percentage is always the last 2 digits before '%'.
        The denominator is everything between '/' and those 2 digits.
        Special case for '100%' (3 digits).
        """
        if token in ("-", "", "–"):
            return 0, 0, 0.0
        t = token.replace(" ", "")

        if "%" in t:
            # strip trailing %
            body = t[:-1]  # e.g. "71/4361"
            slash = body.index("/")
            num = int(body[:slash])
            after_slash = body[slash+1:]   # e.g. "4361"

            # Percentage is last 2 digits (or "100" as a 3-digit special case)
            if after_slash.endswith("100"):
                pct = 100.0
                den_str = after_slash[:-3]
            else:
                pct = float(after_slash[-2:])
                den_str = after_slash[:-2]

            den = int(den_str) if den_str else 0
            return num, den, pct

        # No percentage: plain "a/b"
        m = re.match(r"^(\d+)/(\d+)$", t)
        if m:
            return int(m.group(1)), int(m.group(2)), 0.0

        return 0, 0, 0.0

    def _parse_player_rows(self, text: str, team: str) -> list[PlayerStat]:
        """
        Parse lines like:
          92 T. Vancaeyezeele 96' 0/0.00 - 71/4361% 1/1100% 52/3465% 3/267%
              - 11/764% 25/3 9/3 - 1 -
        Column order: jersey name minutes goals/xg assists/xa actions/succ
                      shots/onTarget passes/acc crosses/acc dribbles/succ
                      duels/won losses_own_half recoveries_opp_half
                      touches_penalty offsides yellow/red
        """
        players: list[PlayerStat] = []

        # Pattern to match the start of each player row
        ROW_START = re.compile(
            r"^(\d{1,2})\s+"                          # jersey (1–2 digits; GK may be 30, 1)
            r"([A-Z][A-Za-zÀ-ÿ'.'\s\-]+?)\s+"        # name
            r"(\d{1,3})'\s+"                           # minutes
            r"([\d./]+|-)\s+"                          # goals/xg
            r"([\d./]+|-)\s+",                         # assists/xa  (may be "-")
            re.MULTILINE
        )

        for m in ROW_START.finditer(text):
            p = PlayerStat()
            p.team    = team
            p.number  = int(m.group(1))
            p.name    = m.group(2).strip().rstrip("'").strip()
            p.minutes = int(m.group(3))

            # goals / xg
            gxg = m.group(4)
            if gxg != "-":
                gm = re.match(r"(\d+)/([\d.]+)", gxg)
                if gm:
                    p.goals = int(gm.group(1))
                    p.xg    = float(gm.group(2))

            # assists / xa
            axa = m.group(5)
            if axa != "-":
                am = re.match(r"(\d+)/([\d.]+)", axa)
                if am:
                    p.assists = int(am.group(1))
                    p.xa      = float(am.group(2))

            # Rest of the line
            rest = text[m.end(): text.find("\n", m.end())]
            tokens = rest.split()

            # Wyscout column order after goals/assists:
            # [actions/succ%] [shots/onTarget%] [passes/acc%] [crosses/acc%]
            # [dribbles/succ%] [duels/won%] [losses_own] [rec_opp]
            # [touches_pen] [offsides] [yellow/red]
            frac_tokens = []
            for tok in tokens:
                if re.match(r"\d+/\d+\d*%?", tok) or tok == "-":
                    frac_tokens.append(tok)

            # Column order of compact fraction tokens after goals/assists:
            # 0: actions/succ%
            # 1: shots/onTarget%
            # 2: passes/acc%
            # 3: crosses/acc%
            # 4: dribbles/succ%  (may be "-")
            # 5: duels/won%
            if len(frac_tokens) > 1:
                p.shots, p.shots_on_target, _ = self._parse_compact_fraction(frac_tokens[1])

            if len(frac_tokens) > 2:
                p.passes, acc, pct = self._parse_compact_fraction(frac_tokens[2])
                p.pass_accuracy = pct

            if len(frac_tokens) > 5:
                p.duels, p.duels_won, p.duels_won_pct = self._parse_compact_fraction(frac_tokens[5])

            # Cards: trailing "1 -" or "-  1/0" or "2 -"
            card_end = rest.strip().split()[-3:]  # last few tokens
            card_m = re.search(r"(\d+)\s+(\d+)/(\d+)\s*$", rest.strip())
            if card_m:
                p.yellow_cards = int(card_m.group(2))
                p.red_cards    = int(card_m.group(3))

            players.append(p)

        return players


# ── Utility helpers ────────────────────────────────────────────────────────────

def load_report(pdf_path: str) -> WyscoutMatchReport:
    """Convenience factory — load & parse in one call."""
    report = WyscoutMatchReport(pdf_path)
    report.parse()
    return report


def to_streamlit_ready(report: WyscoutMatchReport) -> dict:
    """
    Return a dict of DataFrames + metadata ready to hand directly
    to Streamlit widgets (st.dataframe, st.metric, st.write, etc.)
    """
    data = report.parse()
    return {
        "meta":             data["meta"],
        "team_stats_df":    report.team_stats_df(),
        "player_stats_df":  report.player_stats_df(),
        "home_stats":       data["home_team_stats"],
        "away_stats":       data["away_team_stats"],
    }
