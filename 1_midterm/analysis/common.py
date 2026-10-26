"""Shared paths and loaders for the CSE558 midterm analysis (revision r1).

Every loader returns a fresh DataFrame; nothing here mutates its inputs.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]          # 1_midterm/
DATA = ROOT / "data" / "raw"
OUT = ROOT / "results"
FIG = ROOT / "figures"
DERIVED = ROOT / "results" / "derived"   # git-ignored, large
for _d in (OUT, FIG, DERIVED):
    _d.mkdir(parents=True, exist_ok=True)

TRAIN_START = pd.Timestamp("2013-01-01")
TRAIN_END = pd.Timestamp("2015-06-19")
GAP_START = pd.Timestamp("2014-07-01")
GAP_END = pd.Timestamp("2014-12-31")
ALPHA = 0.05
N_TESTS = 4
SEED = 558


def sha256(path: Path) -> str:
    """SHA-256 of a file, read in 1 MB chunks."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_train() -> pd.DataFrame:
    return pd.read_csv(DATA / "orders_train.csv", parse_dates=["Date"])


def load_test() -> pd.DataFrame:
    return pd.read_csv(DATA / "orders_test.csv", parse_dates=["Date"])


def load_meta() -> pd.DataFrame:
    return pd.read_csv(DATA / "hub_metadata.csv")


def open_days(train: pd.DataFrame) -> pd.DataFrame:
    """Rows with IsOpen == 1 (a new frame)."""
    return train.loc[train["IsOpen"] == 1].copy()


def moment_skew(x: np.ndarray) -> float:
    """Moment coefficient of skewness g1 = m3 / m2^(3/2) (population moments)."""
    x = np.asarray(x, dtype=float)
    d = x - x.mean()
    return float(np.mean(d**3) / np.mean(d**2) ** 1.5)


def moment_kurt(x: np.ndarray) -> float:
    """Moment kurtosis m4 / m2^2 (normal = 3, Lecture 3 convention)."""
    x = np.asarray(x, dtype=float)
    d = x - x.mean()
    return float(np.mean(d**4) / np.mean(d**2) ** 2)


def save(df: pd.DataFrame, name: str) -> Path:
    """Write a result table under results/r1 and return its path."""
    path = OUT / name
    df.to_csv(path, index=False)
    return path
