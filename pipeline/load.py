"""Load data from the SQLite database."""

import sqlite3

import pandas as pd

# frpm splits the join key across three columns. District Code is stored as an
# INTEGER, so leading zeros are lost; printf pads it back to five digits.
FRPM_KEY = 'f."County Code" || printf(\'%05d\', f."District Code") || f."School Code"'

# Three-table join. Used by Q1, Q3, and Q4.
SQL_ALL = f"""
    SELECT s.CDSCode      AS cds_code,
           s.County       AS county,
           s.School       AS school,
           s.OpenDate     AS open_date,
           s.StatusType   AS status_type,
           s.Charter      AS is_charter,
           t.rtype        AS record_type,
           t.NumTstTakr   AS num_test_takers,
           t.AvgScrRead   AS avg_read,
           t.AvgScrMath   AS avg_math,
           t.AvgScrWrite  AS avg_write,
           t.AvgScrRead + t.AvgScrMath + t.AvgScrWrite AS avg_total,
           t.PctGE1500    AS pct_ge_1500,
           f."Percent (%) Eligible FRPM (K-12)" AS frpm_rate
    FROM schools s
    JOIN satscores t ON s.CDSCode = t.cds
    JOIN frpm f      ON s.CDSCode = {FRPM_KEY}
"""

# schools + frpm only. Q2 does not need SAT scores, so it can use a larger sample.
SQL_SCHOOLS_FRPM = f"""
    SELECT s.CDSCode    AS cds_code,
           s.County     AS county,
           s.School     AS school,
           s.OpenDate   AS open_date,
           s.Charter    AS is_charter,
           f."Percent (%) Eligible FRPM (K-12)" AS frpm_rate
    FROM schools s
    JOIN frpm f ON s.CDSCode = {FRPM_KEY}
"""


def load_raw(path: str) -> pd.DataFrame:
    """Read the three-table join.

    Args:
        path: Path to the SQLite file.

    Returns:
        Raw joined DataFrame. Not cleaned, so it still contains missing values
        and mixed aggregation levels.
    """
    with sqlite3.connect(path) as conn:
        df = pd.read_sql(SQL_ALL, conn)
    return df


def load_schools_frpm(path: str) -> pd.DataFrame:
    """Read schools joined with frpm only. Used by Q2.

    Args:
        path: Path to the SQLite file.

    Returns:
        DataFrame with school details and the poverty indicator.
    """
    with sqlite3.connect(path) as conn:
        df = pd.read_sql(SQL_SCHOOLS_FRPM, conn)
    return df


def load_by_county(path: str, county: str) -> pd.DataFrame:
    """Read schools in one county.

    Binds the county name with a ? placeholder instead of formatting it into
    the SQL string, which prevents SQL injection.

    Args:
        path: Path to the SQLite file.
        county: County name, for example "Alameda".

    Returns:
        DataFrame containing only schools in that county.
    """
    sql = SQL_ALL + " WHERE s.County = ?"

    with sqlite3.connect(path) as conn:
        df = pd.read_sql(sql, conn, params=(county,))
    return df


if __name__ == "__main__":
    # Running this file directly prints a quick sanity check.
    import os

    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    db = "../data/cdeschools.sqlite"

    print("load_raw         :", load_raw(db).shape)
    print("load_schools_frpm:", load_schools_frpm(db).shape)
    print("load_by_county   :", load_by_county(db, "Alameda").shape)