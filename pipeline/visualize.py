"""Build one chart per research question.

Each function takes the DataFrame produced by the matching analyze function and
returns a Figure. Saving is left to main.py so these stay testable.
"""

import matplotlib

# CI runners have no display, so a GUI backend would fail there. Agg writes to a
# buffer instead. This must be set before pyplot is imported.
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

NAVY = "#1E2761"
CORAL = "#E8734A"
LIGHT = "#CADCFC"
GREY = "#6B7280"

# Chronological order. Alphabetical sorting would scramble the timeline.
ERA_ORDER = ["Before 2000", "2000s", "2010s"]

# NTILE(4) returns 1-4; these read better on an axis than bare numbers.
QUARTILE_NAMES = {1: "Least poor", 2: "2nd quartile", 3: "3rd quartile", 4: "Poorest"}
QUARTILE_SHORT = {1: "Least poor", 2: "2nd", 3: "3rd", 4: "Poorest"}


def _style(ax):
    """Apply the shared look: no top or right spine, muted labels, light grid."""
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#D6DBE8")
    ax.tick_params(colors="#5A6178")
    ax.xaxis.label.set_color("#33384D")
    ax.yaxis.label.set_color("#33384D")


def plot_county_poverty_vs_sat(df: pd.DataFrame) -> plt.Figure:
    """Q1: Scatter county poverty against average SAT total.

    Point size reflects how many schools each county contributes, so counties
    resting on a small sample are visibly less reliable.

    Args:
        df: Output of analyze_county_poverty_vs_sat().

    Returns:
        Figure. Not saved or shown.
    """
    fig, ax = plt.subplots(figsize=(8, 4.8))

    ax.scatter(
        df["avg_frpm_pct"],
        df["avg_total"],
        s=df["n_schools"] * 3.2,
        alpha=0.55,
        color=NAVY,
        edgecolors="white",
        linewidth=0.7,
        zorder=3,
    )

    # A trend line makes the direction readable without implying causation.
    if len(df) >= 2:
        slope, intercept = _fit_line(df["avg_frpm_pct"], df["avg_total"])
        x_line = [df["avg_frpm_pct"].min(), df["avg_frpm_pct"].max()]
        ax.plot(
            x_line,
            [slope * x + intercept for x in x_line],
            color=CORAL,
            linestyle="--",
            linewidth=1.8,
            zorder=2,
        )

    # Label the two ends so the reader has an anchor at each extreme.
    for name, dx, dy in [("Marin", 1.8, -6), ("Merced", 1.6, -16)]:
        match = df[df["county"] == name]
        if not match.empty:
            row = match.iloc[0]
            ax.annotate(
                name,
                (row["avg_frpm_pct"], row["avg_total"]),
                xytext=(row["avg_frpm_pct"] + dx, row["avg_total"] + dy),
                fontsize=9.5,
                color=GREY,
            )

    ax.set_xlabel("Students eligible for subsidized meals (%)", fontsize=10)
    ax.set_ylabel("Average SAT total (of 2400)", fontsize=10)
    ax.grid(alpha=0.18, zorder=0)
    ax.text(
        0.02, 0.03, "Dot size = schools in county",
        transform=ax.transAxes, fontsize=8.5, color=GREY,
    )

    _style(ax)
    fig.tight_layout()
    return fig


def plot_poverty_by_opening_era(df: pd.DataFrame) -> plt.Figure:
    """Q2: Grouped bars of poverty level by opening era and school type.

    Args:
        df: Output of analyze_poverty_by_opening_era().

    Returns:
        Figure. Not saved or shown.
    """
    fig, ax = plt.subplots(figsize=(8, 4.8))

    pivot = df.pivot(index="era", columns="school_type", values="avg_frpm_pct")
    pivot = pivot.reindex([e for e in ERA_ORDER if e in pivot.index])

    positions = range(len(pivot))
    width = 0.34

    for offset, column, color in [(-width / 2, "Charter", CORAL),
                                  (width / 2, "Regular", NAVY)]:
        if column not in pivot.columns:
            continue
        ax.bar(
            [p + offset for p in positions], pivot[column], width,
            label=column, color=color, zorder=3,
        )
        # Printing the value removes any need to read heights off the axis.
        for i, value in enumerate(pivot[column]):
            ax.text(
                i + offset, value + 1, f"{value:.0f}%",
                ha="center", fontsize=10, color=color, weight="bold",
            )

    ax.set_xticks(list(positions))
    ax.set_xticklabels(pivot.index, fontsize=10.5)
    ax.set_ylabel("Average poverty rate of the school (%)", fontsize=10)
    ax.set_ylim(0, 80)
    ax.legend(frameon=False, fontsize=10)
    ax.grid(axis="y", alpha=0.18, zorder=0)

    _style(ax)
    fig.tight_layout()
    return fig


