"""Retrain selected models on full legal history and write the Kaggle submission.

Run only after the walk-forward OOF metrics confirm the blend/offset choice:
    MPLCONFIGDIR=/tmp/kaggle_comp_mpl XDG_CACHE_HOME=/tmp/kaggle_comp_cache \
        conda run -n eda311 python -m scripts.build_submission
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.eda_pipeline import Paths
from src.model_pipeline import (
    NON_FEATURE_COLUMNS,
    fit_catboost,
    fit_lightgbm,
    feature_columns,
    load_fold_tables,
    load_origin_training,
    predict_model,
    rmsle,
)

FEATURE_GROUP = "all"
CATBOOST_WEIGHT = 0.6  # tuned on OOF blend sweep; adjust after final-schema OOF lands


def fit_offset(oof: pd.DataFrame, blend_col: str) -> float:
    open_mask = oof["IsOpen"].eq(1)
    actual = oof.loc[open_mask, "ActualOrderVolume"].to_numpy(float)
    pred = oof.loc[open_mask, blend_col].to_numpy(float)
    resid = np.log1p(actual) - np.log1p(np.clip(pred, 0, None))
    return float(resid.mean())


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    paths = Paths(root)

    # 1. Load all four fold tables purely to recompute the blend weight + log offset
    #    from OOF predictions once the walk-forward run has produced fresh oof files.
    oof_path = paths.root / "artifacts" / "models" / f"walk_forward_{FEATURE_GROUP}_oof.csv.gz"
    oof = pd.read_csv(oof_path)
    cb_col = f"catboost_{FEATURE_GROUP}"
    lgb_col = f"lightgbm_{FEATURE_GROUP}"
    blend = np.where(
        oof["IsOpen"].eq(0),
        0.0,
        np.expm1(
            CATBOOST_WEIGHT * np.log1p(np.clip(oof[cb_col], 0, None))
            + (1 - CATBOOST_WEIGHT) * np.log1p(np.clip(oof[lgb_col], 0, None))
        ),
    )
    oof["blend"] = blend
    offset = fit_offset(oof, "blend")
    actual = oof["ActualOrderVolume"].to_numpy(float)
    corrected = np.where(
        oof["IsOpen"].eq(0), 0.0, np.expm1(np.log1p(np.clip(blend, 0, None)) + offset)
    )
    print("Full 4-fold OOF RMSLE, blend+offset:", rmsle(actual, corrected))
    print("offset:", offset, "catboost_weight:", CATBOOST_WEIGHT)

    # 2. Train on every legal training origin (target_end <= test forecast origin).
    test = pd.read_csv(
        paths.processed / "test_forecast_features.csv.gz",
        parse_dates=["Date", "ForecastOrigin", "HistoryStartDate", "HistoryLastDate"],
    )
    test_origin = pd.Timestamp(test["ForecastOrigin"].iloc[0])
    columns = feature_columns(test, FEATURE_GROUP)
    train = load_origin_training(paths, test_origin, columns)
    print("full-history training rows:", len(train))

    cb_model = fit_catboost(train, train.sample(frac=0.05, random_state=13), columns)
    lgb_model = fit_lightgbm(train, train.sample(frac=0.05, random_state=13), columns)

    cb_pred = predict_model(cb_model, test, columns, "catboost")
    lgb_pred = predict_model(lgb_model, test, columns, "lightgbm")

    blend_pred = np.where(
        test["IsOpen"].eq(0),
        0.0,
        np.expm1(
            CATBOOST_WEIGHT * np.log1p(np.clip(cb_pred, 0, None))
            + (1 - CATBOOST_WEIGHT) * np.log1p(np.clip(lgb_pred, 0, None))
        ),
    )
    final_pred = np.where(
        test["IsOpen"].eq(0),
        0.0,
        np.expm1(np.log1p(np.clip(blend_pred, 0, None)) + offset),
    )
    final_pred = np.clip(final_pred, 0, None)

    submission = pd.DataFrame({"Id": test["Id"], "OrderVolume": final_pred})
    sample = pd.read_csv(paths.raw / "sample_submission.csv")
    assert len(submission) == len(sample), "row count mismatch vs sample_submission"
    assert list(submission["Id"]) == list(sample["Id"]), "Id order mismatch vs sample_submission"

    out_path = paths.root / "artifacts" / "models" / "submission.csv"
    submission.to_csv(out_path, index=False)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
