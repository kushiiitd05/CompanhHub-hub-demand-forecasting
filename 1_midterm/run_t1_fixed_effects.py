
from pathlib import Path
import pandas as pd
from linearmodels.iv import AbsorbingLS

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

OUT_DIR = ROOT / "midterm" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(DATA_DIR / "orders_train.csv", parse_dates=["Date"])

df = df.loc[
    (df["IsOpen"] == 1) & df["Weekday"].isin([1, 5]),
    ["HubID", "Date", "Weekday", "OrderVolume", "PromoActive"],
].dropna().copy()

df["Monday"] = (df["Weekday"] == 1).astype(float)
df["PromoActive"] = df["PromoActive"].astype(float)
df["PromoMonday"] = df["PromoActive"] * df["Monday"]

# Hub fixed effects only.
# Cluster standard errors by hub to account for within-hub dependence.
y = df["OrderVolume"]
X = df[["Monday", "PromoActive", "PromoMonday"]]
absorb = pd.DataFrame({
    "HubID": pd.Categorical(df["HubID"])
})

model = AbsorbingLS(y, X, absorb=absorb)
result = model.fit(
    cov_type="clustered",
    clusters=df[["HubID"]],
)

name = "PromoMonday"
ci = result.conf_int().loc[name]

output = pd.DataFrame([{
    "analysis": "T1_hub_fixed_effects_sensitivity",
    "n_rows": len(df),
    "n_hubs": df["HubID"].nunique(),
    "n_dates": df["Date"].nunique(),
    "monday_minus_friday_promotion_association": result.params[name],
    "clustered_se": result.std_errors[name],
    "ci95_low": ci.iloc[0],
    "ci95_high": ci.iloc[1],
    "p_value": result.pvalues[name],
    "notes": (
        "Hub fixed effects only; standard errors clustered by hub. "
        "Date fixed effects omitted because promotion is constant across "
        "hubs on each date. Observational association, not causal."
    ),
}])

output.to_csv(
    OUT_DIR / "t1_hub_fe_corrected_sensitivity.csv",
    index=False,
)

print("=== T1 HUB-FIXED-EFFECTS SENSITIVITY ===")
print(output.to_string(index=False))
print("\nModel summary:")
print(result.summary)
print("\nSaved:", OUT_DIR / "t1_hub_fe_corrected_sensitivity.csv")
