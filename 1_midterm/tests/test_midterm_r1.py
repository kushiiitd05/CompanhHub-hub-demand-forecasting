"""Unit tests for the r1 midterm analysis.  Run:  pytest -q tests/

Needs 01_prepare.py to have run (it writes the derived frames).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from common import DERIVED, OUT, load_meta, load_train
from inference import chi2_independence, paired_t, pearson_t, two_prop_diff


@pytest.fixture(scope="module")
def clean() -> pd.DataFrame:
    return pd.read_parquet(DERIVED / "hubday_clean.parquet")


def test_keys_unique() -> None:
    tr = load_train()
    assert not tr.duplicated(["HubID", "Date"]).any()
    assert load_meta()["HubID"].is_unique


def test_closed_rows_are_structural_zeros(clean: pd.DataFrame) -> None:
    closed = clean[clean["IsOpen"].eq(0)]
    assert len(closed) == 166_269
    assert closed["OrderVolume"].eq(0).all() and closed["AppSessions"].eq(0).all()


def test_prepare_does_not_drop_or_mutate_rows(clean: pd.DataFrame) -> None:
    tr = load_train().sort_values(["HubID", "Date"]).reset_index(drop=True)
    c = clean.sort_values(["HubID", "Date"]).reset_index(drop=True)
    assert len(c) == len(tr) == 970_379
    for col in tr.columns:
        assert (c[col].to_numpy() == tr[col].to_numpy()).all(), col


def test_waterfall_adds_up() -> None:
    w = pd.read_csv(OUT / "prep_waterfall.csv").set_index("step")["rows"]
    vals = w.to_numpy()
    grid, absent, rows, closed, open_, oz, base = vals[:7]
    assert grid - absent == rows and rows - closed == open_ and open_ - oz == base


def test_encoded_shape() -> None:
    schema = pd.read_csv(OUT / "prep_encoded_schema.csv")
    assert len(schema) == 46 and schema["attribute"].is_unique


def test_t2_table_sums_to_all_hubs() -> None:
    t = pd.read_csv(OUT / "t2_contingency.csv")
    assert int(t["no_gap"].sum() + t["gap"].sum()) == 1115
    assert int(t["gap"].sum()) == 180


def test_paired_t_matches_textbook() -> None:
    d = np.array([1.0, 2.0, 3.0, 4.0, 6.0])
    r = paired_t(d, 1.0)
    t = d.mean() / (d.std(ddof=1) / np.sqrt(5))
    assert np.isclose(r["statistic"], t) and r["df"] == 4
    assert np.isclose(r["p"], 2 * stats.t.sf(t, 4))


def test_pearson_t_formula() -> None:
    rng = np.random.default_rng(0)
    x = rng.normal(size=200)
    y = 0.3 * x + rng.normal(size=200)
    r = pearson_t(x, y, 0.1)
    assert np.isclose(r["statistic"], r["estimate"] * np.sqrt(198) / np.sqrt(1 - r["estimate"]**2))
    assert np.isclose(r["ci_low"], r["scipy_ci_low"]) and np.isclose(r["ci_high"], r["scipy_ci_high"])


def test_chi2_and_two_prop() -> None:
    rows = np.repeat([0, 1], [50, 50])
    cols = np.r_[np.repeat([0, 1], [40, 10]), np.repeat([0, 1], [20, 30])]
    table = pd.crosstab(rows, cols).to_numpy()
    r = chi2_independence(table, 500, np.random.default_rng(1), rows, cols)
    assert r["df"] == 1 and np.isclose(r["statistic"], stats.chi2_contingency(table, correction=False)[0])
    assert r["p"] < 0.01
    tp = two_prop_diff(30, 50, 10, 50, 0.05)
    assert np.isclose(tp["estimate"], 0.4) and tp["ci_low"] < 0.4 < tp["ci_high"]
