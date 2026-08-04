"""Run the full pipeline: load, clean, analyze, and chart."""

import os
import sqlite3

from pipeline.clean import clean, clean_schools_frpm, summarize
from pipeline.load import load_raw, load_schools_frpm
from pipeline import analyze, visualize

DB_PATH = "data/cdeschools.sqlite"
OUTPUT_DIR = "outputs"


def main() -> None:
    """Load the data, verify the cleaning step, then answer all four questions."""
    # Run from the project root regardless of where the command was typed,
    # so the relative paths below always resolve.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Cleaning is reported before analysis so the row counts can be checked
    # against the README rather than taken on trust.
    raw = load_raw(DB_PATH)
    cleaned = clean(raw)
    print(f"SAT sample:  {len(raw):,} rows -> {len(cleaned):,} after cleaning")

    raw_q2 = load_schools_frpm(DB_PATH)
    cleaned_q2 = clean_schools_frpm(raw_q2)
    print(f"Q2 sample:   {len(raw_q2):,} rows -> {len(cleaned_q2):,} after cleaning")

    summary = summarize(cleaned)
    print(f"Shape:       {summary['shape']}")
    print(f"Null counts: {summary['null_counts']}")
    print()

    # Each question pairs one analyze function with one chart function.
    jobs = [
        (
            "q1_county_poverty_vs_sat",
            analyze.analyze_county_poverty_vs_sat,
            visualize.plot_county_poverty_vs_sat,
        ),
        (
            "q2_poverty_by_opening_era",
            analyze.analyze_poverty_by_opening_era,
            visualize.plot_poverty_by_opening_era,
        ),
        (
            "q3_score_distribution",
            analyze.analyze_score_distribution_by_poverty,
            visualize.plot_score_distribution,
        ),
        (
            "q4_above_county_average",
            analyze.analyze_schools_above_county_average,
            visualize.plot_schools_above_county_average,
        ),
    ]

    with sqlite3.connect(DB_PATH) as conn:
        for name, analyze_fn, plot_fn in jobs:
            result = analyze_fn(conn)
            result.to_csv(f"{OUTPUT_DIR}/{name}.csv", index=False)

            figure = plot_fn(result)
            figure.savefig(
                f"{OUTPUT_DIR}/{name}.png", dpi=150, bbox_inches="tight"
            )

            print(f"{name}: {len(result)} rows, chart saved")


if __name__ == "__main__":
    main()