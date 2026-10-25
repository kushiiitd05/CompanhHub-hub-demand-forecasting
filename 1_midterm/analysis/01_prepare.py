"""Stage 2-3: data preparation (ledger Q1-Q18), row waterfall, before/after table.

Pure functions: each takes frames and returns NEW frames; raw frames are never changed.
Outputs (results/r1/): prep_*.csv; derived/hubday_clean.parquet, derived/hub_level.csv.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from common import DERIVED, GAP_END, GAP_START, TRAIN_END, TRAIN_START, load_meta, load_train, moment_kurt, moment_skew, save

LONG_CLOSURE_DAYS = 5      # >= 5 consecutive closed days cannot be Sundays + holidays alone
REOPEN_DAYS = 14
RATIO_MAX = 30.0
ROBUST_Z = 3.5


def clean_meta(me: pd.DataFrame) -> pd.DataFrame:
    """Q9-Q12: sentinel year to NA + flag, missingness indicators, 'None' loyalty level."""
    m = me.copy()
    m["sentinel_year"] = (m["CompetitorOpenSinceYear"] == 1900).astype(int)
    m["extreme_year_kept"] = (m["CompetitorOpenSinceYear"] == 1961).astype(int)
    m.loc[m["sentinel_year"] == 1, ["CompetitorOpenSinceYear", "CompetitorOpenSinceMonth"]] = np.nan
    m["CompetitorDistance_missing"] = m["CompetitorDistance"].isna().astype(int)
    m["CompetitorOpenSince_missing"] = m["CompetitorOpenSinceYear"].isna().astype(int)
    m["LoyaltyProgramInterval"] = m["LoyaltyProgramInterval"].fillna("None")
    m["CompOpenMonthStart"] = pd.to_datetime(
        dict(year=m["CompetitorOpenSinceYear"], month=m["CompetitorOpenSinceMonth"], day=1), errors="coerce")
    return m


def gap_hubs(tr: pd.DataFrame) -> set[int]:
    """Q1: hubs with no rows at all in the 2014-07-01..2014-12-31 block."""
    in_blk = tr.loc[tr["Date"].between(GAP_START, GAP_END), "HubID"].unique()
    return set(tr["HubID"].unique()) - set(in_blk)


def closure_flags(tr: pd.DataFrame) -> pd.DataFrame:
    """Q7: per row, the length of the closure run it belongs to and a reopen-window flag.

    A run is a maximal sequence of closed rows on consecutive calendar dates
    (an absent date breaks the run). reopen_window = the 14 calendar days
    after a run of >= LONG_CLOSURE_DAYS ends.
    """
    t = tr.sort_values(["HubID", "Date"]).reset_index(drop=True)
    new_seg = (t["HubID"].ne(t["HubID"].shift())) | (t["Date"].diff().dt.days.ne(1))
    closed = t["IsOpen"].eq(0)
    run_id = (new_seg | closed.ne(closed.shift())).cumsum()
    run_len = t.groupby(run_id)["IsOpen"].transform("size").where(closed, 0)
    t["closure_run_len"] = run_len.astype(int)
    t["long_closure"] = (t["closure_run_len"] >= LONG_CLOSURE_DAYS).astype(int)
    ends = t.loc[t["long_closure"].eq(1)].groupby(run_id[t["long_closure"].eq(1)]).agg(HubID=("HubID", "first"), end=("Date", "max"))
    t["reopen_window"] = 0
    for hub, end in zip(ends["HubID"], ends["end"]):
        mask = t["HubID"].eq(hub) & t["Date"].between(end + pd.Timedelta(days=1), end + pd.Timedelta(days=REOPEN_DAYS))
        t.loc[mask, "reopen_window"] = 1
    return t


def outlier_flags(t: pd.DataFrame) -> pd.DataFrame:
    """Q3-Q5, Q8: open_zero, pooled IQR fence, per-hub robust z, conversion-ratio anomaly."""
    o = t.copy()
    is_open = o["IsOpen"].eq(1)
    o["open_zero"] = (is_open & o["OrderVolume"].eq(0)).astype(int)
    v = o.loc[is_open, "OrderVolume"]
    q1, q3 = v.quantile([0.25, 0.75])
    o["iqr_flag"] = (is_open & (o["OrderVolume"] > q3 + 1.5 * (q3 - q1))).astype(int)
    base = is_open & o["OrderVolume"].gt(0)
    med = o["OrderVolume"].where(base).groupby(o["HubID"]).transform("median")
    mad = (o["OrderVolume"].where(base) - med).abs().groupby(o["HubID"]).transform("median")
    o["robust_z"] = (0.6745 * (o["OrderVolume"] - med) / mad).where(base)
    o["robust_z_flag"] = o["robust_z"].abs().gt(ROBUST_Z).astype(int)
    ratio = (o["OrderVolume"] / o["AppSessions"]).where(base & o["AppSessions"].gt(0))
    o["ratio_anomaly"] = ratio.gt(RATIO_MAX).astype(int)
    return o


def add_context(o: pd.DataFrame) -> pd.DataFrame:
    """Calendar context for each row, used to explain extremes before any decision."""
    c = o.sort_values(["HubID", "Date"]).copy()
    g = c.groupby("HubID")
    nxt_closed = g["IsOpen"].shift(-1).eq(0) & g["Date"].shift(-1).sub(c["Date"]).dt.days.eq(1)
    prv_closed = g["IsOpen"].shift(1).eq(0) & c["Date"].sub(g["Date"].shift(1)).dt.days.eq(1)
    hol = c["RegionalHoliday"].gt(0)
    near_hol = g["RegionalHoliday"].shift(-1).gt(0) | g["RegionalHoliday"].shift(1).gt(0)
    c["ctx_holiday_or_adjacent"] = (hol | near_hol).astype(int)
    c["ctx_adjacent_closure"] = (nxt_closed | prv_closed).astype(int)
    c["ctx_pre_christmas"] = (c["Date"].dt.month.eq(12) & c["Date"].dt.day.between(1, 24)).astype(int)
    c["ctx_promo"] = c["PromoActive"].astype(int)
    c["ctx_reopen"] = c["reopen_window"]
    return c


def context_table(c: pd.DataFrame, flag: str) -> pd.DataFrame:
    """How many flagged rows each context explains (first match in priority order)."""
    f = c[c[flag].eq(1)].copy()
    order = ["ctx_holiday_or_adjacent", "ctx_adjacent_closure", "ctx_reopen", "ctx_pre_christmas", "ctx_promo"]
    f["explained_by"] = "none of these"
    for col in reversed(order):
        f.loc[f[col].eq(1), "explained_by"] = col.replace("ctx_", "")
    if "robust_z" in f:
        f["side"] = np.where(f["robust_z"] > 0, "high", "low")
    else:
        f["side"] = "high"
    tab = f.groupby(["explained_by", "side"]).size().rename("rows").reset_index()
    tab["share_of_flagged_%"] = 100 * tab["rows"] / len(f)
    return tab


def encode(c: pd.DataFrame, m: pd.DataFrame, gaps: set[int]) -> pd.DataFrame:
    """Q18: join metadata, derive calendar fields, one-hot nominal columns, keep flags."""
    j = c.merge(m, on="HubID", how="left", validate="many_to_one")
    iso = j["Date"].dt.isocalendar()
    e = pd.DataFrame({"HubID": j["HubID"], "Year": j["Date"].dt.year, "Month": j["Date"].dt.month,
                      "DayOfMonth": j["Date"].dt.day, "ISOWeek": iso["week"].astype(int)})
    for col, levels in [("Weekday", range(1, 8)), ("RegionalHoliday", range(4)), ("HubFormat", range(1, 5))]:
        for lv in levels:
            e[f"{col}_{lv}"] = j[col].eq(lv).astype(int)
    keep = ["OrderVolume", "AppSessions", "IsOpen", "PromoActive", "SchoolClosureFlag", "AssortmentTier",
            "CompetitorDistance", "CompetitorDistance_missing", "CompetitorOpenSinceMonth", "CompetitorOpenSinceYear",
            "CompetitorOpenSince_missing", "LoyaltyProgram", "LoyaltyProgramSinceWeek", "LoyaltyProgramSinceYear"]
    e = pd.concat([e, j[keep]], axis=1)
    for lv in ["Jan,Apr,Jul,Oct", "Feb,May,Aug,Nov", "Mar,Jun,Sept,Dec", "None"]:
        e[f"LoyaltyInterval_{lv.replace(',', '')}"] = j["LoyaltyProgramInterval"].eq(lv).astype(int)
    e["gap_hub"] = j["HubID"].isin(gaps).astype(int)
    for f in ["open_zero", "long_closure", "reopen_window", "ratio_anomaly", "sentinel_year", "iqr_flag", "robust_z_flag"]:
        e[f] = j[f].astype(int)
    return e


FLAG_COLS = ["gap_hub", "open_zero", "long_closure", "reopen_window", "ratio_anomaly", "sentinel_year", "iqr_flag", "robust_z_flag"]


def waterfall(c: pd.DataFrame, gaps: set[int]) -> pd.DataFrame:
    """Row waterfall from the full hub-date grid to the analysis base."""
    grid = 1115 * len(pd.date_range(TRAIN_START, TRAIN_END))
    op = c[c["IsOpen"].eq(1)]
    base = op[op["open_zero"].eq(0)]
    steps = [("Full hub x date grid (1,115 x 900)", grid, ""),
             ("Absent hub-dates (180 gap hubs x 184 d + hub 988 on 2013-01-01): kept absent", grid - len(c), "not imputed"),
             ("Rows in orders_train.csv", len(c), ""),
             ("Closed rows (structural zeros): excluded from volume tests", int(c["IsOpen"].eq(0).sum()), "kept in table, flagged"),
             ("Open rows", len(op), ""),
             ("Open with zero volume (open_zero): excluded", int(op["open_zero"].sum()), "listed in README"),
             ("Analysis base (open, volume > 0)", len(base), "all tests start here"),
             ("  of which in reopen windows (sensitivity exclusion)", int(base["reopen_window"].sum()), "sensitivity only"),
             ("  of which ratio_anomaly (only matters for sessions)", int(base["ratio_anomaly"].sum()), "kept"),
             ("  of which on a regional holiday (excluded in T1)", int(base["RegionalHoliday"].gt(0).sum()), "T1 only"),
             ("  of which at gap hubs", int(base["HubID"].isin(gaps).sum()), "kept; T2 studies them")]
    return pd.DataFrame(steps, columns=["step", "rows", "note"])


def before_after(tr: pd.DataFrame, me: pd.DataFrame, e: pd.DataFrame, c: pd.DataFrame) -> pd.DataFrame:
    """Before/after measures (Stage 3)."""
    op = c[c["IsOpen"].eq(1)]
    base = op[op["OrderVolume"].gt(0)]
    lv = np.log1p(base["OrderVolume"])
    raw_join_na = int(tr.merge(me, on="HubID").isna().sum().sum())
    not_appl = int(e[["LoyaltyProgramSinceWeek", "LoyaltyProgramSinceYear"]].isna().sum().sum())
    rows = [("Rows", len(tr), len(e)), ("Attributes", f"9 (+9 metadata)", e.shape[1]),
            ("Instances x attributes", len(tr) * 9, e.shape[0] * e.shape[1]),
            ("Missing cells after join", raw_join_na, int(e.isna().sum().sum())),
            ("  of which 'not applicable' (no loyalty programme)", "-", not_appl),
            ("Duplicate hub-dates / full rows", "0 / 0", "0 / 0"),
            ("Skewness of open-day volume (raw -> log1p, volume>0)", round(moment_skew(op["OrderVolume"]), 3), round(moment_skew(lv), 3)),
            ("Kurtosis (normal = 3) (raw -> log1p)", round(moment_kurt(op["OrderVolume"]), 2), round(moment_kurt(lv), 2)),
            ("Rows flagged: open_zero / ratio / reopen / long_closure", "-",
             f"{int(c.open_zero.sum())} / {int(c.ratio_anomaly.sum())} / {int(c.reopen_window.sum())} / {int(c.long_closure.sum())}"),
            ("Rows flagged: pooled IQR / per-hub robust z", "-", f"{int(c.iqr_flag.sum())} / {int(c.robust_z_flag.sum())}")]
    return pd.DataFrame(rows, columns=["measure", "before", "after"])


def integrity_checks(c: pd.DataFrame) -> pd.DataFrame:
    """Q6 Chebyshev, Q16 last-digit chi-square GOF, Q3 MLE of the open-zero rate."""
    op = c[c["IsOpen"].eq(1)]
    v = op["OrderVolume"]
    z = (v - v.mean()) / v.std(ddof=1)
    out = [{"check": f"Chebyshev |z|>={k}", "observed_%": 100 * (z.abs() >= k).mean(), "bound_%": 100 / k**2,
            "normal_%": 100 * 2 * stats.norm.sf(k)} for k in (2, 3, 4)]
    digits = (v[v >= 100] % 10).value_counts().sort_index().to_numpy()
    chi2, p = stats.chisquare(digits)
    out.append({"check": "last digit uniform chi2 (df=9)", "statistic": chi2, "df": 9, "p": p, "n": int(digits.sum()),
                "min_count": int(digits.min()), "max_count": int(digits.max())})
    k, n = int(op["open_zero"].sum()), len(op)
    ph = k / n
    lo, hi = stats.binomtest(k, n).proportion_ci(0.95, method="wilson")
    out.append({"check": "MLE open-zero rate p_hat = k/n", "statistic": ph, "n": n, "k": k, "ci_low": lo, "ci_high": hi})
    return pd.DataFrame(out)


def iqr_vs_hub_size(c: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    """Q4: does the pooled IQR fence flag anomalies or just large hubs?"""
    op = c[c["IsOpen"].eq(1) & c["OrderVolume"].gt(0)]
    hub_med = op.groupby("HubID")["OrderVolume"].median()
    fence_q3 = op["OrderVolume"].quantile(0.75)
    big = set(hub_med[hub_med > fence_q3].index)
    f = op[op["iqr_flag"].eq(1)]
    mm = m.set_index("HubID")
    f2t3 = mm.index[(mm.HubFormat == 2) & (mm.AssortmentTier == 3)]
    rows = [("IQR-flagged rows", len(f)), ("hubs with any IQR flag", f.HubID.nunique()),
            ("hubs whose own median > pooled Q3", len(big)),
            ("IQR-flagged rows at those hubs", int(f.HubID.isin(big).sum())),
            ("share at those hubs %", 100 * f.HubID.isin(big).mean()),
            ("IQR-flagged rows that are also per-hub robust-z flags", int(f["robust_z_flag"].sum())),
            ("mean open-day volume, format 2 & tier 3 hubs", op[op.HubID.isin(f2t3)]["OrderVolume"].mean()),
            ("n format 2 & tier 3 hubs", len(f2t3))]
    return pd.DataFrame(rows, columns=["measure", "value"])


def second_pass(c: pd.DataFrame) -> pd.DataFrame:
    """Lecture 3: after the fixes (open_zero out, log scale), does an outlier still exist?"""
    b = c[c["IsOpen"].eq(1) & c["OrderVolume"].gt(0)].copy()
    lv = np.log1p(b["OrderVolume"])
    med = lv.groupby(b["HubID"]).transform("median")
    mad = (lv - med).abs().groupby(b["HubID"]).transform("median")
    b["robust_z_log"] = 0.6745 * (lv - med) / mad
    b["flag2"] = b["robust_z_log"].abs().gt(ROBUST_Z).astype(int)
    explained = b[["ctx_holiday_or_adjacent", "ctx_adjacent_closure", "ctx_reopen", "ctx_pre_christmas"]].max(axis=1)
    rows = [("pass-2 flags (per-hub robust z on log1p, |z|>3.5)", int(b.flag2.sum())),
            ("pass-2 hubs", int(b.loc[b.flag2.eq(1), "HubID"].nunique())),
            ("pass-2 high / low side", f"{int((b.robust_z_log > ROBUST_Z).sum())} / {int((b.robust_z_log < -ROBUST_Z).sum())}"),
            ("pass-2 explained by holiday/closure/reopen/pre-Christmas", int((b.flag2.eq(1) & explained.eq(1)).sum())),
            ("pass-2 unexplained (kept; promo or none)", int((b.flag2.eq(1) & explained.eq(0)).sum()))]
    return pd.DataFrame(rows, columns=["measure", "value"])


def hub_level(c: pd.DataFrame, m: pd.DataFrame, gaps: set[int]) -> pd.DataFrame:
    """One row per hub: the independent unit for T2 and T3 (rule S5)."""
    b = c[c["IsOpen"].eq(1) & c["OrderVolume"].gt(0)].assign(lv=lambda d: np.log1p(d["OrderVolume"]))
    agg = b.groupby("HubID").agg(n_open_days=("lv", "size"), mean_log1p=("lv", "mean"), mean_volume=("OrderVolume", "mean"))
    agg_nr = b[b["reopen_window"].eq(0)].groupby("HubID")["lv"].mean().rename("mean_log1p_no_reopen")
    h = m.merge(agg.join(agg_nr), left_on="HubID", right_index=True, how="left", validate="one_to_one")
    h["log_distance"] = np.log(h["CompetitorDistance"])
    h["gap_hub"] = h["HubID"].isin(gaps).astype(int)
    return h


def flagged_rows(c: pd.DataFrame) -> pd.DataFrame:
    """Rows listed in the README: every open_zero and ratio_anomaly row, plus the maximum."""
    cols = ["HubID", "Date", "Weekday", "OrderVolume", "AppSessions", "PromoActive", "RegionalHoliday", "open_zero", "ratio_anomaly"]
    f = c[c["open_zero"].eq(1) | c["ratio_anomaly"].eq(1) | c["OrderVolume"].eq(c["OrderVolume"].max())]
    return f[cols].sort_values(["open_zero", "HubID", "Date"], ascending=[False, True, True])


def main() -> None:
    tr, me = load_train(), load_meta()
    m = clean_meta(me)
    gaps = gap_hubs(tr)
    t = closure_flags(tr)
    o = outlier_flags(t)
    c = add_context(o)
    e = encode(c, m, gaps)
    save(waterfall(c, gaps), "prep_waterfall.csv")
    save(before_after(tr, me, e, c), "prep_before_after.csv")
    save(integrity_checks(c), "prep_integrity_checks.csv")
    save(iqr_vs_hub_size(c, me), "prep_iqr_vs_hub_size.csv")
    save(context_table(c, "robust_z_flag"), "prep_robust_z_context.csv")
    save(context_table(c, "iqr_flag"), "prep_iqr_context.csv")
    save(second_pass(c), "prep_second_pass.csv")
    save(flagged_rows(c), "prep_flagged_rows.csv")
    save(pd.DataFrame({"attribute": e.columns, "dtype": e.dtypes.astype(str).values}), "prep_encoded_schema.csv")
    runs = c[c["long_closure"].eq(1)].groupby(["HubID", "closure_run_len"]).size()
    save(pd.DataFrame({"long_closure_runs": [len(runs)], "hubs": [runs.index.get_level_values(0).nunique()]}), "prep_long_closures.csv")
    hl = hub_level(c, m, gaps)
    hl.to_csv(DERIVED / "hub_level.csv", index=False)
    c.drop(columns=["robust_z"]).to_parquet(DERIVED / "hubday_clean.parquet", index=False)
    print(f"encoded shape {e.shape} -> {e.shape[0]} x {e.shape[1]} = {e.shape[0] * e.shape[1]:,}")
    for name in ["prep_waterfall", "prep_before_after", "prep_integrity_checks", "prep_iqr_vs_hub_size",
                 "prep_robust_z_context", "prep_iqr_context", "prep_second_pass", "prep_long_closures"]:
        print(f"\n== {name}\n" + pd.read_csv(f"../midterm/results/r1/{name}.csv").to_string(index=False))


if __name__ == "__main__":
    main()
