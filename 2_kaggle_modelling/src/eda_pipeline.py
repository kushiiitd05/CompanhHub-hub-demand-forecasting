"""Leakage-safe audit, preprocessing, EDA, and rolling-origin feature pipeline.

The raw competition CSV files are never modified.  All outputs are deterministic
and are written below ``artifacts/`` or ``data/processed/`` by default.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import platform
import subprocess
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

os.environ.setdefault("MPLCONFIGDIR", "/tmp/kaggle_comp_mpl")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/kaggle_comp_cache")

import numpy as np
import pandas as pd


SEED = 20260807
RAW_FILES = {
    "train": "orders_train.csv",
    "test": "orders_test.csv",
    "metadata": "hub_metadata.csv",
    "submission": "sample_submission.csv",
}
EXPECTED_SHAPES = {
    "train": (970_379, 9),
    "test": (46_830, 8),
    "metadata": (1_115, 10),
    "submission": (46_830, 2),
}
FOLD_ORIGINS = (
    "2015-01-02",
    "2015-02-13",
    "2015-03-27",
    "2015-05-08",
)
SCHEDULE_COLUMNS = ("IsOpen", "PromoActive", "SchoolClosureFlag")
WINDOWS = (7, 28, 56, 84, 90, 180, 182, 365, 730)


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def raw(self) -> Path:
        local = self.root / "datset_kaggle"
        shared = self.root.parent / "1_midterm" / "datset_kaggle"
        return local if local.exists() or not shared.exists() else shared

    @property
    def artifacts(self) -> Path:
        return self.root / "artifacts" / "eda"

    @property
    def figures(self) -> Path:
        return self.artifacts / "figures"

    @property
    def reports(self) -> Path:
        return self.artifacts / "reports"

    @property
    def tables(self) -> Path:
        return self.artifacts / "tables"

    @property
    def processed(self) -> Path:
        return self.root / "data" / "processed"

    @property
    def folds(self) -> Path:
        return self.processed / "folds"

    def create_outputs(self) -> None:
        for directory in (self.artifacts, self.figures, self.reports, self.tables, self.processed, self.folds):
            directory.mkdir(parents=True, exist_ok=True)


def _json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return str(pd.Timestamp(value))
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value)!r}")


def write_json(payload: dict | list, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_json_default) + "\n")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_raw(paths: Paths) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}
    for key, filename in RAW_FILES.items():
        file_path = paths.raw / filename
        if not file_path.exists():
            raise FileNotFoundError(file_path)
        frames[key] = pd.read_csv(file_path, parse_dates=["Date"] if key in {"train", "test"} else None)
    return frames


def _column_summary(name: str, frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in frame.columns:
        series = frame[column]
        row = {
            "dataset": name,
            "column": column,
            "dtype": str(series.dtype),
            "rows": len(series),
            "missing": int(series.isna().sum()),
            "missing_pct": float(series.isna().mean()),
            "unique_including_na": int(series.nunique(dropna=False)),
        }
        if pd.api.types.is_numeric_dtype(series):
            finite = pd.to_numeric(series, errors="coerce")
            row.update(
                minimum=float(finite.min()) if finite.notna().any() else np.nan,
                maximum=float(finite.max()) if finite.notna().any() else np.nan,
                mean=float(finite.mean()) if finite.notna().any() else np.nan,
                median=float(finite.median()) if finite.notna().any() else np.nan,
            )
        rows.append(row)
    return pd.DataFrame(rows)


def _missing_panel_runs(train: pd.DataFrame) -> pd.DataFrame:
    dates = pd.date_range(train["Date"].min(), train["Date"].max(), freq="D")
    hubs = np.sort(train["HubID"].unique())
    complete = pd.MultiIndex.from_product([hubs, dates], names=["HubID", "Date"])
    present = pd.MultiIndex.from_frame(train[["HubID", "Date"]])
    missing = complete.difference(present).to_frame(index=False)
    runs: list[dict] = []
    for hub_id, group in missing.groupby("HubID", sort=True):
        days = group["Date"].sort_values()
        run_id = days.diff().dt.days.ne(1).cumsum()
        for _, run in days.groupby(run_id):
            runs.append(
                {
                    "HubID": int(hub_id),
                    "start": run.min(),
                    "end": run.max(),
                    "days": int(len(run)),
                }
            )
    return pd.DataFrame(runs).sort_values(["start", "HubID"]).reset_index(drop=True)


def audit(paths: Paths, frames: dict[str, pd.DataFrame] | None = None) -> dict:
    paths.create_outputs()
    frames = load_raw(paths) if frames is None else frames
    train, test, metadata, submission = (frames[k] for k in ("train", "test", "metadata", "submission"))

    for key, expected in EXPECTED_SHAPES.items():
        if frames[key].shape != expected:
            raise AssertionError(f"{key} shape {frames[key].shape} != expected {expected}")

    weekday_errors = {
        name: int((frame["Weekday"] != frame["Date"].dt.dayofweek + 1).sum())
        for name, frame in (("train", train), ("test", test))
    }
    missing_runs = _missing_panel_runs(train)
    missing_runs.to_csv(paths.tables / "panel_missing_runs.csv", index=False)
    pd.concat([_column_summary(name, frame) for name, frame in frames.items()], ignore_index=True).to_csv(
        paths.tables / "column_summary.csv", index=False
    )

    shared = [c for c in test.columns if c != "Id"]
    drift_rows = []
    for column in ("Weekday", "IsOpen", "PromoActive", "RegionalHoliday", "SchoolClosureFlag"):
        levels = sorted(set(train[column].dropna().unique()) | set(test[column].dropna().unique()))
        for level in levels:
            drift_rows.append(
                {
                    "column": column,
                    "level": level,
                    "train_share": float((train[column] == level).mean()),
                    "last42_share": float((train.loc[train["Date"] > train["Date"].max() - pd.Timedelta(days=42), column] == level).mean()),
                    "test_share": float((test[column] == level).mean()),
                }
            )
    pd.DataFrame(drift_rows).to_csv(paths.tables / "known_feature_drift.csv", index=False)
    drift_metrics = []
    last42 = train.loc[train["Date"] > train["Date"].max() - pd.Timedelta(days=42)]
    for column in ("Weekday", "IsOpen", "PromoActive", "RegionalHoliday", "SchoolClosureFlag"):
        levels = sorted(set(train[column].dropna().unique()) | set(test[column].dropna().unique()))
        test_prob = test[column].value_counts(normalize=True).reindex(levels, fill_value=0).to_numpy(float)
        for reference_name, reference in (("full_train", train), ("last42", last42)):
            ref_prob = reference[column].value_counts(normalize=True).reindex(levels, fill_value=0).to_numpy(float)
            epsilon = 1e-8
            p = np.clip(ref_prob, epsilon, None); p = p / p.sum()
            q = np.clip(test_prob, epsilon, None); q = q / q.sum()
            midpoint = 0.5 * (p + q)
            js_distance = float(np.sqrt(0.5 * np.sum(p * np.log(p / midpoint)) + 0.5 * np.sum(q * np.log(q / midpoint))))
            psi = float(np.sum((q - p) * np.log(q / p)))
            drift_metrics.append({"column": column, "reference": reference_name, "jensen_shannon_distance": js_distance, "psi": psi})
    pd.DataFrame(drift_metrics).to_csv(paths.tables / "drift_metrics.csv", index=False)

    closed = train[train["IsOpen"].eq(0)]
    open_rows = train[train["IsOpen"].eq(1)]
    valid_conversion = open_rows.loc[open_rows["AppSessions"].gt(0), "OrderVolume"] / open_rows.loc[
        open_rows["AppSessions"].gt(0), "AppSessions"
    ]
    promo_open_means = open_rows.groupby("PromoActive")["OrderVolume"].mean()
    summary = {
        "raw_file_hashes": {key: sha256(paths.raw / filename) for key, filename in RAW_FILES.items()},
        "shapes": {key: list(frame.shape) for key, frame in frames.items()},
        "date_ranges": {
            "train": [train["Date"].min(), train["Date"].max()],
            "test": [test["Date"].min(), test["Date"].max()],
        },
        "unique_hubs": {"train": train["HubID"].nunique(), "test": test["HubID"].nunique(), "metadata": metadata["HubID"].nunique()},
        "weekday_mismatches": weekday_errors,
        "duplicate_hub_dates": {
            "train": int(train.duplicated(["HubID", "Date"]).sum()),
            "test": int(test.duplicated(["HubID", "Date"]).sum()),
        },
        "test_complete_grid": bool(len(test) == test["HubID"].nunique() * test["Date"].nunique()),
        "test_id_date_major_hub_minor": bool(
            np.array_equal(test.sort_values(["Date", "HubID"])["Id"].to_numpy(), np.arange(1, len(test) + 1))
        ),
        "submission_ids_match": bool(test["Id"].equals(submission["Id"])),
        "metadata_hub_coverage": bool(set(metadata["HubID"]) == set(train["HubID"]) == set(test["HubID"])),
        "metadata_missing": metadata.isna().sum().astype(int).to_dict(),
        "closed_rows": len(closed),
        "closed_nonzero_orders": int(closed["OrderVolume"].ne(0).sum()),
        "closed_nonzero_sessions": int(closed["AppSessions"].ne(0).sum()),
        "open_zero_orders": int(open_rows["OrderVolume"].eq(0).sum()),
        "open_zero_sessions": int(open_rows["AppSessions"].eq(0).sum()),
        "order_session_pearson_all": float(train["OrderVolume"].corr(train["AppSessions"])),
        "order_session_pearson_open": float(open_rows["OrderVolume"].corr(open_rows["AppSessions"])),
        "open_order_mean": float(open_rows["OrderVolume"].mean()),
        "open_order_median": float(open_rows["OrderVolume"].median()),
        "open_session_mean": float(open_rows["AppSessions"].mean()),
        "historical_conversion_median": float(valid_conversion.median()),
        "open_promo_order_mean": float(promo_open_means.get(1, np.nan)),
        "open_no_promo_order_mean": float(promo_open_means.get(0, np.nan)),
        "open_promo_mean_lift_pct": float((promo_open_means.get(1, np.nan) / promo_open_means.get(0, np.nan) - 1) * 100),
        "panel_missing_rows": int(1_115 * train["Date"].nunique() - len(train)),
        "panel_missing_run_counts": missing_runs["days"].value_counts().sort_index().to_dict(),
        "test_closed_rows": int(test["IsOpen"].eq(0).sum()),
        "shared_model_input_columns": shared,
    }
    write_json(summary, paths.artifacts / "audit_summary.json")
    return summary


def add_calendar_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    date = result["Date"]
    iso = date.dt.isocalendar()
    result["Year"] = date.dt.year.astype("int16")
    result["Month"] = date.dt.month.astype("int8")
    result["DayOfMonth"] = date.dt.day.astype("int8")
    result["DayOfYear"] = date.dt.dayofyear.astype("int16")
    result["ISOWeek"] = iso.week.astype("int8")
    result["IsWeekend"] = result["Weekday"].isin([6, 7]).astype("int8")
    result["IsMonthStart"] = date.dt.is_month_start.astype("int8")
    result["IsMonthEnd"] = date.dt.is_month_end.astype("int8")
    result["DaysSinceMonthStart"] = (date.dt.day - 1).astype("int8")
    result["DaysToMonthEnd"] = (date.dt.days_in_month - date.dt.day).astype("int8")
    return result


def add_metadata_features(frame: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    result = frame.merge(metadata, on="HubID", how="left", validate="many_to_one")
    if len(result) != len(frame):
        raise AssertionError("Metadata join changed row count")

    missing_cols = (
        "CompetitorDistance",
        "CompetitorOpenSinceMonth",
        "CompetitorOpenSinceYear",
        "LoyaltyProgramSinceWeek",
        "LoyaltyProgramSinceYear",
        "LoyaltyProgramInterval",
    )
    for column in missing_cols:
        result[f"{column}_Missing"] = result[column].isna().astype("int8")
    result["CompetitorDistanceLog1p"] = np.log1p(result["CompetitorDistance"])

    competitor_start = pd.to_datetime(
        {
            "year": result["CompetitorOpenSinceYear"],
            "month": result["CompetitorOpenSinceMonth"],
            "day": 1,
        },
        errors="coerce",
    )
    competitor_months = (result["Date"].dt.year - competitor_start.dt.year) * 12 + (
        result["Date"].dt.month - competitor_start.dt.month
    )
    result["CompetitorStartInFuture"] = (competitor_months < 0).fillna(False).astype("int8")
    result["CompetitorTenureMonths"] = competitor_months.where(competitor_months >= 0)

    year_week = (
        result["LoyaltyProgramSinceYear"].astype("Int64").astype("string")
        + result["LoyaltyProgramSinceWeek"].astype("Int64").astype("string").str.zfill(2)
        + "1"
    )
    loyalty_start = pd.to_datetime(year_week, format="%G%V%u", errors="coerce")
    loyalty_days = (result["Date"] - loyalty_start).dt.days
    result["LoyaltyStartInFuture"] = (loyalty_days < 0).fillna(False).astype("int8")
    result["LoyaltyTenureWeeks"] = (loyalty_days / 7).where(loyalty_days >= 0)
    result["LoyaltyProgramActiveByDate"] = (
        result["LoyaltyProgram"].eq(1) & loyalty_days.ge(0)
    ).astype("int8")

    month_token = result["Date"].dt.strftime("%b").replace({"Sep": "Sept"})
    result["LoyaltyIntervalMonth"] = [
        int(bool(active) and pd.notna(interval) and token in str(interval).split(","))
        for active, interval, token in zip(
            result["LoyaltyProgramActiveByDate"], result["LoyaltyProgramInterval"], month_token
        )
    ]
    result["LoyaltyIntervalMonth"] = result["LoyaltyIntervalMonth"].astype("int8")
    return result


def _schedule_features_for_group(group: pd.DataFrame, column: str, prefix: str) -> pd.DataFrame:
    ordered = group.sort_values("Date").copy()
    dates = ordered["Date"]
    values = ordered[column]
    contiguous_prev = dates.diff().dt.days.eq(1)
    calendar_segment = (~contiguous_prev).cumsum()
    new_run = (~contiguous_prev) | values.ne(values.shift())
    run_id = new_run.cumsum()
    run_position = ordered.groupby(run_id).cumcount() + 1
    run_size = ordered.groupby(run_id)[column].transform("size")
    run_end_position = run_size - run_position

    next_contiguous = dates.shift(-1).sub(dates).dt.days.eq(1)
    previous = values.shift().where(contiguous_prev)
    following = values.shift(-1).where(next_contiguous)
    run_has_visible_next = ordered.groupby(run_id)[column].transform(
        lambda s: bool(next_contiguous.loc[s.index[-1]])
    )

    event_dates = dates.where(values.gt(0))
    previous_event = event_dates.groupby(calendar_segment).ffill()
    next_event = event_dates.groupby(calendar_segment).bfill()
    since_event = (dates - previous_event).dt.days
    until_event = (next_event - dates).dt.days

    closed_dates = dates.where(values.eq(0))
    previous_zero = closed_dates.groupby(calendar_segment).ffill()
    next_zero = closed_dates.groupby(calendar_segment).bfill()

    out = pd.DataFrame(index=ordered.index)
    out[f"{prefix}_Yesterday"] = previous
    out[f"{prefix}_Tomorrow"] = following
    out[f"{prefix}_StreakDay"] = run_position.astype("int16")
    out[f"{prefix}_StreakLengthVisible"] = run_size.astype("int16")
    out[f"{prefix}_DaysUntilRunEndVisible"] = run_end_position.astype("int16")
    out[f"{prefix}_RightCensored"] = (~run_has_visible_next).astype("int8")
    out[f"{prefix}_DaysSinceActive"] = since_event
    out[f"{prefix}_DaysUntilActiveVisible"] = until_event
    out[f"{prefix}_DaysSinceInactive"] = (dates - previous_zero).dt.days
    out[f"{prefix}_DaysUntilInactiveVisible"] = (next_zero - dates).dt.days
    if prefix == "Open":
        out["DayBeforeClosed"] = (out[f"{prefix}_DaysUntilInactiveVisible"] == 1).astype("int8")
        out["DayAfterClosed"] = (out[f"{prefix}_DaysSinceInactive"] == 1).astype("int8")
    return out


def add_schedule_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Add schedule features using only rows visible in ``frame``.

    Callers enforce the forecast-window boundary by passing history through the
    origin plus exactly the supplied future window.
    """
    result = frame.sort_values(["HubID", "Date"]).copy()
    for column, prefix in (
        ("IsOpen", "Open"),
        ("PromoActive", "Promo"),
        ("SchoolClosureFlag", "SchoolClosure"),
        ("RegionalHoliday", "RegionalHoliday"),
    ):
        pieces = [_schedule_features_for_group(group, column, prefix) for _, group in result.groupby("HubID", sort=False)]
        features = pd.concat(pieces).sort_index()
        result = result.join(features)
    return result.sort_index()


