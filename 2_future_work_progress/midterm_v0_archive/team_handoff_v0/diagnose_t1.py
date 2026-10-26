
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent

DATA_DIR = next(
    (
        p for p in [ROOT / "datset_kaggle", ROOT / "dataset_kaggle"]
        if (p / "orders_train.csv").exists()
    ),
    None,
)

if DATA_DIR is None:
    raise FileNotFoundError("Cannot find orders_train.csv")

df = pd.read_csv(DATA_DIR / "orders_train.csv", parse_dates=["Date"])

df = df.loc[
    (df["IsOpen"] == 1) & df["Weekday"].isin([1, 5]),
    ["HubID", "Date", "Weekday", "OrderVolume", "PromoActive"],
].dropna().copy()

df["Monday"] = (df["Weekday"] == 1).astype(int)
df["PromoMonday"] = df["PromoActive"] * df["Monday"]

print("\n=== DATASET ===")
print("Rows:", len(df))
print("Hubs:", df["HubID"].nunique())
print("Dates:", df["Date"].nunique())
print("PromoActive unique values:", sorted(df["PromoActive"].unique()))

print("\n=== PROMOTION VARIATION WITHIN DATES ===")
date_variation = df.groupby("Date")["PromoActive"].nunique()
print(date_variation.value_counts().sort_index())
print("Dates with both promo states:", (date_variation > 1).sum())

print("\n=== PROMOTION VARIATION WITHIN HUBS ===")
hub_variation = df.groupby("HubID")["PromoActive"].nunique()
print(hub_variation.value_counts().sort_index())
print("Hubs with both promo states:", (hub_variation > 1).sum())

print("\n=== PROMOTION COUNTS BY WEEKDAY ===")
print(pd.crosstab(df["Weekday"], df["PromoActive"]))

print("\n=== PROMOTION-MONDAY VARIATION ===")
print(pd.crosstab(df["Monday"], df["PromoActive"]))

print("\n=== PROMOTION CHANGES WITHIN HUB-DATE SAMPLE ===")
print(
    df.groupby("Weekday").agg(
        rows=("PromoActive", "size"),
        hubs=("HubID", "nunique"),
        dates=("Date", "nunique"),
        promo_hubs=("PromoActive", "sum"),
        demand_mean=("OrderVolume", "mean"),
    )
)
