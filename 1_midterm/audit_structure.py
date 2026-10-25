
from pathlib import Path
import pandas as pd

DATA = Path("datset_kaggle")

orders = pd.read_csv(DATA / "orders_train.csv")
metadata = pd.read_csv(DATA / "hub_metadata.csv")

orders["Date"] = pd.to_datetime(orders["Date"], errors="raise")

print("\n=== TRAINING DATA STRUCTURE ===")
print("Unique hubs:", orders["HubID"].nunique())
print("Unique dates:", orders["Date"].nunique())
print("Date range:", orders["Date"].min(), "to", orders["Date"].max())

# Check duplicate hub-date keys separately from duplicate rows.
duplicate_keys = orders.duplicated(["HubID", "Date"]).sum()
print("Duplicate HubID-Date keys:", duplicate_keys)

print("\n=== METADATA STRUCTURE ===")
print("Unique metadata hubs:", metadata["HubID"].nunique())
print("Duplicate metadata HubID keys:",
      metadata.duplicated(["HubID"]).sum())

# Verify that every training row can be matched to exactly one hub.
joined = orders.merge(
    metadata,
    on="HubID",
    how="left",
    validate="many_to_one",
    indicator=True
)

print("\n=== METADATA JOIN ===")
print("Joined rows:", len(joined))
print("Matched rows:", (joined["_merge"] == "both").sum())
print("Unmatched rows:", (joined["_merge"] == "left_only").sum())

# Calculate missing hub-date combinations using observed hubs and dates.
hub_ids = orders["HubID"].unique()
dates = orders["Date"].unique()

expected_rows = len(hub_ids) * len(dates)
observed_keys = orders[["HubID", "Date"]].drop_duplicates()

print("\n=== HUB-DATE COVERAGE ===")
print("Expected hub-date combinations:", expected_rows)
print("Observed unique hub-date combinations:", len(observed_keys))
print("Absent combinations:", expected_rows - len(observed_keys))

# Audit recorded closures and zero-order open days.
print("\n=== OPERATING STATUS ===")
print("Recorded closed rows:", (orders["IsOpen"] == 0).sum())
print("Recorded open rows:", (orders["IsOpen"] == 1).sum())
print(
    "Open rows with zero orders:",
    ((orders["IsOpen"] == 1) & (orders["OrderVolume"] == 0)).sum()
)
print(
    "Closed rows with nonzero orders:",
    ((orders["IsOpen"] == 0) & (orders["OrderVolume"] != 0)).sum()
)

# Check consistency of recorded weekday values across dates.
weekday_check = (
    orders.assign(DateWeekday=orders["Date"].dt.dayofweek)
    .groupby("Date")
    .apply(
        lambda g: (g["Weekday"] == g["DateWeekday"]).all(),
        include_groups=False
    )
)
print("\nAll recorded weekdays match pandas weekday convention:",
      weekday_check.all())

print("\nStructural audit complete.")