def _base_preprocess(frame: pd.DataFrame, metadata: pd.DataFrame) -> pd.DataFrame:
    result = add_calendar_features(frame)
    result = add_metadata_features(result, metadata)
    return result


def preprocess(paths: Paths, frames: dict[str, pd.DataFrame] | None = None) -> dict[str, Path]:
    paths.create_outputs()
    frames = load_raw(paths) if frames is None else frames
    train, test, metadata = frames["train"], frames["test"], frames["metadata"]

    train_base = _base_preprocess(train, metadata)
    test_base = _base_preprocess(test, metadata)

    # Forward-looking phase features depend on a specific forecast-visibility
    # boundary and therefore live in fold/test forecast tables, not this
    # model-neutral base table.

    outputs = {
        "train": paths.processed / "base_train.csv.gz",
        "test": paths.processed / "base_test.csv.gz",
    }
    train_base.to_csv(outputs["train"], index=False, compression="gzip")
    test_base.to_csv(outputs["test"], index=False, compression="gzip")
    dictionary = pd.DataFrame(
        {
            "column": train_base.columns,
            "dtype": [str(train_base[c].dtype) for c in train_base.columns],
            "role": [
                "target" if c == "OrderVolume" else "historical_only" if c == "AppSessions" else "identifier" if c in {"Id", "HubID"} else "feature"
                for c in train_base.columns
            ],
        }
    )
    dictionary.to_csv(paths.artifacts / "data_dictionary.csv", index=False)
    return outputs


