import glob
import os
import shutil
import sys

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
os.environ["PYTHONPATH"] = pkg_root + os.pathsep + os.environ.get("PYTHONPATH", "")

# --- locate the competition's own raw files (no external data) ---
raw_dir = None
for path in glob.glob("/kaggle/input/*/orders_train.csv"):
    raw_dir = os.path.dirname(path)
    break
if raw_dir is None:
    for path in glob.glob("/kaggle/input/**/orders_train.csv", recursive=True):
        raw_dir = os.path.dirname(path)
        break
if raw_dir is None:
    raise FileNotFoundError("could not find orders_train.csv under /kaggle/input — is the competition data attached?")
print("using raw competition data from:", raw_dir)

# --- build a working project root with the raw files where our pipeline expects them ---
work_root = "/kaggle/working/proj"
os.makedirs(os.path.join(work_root, "datset_kaggle"), exist_ok=True)
for name in ("orders_train.csv", "orders_test.csv", "hub_metadata.csv", "sample_submission.csv"):
    src = os.path.join(raw_dir, name)
    dst = os.path.join(work_root, "datset_kaggle", name)
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copy(src, dst)

import src.eda_pipeline as edap  # noqa: E402
from src.eda_pipeline import Paths  # noqa: E402
from sklearn.preprocessing import TargetEncoder  # noqa: E402
from src.model_pipeline import (  # noqa: E402
    feature_columns,
    fit_catboost,
    fit_lightgbm,
    fit_lightgbm_tweedie,
    load_origin_training,
    predict_model,
)

print("SEED (fixed, disclosed):", edap.SEED)

# --- regenerate all engineered features from the raw competition files only ---
print("running preprocess...")
edap.main(["preprocess", "--root", work_root])
print("running build-training-origins...")
edap.main(["build-training-origins", "--root", work_root])
print("running build-folds...")
edap.main(["build-folds", "--root", work_root])

from pathlib import Path as _Path  # noqa: E402

paths = Paths(_Path(work_root))
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

valid = train.sample(frac=0.05, random_state=edap.SEED)
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
sample = pd.read_csv(os.path.join(work_root, "datset_kaggle", "sample_submission.csv"))
assert len(submission) == len(sample), "row count mismatch vs sample_submission"
assert list(submission["Id"]) == list(sample["Id"]), "Id order mismatch vs sample_submission"

submission.to_csv("/kaggle/working/submission.csv", index=False)
print("done, rows:", len(submission))
print(submission.head())
