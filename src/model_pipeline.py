"""Leakage-safe model experiments on origin-frozen 42-day forecast tables."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence

os.environ.setdefault("MPLCONFIGDIR", "/tmp/kaggle_comp_mpl")

import numpy as np
import pandas as pd

from src.eda_pipeline import Paths, SEED


HORIZON_BUCKETS = ((1, 7), (8, 14), (15, 21), (22, 28), (29, 35), (36, 42))
NON_FEATURE_COLUMNS = {
    "ActualOrderVolume",
    "ActualAppSessions",
    "OrderVolume",
    "AppSessions",
    "Date",
    "ForecastOrigin",
    "HistoryStartDate",
    "HistoryLastDate",
    "Id",
}
CATEGORICAL_COLUMNS = {
    "HubID",
    "Weekday",
    "Year",
    "Month",
    "DayOfMonth",
    "ISOWeek",
    "HubFormat",
    "AssortmentTier",
    "LoyaltyProgram",
    "LoyaltyProgramInterval",
    "RegionalHoliday",
    "PromoActive",
    "SchoolClosureFlag",
    "IsOpen",
}


def rmsle(actual: np.ndarray | pd.Series, prediction: np.ndarray | pd.Series) -> float:
    actual_array = np.asarray(actual, dtype=float)
    prediction_array = np.clip(np.asarray(prediction, dtype=float), 0, None)
    return float(np.sqrt(np.mean(np.square(np.log1p(prediction_array) - np.log1p(actual_array)))))


def load_fold_tables(paths: Paths) -> list[pd.DataFrame]:
    files = sorted(paths.folds.glob("fold_*.csv.gz"))
    if len(files) != 4:
        raise AssertionError(f"Expected four folds, found {len(files)}")
    folds = []
    for number, file in enumerate(files, start=1):
        frame = pd.read_csv(file, parse_dates=["Date", "ForecastOrigin", "HistoryStartDate", "HistoryLastDate"])
        frame["Fold"] = number
        folds.append(frame)
    return folds


def load_origin_training(paths: Paths, validation_origin: pd.Timestamp, columns: list[str]) -> pd.DataFrame:
    manifest_path = paths.processed / "training_origin_manifest.csv"
    if not manifest_path.exists():
        return pd.DataFrame()
    manifest = pd.read_csv(manifest_path, parse_dates=["origin", "target_start", "target_end"])
    eligible = manifest.loc[manifest["target_end"].le(validation_origin)].sort_values("origin")
    required = list(dict.fromkeys([*columns, "ActualOrderVolume", "IsOpen"]))
    frames = [pd.read_parquet(paths.root / path, columns=required) for path in eligible["path"]]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def feature_columns(frame: pd.DataFrame, group: str = "all") -> list[str]:
    candidates = [c for c in frame.columns if c not in NON_FEATURE_COLUMNS | {"Fold"}]
    static_calendar = {
        "HubID", "Weekday", "IsOpen", "PromoActive", "RegionalHoliday", "SchoolClosureFlag",
        "Year", "Month", "DayOfMonth", "DayOfYear", "ISOWeek", "IsWeekend", "IsMonthStart",
        "IsMonthEnd", "DaysSinceMonthStart", "DaysToMonthEnd", "Horizon", "HubFormat",
        "AssortmentTier", "CompetitorDistance", "CompetitorOpenSinceMonth", "CompetitorOpenSinceYear",
        "LoyaltyProgram", "LoyaltyProgramSinceWeek", "LoyaltyProgramSinceYear", "LoyaltyProgramInterval",
        "CompetitorDistance_Missing", "CompetitorOpenSinceMonth_Missing", "CompetitorOpenSinceYear_Missing",
        "LoyaltyProgramSinceWeek_Missing", "LoyaltyProgramSinceYear_Missing", "LoyaltyProgramInterval_Missing",
        "CompetitorDistanceLog1p", "CompetitorStartInFuture", "CompetitorTenureMonths",
        "LoyaltyStartInFuture", "LoyaltyTenureWeeks", "LoyaltyProgramActiveByDate", "LoyaltyIntervalMonth",
    }
    if group == "static":
        return [c for c in candidates if c in static_calendar]
    if group == "orders":
        return [c for c in candidates if c in static_calendar or "Orders" in c or c.startswith("History")]
    if group == "orders_sessions":
        return [c for c in candidates if c in static_calendar or any(token in c for token in ("Orders", "Sessions", "History"))]
    if group == "history":
        return [c for c in candidates if not c.startswith(("Open_", "Promo_", "SchoolClosure_"))]
    return candidates


def _hierarchical_baseline(frame: pd.DataFrame) -> np.ndarray:
    prediction = frame["HistHubDOWPromoOrdersMean"].copy()
    prediction = prediction.fillna(frame["HistHubDOWOrdersMean"])
    prediction = prediction.fillna(frame["HistHubPromoOrdersMean"])
    prediction = prediction.fillna(frame.get("Orders_90D_MedianOpen"))
    prediction = prediction.fillna(frame.get("Orders_180D_MedianOpen"))
    prediction = prediction.fillna(frame.get("Orders_28D_MeanOpen"))
    prediction = prediction.fillna(0.0)
    return np.where(frame["IsOpen"].eq(0), 0.0, np.clip(prediction.to_numpy(float), 0, None))


def baseline_predictions(frame: pd.DataFrame) -> dict[str, np.ndarray]:
    predictions: dict[str, np.ndarray] = {"hierarchical_mean": _hierarchical_baseline(frame)}
    for name, column in (
        ("recent_28d_open_mean", "Orders_28D_MeanOpen"),
        ("recent_90d_open_median", "Orders_90D_MedianOpen"),
        ("origin_minus_7d", "Orders_AtOriginMinus7D"),
        ("origin_minus_14d", "Orders_AtOriginMinus14D"),
        ("origin_minus_28d", "Orders_AtOriginMinus28D"),
        ("target_lag_7d_legal", "Orders_TargetLag7D"),
        ("target_lag_14d_legal", "Orders_TargetLag14D"),
        ("target_lag_28d_legal", "Orders_TargetLag28D"),
        ("target_lag_42d", "Orders_TargetLag42D"),
        ("target_lag_364d", "Orders_TargetLag364D"),
    ):
        values = frame[column].where(frame[column].gt(0)).fillna(frame["Orders_90D_MedianOpen"]).fillna(0).to_numpy(float)
        predictions[name] = np.where(frame["IsOpen"].eq(0), 0.0, np.clip(values, 0, None))
    return predictions


def metric_rows(frame: pd.DataFrame, predictions: dict[str, np.ndarray], fold: int | str) -> list[dict]:
    rows = []
    actual = frame["ActualOrderVolume"].to_numpy(float)
    open_mask = frame["IsOpen"].eq(1).to_numpy()
    for model, prediction in predictions.items():
        rows.append({"fold": fold, "model": model, "horizon_bucket": "all", "rows": len(frame), "rmsle": rmsle(actual, prediction)})
        rows.append({"fold": fold, "model": model, "horizon_bucket": "open_only", "rows": int(open_mask.sum()), "rmsle": rmsle(actual[open_mask], prediction[open_mask])})
        for start, end in HORIZON_BUCKETS:
            mask = frame["Horizon"].between(start, end).to_numpy()
            rows.append({"fold": fold, "model": model, "horizon_bucket": f"h{start:02d}_{end:02d}", "rows": int(mask.sum()), "rmsle": rmsle(actual[mask], prediction[mask])})
    return rows


def evaluate_baselines(paths: Paths) -> pd.DataFrame:
    rows = []
    for fold_number, frame in enumerate(load_fold_tables(paths), start=1):
        rows.extend(metric_rows(frame, baseline_predictions(frame), fold_number))
    metrics = pd.DataFrame(rows)
    output = paths.root / "artifacts" / "models"
    output.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(output / "baseline_metrics.csv", index=False)
    summary = metrics.loc[metrics["horizon_bucket"].eq("all")].groupby("model", as_index=False)["rmsle"].agg(["mean", "std"]).sort_values("mean")
    summary.to_csv(output / "baseline_summary.csv")
    return metrics


def _prepare(frame: pd.DataFrame, columns: list[str], backend: str) -> pd.DataFrame:
    result = frame[columns].copy()
    for column in result.columns:
        if column in CATEGORICAL_COLUMNS or result[column].dtype == object:
            values = result[column].astype("string").fillna("__MISSING__")
            result[column] = values if backend == "catboost" else values.astype("category")
        elif pd.api.types.is_bool_dtype(result[column]):
            result[column] = result[column].astype("int8")
    return result


def fit_catboost(train: pd.DataFrame, valid: pd.DataFrame, columns: list[str]):
    from catboost import CatBoostRegressor

    train_open = train[train["IsOpen"].eq(1) & train["ActualOrderVolume"].gt(0)]
    valid_open = valid[valid["IsOpen"].eq(1) & valid["ActualOrderVolume"].gt(0)]
    x_train = _prepare(train_open, columns, "catboost")
    x_valid = _prepare(valid_open, columns, "catboost")
    cat_indices = [i for i, c in enumerate(columns) if c in CATEGORICAL_COLUMNS or x_train[c].dtype == object or str(x_train[c].dtype).startswith("string")]
    model = CatBoostRegressor(
        loss_function="RMSE", eval_metric="RMSE", iterations=1_500, learning_rate=0.04,
        depth=8, l2_leaf_reg=5.0, random_seed=SEED, random_strength=0.5,
        verbose=False, allow_writing_files=False,
    )
    model.fit(x_train, np.log1p(train_open["ActualOrderVolume"]), cat_features=cat_indices,
              eval_set=(x_valid, np.log1p(valid_open["ActualOrderVolume"])), early_stopping_rounds=100, verbose=False)
    return model


def fit_lightgbm(train: pd.DataFrame, valid: pd.DataFrame, columns: list[str]):
    import lightgbm as lgb

    train_open = train[train["IsOpen"].eq(1) & train["ActualOrderVolume"].gt(0)]
    valid_open = valid[valid["IsOpen"].eq(1) & valid["ActualOrderVolume"].gt(0)]
    x_train = _prepare(train_open, columns, "lightgbm")
    x_valid = _prepare(valid_open, columns, "lightgbm")
    model = lgb.LGBMRegressor(
        objective="regression", n_estimators=3_000, learning_rate=0.025, num_leaves=63,
        max_depth=-1, min_child_samples=80, subsample=0.85, colsample_bytree=0.8,
        reg_lambda=1.0, random_state=SEED, n_jobs=-1, verbosity=-1,
    )
    model.fit(x_train, np.log1p(train_open["ActualOrderVolume"]),
              eval_set=[(x_valid, np.log1p(valid_open["ActualOrderVolume"]))],
              callbacks=[lgb.early_stopping(150, verbose=False)])
    return model


def fit_lightgbm_tweedie(train: pd.DataFrame, valid: pd.DataFrame, columns: list[str]):
    import lightgbm as lgb

    train_open = train[train["IsOpen"].eq(1) & train["ActualOrderVolume"].gt(0)]
    valid_open = valid[valid["IsOpen"].eq(1) & valid["ActualOrderVolume"].gt(0)]
    x_train = _prepare(train_open, columns, "lightgbm")
    x_valid = _prepare(valid_open, columns, "lightgbm")
    model = lgb.LGBMRegressor(
        objective="tweedie", tweedie_variance_power=1.1, n_estimators=3_000, learning_rate=0.025, num_leaves=63,
        max_depth=-1, min_child_samples=80, subsample=0.85, colsample_bytree=0.8,
        reg_lambda=1.0, random_state=SEED, n_jobs=-1, verbosity=-1,
    )
    model.fit(x_train, train_open["ActualOrderVolume"],
              eval_set=[(x_valid, valid_open["ActualOrderVolume"])],
              callbacks=[lgb.early_stopping(150, verbose=False)])
    return model


def predict_model(model, frame: pd.DataFrame, columns: list[str], backend: str) -> np.ndarray:
    prediction = np.zeros(len(frame), dtype=float)
    mask = frame["IsOpen"].eq(1).to_numpy()
    if mask.any():
        x_backend = "lightgbm" if backend == "lightgbm_tweedie" else backend
        x = _prepare(frame.loc[mask], columns, x_backend)
        preds = model.predict(x)
        if backend == "lightgbm_tweedie":
            prediction[mask] = preds
        else:
            prediction[mask] = np.expm1(preds)
    return np.clip(prediction, 0, None)


def walk_forward_models(
    paths: Paths,
    feature_group: str = "all",
    backends: tuple[str, ...] = ("catboost", "lightgbm", "lightgbm_tweedie"),
    folds_to_run: tuple[int, ...] | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    folds = load_fold_tables(paths)
    metrics_rows = []
    oof_parts = []
    for valid_index in range(len(folds)):
        fold_number = valid_index + 1
        if folds_to_run is not None and fold_number not in folds_to_run:
            continue
        valid = folds[valid_index].copy()
        validation_origin = pd.Timestamp(valid["ForecastOrigin"].iloc[0])
        columns = feature_columns(valid, feature_group)
        train = load_origin_training(paths, validation_origin, columns)
        if train.empty:
            if valid_index == 0:
                continue
            train = pd.concat(folds[:valid_index], ignore_index=True)
            
        from sklearn.preprocessing import TargetEncoder
        encoder = TargetEncoder(smooth="auto")
        train_mask = train["IsOpen"].eq(1)
        # Handle cases where training data might be empty for some reason, though unlikely
        if train_mask.any():
            encoder.fit(train.loc[train_mask, ["HubID"]], np.log1p(train.loc[train_mask, "ActualOrderVolume"]))
            train["HubID_TargetEncoded"] = encoder.transform(train[["HubID"]])
            valid["HubID_TargetEncoded"] = encoder.transform(valid[["HubID"]])
            if "HubID_TargetEncoded" not in columns:
                columns.append("HubID_TargetEncoded")
                
        predictions = baseline_predictions(valid)
        fitters = {"catboost": fit_catboost, "lightgbm": fit_lightgbm, "lightgbm_tweedie": fit_lightgbm_tweedie}
        
        ensemble_log = np.zeros(len(valid))
        for backend in backends:
            fit_function = fitters[backend]
            model = fit_function(train, valid, columns)
            preds = predict_model(model, valid, columns, backend)
            predictions[f"{backend}_{feature_group}"] = preds
            
            train_mask = train["IsOpen"].eq(1)
            train_preds = predict_model(model, train, columns, backend)
            c = np.mean(np.log1p(train.loc[train_mask, "ActualOrderVolume"]) - np.log1p(train_preds[train_mask]))
            corrected_preds = np.where(valid["IsOpen"].eq(1), np.expm1(np.log1p(preds) + c), 0.0)
            predictions[f"{backend}_{feature_group}_corrected"] = corrected_preds
            
            ensemble_log += np.log1p(corrected_preds)
            
        ensemble_log /= len(backends)
        predictions[f"ensemble_log_mean_{feature_group}"] = np.where(valid["IsOpen"].eq(1), np.expm1(ensemble_log), 0.0)
        metrics_rows.extend(metric_rows(valid, predictions, valid_index + 1))
        oof = valid[["Fold", "HubID", "Date", "Horizon", "IsOpen", "ActualOrderVolume"]].copy()
        for name, values in predictions.items():
            oof[name] = values
        oof_parts.append(oof)

    output = paths.root / "artifacts" / "models"
    output.mkdir(parents=True, exist_ok=True)
    metrics = pd.DataFrame(metrics_rows)
    oof = pd.concat(oof_parts, ignore_index=True)
    suffix = "both" if set(backends) == {"catboost", "lightgbm"} else "_".join(backends)
    metrics.to_csv(output / f"walk_forward_{feature_group}_{suffix}_metrics.csv", index=False)
    oof.to_csv(output / f"walk_forward_{feature_group}_{suffix}_oof.csv.gz", index=False, compression="gzip")
    return metrics, oof


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("baselines", "walk-forward"))
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--feature-group", choices=("static", "orders", "orders_sessions", "history", "all"), default="all")
    parser.add_argument("--backend", choices=("both", "catboost", "lightgbm"), default="both")
    parser.add_argument("--folds", default="1,2,3,4", help="Comma-separated fold numbers")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    paths = Paths(args.root.resolve())
    if args.command == "baselines":
        evaluate_baselines(paths)
    else:
        backends = ("catboost", "lightgbm", "lightgbm_tweedie") if args.backend == "both" else (args.backend,)
        folds_to_run = tuple(int(value) for value in args.folds.split(",") if value.strip())
        walk_forward_models(paths, args.feature_group, backends=backends, folds_to_run=folds_to_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
