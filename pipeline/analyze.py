"""Answer the four research questions. One function per question.

Each function runs SQL so the required techniques stay visible: a join and
aggregate for Q1, date functions for Q2, a CTE for Q3, and window functions
for Q4. Cleaning rules are imported from clean.py so they are defined once.
"""

import pandas as pd

from pipeline.clean import SCHOOL_RECORD_TYPE, SENTINEL_OPEN_DATE

# frpm splits the join key across three columns; printf restores the padding.
FRPM_KEY = 'f."County Code" || printf(\'%05d\', f."District Code") || f."School Code"'

# Counties with very few schools produce unstable averages and meaningless
# deviations, so they are excluded from county-level comparisons.
MIN_SCHOOLS_PER_COUNTY = 5
MIN_SCHOOLS_FOR_RANKING = 10


def analyze_county_poverty_vs_sat(conn) -> pd.DataFrame:
    """Q1: Compare average poverty and SAT performance by county.

    Uses a three-table join, GROUP BY, and aggregate functions.

    Args:
        conn: Open sqlite3 connection.

    Returns:
        DataFrame with county, n_schools, avg_frpm_pct, avg_total, and
        avg_pct_ge_1500, sorted from the poorest county to the wealthiest.
    """
    sql = f"""
        SELECT s.County                                       AS county,
               COUNT(*)                                       AS n_schools,
               ROUND(AVG(f."Percent (%) Eligible FRPM (K-12)") * 100, 1)
                                                              AS avg_frpm_pct,
               ROUND(AVG(t.AvgScrRead + t.AvgScrMath + t.AvgScrWrite), 1)
                                                              AS avg_total,
               ROUND(AVG(t.PctGE1500), 1)                     AS avg_pct_ge_1500
        FROM schools s
        JOIN satscores t ON s.CDSCode = t.cds
        JOIN frpm f      ON s.CDSCode = {FRPM_KEY}
        WHERE t.rtype = ?
          AND t.AvgScrMath IS NOT NULL
        GROUP BY s.County
        HAVING COUNT(*) >= ?
        ORDER BY avg_frpm_pct DESC
    """
    return pd.read_sql(
        sql, conn, params=(SCHOOL_RECORD_TYPE, MIN_SCHOOLS_PER_COUNTY)
    )


def analyze_poverty_by_opening_era(conn) -> pd.DataFrame:
    """Q2: Track the poverty level of the areas new schools opened in.

    Uses strftime to group schools by the decade they opened. Charter and
    regular schools are kept separate because their trends diverge.

    SAT scores are not needed here, so satscores is left out and the sample
    is roughly three times larger.

    Args:
        conn: Open sqlite3 connection.

    Returns:
        DataFrame with era, school_type, n_schools, and avg_frpm_pct.
    """
    sql = f"""
        SELECT CASE
                 WHEN strftime('%Y', s.OpenDate) < '1990' THEN 'Before 1990'
                 WHEN strftime('%Y', s.OpenDate) < '2000' THEN '1990s'
                 WHEN strftime('%Y', s.OpenDate) < '2010' THEN '2000s'
                 ELSE '2010s'
               END                                            AS era,
               CASE WHEN s.Charter = 1 THEN 'Charter' ELSE 'Regular' END
                                                              AS school_type,
               COUNT(*)                                       AS n_schools,
               ROUND(AVG(f."Percent (%) Eligible FRPM (K-12)") * 100, 1)
                                                              AS avg_frpm_pct
        FROM schools s
        JOIN frpm f ON s.CDSCode = {FRPM_KEY}
        WHERE s.OpenDate IS NOT NULL
          -- This date was stamped on existing schools when CDE built its
          -- electronic system, so it is not a real opening date.
          AND s.OpenDate != ?
          AND f."Percent (%) Eligible FRPM (K-12)" IS NOT NULL
        GROUP BY era, school_type
        ORDER BY era, school_type
    """
    return pd.read_sql(sql, conn, params=(SENTINEL_OPEN_DATE,))