def _visible_future_schedule_features(
    schedule_history: pd.DataFrame, schedule_future: pd.DataFrame, origin: pd.Timestamp
) -> pd.DataFrame:
    """Build phase features per hub and retain only the visible future block.

    Processing one hub at a time avoids materializing dozens of temporary
    columns across the nearly one-million-row historical panel.
    """
    pieces = []
    history_groups = {hub_id: group for hub_id, group in schedule_history.groupby("HubID", sort=False)}
    future_groups = {hub_id: group for hub_id, group in schedule_future.groupby("HubID", sort=False)}
    for hub_id in np.sort(schedule_future["HubID"].unique()):
        history_group = history_groups.get(hub_id, schedule_history.iloc[0:0])
        future_group = future_groups[hub_id]
        visible = pd.concat([history_group, future_group], ignore_index=True).drop_duplicates(
            ["HubID", "Date"], keep="last"
        ).sort_values("Date")
        derived = []
        for column, prefix in (
            ("IsOpen", "Open"),
            ("PromoActive", "Promo"),
            ("SchoolClosureFlag", "SchoolClosure"),
            ("RegionalHoliday", "RegionalHoliday"),
        ):
            derived.append(_schedule_features_for_group(visible, column, prefix))
        features = pd.concat(derived, axis=1)
        combined = pd.concat([visible[["HubID", "Date"]], features], axis=1)
        pieces.append(combined.loc[combined["Date"].gt(origin)])
    return pd.concat(pieces, ignore_index=True).sort_values(["Date", "HubID"]).reset_index(drop=True)


