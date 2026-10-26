
from pathlib import Path
import json

import numpy as np
import pandas as pd
from scipy import stats


# ============================================================
# COMPANHHUB — CSE558 MIDTERM HYPOTHESIS TESTS
# Four primary tests; alpha = 0.05; Holm correction across tests
# ============================================================

ROOT = Path(__file__).resolve().parent
DATA_DIR = next(
    (
        p for p in [ROOT / "datset_kaggle", ROOT / "dataset_kaggle"]
        if (p / "orders_train.csv").exists()
    ),
    None,
)

if DATA_DIR is None:
    raise FileNotFoundError(
        "Cannot find orders_train.csv in datset_kaggle or dataset_kaggle."
    )

ORDERS_FILE = DATA_DIR / "orders_train.csv"
HUBS_FILE = DATA_DIR / "hub_metadata.csv"
OUT_DIR = ROOT / "midterm" / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ALPHA = 0.05
N_PERMUTATIONS = 20000
N_BOOTSTRAPS = 2000
RNG = np.random.default_rng(558)


# ------------------------------------------------------------
# Load and validate data
# ------------------------------------------------------------
orders = pd.read_csv(ORDERS_FILE, parse_dates=["Date"])
hubs = pd.read_csv(HUBS_FILE)

required_orders = {
    "HubID", "Date", "Weekday", "OrderVolume", "IsOpen", "PromoActive"
}
required_hubs = {
    "HubID", "HubFormat", "CompetitorDistance",
    "CompetitorOpenSinceMonth", "CompetitorOpenSinceYear"
}

if not required_orders.issubset(orders.columns):
    raise ValueError(
        f"Missing order columns: {required_orders - set(orders.columns)}"
    )

if not required_hubs.issubset(hubs.columns):
    raise ValueError(
        f"Missing metadata columns: {required_hubs - set(hubs.columns)}"
    )

if orders.duplicated(["HubID", "Date"]).any():
    raise ValueError("Duplicate HubID-Date records found.")

if hubs["HubID"].duplicated().any():
    raise ValueError("Duplicate HubID rows in metadata.")

orders["Date"] = pd.to_datetime(orders["Date"], errors="raise")
for col in ["Weekday", "OrderVolume", "IsOpen", "PromoActive"]:
    orders[col] = pd.to_numeric(orders[col], errors="raise")

open_orders = orders.loc[orders["IsOpen"] == 1].copy()
all_dates = pd.date_range(
    orders["Date"].min(), orders["Date"].max(), freq="D"
)

print("Orders:", len(orders))
print("Operating-day records:", len(open_orders))
print("Hubs in training data:", orders["HubID"].nunique())
print("Training date range:", orders["Date"].min().date(),
      "to", orders["Date"].max().date())


# ------------------------------------------------------------
# Common helpers
# ------------------------------------------------------------
def mean_ci(values, confidence=0.95):
    """Two-sided t confidence interval for a sample mean."""
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return np.nan, np.nan
    se = stats.sem(x)
    crit = stats.t.ppf((1 + confidence) / 2, len(x) - 1)
    return float(x.mean() - crit * se), float(x.mean() + crit * se)


