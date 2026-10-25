
from pathlib import Path
import pandas as pd

DATA_DIR = Path("datset_kaggle")

files = [
    "orders_train.csv",
    "hub_metadata.csv",
    "orders_test.csv",
]

for filename in files:
    path = DATA_DIR / filename

    print(f"\n{'=' * 60}")
    print(f"FILE: {filename}")
    print(f"{'=' * 60}")

    if not path.exists():
        print(f"ERROR: File not found: {path}")
        continue

    df = pd.read_csv(path)

    print("Shape:", df.shape)
    print("\nColumn names and data types:")
    print(df.dtypes.to_string())

    print("\nMissing values per column:")
    print(df.isna().sum().to_string())

    print("\nFull-row duplicates:", df.duplicated().sum())

    print("\nFirst five rows:")
    print(df.head().to_string(index=False))

print("\nInitial audit complete.")
