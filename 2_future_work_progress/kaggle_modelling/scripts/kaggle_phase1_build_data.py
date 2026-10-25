import glob
import os
import shutil
import sys

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

print("SEED (fixed, disclosed):", edap.SEED)

print("running preprocess...")
edap.main(["preprocess", "--root", work_root])
print("running build-training-origins...")
edap.main(["build-training-origins", "--root", work_root])
print("running build-folds...")
edap.main(["build-folds", "--root", work_root])

print("PHASE 1 DONE. Outputs under /kaggle/working/proj/data/processed/")
print("Save this notebook's version, then in the phase-2 notebook add this")
print("notebook's OUTPUT as an Input source (Add Input -> Notebook Output Files).")
