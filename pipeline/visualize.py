"""Build one chart per research question.

Each function takes the DataFrame produced by the matching analyze function
and returns a Figure. Saving is left to main.py so these stay testable.
"""

import matplotlib

# CI runners have no display, so a GUI backend would fail there. Agg writes to
# a buffer instead. This must be set before pyplot is imported.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

CHARTER_COLOR = "#d85a30"
REGULAR_COLOR = "#378add"
NEUTRAL_COLOR = "#5f5e5a"


def plot_county_poverty_vs_sat(df: pd.DataFrame) -> plt.Figure:
    """Q1: Scatter county poverty against average SAT total.

    Point size reflects how many schools each county contributes, so counties
    resting on a small sample are visibly less reliable.

    Args:
        df: Output of analyze_county_poverty_vs_sat().

    Returns:
        Figure. Not saved or shown.
    """
    fig, ax = plt.subplots(figsize=(9, 6))

    ax.scatter(
        df["avg_frpm_pct"],
        df["avg_total"],
        s=df["n_schools"] * 4,
        alpha=0.6,
        color=REGULAR_COLOR,
        edgecolors="white",
        linewidth=0.5,
    )

    # A trend line makes the direction readable without implying causation.
    if len(df) >= 2:
        slope, intercept = _fit_line(df["avg_frpm_pct"], df["avg_total"])
        x_line = [df["avg_frpm_pct"].min(), df["avg_frpm_pct"].max()]
        y_line = [slope * x + intercept for x in x_line]
        ax.plot(x_line, y_line, color=NEUTRAL_COLOR, linestyle="--", linewidth=1)

    ax.set_xlabel("Students eligible for free or reduced-price meals (%)")
    ax.set_ylabel("Average SAT total (out of 2400)")
    ax.set_title("County poverty and SAT performance")
    ax.grid(True, alpha=0.2)

    # Readers need to know the dot size carries information.
    ax.annotate(
        "Dot size = number of schools in the county",
        xy=(0.02, 0.02),
        xycoords="axes fraction",
        fontsize=9,
        color=NEUTRAL_COLOR,
    )

    fig.tight_layout()
    return fig


def plot_poverty_by_opening_era(df: pd.DataFrame) -> plt.Figure:
    """Q2: Grouped bars of poverty level by opening era and school type.

    Args:
        df: Output of analyze_poverty_by_opening_era().

    Returns:
        Figure. Not saved or shown.
    """
    fig, ax = plt.subplots(figsize=(9, 6))

    # Pivot so each era becomes a group with one bar per school type.
    pivot = df.pivot(index="era", columns="school_type", values="avg_frpm_pct")

    # Chronological order, since alphabetical would scramble the timeline.
    era_order = ["Before 1990", "1990s", "2000s", "2010s"]
    pivot = pivot.reindex([e for e in era_order if e in pivot.index])

    positions = range(len(pivot))
    width = 0.38

    if "Charter" in pivot.columns:
        ax.bar(
            [p - width / 2 for p in positions],
            pivot["Charter"],
            width,
            label="Charter",
            color=CHARTER_COLOR,
        )
    if "Regular" in pivot.columns:
        ax.bar(
            [p + width / 2 for p in positions],
            pivot["Regular"],
            width,
            label="Regular",
            color=REGULAR_COLOR,
        )

    ax.set_xticks(list(positions))
    ax.set_xticklabels(pivot.index)
    ax.set_xlabel("Decade the school opened")
    ax.set_ylabel("Average poverty rate of the school (%)")
    ax.set_title("Poverty level of areas where new schools opened")
    ax.legend()
    ax.grid(True, axis="y", alpha=0.2)

    fig.tight_layout()
    return fig


