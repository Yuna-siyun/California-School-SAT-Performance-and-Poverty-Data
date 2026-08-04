"""Clean the raw data so it is ready for analysis.

Three problems in this dataset are handled here:
  1. satscores mixes state, county, district, and school aggregates.
  2. frpm_rate is stored as a proportion (0-1) despite its "Percent" name.
  3. open_date uses 1980-07-01 as a placeholder, not a real opening date.
"""

import pandas as pd

# CDE stamped this date on every school that already existed when their
# electronic system was built. It covers 65% of all opening dates, so it is a
# disguised missing value rather than a real one.
SENTINEL_OPEN_DATE = "1980-07-01"

# satscores aggregation codes. Only "S" means an individual school.
SCHOOL_RECORD_TYPE = "S"


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the SAT-joined data for Q1, Q3, and Q4.

    Transforms applied:
        1. Keep school-level rows only
        2. Drop rows with missing SAT scores
        3. Convert frpm_rate from a proportion to a percentage
        4. Parse dates and treat the sentinel as missing

    Args:
        df: Raw DataFrame from load_raw().

    Returns:
        Cleaned DataFrame, about 1,251 rows. Returns an empty DataFrame with
        the same columns if the input is empty.
    """
    # An empty input must pass through without raising, since later steps
    # still expect the column structure to exist.
    if df.empty:
        return df.copy()

    # Never modify the caller's DataFrame. Keeping the raw version intact lets
    # us compare before and after to verify what was removed.
    out = df.copy()

    # satscores stores state (X), county (C), district (D), and school (S)
    # aggregates in one table. Averaging without this filter counts the same
    # students several times.
    out = out[out["record_type"] == SCHOOL_RECORD_TYPE]

    # Schools with fewer than 11 test takers have their scores suppressed to
    # protect student privacy. Imputing a value would invent performance that
    # was never measured, so these rows are dropped instead. The sample is
    # therefore limited to schools with 11 or more test takers.
    out = out.dropna(subset=["avg_total"])

    # The column is named "Percent (%) Eligible FRPM" but holds values like
    # 0.66. Converting to a percentage keeps it on the same scale as
    # pct_ge_1500 and stops charts from being read as fractions of a percent.
    out["frpm_pct"] = out["frpm_rate"] * 100

    # SQLite has no date type, so open_date arrives as text. Converting to
    # datetime is what makes .dt.year and date comparisons possible.
    out = parse_dates(out)

    # Filtering leaves gaps in the index, which is confusing when the result
    # is later merged or written out.
    return out.reset_index(drop=True)


def clean_schools_frpm(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the schools-plus-frpm data for Q2.

    No SAT scores are involved, so there is no record_type filter and no score
    check. Opening dates are required instead, since they are the analysis axis.

    Args:
        df: Raw DataFrame from load_schools_frpm().

    Returns:
        Cleaned DataFrame, about 3,701 rows. Returns an empty DataFrame with
        the same columns if the input is empty.
    """
    if df.empty:
        return df.copy()

    out = df.copy()

    # Same unit problem as above.
    out["frpm_pct"] = out["frpm_rate"] * 100

    # Parse dates; the sentinel becomes NaT here.
    out = parse_dates(out)

    # Q2 groups schools by when they opened, so rows without a usable date
    # cannot contribute. Sentinel rows are already NaT and drop out here too.
    out = out.dropna(subset=["open_date"])

    # Without a poverty figure there is nothing to compare across eras.
    out = out.dropna(subset=["frpm_pct"])

    return out.reset_index(drop=True)


def parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Convert date columns to datetime and mark the sentinel as missing.

    1980-07-01 is a valid-looking date, so nothing filters it automatically.
    Converting it to NaT lets every later step treat it like any other
    missing value.

    Args:
        df: DataFrame containing an open_date column.

    Returns:
        DataFrame with parsed dates. The input is not modified.
    """
    out = df.copy()

    if "open_date" in out.columns:
        # Compare as text before parsing, so the check matches the raw value
        # exactly and the intent is easy to read.
        out.loc[out["open_date"] == SENTINEL_OPEN_DATE, "open_date"] = None

        # errors="coerce" turns unparseable values into NaT instead of raising,
        # so one bad row cannot stop the whole pipeline.
        out["open_date"] = pd.to_datetime(out["open_date"], format="%Y-%m-%d", errors="coerce")

    return out


def summarize(df: pd.DataFrame) -> dict:
    """Summarize a DataFrame so the result can be verified.

    Args:
        df: DataFrame to summarize.

    Returns:
        Dict with "shape", "null_counts", and "dtypes".
    """
    null_counts = df.isna().sum()

    return {
        "shape": df.shape,
        "null_counts": null_counts[null_counts > 0].to_dict(),
        "dtypes": df.dtypes.astype(str).to_dict(),
    }


if __name__ == "__main__":
    import os

    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    from load import load_raw, load_schools_frpm

    db = "../data/cdeschools.sqlite"

    raw = load_raw(db)
    q2_raw = load_schools_frpm(db)

    print("clean            :", raw.shape[0], "->", clean(raw).shape[0])
    print("clean_schools_frpm:", q2_raw.shape[0], "->", clean_schools_frpm(q2_raw).shape[0])
    print(summarize(clean(raw)))