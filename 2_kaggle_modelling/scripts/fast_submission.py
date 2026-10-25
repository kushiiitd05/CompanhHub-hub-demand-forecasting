"""Fast path: train CatBoost (best solo performer) on full legal history and submit.

No dependency on stale/incomplete OOF files. Time-boxed safety net.
    MPLCONFIGDIR=/tmp/kaggle_comp_mpl XDG_CACHE_HOME=/tmp/kaggle_comp_cache \
        conda run -n eda311 python -m scripts.fast_submission
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.eda_pipeline import Paths
from src.model_pipeline import fit_catboost, feature_columns, load_origin_training, predict_model

FEATURE_GROUP = "all"


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

    valid = train.sample(frac=0.05, random_state=13)
    model = fit_catboost(train, valid, columns)
    print("model fit done", flush=True)

    pred = predict_model(model, test, columns, "catboost")
    pred = np.where(test["IsOpen"].eq(0), 0.0, np.clip(pred, 0, None))

    submission = pd.DataFrame({"Id": test["Id"], "OrderVolume": pred})
    sample = pd.read_csv(paths.root / "datset_kaggle" / "sample_submission.csv")
    assert len(submission) == len(sample), "row count mismatch vs sample_submission"
    assert list(submission["Id"]) == list(sample["Id"]), "Id order mismatch vs sample_submission"

    out_path = paths.root / "artifacts" / "models" / "submission.csv"
    submission.to_csv(out_path, index=False)
    print("wrote", out_path, flush=True)


if __name__ == "__main__":
    main()