def paired_test_result(name, differences, description):
    """
    Tests whether the mean of paired, hub-level differences is zero.
    Positive values mean the first quantity exceeds the second.
    """
    d = np.asarray(differences, dtype=float)
    d = d[np.isfinite(d)]
    n = len(d)

    result = {
        "test": name,
        "method": "Paired hub-level t-test",
        "n_units": int(n),
        "effect_estimate": np.nan,
        "ci95_low": np.nan,
        "ci95_high": np.nan,
        "effect_size": np.nan,
        "statistic": np.nan,
        "p_raw": np.nan,
        "notes": description,
    }
    sensitivity = {
        "test": name,
        "sensitivity_method": "Wilcoxon signed-rank",
        "n_units": int(n),
        "statistic": np.nan,
        "p_raw": np.nan,
        "notes": "",
    }

    if n < 2:
        result["notes"] += " Insufficient paired hubs."
        sensitivity["notes"] = "Insufficient paired hubs."
        return result, sensitivity

    mean_d = float(np.mean(d))
    low, high = mean_ci(d)
    sd = float(np.std(d, ddof=1))
    t_stat, p_val = stats.ttest_1samp(d, popmean=0)

    result.update({
        "effect_estimate": mean_d,
        "ci95_low": low,
        "ci95_high": high,
        "effect_size": mean_d / sd if sd > 0 else np.nan,
        "statistic": float(t_stat),
        "p_raw": float(p_val),
    })

    if np.allclose(d, 0):
        sensitivity.update({
            "statistic": 0.0,
            "p_raw": 1.0,
            "notes": "All differences are zero.",
        })
    else:
        try:
            w_stat, w_p = stats.wilcoxon(d, alternative="two-sided")
            sensitivity.update({
                "statistic": float(w_stat),
                "p_raw": float(w_p),
                "notes": "Nonparametric paired sensitivity test.",
            })
        except ValueError as exc:
            sensitivity["notes"] = str(exc)

    return result, sensitivity


# ============================================================
# TEST 1 — Does promotion lift differ between Monday and Friday?
#
# Per hub:
# Monday lift = mean(Monday, promo) - mean(Monday, no promo)
# Friday lift = mean(Friday, promo) - mean(Friday, no promo)
# Tested quantity = Monday lift - Friday lift
# ============================================================
weekday_promo = (
    open_orders.loc[open_orders["Weekday"].isin([1, 5])]
    .groupby(["HubID", "Weekday", "PromoActive"])["OrderVolume"]
    .mean()
    .unstack(["Weekday", "PromoActive"])
)

needed = [(1, 0), (1, 1), (5, 0), (5, 1)]
missing = [key for key in needed if key not in weekday_promo.columns]
if missing:
    raise ValueError(f"Required Monday/Friday promotion groups missing: {missing}")

monday_lift = weekday_promo[(1, 1)] - weekday_promo[(1, 0)]
friday_lift = weekday_promo[(5, 1)] - weekday_promo[(5, 0)]
t1_differences = (monday_lift - friday_lift).dropna()

t1, t1_sens = paired_test_result(
    "T1_monday_vs_friday_promotion_lift",
    t1_differences,
    "Positive effect means the Monday promotion-associated difference "
    "exceeds Friday's. Uses hubs with all four groups; observational."
)


# ============================================================
# TEST 2 — Is long missing historical data associated with hub format?
#
# Long gap = >=100 consecutive absent hub-date records within the
# overall training date range. Missing records are NOT closures.
# Monte Carlo permutation p-value used because expected cells are sparse.
# ============================================================
present_dates = (
    orders.groupby("HubID")["Date"]
    .apply(lambda s: set(pd.to_datetime(s).dt.normalize()))
    .to_dict()
)

gap_rows = []
for hub_id in hubs["HubID"]:
    present = present_dates.get(hub_id, set())
    missing_flags = [date not in present for date in all_dates]
    longest = current = 0
    for flag in missing_flags:
        if flag:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    gap_rows.append({
        "HubID": hub_id,
        "LongestMissingRunDays": longest,
        "LongGap100Days": longest >= 100,
    })

gap_df = pd.DataFrame(gap_rows)
t2_data = (
    hubs[["HubID", "HubFormat"]]
    .merge(gap_df, on="HubID", validate="one_to_one")
    .dropna(subset=["HubFormat"])
)

contingency = pd.crosstab(
    t2_data["HubFormat"], t2_data["LongGap100Days"]
).reindex(columns=[False, True], fill_value=0)

chi2, chi_p_asymptotic, dof, expected = stats.chi2_contingency(
    contingency, correction=False
)

formats = t2_data["HubFormat"].to_numpy()
gap_labels = t2_data["LongGap100Days"].to_numpy(dtype=bool)
perm_stats = np.empty(N_PERMUTATIONS)