def plot_score_distribution(df: pd.DataFrame) -> plt.Figure:
    """Q3: Show the spread of achievement within each poverty quartile.

    The dot is the mean and the bar is the observed range. The shaded band marks
    where the wealthiest and poorest quartiles overlap, which is the finding a
    chart of means alone would hide.

    Args:
        df: Output of analyze_score_distribution_by_poverty().

    Returns:
        Figure. Not saved or shown.
    """
    fig, ax = plt.subplots(figsize=(8, 4.8))

    for i, row in df.reset_index(drop=True).iterrows():
        color = NAVY if row["poverty_quartile"] < 3 else CORAL
        ax.plot(
            [i, i], [row["pct_min"], row["pct_max"]],
            color=color, linewidth=3, alpha=0.35,
            solid_capstyle="round", zorder=2,
        )
        ax.plot(i, row["pct_mean"], "o", markersize=13, color=color, zorder=4)
        ax.text(
            i + 0.16, row["pct_mean"] - 4.5, f"{row['pct_mean']:.1f}%",
            fontsize=10.5, color=color, va="center", weight="bold",
        )

    # The overlap runs from the weakest school in the least poor quartile to the
    # strongest school in the poorest one.
    low = df.loc[df["poverty_quartile"] == 1, "pct_min"].iloc[0]
    high = df.loc[df["poverty_quartile"] == 4, "pct_max"].iloc[0]

    ax.axhline(low, color=GREY, linestyle=":", linewidth=1.2, zorder=1)
    ax.axhline(high, color=GREY, linestyle=":", linewidth=1.2, zorder=1)
    ax.axhspan(low, high, color=LIGHT, alpha=0.32, zorder=0)

    ax.text(len(df) - 0.56, (low + high) / 2, "overlap",
            fontsize=10, color=GREY, ha="center", rotation=90)
    ax.text(-0.44, high + 3.3, f"{high:.1f}", fontsize=10.5, color=GREY,
            va="center", ha="right", weight="bold")
    ax.text(-0.44, low - 3.3, f"{low:.1f}", fontsize=10.5, color=GREY,
            va="center", ha="right", weight="bold")

    ax.annotate(
        "strongest school\nin poorest quartile",
        xy=(len(df) - 1, high), xytext=(len(df) - 2.25, high + 16),
        fontsize=9, color=GREY, ha="center",
        arrowprops=dict(arrowstyle="-", color=GREY, linewidth=0.8,
                        connectionstyle="arc3,rad=-0.2"),
    )
    ax.annotate(
        "weakest school\nin wealthiest quartile",
        xy=(0.0, low - 1.0), xytext=(0.02, low - 11.7),
        fontsize=9, color=GREY, ha="center",
        arrowprops=dict(arrowstyle="-", color=GREY, linewidth=0.8,
                        connectionstyle="arc3,rad=0.0"),
    )

    labels = [
        f"{QUARTILE_NAMES[int(r.poverty_quartile)]}\n"
        f"{r.frpm_min:.0f}–{r.frpm_max:.0f}% poverty"
        for r in df.itertuples()
    ]
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylabel("Students scoring 1500 or above (%)", fontsize=10)
    ax.set_xlim(-0.95, len(df) - 0.15)
    ax.grid(axis="y", alpha=0.18, zorder=0)
    ax.text(0.01, 0.96, "Dot = mean, bar = observed range",
            transform=ax.transAxes, fontsize=8.5, color=GREY)

    _style(ax)
    fig.tight_layout()
    return fig


def plot_top_schools_by_poverty_quartile(df: pd.DataFrame) -> plt.Figure:
    """Q4: Show the strongest schools in each poverty quartile.

    The dashed line is the mean of the wealthiest quartile, so a bar reaching it
    from the poorest quartile is immediately readable.

    Args:
        df: Output of analyze_top_schools_by_poverty_quartile().

    Returns:
        Figure. Not saved or shown.
    """
    fig, ax = plt.subplots(figsize=(8.4, 5.2))

    # Reverse so the poorest quartile lands at the top of the chart.
    plot_df = df.sort_values(
        ["poverty_quartile", "rank_in_quartile"], ascending=[True, False]
    ).reset_index(drop=True)

    labels = []
    for i, row in plot_df.iterrows():
        color = CORAL if row["is_charter"] == 1 else NAVY
        ax.barh(i, row["avg_total"], color=color, zorder=3, height=0.66)
        ax.text(
            row["avg_total"] - 22, i, f"{row['avg_total']:,.0f}",
            ha="right", va="center", fontsize=9.5,
            color="white", weight="bold", zorder=5,
        )
        labels.append(
            f"{QUARTILE_SHORT[int(row['poverty_quartile'])]} · "
            f"{row['school'][:30]} · {row['frpm_pct']:.0f}%"
        )

    ax.set_yticks(range(len(plot_df)))
    ax.set_yticklabels(labels, fontsize=8.8)

    wealthiest_mean = df.loc[df["poverty_quartile"] == 1, "quartile_avg"].iloc[0]
    ax.axvline(wealthiest_mean, color=GREY, linestyle="--", linewidth=1.4, zorder=4)
    ax.text(
        wealthiest_mean + 19, len(plot_df) - 0.42,
        f"Wealthiest quartile mean  {wealthiest_mean:,.0f}",
        fontsize=9, color=GREY, va="center",
    )

    ax.set_xlabel("Average SAT total (of 2400)", fontsize=10)
    # Every score sits above 1,200, so starting there keeps the differences
    # readable. The value is printed on each bar so nothing is hidden.
    ax.set_xlim(1200, plot_df["avg_total"].max() + 100)
    ax.set_ylim(-0.7, len(plot_df) - 0.1)
    ax.grid(axis="x", alpha=0.16, zorder=0)

    handles = [
        plt.Rectangle((0, 0), 1, 1, color=CORAL),
        plt.Rectangle((0, 0), 1, 1, color=NAVY),
    ]
    ax.legend(handles, ["Charter", "Regular"], frameon=False, fontsize=9.5,
              ncol=2, loc="upper center", bbox_to_anchor=(0.62, -0.10))

    _style(ax)
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