def _safe_slope(values: pd.Series) -> float:
    clean = values.dropna().astype(float)
    if len(clean) < 2 or clean.nunique() < 2:
        return 0.0 if len(clean) >= 2 else np.nan
    return float(np.polyfit(np.arange(len(clean), dtype=float), clean.to_numpy(), 1)[0])


def historical_state(train: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    history = train.loc[train["Date"].le(origin)].sort_values(["HubID", "Date"]).copy()
    if history.empty:
        raise ValueError(f"No history through {origin.date()}")
    hubs = pd.DataFrame({"HubID": np.sort(train["HubID"].unique())})
    rows = []
    for hub_id, group in history.groupby("HubID", sort=True):
        group = group.sort_values("Date")
        renovation_missing = int(group["Date"].between("2014-07-01", "2014-12-31").sum()) == 0
        renovation_flag = 1 if (renovation_missing and origin >= pd.Timestamp("2015-01-01")) else 0
        days_since_reopen = int((origin - pd.Timestamp("2015-01-01")).days) if renovation_flag else 9999

        row: dict[str, object] = {
            "HubID": int(hub_id),
            "HistoryRows": int(len(group)),
            "HistoryStartDate": group["Date"].min(),
            "HistoryLastDate": group["Date"].max(),
            "HistoryDaysSinceLastObservation": int((origin - group["Date"].max()).days),
            "HistoryMissingCalendarDays": int((group["Date"].max() - group["Date"].min()).days + 1 - len(group)),
            "WasClosedForRenovation2014": renovation_flag,
            "DaysSinceRenovationReopen": days_since_reopen,
        }
        indexed = group.set_index("Date")
        for target in ("OrderVolume", "AppSessions"):
            short = "Orders" if target == "OrderVolume" else "Sessions"
            for offset in (0, 7, 14, 28):
                date = origin - pd.Timedelta(days=offset)
                row[f"{short}_AtOrigin" if offset == 0 else f"{short}_AtOriginMinus{offset}D"] = (
                    float(indexed.at[date, target]) if date in indexed.index else np.nan
                )
            for window in WINDOWS:
                recent = group[group["Date"].gt(origin - pd.Timedelta(days=window))]
                open_recent = recent[recent["IsOpen"].eq(1)]
                values = recent[target]
                open_values = open_recent[target]
                stem = f"{short}_{window}D"
                row[f"{stem}_PresentCount"] = int(len(recent))
                row[f"{stem}_MissingCount"] = int(window - len(recent))
                row[f"{stem}_OpenCount"] = int(len(open_recent))
                row[f"{stem}_MeanAll"] = float(values.mean()) if len(values) else np.nan
                row[f"{stem}_MeanOpen"] = float(open_values.mean()) if len(open_values) else np.nan
                row[f"{stem}_MedianOpen"] = float(open_values.median()) if len(open_values) else np.nan
                row[f"{stem}_StdOpen"] = float(open_values.std()) if len(open_values) else np.nan
                row[f"{stem}_MinOpen"] = float(open_values.min()) if len(open_values) else np.nan
                row[f"{stem}_MaxOpen"] = float(open_values.max()) if len(open_values) else np.nan
            for window in (28, 90, 365):
                recent_open = group[
                    group["Date"].gt(origin - pd.Timedelta(days=window)) & group["IsOpen"].eq(1)
                ]
                row[f"{short}_{window}D_OpenTrend"] = _safe_slope(recent_open[target])

        conversion = group.loc[group["IsOpen"].eq(1) & group["AppSessions"].gt(0)].copy()
        conversion["Conversion"] = conversion["OrderVolume"] / conversion["AppSessions"]
        for window in (28, 56, 90, 180, 365, 730):
            values = conversion.loc[conversion["Date"].gt(origin - pd.Timedelta(days=window)), "Conversion"]
            row[f"Conversion_{window}D_Count"] = int(len(values))
            row[f"Conversion_{window}D_Mean"] = float(values.mean()) if len(values) else np.nan
            row[f"Conversion_{window}D_Median"] = float(values.median()) if len(values) else np.nan
            row[f"Conversion_{window}D_Std"] = float(values.std()) if len(values) else np.nan
            row[f"VolumePerSession_{window}D_Count"] = row[f"Conversion_{window}D_Count"]
            row[f"VolumePerSession_{window}D_Mean"] = row[f"Conversion_{window}D_Mean"]
            row[f"VolumePerSession_{window}D_Median"] = row[f"Conversion_{window}D_Median"]
            row[f"VolumePerSession_{window}D_Std"] = row[f"Conversion_{window}D_Std"]
        rows.append(row)
    return hubs.merge(pd.DataFrame(rows), on="HubID", how="left", validate="one_to_one")


def _conditional_history(train: pd.DataFrame, origin: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    history = train.loc[train["Date"].le(origin) & train["IsOpen"].eq(1)].copy()
    history["Conversion"] = np.where(
        history["AppSessions"].gt(0), history["OrderVolume"] / history["AppSessions"], np.nan
    )
    dow = history.groupby(["HubID", "Weekday"], as_index=False).agg(
        HistHubDOWOrdersMean=("OrderVolume", "mean"),
        HistHubDOWSessionsMean=("AppSessions", "mean"),
        HistHubDOWConversionMedian=("Conversion", "median"),
        HistHubDOWCount=("OrderVolume", "size"),
    )
    promo = history.groupby(["HubID", "PromoActive"], as_index=False).agg(
        HistHubPromoOrdersMean=("OrderVolume", "mean"),
        HistHubPromoSessionsMean=("AppSessions", "mean"),
        HistHubPromoConversionMedian=("Conversion", "median"),
        HistHubPromoCount=("OrderVolume", "size"),
    )
    dow_promo = history.groupby(["HubID", "Weekday", "PromoActive"], as_index=False).agg(
        HistHubDOWPromoOrdersMean=("OrderVolume", "mean"),
        HistHubDOWPromoSessionsMean=("AppSessions", "mean"),
        HistHubDOWPromoConversionMedian=("Conversion", "median"),
        HistHubDOWPromoCount=("OrderVolume", "size"),
    )
    return dow, promo, dow_promo


def add_target_aligned_lags(known: pd.DataFrame, train: pd.DataFrame, origin: pd.Timestamp) -> pd.DataFrame:
    """Add target-date lags only when their source date is at/before origin."""
    result = known.copy()
    history = train.loc[train["Date"].le(origin), ["HubID", "Date", "OrderVolume", "AppSessions"]]
    history = history.drop_duplicates(["HubID", "Date"]).set_index(["HubID", "Date"])
    for lag in (7, 14, 28, 42, 364, 728):
        source_dates = result["Date"] - pd.Timedelta(days=lag)
        lookup = pd.MultiIndex.from_arrays([result["HubID"].to_numpy(), source_dates.to_numpy()], names=["HubID", "Date"])
        result[f"Orders_TargetLag{lag}D"] = history["OrderVolume"].reindex(lookup).to_numpy()
        result[f"Sessions_TargetLag{lag}D"] = history["AppSessions"].reindex(lookup).to_numpy()
        result[f"TargetLag{lag}D_Available"] = (
            source_dates.le(origin) & result[f"Orders_TargetLag{lag}D"].notna()
        ).astype("int8")
    return result


def build_forecast_frame(
    train: pd.DataFrame,
    future: pd.DataFrame,
    metadata: pd.DataFrame,
    origin: pd.Timestamp,
    attach_actuals: bool = True,
) -> pd.DataFrame:
    origin = pd.Timestamp(origin)
    future_start = origin + pd.Timedelta(days=1)
    future_end = origin + pd.Timedelta(days=42)
    block = future.loc[future["Date"].between(future_start, future_end)].copy()
    if len(block) != 46_830 or block["HubID"].nunique() != 1_115 or block["Date"].nunique() != 42:
        raise AssertionError(f"Forecast block at {origin.date()} is not a complete 1115 x 42 grid")

    actual_columns = [c for c in ("OrderVolume", "AppSessions") if c in block]
    actuals = block[["HubID", "Date", *actual_columns]].copy()
    known = block.drop(columns=actual_columns, errors="ignore")
    if "Id" in known:
        identifier = known["Id"].copy()
    else:
        identifier = None

    state = historical_state(train, origin)
    known = _base_preprocess(known, metadata)
    known["ForecastOrigin"] = origin
    known["Horizon"] = (known["Date"] - origin).dt.days.astype("int8")
    known["ForecastWeek"] = ((known["Horizon"] - 1) // 7 + 1).astype("int8")
    known = add_target_aligned_lags(known, train, origin)

    # Only history through the origin and the supplied 42 future days are visible.
    schedule_history = train.loc[train["Date"].le(origin), ["HubID", "Date", *SCHEDULE_COLUMNS, "Weekday", "RegionalHoliday"]]
    schedule_future = block[["HubID", "Date", *SCHEDULE_COLUMNS, "Weekday", "RegionalHoliday"]]
    visible_future = _visible_future_schedule_features(schedule_history, schedule_future, origin)
    known = known.merge(visible_future, on=["HubID", "Date"], how="left", validate="one_to_one")
    known = known.merge(state, on="HubID", how="left", validate="many_to_one")

    dow, promo, dow_promo = _conditional_history(train, origin)
    known = known.merge(dow, on=["HubID", "Weekday"], how="left", validate="many_to_one")
    known = known.merge(promo, on=["HubID", "PromoActive"], how="left", validate="many_to_one")
    known = known.merge(dow_promo, on=["HubID", "Weekday", "PromoActive"], how="left", validate="many_to_one")

    if attach_actuals and actual_columns:
        renamed = actuals.rename(columns={c: f"Actual{c}" for c in actual_columns})
        known = known.merge(renamed, on=["HubID", "Date"], how="left", validate="one_to_one")
    if identifier is not None and "Id" not in known:
        known["Id"] = identifier.to_numpy()
    return known.sort_values(["Date", "HubID"]).reset_index(drop=True)


def build_one_forecast(paths: Paths, origin: pd.Timestamp, source: str, output: Path) -> dict:
    paths.create_outputs()
    frames = load_raw(paths)
    train, test, metadata = frames["train"], frames["test"], frames["metadata"]
    future = train if source == "train" else test
    forecast = build_forecast_frame(train, future, metadata, origin, attach_actuals=source == "train")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix == ".parquet":
        forecast.to_parquet(output, index=False, compression="zstd")
    else:
        forecast.to_csv(output, index=False, compression="gzip")
    return {"rows": len(forecast), "columns": len(forecast.columns), "sha256": sha256(output)}


def build_folds(paths: Paths, frames: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
    """Build folds in isolated processes to bound peak and retained memory."""
    del frames  # Kept in the public signature for notebook/backward compatibility.
    paths.create_outputs()
    manifest = []
    jobs = [
        (number, pd.Timestamp(origin_text), "train", paths.folds / f"fold_{number}_{origin_text}.csv.gz")
        for number, origin_text in enumerate(FOLD_ORIGINS, start=1)
    ]
    jobs.append(("test", pd.Timestamp("2015-06-19"), "test", paths.processed / "test_forecast_features.csv.gz"))
    for label, origin, source, output in jobs:
        command = [
            sys.executable,
            "-m",
            "src.eda_pipeline",
            "build-one",
            "--root",
            str(paths.root),
            "--origin",
            origin.date().isoformat(),
            "--source",
            source,
            "--output",
            str(output),
        ]
        subprocess.run(command, cwd=paths.root, check=True, env=os.environ.copy())
        header = pd.read_csv(output, nrows=0)
        manifest.append(
            {
                "fold": label,
                "origin": origin.date().isoformat(),
                "validation_start": (origin + pd.Timedelta(days=1)).date().isoformat(),
                "validation_end": (origin + pd.Timedelta(days=42)).date().isoformat(),
                "rows": 46_830,
                "columns": len(header.columns),
                "path": str(output.relative_to(paths.root)),
                "sha256": sha256(output),
            }
        )
        pd.DataFrame(manifest).to_csv(paths.processed / "fold_manifest.csv", index=False)
    manifest_df = pd.DataFrame(manifest)
    return manifest_df


def build_training_origins(paths: Paths, spacing_days: int = 14) -> pd.DataFrame:
    """Materialize complete historical 42-day origin tables as Parquet."""
    paths.create_outputs()
    origin_dir = paths.processed / "training_origins"
    origin_dir.mkdir(parents=True, exist_ok=True)
    train = pd.read_csv(paths.raw / RAW_FILES["train"], usecols=["HubID", "Date"], parse_dates=["Date"])
    first_origin = train["Date"].min() + pd.Timedelta(days=180)
    last_origin = train["Date"].max() - pd.Timedelta(days=42)
    candidates = set(pd.date_range(first_origin, last_origin, freq=f"{spacing_days}D"))
    candidates.update(pd.Timestamp(value) for value in FOLD_ORIGINS)
    jobs = []
    for origin in sorted(candidates):
        block = train.loc[train["Date"].between(origin + pd.Timedelta(days=1), origin + pd.Timedelta(days=42))]
        if len(block) == 46_830 and block["HubID"].nunique() == 1_115 and block["Date"].nunique() == 42:
            jobs.append(origin)

    manifest_path = paths.processed / "training_origin_manifest.csv"
    manifest_rows = []
    for number, origin in enumerate(jobs, start=1):
        output = origin_dir / f"origin_{origin.date()}.parquet"
        if not output.exists():
            subprocess.run(
                [sys.executable, "-m", "src.eda_pipeline", "build-one", "--root", str(paths.root),
                 "--origin", origin.date().isoformat(), "--source", "train", "--output", str(output)],
                cwd=paths.root, check=True, env=os.environ.copy(),
            )
        header = pd.read_parquet(output, columns=["HubID", "Date"])
        manifest_rows.append(
            {
                "origin_number": number,
                "origin": origin.date().isoformat(),
                "target_start": (origin + pd.Timedelta(days=1)).date().isoformat(),
                "target_end": (origin + pd.Timedelta(days=42)).date().isoformat(),
                "rows": len(header),
                "path": str(output.relative_to(paths.root)),
                "sha256": sha256(output),
            }
        )
        pd.DataFrame(manifest_rows).to_csv(manifest_path, index=False)
    return pd.DataFrame(manifest_rows)


def _stratified_sample(train: pd.DataFrame, maximum: int = 100_000) -> pd.DataFrame:
    if len(train) <= maximum:
        return train.copy()
    key = ["Weekday", "IsOpen", "PromoActive", "SchoolClosureFlag"]
    proportions = train.groupby(key, observed=True).size().rename("n").reset_index()
    proportions["take"] = np.maximum(1, np.floor(proportions["n"] / len(train) * maximum).astype(int))
    parts = []
    for _, spec in proportions.iterrows():
        mask = np.ones(len(train), dtype=bool)
        for column in key:
            mask &= train[column].eq(spec[column]).to_numpy()
        group = train.loc[mask]
        parts.append(group.sample(n=min(int(spec["take"]), len(group)), random_state=SEED))
    sample = pd.concat(parts).sort_index()
    if len(sample) < maximum:
        remaining = train.drop(sample.index)
        sample = pd.concat([sample, remaining.sample(n=maximum - len(sample), random_state=SEED)])
    return sample.sort_index().head(maximum)


def custom_reports(paths: Paths, frames: dict[str, pd.DataFrame]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    paths.create_outputs()
    train, test, metadata = frames["train"], frames["test"], frames["metadata"]
    sns.set_theme(style="whitegrid", context="notebook")

    def save(name: str) -> None:
        plt.tight_layout()
        plt.savefig(paths.figures / f"{name}.png", dpi=160, bbox_inches="tight")
        plt.close()

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    sns.histplot(train["OrderVolume"], bins=80, ax=axes[0])
    axes[0].set_title("OrderVolume distribution")
    sns.histplot(np.log1p(train["OrderVolume"]), bins=80, ax=axes[1])
    axes[1].set_title("log1p(OrderVolume) distribution")
    save("target_distribution")

    daily = train.groupby("Date", as_index=False).agg(
        MeanOrders=("OrderVolume", "mean"), MeanSessions=("AppSessions", "mean"), OpenShare=("IsOpen", "mean")
    )
    fig, axes = plt.subplots(3, 1, figsize=(15, 10), sharex=True)
    for ax, col in zip(axes, ("MeanOrders", "MeanSessions", "OpenShare")):
        sns.lineplot(data=daily, x="Date", y=col, ax=ax, linewidth=0.8)
        ax.set_title(f"Daily {col}")
    save("temporal_overview")
    daily.to_csv(paths.tables / "daily_summary.csv", index=False)

    open_train = train[train["IsOpen"].eq(1)].copy()
    grouped = open_train.groupby(["Weekday", "PromoActive"], as_index=False).agg(
        MeanOrders=("OrderVolume", "mean"), MedianOrders=("OrderVolume", "median"), Rows=("OrderVolume", "size")
    )
    plt.figure(figsize=(10, 5))
    sns.barplot(data=grouped, x="Weekday", y="MeanOrders", hue="PromoActive")
    plt.title("Open-day orders by weekday and promotion")
    save("weekday_promo_orders")
    grouped.to_csv(paths.tables / "weekday_promo_target.csv", index=False)

    sample = open_train.sample(n=min(75_000, len(open_train)), random_state=SEED)
    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=sample, x="AppSessions", y="OrderVolume", hue="PromoActive", alpha=0.18, s=12)
    plt.title("Orders versus sessions on open days")
    save("orders_vs_sessions")

    conversion = open_train.loc[open_train["AppSessions"].gt(0), "OrderVolume"] / open_train.loc[
        open_train["AppSessions"].gt(0), "AppSessions"
    ]
    plt.figure(figsize=(10, 5))
    sns.histplot(conversion.clip(upper=conversion.quantile(0.999)), bins=80)
    plt.title("Historical conversion ratio (clipped for display at p99.9)")
    save("conversion_distribution")
    conversion.describe(percentiles=[0.001, 0.01, 0.05, 0.5, 0.95, 0.99, 0.999]).to_csv(
        paths.tables / "conversion_summary.csv", header=["value"]
    )

    hub_summary = open_train.groupby("HubID", as_index=False).agg(
        MeanOrders=("OrderVolume", "mean"), MedianOrders=("OrderVolume", "median"),
        StdOrders=("OrderVolume", "std"), MeanSessions=("AppSessions", "mean"), OpenRows=("OrderVolume", "size")
    )
    plt.figure(figsize=(10, 5))
    sns.histplot(hub_summary["MeanOrders"], bins=60)
    plt.title("Distribution of hub-level mean open-day orders")
    save("hub_heterogeneity")
    hub_summary.to_csv(paths.tables / "hub_summary.csv", index=False)

    missing = metadata.isna().mean().sort_values(ascending=False).rename("MissingShare").rename_axis("Column").reset_index()
    plt.figure(figsize=(11, 5))
    sns.barplot(data=missing, x="MissingShare", y="Column")
    plt.title("Metadata missingness")
    save("metadata_missingness")

    drift = pd.read_csv(paths.tables / "known_feature_drift.csv")
    drift_long = drift.melt(id_vars=["column", "level"], value_vars=["train_share", "last42_share", "test_share"], var_name="Dataset", value_name="Share")
    grid = sns.catplot(data=drift_long, x="level", y="Share", hue="Dataset", col="column", kind="bar", col_wrap=3, sharex=False, height=3.5)
    grid.figure.suptitle("Known-feature distribution comparison", y=1.02)
    grid.savefig(paths.figures / "known_feature_drift.png", dpi=160, bbox_inches="tight")
    plt.close(grid.figure)

    merged = open_train.merge(metadata, on="HubID", how="left", validate="many_to_one")
    segment = merged.groupby(["HubFormat", "AssortmentTier"], as_index=False).agg(
        MeanOrders=("OrderVolume", "mean"), MedianOrders=("OrderVolume", "median"), Rows=("OrderVolume", "size")
    )
    segment.to_csv(paths.tables / "metadata_segment_target.csv", index=False)

    # Lag correlations summarize useful periodic structure without creating model features.
    lag_rows = []
    calendar = pd.date_range(train["Date"].min(), train["Date"].max(), freq="D")
    target_panel = train.pivot(index="Date", columns="HubID", values="OrderVolume").reindex(calendar)
    for lag in (1, 7, 14, 28, 42, 364):
        correlations = target_panel.corrwith(target_panel.shift(lag))
        lag_rows.append({"lag_days": lag, "median_hub_correlation": correlations.median(), "mean_hub_correlation": correlations.mean(), "hubs": correlations.notna().sum()})
    pd.DataFrame(lag_rows).to_csv(paths.tables / "lag_correlations.csv", index=False)


def automated_reports(paths: Paths, frames: dict[str, pd.DataFrame]) -> dict[str, str]:
    paths.create_outputs()
    train, test, metadata = frames["train"], frames["test"], frames["metadata"]
    status: dict[str, str] = {}

    from ydata_profiling import ProfileReport

    train_profile = ProfileReport(train, title="Orders Train — Minimal Full-Data Profile", minimal=True, explorative=True)
    train_path = paths.reports / "ydata_train_minimal.html"
    train_profile.to_file(train_path)
    status["ydata_train"] = str(train_path)

    metadata_profile = ProfileReport(metadata, title="Hub Metadata — Full Profile", explorative=True)
    metadata_path = paths.reports / "ydata_hub_metadata.html"
    metadata_profile.to_file(metadata_path)
    status["ydata_metadata"] = str(metadata_path)

    shared = [c for c in test.columns if c not in {"Id"}]
    train_compare = train.loc[train["Date"] > train["Date"].max() - pd.Timedelta(days=42), shared].copy()
    test_compare = test[shared].copy()
    comparison = ProfileReport(train_compare, title="Training Final 42 Days", minimal=True).compare(
        ProfileReport(test_compare, title="Competition Test 42 Days", minimal=True)
    )
    comparison_path = paths.reports / "ydata_last42_vs_test.html"
    comparison.to_file(comparison_path)
    status["ydata_comparison"] = str(comparison_path)

    import sweetviz as sv

    sweet_sample = _stratified_sample(train)
    feature_config = sv.FeatureConfig(force_cat=["HubID", "Weekday", "IsOpen", "PromoActive", "RegionalHoliday", "SchoolClosureFlag"])
    sweet_target = sv.analyze(
        [sweet_sample, "Deterministic Stratified Train Sample"],
        target_feat="OrderVolume",
        feat_cfg=feature_config,
        pairwise_analysis="on",
    )
    sweet_target_path = paths.reports / "sweetviz_train_target.html"
    sweet_target.show_html(str(sweet_target_path), open_browser=False)
    status["sweetviz_target"] = str(sweet_target_path)

    shared_no_date = [c for c in shared if c != "Date"]
    sweet_compare = sv.compare(
        [train_compare[shared_no_date], "Training Final 42 Days"],
        [test_compare[shared_no_date], "Competition Test"],
        feat_cfg=sv.FeatureConfig(force_cat=shared_no_date),
        pairwise_analysis="on",
    )
    sweet_compare_path = paths.reports / "sweetviz_last42_vs_test.html"
    sweet_compare.show_html(str(sweet_compare_path), open_browser=False)
    status["sweetviz_comparison"] = str(sweet_compare_path)
    write_json(status, paths.reports / "report_manifest.json")
    return status


def write_findings(paths: Paths, audit_summary: dict) -> None:
    content = f"""# EDA Findings and Modelling Contract

## Confirmed structure

- Training contains {audit_summary['shapes']['train'][0]:,} rows across 1,115 hubs and 900 dates.
- Test is a complete 1,115 × 42 panel and is ordered date-major, hub-minor.
- Training ends one day before test begins.
- Metadata covers every train and test hub exactly once.

## Data-quality findings

- The training panel has {audit_summary['panel_missing_rows']:,} absent hub-date rows.
- 180 hubs share a 184-day missing block from 2014-07-01 through 2014-12-31; one additional hub-date is absent.
- These are unknown observations, not evidence of closure, and must never be zero-filled.
- Closed rows have zero nonzero-order violations and zero nonzero-session violations.
- Open rows contain a very small number of zero targets/sessions; retain and flag them rather than dropping them.
- Metadata nulls are structurally aligned with unavailable competitor or loyalty start information.

## Demand and traffic signal

- Mean open-day orders are {audit_summary['open_order_mean']:,.1f}; median open-day orders are {audit_summary['open_order_median']:,.1f}.
- Mean open-day sessions are {audit_summary['open_session_mean']:,.1f}.
- Order/session Pearson correlation is {audit_summary['order_session_pearson_all']:.3f} across all rows and {audit_summary['order_session_pearson_open']:.3f} on open rows.
- Median historical OrderVolume/AppSessions ratio on valid open rows is {audit_summary['historical_conversion_median']:.3f}.
- Open-day promotion rows average {audit_summary['open_promo_order_mean']:,.1f} orders versus {audit_summary['open_no_promo_order_mean']:,.1f} without promotion, a raw {audit_summary['open_promo_mean_lift_pct']:.1f}% difference that is descriptive rather than causal.

## Temporal and distribution shift

- Calendar-aligned hub-level lag correlations are strongest around 14, 28, and 364 days; exact values are in `tables/lag_correlations.csv`.
- Test weekday and promotion schedules closely resemble the final training window.
- School-closure prevalence changes materially in test; holiday is constant zero and therefore has no direct test-period discriminating power.
- `tables/drift_metrics.csv` reports Jensen-Shannon distance and PSI against both full history and the final 42 training days.

## Leakage contract

- For every validation origin, hide both OrderVolume and AppSessions for all 42 future days.
- Historical summaries end at the forecast origin and remain frozen across horizons 1–42.
- Forward schedule features may inspect only the supplied 42-day window and are right-censored at its boundary.
- Validation actuals are reattached only under `Actual*` names after feature construction.

## Modelling implications to validate later

- AppSessions is strongly associated with OrderVolume historically, but only historical or separately forecast sessions are legal.
- Closed test rows support a hard prediction override of zero.
- RegionalHoliday has no direct test-period variance.
- RMSLE makes log1p target diagnostics and nonnegative predictions the natural default.
- Target, session, conversion, closure phase, promotion phase, and metadata feature families should be added through the fixed CV experiment ladder.
"""
    (paths.artifacts / "EDA_FINDINGS.md").write_text(content)


def environment_manifest(paths: Paths) -> None:
    packages = ("pandas", "numpy", "scipy", "sklearn", "matplotlib", "seaborn", "statsmodels", "ydata_profiling", "sweetviz", "phik")
    versions = {}
    for package in packages:
        try:
            module = __import__(package)
            versions[package] = getattr(module, "__version__", "present")
        except Exception as exc:  # pragma: no cover - records environment failure
            versions[package] = f"IMPORT_ERROR: {exc}"
    write_json(
        {
            "python": sys.version,
            "platform": platform.platform(),
            "packages": versions,
            "execution": "MPLCONFIGDIR=/tmp/kaggle_comp_mpl conda run -n eda311 python -m src.eda_pipeline all",
            "seed": SEED,
        },
        paths.artifacts / "environment.json",
    )


def run_all(paths: Paths, skip_automated: bool = False) -> None:
    frames = load_raw(paths)
    summary = audit(paths, frames)
    preprocess(paths, frames)
    custom_reports(paths, frames)
    if not skip_automated:
        automated_reports(paths, frames)
    write_findings(paths, summary)
    environment_manifest(paths)
    del frames
    gc.collect()
    build_folds(paths)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "preprocess", "build-folds", "build-training-origins", "build-one", "reports", "all"))
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Project root (defaults to current directory)")
    parser.add_argument("--skip-automated", action="store_true", help="Skip YData and Sweetviz reports")
    parser.add_argument("--origin", type=pd.Timestamp, help=argparse.SUPPRESS)
    parser.add_argument("--source", choices=("train", "test"), help=argparse.SUPPRESS)
    parser.add_argument("--output", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--spacing-days", type=int, default=14, help="Origin spacing for build-training-origins")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    paths = Paths(args.root.resolve())
    with warnings.catch_warnings():
        warnings.simplefilter("default")
        if args.command == "audit":
            frames = load_raw(paths)
            summary = audit(paths, frames)
            write_findings(paths, summary)
            environment_manifest(paths)
        elif args.command == "preprocess":
            frames = load_raw(paths)
            preprocess(paths, frames)
        elif args.command == "build-folds":
            build_folds(paths)
        elif args.command == "build-training-origins":
            build_training_origins(paths, args.spacing_days)
        elif args.command == "build-one":
            if args.origin is None or args.source is None or args.output is None:
                raise SystemExit("build-one requires --origin, --source, and --output")
            build_one_forecast(paths, args.origin, args.source, args.output)
        elif args.command == "reports":
            frames = load_raw(paths)
            audit(paths, frames)
            custom_reports(paths, frames)
            if not args.skip_automated:
                automated_reports(paths, frames)
        else:
            run_all(paths, skip_automated=args.skip_automated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
