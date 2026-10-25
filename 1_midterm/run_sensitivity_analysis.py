
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm


# ============================================================
# CompanhHub: sensitivity analysis
# T1: two-way fixed-effects regression
# T4: alternative competitor-opening event windows
# ============================================================

ROOT = Path(__file__).resolve().parent
DATA_DIR = next(
    (p for p in [ROOT / "datset_kaggle", ROOT / "dataset_kaggle"]
     if (p / "orders_train.csv").exists()),
    None,
)

if DATA_DIR is None:
    raise FileNotFoundError(
        "Could not find orders_train.csv in datset_kaggle or dataset_kaggle."
    )

orders = pd.read_csv(DATA_DIR / "orders_train.csv", parse_dates=["Date"])
hubs = pd.read_csv(DATA_DIR / "hub_metadata.csv")

OUT_DIR = ROOT / "midterm" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ALPHA = 0.05

orders["Date"] = pd.to_datetime(orders["Date"], errors="raise")
for col in ["Weekday", "OrderVolume", "IsOpen", "PromoActive"]:
    orders[col] = pd.to_numeric(orders[col], errors="raise")

open_orders = orders.loc[orders["IsOpen"] == 1].copy()


def ci_mean(values):
    """95% t confidence interval for a mean paired difference."""
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return np.nan, np.nan
    mean = x.mean()
    half = stats.t.ppf(0.975, len(x) - 1) * stats.sem(x)
    return float(mean - half), float(mean + half)


# ============================================================
# T1 SENSITIVITY:
# Outcome = promotion + promotion x Monday + hub FE + date FE
#
# Monday=1; Friday=0.
# The interaction coefficient estimates how much the promotion
# association differs on Monday compared with Friday.
#
# Date FE absorb the Monday main effect, so it is not included
# as a separate regressor after fixed-effect demeaning.
# Standard errors are clustered by HubID.
# ============================================================

print("Skipping non-identifiable two-way T1 FE specification. "
      "Use run_t1_fixed_effects.py and t1_date_robustness.py instead.")

# ============================================================
# T4 SENSITIVITY:
# Recalculate pre/post changes using several symmetric windows.
#
# Event date is approximated as the 15th of opening month.
# A 15-day buffer excludes the uncertain event period.
# Only operating-day observations are used.
# ============================================================

print("\nRunning T4 alternative event-window sensitivity...")

event_hubs = hubs[
    ["HubID", "CompetitorOpenSinceMonth", "CompetitorOpenSinceYear"]
].copy()

event_hubs["CompetitorOpenSinceMonth"] = pd.to_numeric(
    event_hubs["CompetitorOpenSinceMonth"], errors="coerce"
)
event_hubs["CompetitorOpenSinceYear"] = pd.to_numeric(
    event_hubs["CompetitorOpenSinceYear"], errors="coerce"
)

event_hubs = event_hubs.dropna(
    subset=["CompetitorOpenSinceMonth", "CompetitorOpenSinceYear"]
).copy()

event_hubs = event_hubs[
    event_hubs["CompetitorOpenSinceMonth"].between(1, 12)
].copy()

event_hubs["EventDate"] = event_hubs.apply(
    lambda r: pd.Timestamp(
        year=int(r["CompetitorOpenSinceYear"]),
        month=int(r["CompetitorOpenSinceMonth"]),
        day=15,
    ),
    axis=1,
)

date_min = orders["Date"].min()
date_max = orders["Date"].max()

# (window outer boundary in days, buffer around event in days)
# 75 gives 61-day pre/post windows; 105 gives 91 days;
# 135 gives 121 days.
WINDOWS = [(75, 15), (105, 15), (135, 15)]
MIN_OPERATING_DAYS = 30

event_rows = []
hub_groups = {
    hub_id: frame
    for hub_id, frame in open_orders.groupby("HubID")
}

for outer_days, buffer_days in WINDOWS:
    changes = []

    for row in event_hubs.itertuples(index=False):
        hub_id = row.HubID
        event_date = row.EventDate

        pre_start = event_date - pd.Timedelta(days=outer_days)
        pre_end = event_date - pd.Timedelta(days=buffer_days)
        post_start = event_date + pd.Timedelta(days=buffer_days)
        post_end = event_date + pd.Timedelta(days=outer_days)

        # Require both full windows inside the training date range.
        if pre_start < date_min or post_end > date_max:
            continue

        frame = hub_groups.get(hub_id)
        if frame is None:
            continue

        pre = frame.loc[
            frame["Date"].between(pre_start, pre_end), "OrderVolume"
        ]
        post = frame.loc[
            frame["Date"].between(post_start, post_end), "OrderVolume"
        ]

        if len(pre) < MIN_OPERATING_DAYS or len(post) < MIN_OPERATING_DAYS:
            continue

        changes.append({
            "HubID": hub_id,
            "PreMean": float(pre.mean()),
            "PostMean": float(post.mean()),
            "ChangePostMinusPre": float(post.mean() - pre.mean()),
            "PreOperatingDays": len(pre),
            "PostOperatingDays": len(post),
        })

    detail = pd.DataFrame(changes)
    detail_path = OUT_DIR / (
        f"t4_event_window_detail_{outer_days}d.csv"
    )
    detail.to_csv(detail_path, index=False)

    if len(detail) < 2:
        event_rows.append({
            "outer_window_days": outer_days,
            "buffer_days": buffer_days,
            "n_hubs": len(detail),
            "mean_change_post_minus_pre": np.nan,
            "ci95_low": np.nan,
            "ci95_high": np.nan,
            "paired_t_statistic": np.nan,
            "paired_t_p": np.nan,
            "wilcoxon_statistic": np.nan,
            "wilcoxon_p": np.nan,
            "notes": "Insufficient eligible hubs.",
        })
        continue

    diff = detail["ChangePostMinusPre"].to_numpy(dtype=float)
    mean_diff = float(diff.mean())
    low, high = ci_mean(diff)
    t_stat, t_p = stats.ttest_1samp(diff, popmean=0)

    if np.allclose(diff, 0):
        w_stat, w_p = 0.0, 1.0
    else:
        try:
            w_stat, w_p = stats.wilcoxon(diff)
        except ValueError:
            w_stat, w_p = np.nan, np.nan

    event_rows.append({
        "outer_window_days": outer_days,
        "buffer_days": buffer_days,
        "n_hubs": len(detail),
        "mean_change_post_minus_pre": mean_diff,
        "ci95_low": low,
        "ci95_high": high,
        "paired_t_statistic": float(t_stat),
        "paired_t_p": float(t_p),
        "wilcoxon_statistic": float(w_stat),
        "wilcoxon_p": float(w_p),
        "notes": (
            "Opening date approximated as day 15; at least 30 operating "
            "days required in each window; no comparison hubs or "
            "calendar controls."
        ),
    })

t4_output = pd.DataFrame(event_rows)
t4_output.to_csv(
    OUT_DIR / "t4_event_window_sensitivity.csv", index=False
)

print("\nT4 event-window sensitivity:")
print(t4_output.to_string(index=False))

print("\nSaved:")

print(OUT_DIR / "t4_event_window_sensitivity.csv")
print("Per-window hub-level details: t4_event_window_detail_*d.csv")
