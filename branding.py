from pptx.dml.color import RGBColor

# ── BROOKLYN FC BRAND PALETTE ───────────────────────────────────────────────
COLORS = {
    "BLACK":     "111111",   # Primary backgrounds & headers
    "GOLD":      "C8A84B",   # Accent lines, titles, BKFC data highlights
    "SILVER":    "BFC5CC",   # Neutral secondary text, borders, league benchmarks
    "WHITE":     "FFFFFF",   # Content area backgrounds
    "DARK_GRAY": "2A2A2A",   # Subtle block backgrounds / insight cards
    "GRID":      "E6E6E6",   # Subtle gridlines for tables
    "ROW_ALT":   "F5F5F5",   # Alternating table row background
    "GREEN":     "4CAF50",   # Positive performance indicators
    "RED":       "E53935",   # Negative performance indicators
}


def get_rgb(hex_str: str) -> RGBColor:
    """Convert a 6-char hex string to a python-pptx RGBColor."""
    return RGBColor(
        int(hex_str[0:2], 16),
        int(hex_str[2:4], 16),
        int(hex_str[4:6], 16),
    )
