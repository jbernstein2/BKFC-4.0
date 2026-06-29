def safe_float(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def generate_insights(stats_list: list[dict]) -> list[str]:
    """
    Rule-based insight engine. Produces detailed, contextual language
    by evaluating each stat against the season baseline.

    Each entry in stats_list must have:
        label   — human-readable metric name
        match   — value from this match
        season  — season average (excluding this match)
    """
    insights = []

    for s in stats_list:
        label  = s["label"]
        match  = safe_float(s["match"])
        season = safe_float(s["season"])

        if season == 0:
            continue

        diff    = match - season
        pct     = diff / season  # fractional deviation

        # ── Large positive outlier ──────────────────────────────────────────
        if pct > 0.30:
            insights.append(
                f"{label} was exceptional this match at {match:.2g}, running "
                f"{pct:.0%} above our season baseline of {season:.2g}. "
                f"This represents one of our stronger single-match outputs in this category."
            )
        elif pct > 0.15:
            insights.append(
                f"{label} came in above expectations at {match:.2g} "
                f"(+{pct:.0%} vs. season avg {season:.2g}), indicating a strong showing in this phase."
            )

        # ── Large negative outlier ──────────────────────────────────────────
        elif pct < -0.30:
            insights.append(
                f"{label} dropped sharply to {match:.2g} this match, "
                f"representing a {abs(pct):.0%} decline from our season average of {season:.2g}. "
                f"This is an area that warrants closer review in the next preparation cycle."
            )
        elif pct < -0.15:
            insights.append(
                f"{label} fell below our typical standard at {match:.2g} "
                f"({pct:.0%} vs. season avg {season:.2g}). Performance in this area was below par."
            )

    # ── Fallback if no strong deviations detected ───────────────────────────
    if not insights:
        insights.append(
            "Performance metrics tracked closely within established season baselines across all phases. "
            "No significant statistical outliers were detected in this fixture."
        )

    return insights[:6]  # Cap at 6 to prevent slide overflow


def generate_phase_insights(attack_stats: list[dict], defense_stats: list[dict]) -> dict:
    """
    Generate separate insight bullets for the attacking and defensive
    phase breakdown slides.
    Returns {"attack": [...], "defense": [...]}
    """
    return {
        "attack":  generate_insights(attack_stats),
        "defense": generate_insights(defense_stats),
    }