for i in range(N_PERMUTATIONS):
    shuffled = RNG.permutation(gap_labels)
    # Retain exact hub-format categories and the 2-column observed margin.
    perm_table = np.zeros_like(contingency.to_numpy(), dtype=np.int64)
    np.add.at(perm_table, (pd.Categorical(formats, categories=contingency.index).codes, shuffled.astype(int)), 1)
    perm_stats[i] = stats.chi2_contingency(perm_table, correction=False)[0]

chi_p_permutation = (
    1 + np.sum(perm_stats >= chi2)
) / (N_PERMUTATIONS + 1)

n_t2 = int(contingency.to_numpy().sum())
cramers_v = (
    float(np.sqrt(
        chi2 / (n_t2 * min(contingency.shape[0] - 1,
                           contingency.shape[1] - 1))
    ))
    if min(contingency.shape) > 1 and n_t2 > 0 else np.nan
)
min_expected = float(expected.min()) if expected.size else np.nan

# 95% percentile bootstrap CI for Cramer's V, resampling hubs.
# The effect-size CI complements (does not replace) the permutation p-value.
t2_boot_rng = np.random.default_rng(20261025)
t2_format_codes = pd.Categorical(t2_data["HubFormat"],
                                  categories=contingency.index).codes
t2_gap_codes = t2_data["LongGap100Days"].astype(int).to_numpy()
t2_boot_effects = []
for _ in range(5000):
    ix = t2_boot_rng.integers(0, n_t2, size=n_t2)
    tab = np.zeros(contingency.shape, dtype=int)
    np.add.at(tab, (t2_format_codes[ix], t2_gap_codes[ix]), 1)
    if np.any(tab.sum(axis=0) == 0) or np.any(tab.sum(axis=1) == 0):
        continue
    chi_boot = stats.chi2_contingency(tab, correction=False)[0]
    t2_boot_effects.append(np.sqrt(chi_boot / n_t2))
t2_ci_low, t2_ci_high = np.quantile(t2_boot_effects, [0.025, 0.975])

t2 = {
    "test": "T2_long_gap_vs_hub_format",
    "method": "Pearson chi-square statistic with Monte Carlo permutation p-value",
    "n_units": n_t2,
    "effect_estimate": cramers_v,
    "ci95_low": float(t2_ci_low),
    "ci95_high": float(t2_ci_high),
    "effect_size": cramers_v,
    "statistic": float(chi2),
    "p_raw": float(chi_p_permutation),
    "notes": (
        f"Cramer's V effect size. Permutations={N_PERMUTATIONS}; "
        f"asymptotic p={chi_p_asymptotic:.8g}; df={dof}; "
        f"minimum expected cell={min_expected:.4f}. "
        "Missing records do not imply closure."
    ),
}
t2_sens = {
    "test": "T2_long_gap_vs_hub_format",
    "sensitivity_method": "Expected-cell-count diagnostic",
    "n_units": n_t2,
    "statistic": min_expected,
    "p_raw": np.nan,
    "notes": (
        f"Any expected cell below 5: {bool((expected < 5).any())}. "
        "Use permutation p-value rather than relying only on asymptotic p."
    ),
}


# ============================================================
# TEST 3 — Is competitor distance associated with hub demand?
#
# One row per hub; Spearman correlation, with hub bootstrap CI.
# ============================================================
hub_demand = (
    open_orders.groupby("HubID", as_index=False)["OrderVolume"]
    .mean()
    .rename(columns={"OrderVolume": "MeanOrderVolume"})
)

distance_data = hub_demand.merge(
    hubs[["HubID", "CompetitorDistance"]],
    on="HubID", how="inner", validate="one_to_one"
)
distance_data["CompetitorDistance"] = pd.to_numeric(
    distance_data["CompetitorDistance"], errors="coerce"
)
distance_data = distance_data.dropna(
    subset=["CompetitorDistance", "MeanOrderVolume"]
)