def analyze_score_distribution_by_poverty(conn) -> pd.DataFrame:
    """Q3: Describe how achievement is distributed across poverty quartiles.

    Builds the joined set in a CTE, assigns quartiles with NTILE, then
    aggregates. The quartile boundaries have to exist before grouping, which
    is why a CTE is needed rather than a plain GROUP BY.

    Args:
        conn: Open sqlite3 connection.

    Returns:
        DataFrame with poverty_quartile, n_schools, and the min, mean, and max
        of pct_ge_1500 for each quartile.
    """
    sql = f"""
        WITH joined AS (
            SELECT s.County                                   AS county,
                   f."Percent (%) Eligible FRPM (K-12)" * 100 AS frpm_pct,
                   t.PctGE1500                                AS pct_ge_1500
            FROM schools s
            JOIN satscores t ON s.CDSCode = t.cds
            JOIN frpm f      ON s.CDSCode = {FRPM_KEY}
            WHERE t.rtype = ?
              AND t.PctGE1500 IS NOT NULL
              AND f."Percent (%) Eligible FRPM (K-12)" IS NOT NULL
        ),
        bucketed AS (
            SELECT *,
                   NTILE(4) OVER (ORDER BY frpm_pct) AS poverty_quartile
            FROM joined
        )
        SELECT poverty_quartile,
               COUNT(*)                       AS n_schools,
               ROUND(MIN(frpm_pct), 1)        AS frpm_min,
               ROUND(MAX(frpm_pct), 1)        AS frpm_max,
               ROUND(MIN(pct_ge_1500), 1)     AS pct_min,
               ROUND(AVG(pct_ge_1500), 1)     AS pct_mean,
               ROUND(MAX(pct_ge_1500), 1)     AS pct_max
        FROM bucketed
        GROUP BY poverty_quartile
        ORDER BY poverty_quartile
    """
    return pd.read_sql(sql, conn, params=(SCHOOL_RECORD_TYPE,))


def analyze_schools_above_county_average(conn, top_n: int = 15) -> pd.DataFrame:
    """Q4: Find the schools that most exceed their own county's average.

    Uses RANK and AVG as window functions partitioned by county, so each
    school is measured against its local peers rather than the whole state.

    Args:
        conn: Open sqlite3 connection.
        top_n: How many schools to return.

    Returns:
        DataFrame with county, school, avg_total, rank_in_county, county_avg,
        diff_from_avg, frpm_pct, and is_charter.
    """
    sql = f"""
        WITH school_scores AS (
            SELECT s.County                                   AS county,
                   s.School                                   AS school,
                   s.Charter                                  AS is_charter,
                   f."Percent (%) Eligible FRPM (K-12)" * 100 AS frpm_pct,
                   t.AvgScrRead + t.AvgScrMath + t.AvgScrWrite AS avg_total
            FROM schools s
            JOIN satscores t ON s.CDSCode = t.cds
            JOIN frpm f      ON s.CDSCode = {FRPM_KEY}
            WHERE t.rtype = ?
              AND t.AvgScrMath IS NOT NULL
        ),
        ranked AS (
            SELECT *,
                   RANK()   OVER (PARTITION BY county ORDER BY avg_total DESC)
                                                      AS rank_in_county,
                   AVG(avg_total) OVER (PARTITION BY county)
                                                      AS county_avg,
                   COUNT(*) OVER (PARTITION BY county) AS county_size
            FROM school_scores
        )
        SELECT county,
               school,
               avg_total,
               rank_in_county,
               ROUND(county_avg, 1)              AS county_avg,
               ROUND(avg_total - county_avg, 1)  AS diff_from_avg,
               ROUND(frpm_pct, 1)                AS frpm_pct,
               is_charter
        FROM ranked
        -- In a county with only two or three schools, the gap between them
        -- becomes the deviation, which says nothing about the school.
        WHERE county_size >= ?
        ORDER BY diff_from_avg DESC
        LIMIT ?
    """
    return pd.read_sql(
        sql, conn, params=(SCHOOL_RECORD_TYPE, MIN_SCHOOLS_FOR_RANKING, top_n)
    )


if __name__ == "__main__":
    import os
    import sqlite3

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    with sqlite3.connect("../data/cdeschools.sqlite") as conn:
        print("Q1:", analyze_county_poverty_vs_sat(conn).shape)
        print("Q2:", analyze_poverty_by_opening_era(conn).shape)
        print("Q3:", analyze_score_distribution_by_poverty(conn).shape)
        print("Q4:", analyze_schools_above_county_average(conn).shape)
        print()
        print(analyze_poverty_by_opening_era(conn).to_string(index=False))