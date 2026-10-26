
from pathlib import Path
import pandas as pd

DATA = Path("datset_kaggle")
OUT = Path("midterm/results")
OUT.mkdir(parents=True, exist_ok=True)

orders = pd.read_csv(DATA / "orders_train.csv")
metadata = pd.read_csv(DATA / "hub_metadata.csv")

# Join each order record to exactly one hub metadata record.
df = orders.merge(
    metadata,
    on="HubID",
    how="left",
    validate="many_to_one"
)

assert len(df) == len(orders), "Unexpected row-count change after join"
assert df["HubFormat"].notna().all(), "Some hubs lack metadata"

# Preserve information about unavailable metadata.
df["CompetitorDistanceMissing"] = (
    df["CompetitorDistance"].isna().astype("int8")
)

df["CompetitorHistoryMissing"] = (
    df["CompetitorOpenSinceMonth"].isna()
    | df["CompetitorOpenSinceYear"].isna()
).astype("int8")

df["LoyaltyHistoryMissing"] = (
    df["LoyaltyProgramSinceWeek"].isna()
    | df["LoyaltyProgramSinceYear"].isna()
    | df["LoyaltyProgramInterval"].isna()
).astype("int8")

# Binary indicators remain binary.
binary_cols = [
    "IsOpen",
    "PromoActive",
    # RegionalHoliday has multiple coded levels, not a binary indicator.
    # It remains in the numeric-code representation in this analysis,
    # and is not used as a response regressor in the four tests.
    "SchoolClosureFlag",
    "LoyaltyProgram",
]

# Treat weekday and the coded hub categories as categorical.
categorical_cols = [
    "Weekday",
    "HubFormat",
    "AssortmentTier",
    "LoyaltyProgramInterval",
]

# Use string labels so the encoding schema is explicit.
for col in categorical_cols:
    df[col] = df[col].astype("string").fillna("MISSING")

encoded = pd.get_dummies(
    df,
    columns=categorical_cols,
    dtype="int8"
)

# Date is retained for time-based analysis but is not a numeric magnitude.
# HubID remains an identifier and is not one-hot encoded.
encoded["Date"] = pd.to_datetime(encoded["Date"])

n_rows, n_columns = encoded.shape
product = n_rows * n_columns

print("=== ENCODED DATASET ===")
print("Rows:", n_rows)
print("Columns:", n_columns)
print(f"Rows x columns = {n_rows:,} x {n_columns:,} = {product:,}")
print("Requirement met:", product >= 3_000_000)

# Record the actual encoded schema.
schema = pd.DataFrame({
    "column": encoded.columns,
    "dtype": [str(encoded[c].dtype) for c in encoded.columns],
})

schema.to_csv(OUT / "encoded_schema.csv", index=False)

# Save the encoded dataset for reproducibility.
# This file is generated output; raw input files remain unchanged.
encoded.to_parquet(OUT / "encoded_training.parquet", index=False)

# Baseline comparison: raw, joined, encoded.
comparison = pd.DataFrame([
    {
        "stage": "Raw training",
        "rows": len(orders),
        "columns": len(orders.columns),
        "rows_times_columns": len(orders) * len(orders.columns),
        "missing_cells": int(orders.isna().sum().sum()),
    },
    {
        "stage": "Joined",
        "rows": len(df),
        "columns": len(df.columns),
        "rows_times_columns": len(df) * len(df.columns),
        "missing_cells": int(df.isna().sum().sum()),
    },
    {
        "stage": "Encoded",
        "rows": n_rows,
        "columns": n_columns,
        "rows_times_columns": product,
        "missing_cells": int(encoded.isna().sum().sum()),
    },
])

comparison.to_csv(OUT / "preprocess_comparison.csv", index=False)

print("\n=== BEFORE-AND-AFTER COMPARISON ===")
print(comparison.to_string(index=False))
print("\nSaved outputs to:", OUT)

