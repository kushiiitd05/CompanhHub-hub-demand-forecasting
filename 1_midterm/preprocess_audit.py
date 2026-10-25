
from pathlib import Path
import pandas as pd

data_dir = Path("datset_kaggle")
out_dir = Path("midterm/results")
out_dir.mkdir(parents=True, exist_ok=True)

train = pd.read_csv(data_dir / "orders_train.csv")
metadata = pd.read_csv(data_dir / "hub_metadata.csv")

joined = train.merge(
    metadata,
    on="HubID",
    how="left",
    validate="many_to_one"
)

audit = pd.DataFrame([
    {
        "stage": "Raw training data",
        "rows": len(train),
        "columns": len(train.columns),
        "missing_cells": int(train.isna().sum().sum()),
        "duplicate_rows": int(train.duplicated().sum()),
        "duplicate_hub_date_keys": int(
            train.duplicated(["HubID", "Date"]).sum()
        ),
    },
    {
        "stage": "Joined training data",
        "rows": len(joined),
        "columns": len(joined.columns),
        "missing_cells": int(joined.isna().sum().sum()),
        "duplicate_rows": int(joined.duplicated().sum()),
        "duplicate_hub_date_keys": int(
            joined.duplicated(["HubID", "Date"]).sum()
        ),
    },
])

audit.to_csv(out_dir / "preprocess_comparison.csv", index=False)

print(audit.to_string(index=False))
print("\nSaved:", out_dir / "preprocess_comparison.csv")
print("\nJoined column names:")
print(joined.columns.tolist())
print("\nJoined missing values:")
print(joined.isna().sum().to_string())
