import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# --- locate our uploaded code (the solari-pipeline dataset) ---
pkg_root = None
for path in glob.glob("/kaggle/input/*/src/model_pipeline.py"):
    pkg_root = path[: -len("/src/model_pipeline.py")]
    break
if pkg_root is None:
    for path in glob.glob("/kaggle/input/**/model_pipeline.py", recursive=True):
        pkg_root = os.path.dirname(os.path.dirname(path))
        break
if pkg_root is None:
    raise FileNotFoundError("could not find src/model_pipeline.py under /kaggle/input")
print("using code from:", pkg_root)
sys.path.insert(0, pkg_root)

# --- locate phase 1's output (test_forecast_features.csv.gz + training_origins/) ---
data_root = None
for path in glob.glob("/kaggle/input/*/proj/data/processed/test_forecast_features.csv.gz"):
    data_root = path[: -len("/data/processed/test_forecast_features.csv.gz")]
    break
if data_root is None:
    for path in glob.glob("/kaggle/input/**/test_forecast_features.csv.gz", recursive=True):
        data_root = os.path.dirname(os.path.dirname(os.path.dirname(path)))
        break
if data_root is None:
    raise FileNotFoundError(
        "could not find phase-1 output (test_forecast_features.csv.gz) under /kaggle/input — "
        "did you add the phase-1 notebook's Output as an Input source here?"
    )
print("using phase-1 data from:", data_root)

from src.eda_pipeline import Paths, SEED  # noqa: E402
from sklearn.preprocessing import TargetEncoder  # noqa: E402
from src.model_pipeline import (  # noqa: E402
    feature_columns,
    fit_catboost,
    fit_lightgbm,
    fit_lightgbm_tweedie,
    load_origin_training,
    predict_model,
)

print("SEED (fixed, disclosed):", SEED)

paths = Paths(Path(data_root))
test = pd.read_csv(
    paths.processed / "test_forecast_features.csv.gz",
    parse_dates=["Date", "ForecastOrigin", "HistoryStartDate", "HistoryLastDate"],
)
test_origin = pd.Timestamp(test["ForecastOrigin"].iloc[0])
columns = feature_columns(test, "all")

train = load_origin_training(paths, test_origin, columns)
print("train rows:", len(train))

encoder = TargetEncoder(smooth="auto")
mask = train["IsOpen"].eq(1)
encoder.fit(train.loc[mask, ["HubID"]], np.log1p(train.loc[mask, "ActualOrderVolume"]))
train["HubID_TargetEncoded"] = encoder.transform(train[["HubID"]])
test["HubID_TargetEncoded"] = encoder.transform(test[["HubID"]])
columns.append("HubID_TargetEncoded")

valid = train.sample(frac=0.05, random_state=SEED)
fitters = {"catboost": fit_catboost, "lightgbm": fit_lightgbm, "lightgbm_tweedie": fit_lightgbm_tweedie}

ensemble_log = np.zeros(len(test))
for name, fitter in fitters.items():
    print("fitting", name)
    model = fitter(train, valid, columns)
    train_pred = predict_model(model, train, columns, name)
    c = float(
        np.mean(np.log1p(train.loc[mask, "ActualOrderVolume"]) - np.log1p(train_pred[mask.to_numpy()]))
    )
    test_pred = predict_model(model, test, columns, name)
    corrected = np.where(test["IsOpen"].eq(1), np.expm1(np.log1p(test_pred) + c), 0.0)
    ensemble_log += np.log1p(corrected)
    print(name, "done, log-offset c =", c)

ensemble_log /= len(fitters)
final = np.clip(np.where(test["IsOpen"].eq(1), np.expm1(ensemble_log), 0.0), 0, None)

submission = pd.DataFrame({"Id": test["Id"], "OrderVolume": final})

sample_path = None
for path in glob.glob("/kaggle/input/*/sample_submission.csv"):
    sample_path = path
    break
if sample_path is None:
    for path in glob.glob("/kaggle/input/**/sample_submission.csv", recursive=True):
        sample_path = path
        break
if sample_path is not None:
    sample = pd.read_csv(sample_path)
    assert len(submission) == len(sample), "row count mismatch vs sample_submission"
    assert list(submission["Id"]) == list(sample["Id"]), "Id order mismatch vs sample_submission"

submission.to_csv("/kaggle/working/submission.csv", index=False)
print("done, rows:", len(submission))
print(submission.head())
