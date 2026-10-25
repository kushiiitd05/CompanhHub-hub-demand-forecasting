"""One-shot full-history fit using the upgraded recipe: target-encoded HubID,
catboost + lightgbm + lightgbm_tweedie, per-model log-space bias correction,
log-mean ensemble. Mirrors walk_forward_models' per-fold logic but trains once
on all legal history and predicts the real test set directly (no 4-fold CV
re-run, which is what stalled for 6+ hours last time).

    MPLCONFIGDIR=/tmp/kaggle_comp_mpl XDG_CACHE_HOME=/tmp/kaggle_comp_cache \
        conda run -n eda311 python -m scripts.full_submission
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import TargetEncoder

from src.eda_pipeline import Paths
from src.model_pipeline import (
    feature_columns,
    fit_catboost,
    fit_lightgbm,
    fit_lightgbm_tweedie,
    load_origin_training,
    predict_model,
)

FEATURE_GROUP = "all"
BACKENDS = ("catboost", "lightgbm", "lightgbm_tweedie")
FITTERS = {"catboost": fit_catboost, "lightgbm": fit_lightgbm, "lightgbm_tweedie": fit_lightgbm_tweedie}


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    paths = Paths(root)

    test = pd.read_csv(
        paths.processed / "test_forecast_features.csv.gz",
        parse_dates=["Date", "ForecastOrigin", "HistoryStartDate", "HistoryLastDate"],
    )
    test_origin = pd.Timestamp(test["ForecastOrigin"].iloc[0])
    columns = feature_columns(test, FEATURE_GROUP)

    train = load_origin_training(paths, test_origin, columns)
    print("full-history training rows:", len(train), flush=True)

    encoder = TargetEncoder(smooth="auto")
    train_mask = train["IsOpen"].eq(1)
    encoder.fit(train.loc[train_mask, ["HubID"]], np.log1p(train.loc[train_mask, "ActualOrderVolume"]))
    train["HubID_TargetEncoded"] = encoder.transform(train[["HubID"]])
    test["HubID_TargetEncoded"] = encoder.transform(test[["HubID"]])
    if "HubID_TargetEncoded" not in columns:
        columns.append("HubID_TargetEncoded")

    valid = train.sample(frac=0.05, random_state=13)

    ensemble_log = np.zeros(len(test))
    per_model = {}
    for backend in BACKENDS:
        print(f"fitting {backend}...", flush=True)
        model = FITTERS[backend](train, valid, columns)

        train_preds = predict_model(model, train, columns, backend)
        c = float(
            np.mean(
                np.log1p(train.loc[train_mask, "ActualOrderVolume"]) - np.log1p(train_preds[train_mask.to_numpy()])
            )
        )
        print(f"{backend} log-offset c =", c, flush=True)

        test_preds = predict_model(model, test, columns, backend)
        corrected = np.where(test["IsOpen"].eq(1), np.expm1(np.log1p(test_preds) + c), 0.0)
        per_model[backend] = corrected
        ensemble_log += np.log1p(corrected)

    ensemble_log /= len(BACKENDS)
    final_pred = np.where(test["IsOpen"].eq(1), np.expm1(ensemble_log), 0.0)
    final_pred = np.clip(final_pred, 0, None)

    submission = pd.DataFrame({"Id": test["Id"], "OrderVolume": final_pred})
    sample = pd.read_csv(paths.root / "datset_kaggle" / "sample_submission.csv")
    assert len(submission) == len(sample), "row count mismatch vs sample_submission"
    assert list(submission["Id"]) == list(sample["Id"]), "Id order mismatch vs sample_submission"

    out_path = paths.root / "artifacts" / "models" / "submission_full.csv"
    submission.to_csv(out_path, index=False)
    print("wrote", out_path, flush=True)


if __name__ == "__main__":
    main()