rho, rho_p = stats.spearmanr(
    distance_data["CompetitorDistance"],
    distance_data["MeanOrderVolume"]
)

boot_rho = []
x = distance_data["CompetitorDistance"].to_numpy()
y = distance_data["MeanOrderVolume"].to_numpy()

for _ in range(N_BOOTSTRAPS):
    idx = RNG.integers(0, len(distance_data), size=len(distance_data))
    xb, yb = x[idx], y[idx]
    if np.unique(xb).size > 1 and np.unique(yb).size > 1:
        boot_rho.append(stats.spearmanr(xb, yb).statistic)

rho_low, rho_high = (
    np.quantile(boot_rho, [0.025, 0.975])
    if boot_rho else (np.nan, np.nan)
)

tau, tau_p = stats.kendalltau(x, y)

t3 = {
    "test": "T3_competitor_distance_vs_demand",
    "method": "Spearman rank correlation; one row per hub",
    "n_units": int(len(distance_data)),
    "effect_estimate": float(rho),
    "ci95_low": float(rho_low),
    "ci95_high": float(rho_high),
    "effect_size": float(rho),
    "statistic": float(rho),
    "p_raw": float(rho_p),
    "notes": (
        f"Bootstrap CI resamples hubs. Kendall sensitivity tau={tau:.6f}, "
        f"p={tau_p:.8g}. Association is not causation."
    ),
}
t3_sens = {
    "test": "T3_competitor_distance_vs_demand",
    "sensitivity_method": "Kendall rank correlation",
    "n_units": int(len(distance_data)),
    "statistic": float(tau),
    "p_raw": float(tau_p),
    "notes": "Alternative rank-based association measure.",
}


# ============================================================
# TEST 4 — Does demand change after a competitor opens?
#
# Metadata only gives opening month/year, not exact day.
# Approximate event date as the 15th of that month.
# Compare recorded operating-day mean demand in:
#   pre: 105 to 15 days before approximate event date
#   post: 15 to 105 days after approximate event date
# Require >=30 recorded operating-day observations in EACH window.
#
# This is a paired event-window test, not a fully controlled causal
# event-study regression. Only events with complete pre/post windows
# inside the observed training date range are included.
# ============================================================
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
    lambda row: pd.Timestamp(
        year=int(row["CompetitorOpenSinceYear"]),
        month=int(row["CompetitorOpenSinceMonth"]),
        day=15
    ),
    axis=1
)

event_rows = []
for row in event_hubs.itertuples(index=False):
    hub_id = row.HubID
    event_date = row.EventDate

    # Require complete calendar windows within the dataset period.
    pre_start = event_date - pd.Timedelta(days=105)
    pre_end = event_date - pd.Timedelta(days=15)
    post_start = event_date + pd.Timedelta(days=15)
    post_end = event_date + pd.Timedelta(days=105)

    if pre_start < all_dates.min() or post_end > all_dates.max():
        continue

    hub_rows = open_orders.loc[open_orders["HubID"] == hub_id]

    pre = hub_rows.loc[
        hub_rows["Date"].between(pre_start, pre_end), "OrderVolume"
    ]
    post = hub_rows.loc[
        hub_rows["Date"].between(post_start, post_end), "OrderVolume"
    ]

    if len(pre) < 30 or len(post) < 30:
        continue

    event_rows.append({
        "HubID": hub_id,
        "ApproxEventDate": event_date,
        "PreMeanOrderVolume": float(pre.mean()),
        "PostMeanOrderVolume": float(post.mean()),
        "PreOperatingDays": int(len(pre)),
        "PostOperatingDays": int(len(post)),
        "ChangePostMinusPre": float(post.mean() - pre.mean()),
    })

event_results = pd.DataFrame(event_rows)
event_results.to_csv(OUT_DIR / "competitor_event_window_data.csv", index=False)