def plot_score_distribution(df: pd.DataFrame) -> plt.Figure:
    """Q3: Show the spread of achievement within each poverty quartile.

    Bars carry the mean and the vertical lines carry the observed range, so a
    quartile with a low mean but a wide range is not mistaken for a uniform
    one.

    Args:
        df: Output of analyze_score_distribution_by_poverty().

    Returns:
        Figure. Not saved or shown.
    """
    fig, ax = plt.subplots(figsize=(9, 6))

    positions = range(len(df))

    ax.bar(positions, df["pct_mean"], width=0.6, color=REGULAR_COLOR, alpha=0.75)

    # Draw the min-max range as a thin line through each bar.
    for pos, row in zip(positions, df.itertuples()):
        ax.plot(
            [pos, pos],
            [row.pct_min, row.pct_max],
            color=NEUTRAL_COLOR,
            linewidth=1.2,
        )
        ax.plot([pos - 0.1, pos + 0.1], [row.pct_min] * 2, color=NEUTRAL_COLOR)
        ax.plot([pos - 0.1, pos + 0.1], [row.pct_max] * 2, color=NEUTRAL_COLOR)

    labels = [
        f"Q{row.poverty_quartile}\n{row.frpm_min:.0f}-{row.frpm_max:.0f}% poverty"
        for row in df.itertuples()
    ]
    ax.set_xticks(list(positions))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_xlabel("Poverty quartile (Q1 = least poor)")
    ax.set_ylabel("Students scoring 1500 or above (%)")
    ax.set_title("Achievement across poverty quartiles")
    ax.grid(True, axis="y", alpha=0.2)

    ax.annotate(
        "Bar = mean, line = observed range",
        xy=(0.02, 0.95),
        xycoords="axes fraction",
        fontsize=9,
        color=NEUTRAL_COLOR,
    )

    fig.tight_layout()
    return fig


def plot_top_schools_by_poverty_quartile(df: pd.DataFrame) -> plt.Figure:
    """Q4: Show the strongest schools in each poverty quartile.

    Grouping by quartile keeps each school next to the peers it was ranked
    against, so a high bar in the poorest quartile reads as what it is.

    Args:
        df: Output of analyze_top_schools_by_poverty_quartile().

    Returns:
        Figure. Not saved or shown.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # Reverse so the least poor quartile ends up at the top of the chart.
    plot_df = df.iloc[::-1].reset_index(drop=True)

    colors = [
        CHARTER_COLOR if charter == 1 else REGULAR_COLOR
        for charter in plot_df["is_charter"]
    ]

    positions = range(len(plot_df))
    ax.barh(positions, plot_df["avg_total"], color=colors)

    labels = [
        f"Q{row.poverty_quartile}  {row.school[:30]} ({row.frpm_pct:.0f}%)"
        for row in plot_df.itertuples()
    ]
    ax.set_yticks(list(positions))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Average SAT total (out of 2400)")
    ax.set_title("Strongest schools within each poverty quartile")
    ax.grid(True, axis="x", alpha=0.2)

    # Each quartile's own average, so the bars can be read against the right
    # baseline rather than against the whole state.
    for pos, row in zip(positions, plot_df.itertuples()):
        ax.plot(
            [row.quartile_avg, row.quartile_avg],
            [pos - 0.4, pos + 0.4],
            color=NEUTRAL_COLOR,
            linewidth=1.5,
        )

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=CHARTER_COLOR),
        plt.Rectangle((0, 0), 1, 1, color=REGULAR_COLOR),
    ]
    ax.legend(
        handles + [plt.Line2D([0], [0], color=NEUTRAL_COLOR, linewidth=1.5)],
        ["Charter", "Regular", "Quartile average"],
        loc="lower right",
    )

    ax.annotate(
        "Label shows quartile, school, and poverty rate",
        xy=(0.02, 0.02),
        xycoords="axes fraction",
        fontsize=9,
        color=NEUTRAL_COLOR,
    )

    fig.tight_layout()
    return fig


def _fit_line(x: pd.Series, y: pd.Series) -> tuple:
    """Fit a least-squares line and return its slope and intercept.

    Written out rather than pulled from numpy.polyfit so the dependency list
    stays short and the arithmetic is visible.

    Args:
        x: Predictor values.
        y: Response values.

    Returns:
        Tuple of (slope, intercept). Returns (0, mean of y) if x has no spread.
    """
    x_mean = x.mean()
    y_mean = y.mean()

    denominator = ((x - x_mean) ** 2).sum()
    if denominator == 0:
        return 0.0, y_mean

    slope = ((x - x_mean) * (y - y_mean)).sum() / denominator
    return slope, y_mean - slope * x_mean


if __name__ == "__main__":
    import os
    import sqlite3

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    import analyze

    with sqlite3.connect("../data/cdeschools.sqlite") as conn:
        figures = {
            "q1": plot_county_poverty_vs_sat(
                analyze.analyze_county_poverty_vs_sat(conn)
            ),
            "q2": plot_poverty_by_opening_era(
                analyze.analyze_poverty_by_opening_era(conn)
            ),
            "q3": plot_score_distribution(
                analyze.analyze_score_distribution_by_poverty(conn)
            ),
            "q4": plot_schools_above_county_average(
                analyze.analyze_schools_above_county_average(conn)
            ),
        }

    for name, fig in figures.items():
        fig.savefig(f"../outputs/{name}_preview.png", dpi=120, bbox_inches="tight")
        print(f"{name} saved")