
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

DATA = Path("datset_kaggle")
FIGURES = Path("midterm/figures")
TABLES = Path("midterm/tables")

FIGURES.mkdir(parents=True, exist_ok=True)
TABLES.mkdir(parents=True, exist_ok=True)

orders = pd.read_csv(DATA / "orders_train.csv")
metadata = pd.read_csv(DATA / "hub_metadata.csv")

orders["Date"] = pd.to_datetime(orders["Date"])

# Primary descriptive analysis: recorded operating days.
open_days = orders.loc[orders["IsOpen"] == 1].copy()

print("=== EDA DATA SUMMARY ===")
print("Training rows:", len(orders))
print("Operating-day rows:", len(open_days))
print("Distinct hubs:", orders["HubID"].nunique())
print("Distinct dates:", orders["Date"].nunique())

print("\n=== ORDER VOLUME DESCRIPTIVES ===")
print(
    open_days["OrderVolume"]
    .describe(percentiles=[0.25, 0.50, 0.75, 0.90, 0.95, 0.99])
    .to_string()
)

print("Skewness:", open_days["OrderVolume"].skew())

# Figure 1: Distribution of order volume on operating days.
plt.figure(figsize=(8, 5))
sns.histplot(
    data=open_days,
    x="OrderVolume",
    bins=60
)
plt.title("Order Volume on Recorded Operating Days")
plt.xlabel("Orders per hub-day")
plt.ylabel("Number of hub-days")
plt.tight_layout()
plt.savefig(FIGURES / "order_distribution.png", dpi=200)
plt.close()

# Figure 2: Promotion versus non-promotion by weekday.
weekday_labels = {
    1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu",
    5: "Fri", 6: "Sat", 7: "Sun"
}

plot_data = open_days.copy()
plot_data["WeekdayName"] = plot_data["Weekday"].map(weekday_labels)
plot_data["Promotion"] = plot_data["PromoActive"].map(
    {0: "No promotion", 1: "Promotion"}
)

plt.figure(figsize=(10, 5))
sns.boxplot(
    data=plot_data,
    x="WeekdayName",
    y="OrderVolume",
    hue="Promotion",
    showfliers=False
)
plt.title("Operating-Day Order Volume by Weekday and Promotion")
plt.xlabel("Weekday")
plt.ylabel("Orders per hub-day")
plt.tight_layout()
plt.savefig(FIGURES / "promotion_by_weekday.png", dpi=200)
plt.close()

# Save exact group summaries behind Figure 2.
promotion_summary = (
    plot_data.groupby(["Weekday", "PromoActive"])["OrderVolume"]
    .agg(["count", "mean", "median", "std"])
    .reset_index()
)
promotion_summary.to_csv(
    TABLES / "promotion_by_weekday.csv",
    index=False
)

# Figure 3: Daily average orders per recorded operating hub.
daily = (
    open_days.groupby("Date")["OrderVolume"]
    .agg(["mean", "median", "count"])
    .reset_index()
)

plt.figure(figsize=(11, 5))
plt.plot(daily["Date"], daily["mean"])
plt.title("Mean Order Volume per Operating Hub over Time")
plt.xlabel("Date")
plt.ylabel("Mean orders per recorded operating hub")
plt.tight_layout()
plt.savefig(FIGURES / "daily_order_trend.png", dpi=200)
plt.close()

daily.to_csv(TABLES / "daily_order_summary.csv", index=False)

# Figure 4: Competitor distance versus hub-level mean orders.
hub_means = (
    open_days.groupby("HubID")["OrderVolume"]
    .mean()
    .rename("MeanOrderVolume")
    .reset_index()
)

competition = hub_means.merge(
    metadata[["HubID", "CompetitorDistance", "HubFormat",
              "AssortmentTier"]],
    on="HubID",
    how="left",
    validate="one_to_one"
)

competition = competition.dropna(
    subset=["CompetitorDistance", "MeanOrderVolume"]
)

competition = competition.loc[
    competition["CompetitorDistance"] >= 0
].copy()

competition["LogDistance"] = (
    competition["CompetitorDistance"].apply(lambda x: __import__("math").log1p(x))
)

plt.figure(figsize=(8, 5))
sns.scatterplot(
    data=competition,
    x="LogDistance",
    y="MeanOrderVolume"
)
plt.title("Competitor Distance and Mean Hub Order Volume")
plt.xlabel("log(1 + competitor distance)")
plt.ylabel("Mean orders per operating day")
plt.tight_layout()
plt.savefig(FIGURES / "competitor_distance.png", dpi=200)
plt.close()

competition.to_csv(
    TABLES / "competitor_demand_by_hub.csv",
    index=False
)

print("\n=== PROMOTION SUMMARY ===")
print(promotion_summary.to_string(index=False))

print("\n=== COMPETITOR ASSOCIATION: DESCRIPTIVE ONLY ===")
print("Hubs with usable competitor distances:", len(competition))
print(
    "Spearman correlation:",
    competition["LogDistance"].corr(
        competition["MeanOrderVolume"],
        method="spearman"
    )
)

print("\nFigures saved in:", FIGURES)
print("Summary tables saved in:", TABLES)