if len(event_results) >= 2:
    t4, t4_sens = paired_test_result(
        "T4_demand_after_competitor_opening",
        event_results["ChangePostMinusPre"].to_numpy(),
        "Post minus pre mean demand per hub. Opening date approximated "
        "as the 15th of the recorded month; 15-day buffer on both sides. "
        "Requires >=30 recorded operating days per window. Not causal."
    )
    t4["method"] = "Paired t-test on pre/post event-window hub means"
    t4_sens["notes"] += (
        " Interpretation limited by approximate opening dates, selection "
        "of hubs with complete windows, and lack of control hubs."
    )
else:
    t4 = {
        "test": "T4_demand_after_competitor_opening",
        "method": "Paired event-window t-test",
        "n_units": int(len(event_results)),
        "effect_estimate": np.nan,
        "ci95_low": np.nan,
        "ci95_high": np.nan,
        "effect_size": np.nan,
        "statistic": np.nan,
        "p_raw": np.nan,
        "notes": (
            "Fewer than two eligible hubs. Test not estimable under the "
            "specified windows and minimum observation requirement."
        ),
    }
    t4_sens = {
        "test": "T4_demand_after_competitor_opening",
        "sensitivity_method": "Wilcoxon signed-rank",
        "n_units": int(len(event_results)),
        "statistic": np.nan,
        "p_raw": np.nan,
        "notes": "Insufficient eligible event hubs.",
    }


# ============================================================
# Holm correction across four primary tests
# ============================================================
results = pd.DataFrame([t1, t2, t3, t4])
valid = results["p_raw"].notna()
pvals = results.loc[valid, "p_raw"].to_numpy()

m = len(pvals)
order = np.argsort(pvals)
sorted_p = pvals[order]
sorted_adj = np.maximum.accumulate(
    np.minimum(1.0, (m - np.arange(m)) * sorted_p)
)
adjusted = np.empty(m)
adjusted[order] = sorted_adj

results["p_holm"] = np.nan
results.loc[valid, "p_holm"] = adjusted
results["significant_raw_0_05"] = results["p_raw"] < ALPHA
results["significant_holm_0_05"] = results["p_holm"] < ALPHA

sensitivities = pd.DataFrame([t1_sens, t2_sens, t3_sens, t4_sens])

# Save all output artifacts.
results.to_csv(OUT_DIR / "test_results.csv", index=False)
sensitivities.to_csv(OUT_DIR / "sensitivity.csv", index=False)
contingency.to_csv(OUT_DIR / "t2_contingency_table.csv")
gap_df.to_csv(OUT_DIR / "hub_gap_classification.csv", index=False)

with open(OUT_DIR / "test_results.json", "w", encoding="utf-8") as f:
    json.dump({
        "alpha": ALPHA,
        "holm_family_size": int(valid.sum()),
        "results": results.replace({np.nan: None}).to_dict(orient="records"),
        "sensitivity": sensitivities.replace({np.nan: None}).to_dict(orient="records"),
    }, f, indent=2, default=str)

print("\n=== PRIMARY TEST RESULTS ===")
print(results[
    ["test", "n_units", "effect_estimate", "ci95_low", "ci95_high",
     "statistic", "p_raw", "p_holm", "significant_holm_0_05"]
].to_string(index=False, float_format=lambda v: f"{v:.8g}"))

print("\n=== SENSITIVITY RESULTS ===")
print(sensitivities.to_string(index=False))

print("\n=== MISSING-GAP CONTINGENCY TABLE ===")
print(contingency)
print(f"Minimum expected count: {min_expected:.4f}")
print(f"Monte Carlo permutations: {N_PERMUTATIONS}")
print(f"Eligible competitor event hubs: {len(event_results)}")

print("\nSaved files:")
for name in [
    "test_results.csv",
    "test_results.json",
    "sensitivity.csv",
    "t2_contingency_table.csv",
    "hub_gap_classification.csv",
    "competitor_event_window_data.csv",
]:
    print(OUT_DIR / name)
