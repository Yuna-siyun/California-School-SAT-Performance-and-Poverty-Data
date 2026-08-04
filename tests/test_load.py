"""Unit tests for the load module."""

import os

import pandas as pd
import pytest

from pipeline.load import load_by_county, load_raw, load_schools_frpm

DB_PATH = "data/cdeschools.sqlite"

# The database ships with the repository, but skipping is safer than failing
# if someone runs the tests from a different working directory.
needs_db = pytest.mark.skipif(
    not os.path.exists(DB_PATH), reason=f"{DB_PATH} not found"
)


@needs_db
def test_load_raw_returns_a_dataframe():
    """The pipeline downstream assumes a DataFrame, not a cursor."""
    result = load_raw(DB_PATH)

    assert isinstance(result, pd.DataFrame)
    assert len(result) > 0


@needs_db
def test_load_raw_has_the_expected_columns():
    """clean() and analyze() reference these names directly."""
    result = load_raw(DB_PATH)

    for column in ["county", "record_type", "avg_total", "frpm_rate"]:
        assert column in result.columns


@needs_db
def test_load_raw_computes_the_score_total():
    """avg_total must equal the three section scores added together."""
    result = load_raw(DB_PATH).dropna(subset=["avg_total"])
    row = result.iloc[0]

    assert row["avg_total"] == row["avg_read"] + row["avg_math"] + row["avg_write"]


@needs_db
def test_load_schools_frpm_has_a_larger_sample():
    """Dropping the satscores join is the whole point of this function."""
    with_scores = load_raw(DB_PATH)
    without_scores = load_schools_frpm(DB_PATH)

    assert len(without_scores) > len(with_scores)


@needs_db
def test_load_by_county_filters_to_one_county():
    """The county parameter must actually reach the query."""
    result = load_by_county(DB_PATH, "Alameda")

    assert len(result) > 0
    assert (result["county"] == "Alameda").all()


@needs_db
def test_load_by_county_returns_empty_for_unknown_county():
    """A name that matches nothing should give no rows, not an error."""
    result = load_by_county(DB_PATH, "Nowhere County")

    assert result.empty


@needs_db
def test_load_by_county_is_not_vulnerable_to_injection():
    """The ? placeholder must treat input as a value, never as SQL."""
    result = load_by_county(DB_PATH, "Alameda' OR '1'='1")

    # If the string were interpolated, this would return every row.
    assert result.empty