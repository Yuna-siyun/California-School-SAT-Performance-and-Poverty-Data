"""Unit tests for the clean module."""

import pandas as pd
import pytest

from pipeline.clean import (
    SENTINEL_OPEN_DATE,
    clean,
    clean_schools_frpm,
    parse_dates,
    summarize,
)


@pytest.fixture
def sat_sample() -> pd.DataFrame:
    """Small SAT-joined frame covering the cases clean() has to handle."""
    return pd.DataFrame(
        {
            "cds_code": ["01100170000000", "01100170112607", "02100170112608"],
            "county": ["Alameda", "Alameda", "Alpine"],
            "school": [None, "Envision Academy", "Alpine High"],
            "record_type": ["D", "S", "S"],       # one district, two schools
            "avg_total": [1300, 1450, None],      # one suppressed score
            "frpm_rate": [0.50, 0.66, 0.20],      # proportions, not percents
            "open_date": ["2005-08-29", "2006-08-28", SENTINEL_OPEN_DATE],
        }
    )


def test_clean_keeps_only_school_records(sat_sample):
    """District-level rows must not survive cleaning."""
    result = clean(sat_sample)

    assert (result["record_type"] == "S").all()


def test_clean_drops_suppressed_scores(sat_sample):
    """Rows without a SAT total cannot be analyzed, so they are removed."""
    result = clean(sat_sample)

    assert result["avg_total"].notna().all()
    # Only Envision Academy is both school-level and scored.
    assert len(result) == 1


def test_clean_converts_poverty_rate_to_percent(sat_sample):
    """frpm_rate is stored as 0-1 but analysis expects 0-100."""
    result = clean(sat_sample)

    assert result["frpm_pct"].iloc[0] == pytest.approx(66.0)


def test_clean_parses_dates(sat_sample):
    """Dates arrive as text from SQLite and must become datetime."""
    result = clean(sat_sample)

    assert pd.api.types.is_datetime64_any_dtype(result["open_date"])


def test_clean_does_not_mutate_input(sat_sample):
    """The caller must be able to reuse the raw frame afterwards."""
    before = sat_sample.copy()

    clean(sat_sample)

    pd.testing.assert_frame_equal(sat_sample, before)


def test_clean_handles_empty_input():
    """An empty frame should pass through instead of raising."""
    empty = pd.DataFrame(
        columns=["record_type", "avg_total", "frpm_rate", "open_date"]
    )

    result = clean(empty)

    assert result.empty


def test_parse_dates_treats_sentinel_as_missing():
    """1980-07-01 is a placeholder, so it must become NaT rather than a date."""
    df = pd.DataFrame({"open_date": [SENTINEL_OPEN_DATE, "2010-09-01"]})

    result = parse_dates(df)

    assert pd.isna(result["open_date"].iloc[0])
    assert result["open_date"].iloc[1].year == 2010


def test_parse_dates_coerces_invalid_values():
    """A malformed date must not stop the pipeline."""
    df = pd.DataFrame({"open_date": ["not a date", "2010-09-01"]})

    result = parse_dates(df)

    assert pd.isna(result["open_date"].iloc[0])


def test_clean_schools_frpm_requires_an_opening_date():
    """Q2 groups by opening decade, so undated rows are unusable."""
    df = pd.DataFrame(
        {
            "school": ["Kept", "Sentinel", "Missing"],
            "frpm_rate": [0.4, 0.5, 0.6],
            "open_date": ["1999-08-01", SENTINEL_OPEN_DATE, None],
        }
    )

    result = clean_schools_frpm(df)

    assert len(result) == 1
    assert result["school"].iloc[0] == "Kept"


def test_clean_schools_frpm_handles_empty_input():
    """An empty frame should pass through instead of raising."""
    empty = pd.DataFrame(columns=["school", "frpm_rate", "open_date"])

    assert clean_schools_frpm(empty).empty


def test_summarize_reports_shape_and_nulls():
    """summarize() is how the pipeline output gets verified."""
    df = pd.DataFrame({"a": [1, 2, None], "b": ["x", "y", "z"]})

    result = summarize(df)

    assert result["shape"] == (3, 2)
    assert result["null_counts"] == {"a": 1}
    assert "a" in result["dtypes"]