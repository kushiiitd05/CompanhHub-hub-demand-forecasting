"""Stage 6, part 1: T1 (promo lift Monday vs Friday) and T2 (data gap vs hub format).

Follows docs/analysis_plan_r1.md exactly. Writes results/t1_*.csv, t2_*.csv, t1.json, t2.json.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from common import DERIVED, OUT, SEED, save
from inference import chi2_independence, paired_t, two_prop_diff

T1_DELTA, T2_DELTA = 0.05, 0.05
MIN_CELL = 4
N_PLACEBO = 200


def load_base() -> pd.DataFrame:
    c = pd.read_parquet(DERIVED / "hubday_clean.parquet")
    b = c[c["IsOpen"].eq(1) & c["OrderVolume"].gt(0)].copy()
    b["y"] = np.log1p(b["OrderVolume"])
    return b


def t1_rows(b: pd.DataFrame, holidays: bool = False, reopen: bool = False) -> pd.DataFrame:
    r = b[b["Weekday"].isin([1, 5])]
    if not holidays:
        r = r[r["RegionalHoliday"].eq(0)]
    if not reopen:
        r = r[r["reopen_window"].eq(0)]
    return r.sort_values(["HubID", "Weekday"]).reset_index(drop=True)


def t1_diffs(r: pd.DataFrame, col: str = "y", promo: str = "PromoActive") -> pd.DataFrame:
    """Per hub: Monday lift, Friday lift and d_i = L_Mon - L_Fri (hubs with >= MIN_CELL days per cell)."""
    g = r.groupby(["HubID", "Weekday", promo])[col].agg(["mean", "size"]).unstack([1, 2])
    ok = (g["size"] >= MIN_CELL).all(axis=1) & g["size"].notna().all(axis=1)
    m = g["mean"][ok]
    out = pd.DataFrame({"L_mon": m[(1, 1)] - m[(1, 0)], "L_fri": m[(5, 1)] - m[(5, 0)]})
    out["d"] = out["L_mon"] - out["L_fri"]
    return out.reset_index()


def placebo(r: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Permute promo labels within hub x weekday; return one row per replicate."""
    codes = r.groupby(["HubID", "Weekday"]).ngroup().to_numpy()
    promo = r["PromoActive"].to_numpy()
    rows = []
    for i in range(N_PLACEBO):
        perm = np.lexsort((rng.random(len(r)), codes))   # r is sorted by group, so this permutes within groups
        res = paired_t(t1_diffs(r.assign(placebo=promo[perm]), promo="placebo")["d"].to_numpy(), T1_DELTA)
        rows.append({"rep": i, "n": res["n"], "estimate": res["estimate"], "t": res["statistic"], "p": res["p"]})
    return pd.DataFrame(rows)


def run_t1(b: pd.DataFrame) -> dict:
    r = t1_rows(b)
    diffs = t1_diffs(r)
    save(diffs, "t1_hub_differences.csv")
    main = paired_t(diffs["d"].to_numpy(), T1_DELTA)
    lifts = {k: paired_t(diffs[k].to_numpy(), T1_DELTA) for k in ("L_mon", "L_fri")}
    rows = [{"variant": "PRIMARY log scale, no holidays, no reopen windows", **main}]
    rows.append({"variant": "raw orders scale (v0 comparability)", **paired_t(t1_diffs(r, "OrderVolume")["d"].to_numpy(), 350)})
    rows.append({"variant": "include holidays and reopen windows", **paired_t(t1_diffs(t1_rows(b, True, True))["d"].to_numpy(), T1_DELTA)})
    yr = r["Date"].dt.year
    rows.append({"variant": "replication: 2013 only", **paired_t(t1_diffs(r[yr.eq(2013)])["d"].to_numpy(), T1_DELTA)})
    rows.append({"variant": "replication: 2014-15 only", **paired_t(t1_diffs(r[yr.ge(2014)])["d"].to_numpy(), T1_DELTA)})
    rows.append({"variant": "replication: odd HubID", **paired_t(diffs.loc[diffs.HubID % 2 == 1, "d"].to_numpy(), T1_DELTA)})
    rows.append({"variant": "replication: even HubID", **paired_t(diffs.loc[diffs.HubID % 2 == 0, "d"].to_numpy(), T1_DELTA)})
    for k, v in lifts.items():
        rows.append({"variant": f"component: {k} (lift on its own)", **v})
    tab = pd.DataFrame(rows)
    save(tab, "t1_results.csv")
    pl = placebo(r, np.random.default_rng(SEED))
    save(pl, "t1_placebo.csv")
    summary = {"primary": main, "placebo_reject_rate": float((pl["p"] < 0.05).mean()), "placebo_first": pl.iloc[0].to_dict(),
               "placebo_mean_estimate": float(pl["estimate"].mean()), "n_rows": len(r),
               "lift_mon": lifts["L_mon"], "lift_fri": lifts["L_fri"]}
    return summary


def bootstrap_v(fmt: np.ndarray, gap: np.ndarray, rng: np.random.Generator, n_boot: int = 5000) -> tuple[float, float]:
    vals = []
    n = len(fmt)
    for _ in range(n_boot):
        ix = rng.integers(0, n, n)
        tab = np.zeros((4, 2))
        np.add.at(tab, (fmt[ix], gap[ix]), 1)
        if (tab.sum(0) == 0).any() or (tab.sum(1) == 0).any():
            continue
        e = tab.sum(1, keepdims=True) @ tab.sum(0, keepdims=True) / n
        vals.append(np.sqrt(((tab - e)**2 / e).sum() / n))
    lo, hi = np.quantile(vals, [0.025, 0.975])
    return float(lo), float(hi)


def chi_for(h: pd.DataFrame, rng: np.random.Generator, n_perm: int, merge2: bool = False) -> dict:
    fmt = h["HubFormat"].replace({2: 1}) if merge2 else h["HubFormat"]
    codes = pd.Categorical(fmt).codes
    gap = h["gap_hub"].to_numpy()
    table = pd.crosstab(codes, gap).to_numpy()
    return chi2_independence(table, n_perm, rng, codes, gap)


def run_t2() -> dict:
    h = pd.read_csv(DERIVED / "hub_level.csv")
    rng = np.random.default_rng(SEED)
    tab = pd.crosstab(h["HubFormat"], h["gap_hub"]).rename(columns={0: "no_gap", 1: "gap"})
    tab["gap_rate_%"] = 100 * tab["gap"] / tab.sum(axis=1)
    save(tab.reset_index(), "t2_contingency.csv")
    main = chi_for(h, rng, 100_000)
    main["v_ci_low"], main["v_ci_high"] = bootstrap_v(pd.Categorical(h["HubFormat"]).codes, h["gap_hub"].to_numpy(), rng)
    merged = chi_for(h, rng, 20_000, merge2=True)
    odd, even = (chi_for(h[h.HubID % 2 == k], rng, 20_000) for k in (1, 0))
    f4 = h["HubFormat"].eq(4)
    follow = two_prop_diff(int(h.loc[f4, "gap_hub"].sum()), int(f4.sum()), int(h.loc[~f4, "gap_hub"].sum()), int((~f4).sum()), T2_DELTA)
    observed = h[h["gap_hub"].eq(0)]["HubFormat"].value_counts(normalize=True).sort_index()
    allmix = h["HubFormat"].value_counts(normalize=True).sort_index()
    mix = pd.DataFrame({"share_all_hubs_%": 100 * allmix, "share_hubs_observed_2014H2_%": 100 * observed}).reset_index()
    save(mix, "t2_format_mix_bias.csv")
    rows = [{"variant": "PRIMARY 4x2, permutation p", **main}, {"variant": "check: format 2 merged into 1 (3x2)", **merged},
            {"variant": "replication: odd HubID", **odd}, {"variant": "replication: even HubID", **even}]
    save(pd.DataFrame(rows), "t2_results.csv")
    save(pd.DataFrame([follow]), "t2_followup_format4_vs_rest.csv")
    return {"primary": main, "merged": merged, "odd": odd, "even": even, "followup": follow}


def main() -> None:
    b = load_base()
    out = {"T1": run_t1(b), "T2": run_t2()}
    (OUT / "t1_t2.json").write_text(json.dumps(out, indent=2, default=float))
    pd.set_option("display.width", 250, "display.max_columns", 40)
    for f in ["t1_results", "t2_contingency", "t2_results", "t2_followup_format4_vs_rest", "t2_format_mix_bias"]:
        print(f"\n== {f}\n" + pd.read_csv(OUT / f"{f}.csv").to_string(index=False))
    print("\nplacebo:", {k: out["T1"][k] for k in ("placebo_reject_rate", "placebo_mean_estimate", "placebo_first")})


if __name__ == "__main__":
    main()
