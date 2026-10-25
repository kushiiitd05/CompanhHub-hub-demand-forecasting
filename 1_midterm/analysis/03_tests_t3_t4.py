"""Stage 6, part 2: T3 (competitor distance) and T4 (competitor opening, difference-in-differences).

Follows midterm/analysis_plan_r1.md. Writes results/r1/t3_*.csv, t4_*.csv, t3_t4.json.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd

from common import DERIVED, OUT, TRAIN_END, TRAIN_START, save
from inference import paired_t, pearson_t

T3_DELTA, T4_DELTA = 0.10, 0.03
WIN, MIN_ROWS = 56, 30


def load_base() -> pd.DataFrame:
    c = pd.read_parquet(DERIVED / "hubday_clean.parquet")
    b = c[c["IsOpen"].eq(1) & c["OrderVolume"].gt(0)].copy()
    b["y"] = np.log1p(b["OrderVolume"])
    return b[["HubID", "Date", "y", "OrderVolume", "reopen_window"]]


def load_hubs() -> pd.DataFrame:
    h = pd.read_csv(DERIVED / "hub_level.csv", parse_dates=["CompOpenMonthStart"])
    return h


# ------------------------------------------------------------------ T3
def run_t3(b: pd.DataFrame, h: pd.DataFrame) -> dict:
    d = h.dropna(subset=["log_distance"])
    main = pearson_t(d["log_distance"].to_numpy(), d["mean_log1p"].to_numpy(), T3_DELTA)
    rows = [{"variant": "PRIMARY Pearson r, ln(distance) vs hub mean log1p volume", **main}]
    rows.append({"variant": "raw scale Pearson (distance vs mean volume)", **pearson_t(d["CompetitorDistance"].to_numpy(), d["mean_volume"].to_numpy(), T3_DELTA)})
    rows.append({"variant": "y without reopen windows", **pearson_t(d["log_distance"].to_numpy(), d["mean_log1p_no_reopen"].to_numpy(), T3_DELTA)})
    for label, mask in [("2013", b["Date"].dt.year.eq(2013)), ("2014-15", b["Date"].dt.year.ge(2014))]:
        y = b[mask].groupby("HubID")["y"].mean().rename("y_sub")
        dd = d.merge(y, left_on="HubID", right_index=True)
        rows.append({"variant": f"replication: y from {label} rows", **pearson_t(dd["log_distance"].to_numpy(), dd["y_sub"].to_numpy(), T3_DELTA)})
    for f in sorted(d["HubFormat"].unique()):
        s = d[d["HubFormat"].eq(f)]
        if len(s) > 10:
            rows.append({"variant": f"within format {f}", **pearson_t(s["log_distance"].to_numpy(), s["mean_log1p"].to_numpy(), T3_DELTA)})
    save(pd.DataFrame(rows), "t3_results.csv")
    save(d[["HubID", "HubFormat", "CompetitorDistance", "log_distance", "mean_log1p"]], "t3_hub_data.csv")
    dec = d.assign(decile=pd.qcut(d["log_distance"], 10, labels=False) + 1).groupby("decile").agg(
        dist_min=("CompetitorDistance", "min"), dist_max=("CompetitorDistance", "max"), n=("HubID", "size"),
        mean_y=("mean_log1p", "mean"), share_format4=("HubFormat", lambda s: (s == 4).mean())).reset_index()
    dec["pct_vs_deciles_2_10"] = np.expm1(dec["mean_y"] - d.loc[d["log_distance"] > d["log_distance"].quantile(0.1), "mean_log1p"].mean())
    save(dec, "t3_deciles_posthoc.csv")  # post-hoc diagnostic, not a test
    lo, hi = d["log_distance"].quantile([0.05, 0.95])
    trim = d[d["log_distance"].between(lo, hi)]
    save(pd.DataFrame([{"variant": "post-hoc: 5% tails of ln(distance) trimmed", **pearson_t(trim["log_distance"].to_numpy(), trim["mean_log1p"].to_numpy(), T3_DELTA)}]), "t3_trimmed_posthoc.csv")
    return {"primary": main}


# ------------------------------------------------------------------ T4
def windows(month_start: pd.Timestamp, w: int) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    """Pre = w days before the opening month; post = w days after it; the month itself is excluded."""
    month_end = month_start + pd.offsets.MonthEnd(0)
    return (month_start - pd.Timedelta(days=w), month_start - pd.Timedelta(days=1),
            month_end + pd.Timedelta(days=1), month_end + pd.Timedelta(days=w))


def window_change(b: pd.DataFrame, hubs: set[int], win: tuple, min_rows: int) -> pd.Series:
    """Per hub: mean y in post window minus mean y in pre window (hubs with >= min_rows in each)."""
    s = b[b["HubID"].isin(hubs)]
    pre = s[s["Date"].between(win[0], win[1])].groupby("HubID")["y"].agg(["mean", "size"])
    post = s[s["Date"].between(win[2], win[3])].groupby("HubID")["y"].agg(["mean", "size"])
    j = pre.add_suffix("_pre").join(post.add_suffix("_post"), how="inner")
    j = j[(j["size_pre"] >= min_rows) & (j["size_post"] >= min_rows)]
    return j["mean_post"] - j["mean_pre"]


def groups(h: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Treated pool (opening date known and inside the data) and clean controls."""
    known = h.dropna(subset=["CompOpenMonthStart"])
    ctrl = known[(known["CompOpenMonthStart"] <= "2011-12-01") | (known["CompOpenMonthStart"] > TRAIN_END)]
    treated = known[known["CompOpenMonthStart"].between(TRAIN_START, TRAIN_END)]
    return treated, ctrl


def did(b: pd.DataFrame, h: pd.DataFrame, w: int = WIN, shift_months: int = 0, same_format: bool = False,
        min_open: str = "1900-01-01") -> pd.DataFrame:
    """One row per eligible treated hub: own change, control change over the same dates, and DiD."""
    treated, ctrl = groups(h)
    treated = treated[treated["CompOpenMonthStart"] >= min_open]
    min_rows = math.ceil(MIN_ROWS * w / WIN)
    fmt = h.set_index("HubID")["HubFormat"]
    rows = []
    key = treated["HubFormat"] if same_format else pd.Series(0, index=treated.index)
    for (ms, f), grp in treated.groupby([treated["CompOpenMonthStart"], key]):
        event = ms - pd.DateOffset(months=shift_months)
        win = windows(event, w)
        if win[0] < TRAIN_START or win[3] > TRAIN_END:
            continue
        own = window_change(b, set(grp["HubID"]), win, min_rows)
        cset = set(ctrl["HubID"]) if not same_format else set(ctrl.loc[ctrl["HubFormat"].eq(f), "HubID"])
        cc = window_change(b, cset, win, min_rows)
        for hub, delta in own.items():
            rows.append({"HubID": hub, "HubFormat": fmt[hub], "open_month": ms.date(), "event_month": event.date(),
                         "own_change": delta, "control_change": cc.mean(), "n_controls": len(cc), "did": delta - cc.mean()})
    return pd.DataFrame(rows)


def run_t4(b: pd.DataFrame, h: pd.DataFrame) -> dict:
    treated, ctrl = groups(h)
    prim = did(b, h)
    save(prim, "t4_did_hubs.csv")
    main = paired_t(prim["did"].to_numpy(), T4_DELTA)
    rows = [{"variant": "PRIMARY DiD, 56-day windows, all clean controls", **main},
            {"variant": "no control (before/after only, log scale)", **paired_t(prim["own_change"].to_numpy(), T4_DELTA)}]
    for w in (28, 84):
        rows.append({"variant": f"sensitivity: {w}-day windows", **paired_t(did(b, h, w)["did"].to_numpy(), T4_DELTA)})
    rows.append({"variant": "sensitivity: same-format controls", **paired_t(did(b, h, same_format=True)["did"].to_numpy(), T4_DELTA)})
    nr = b[b["reopen_window"].eq(0)]
    rows.append({"variant": "sensitivity: reopen windows excluded", **paired_t(did(nr, h)["did"].to_numpy(), T4_DELTA)})
    for label, mask in [("odd HubID", prim.HubID % 2 == 1), ("even HubID", prim.HubID % 2 == 0),
                        ("openings in 2013", pd.to_datetime(prim.open_month).dt.year.eq(2013)),
                        ("openings in 2014-15", pd.to_datetime(prim.open_month).dt.year.ge(2014))]:
        rows.append({"variant": f"replication: {label}", **paired_t(prim.loc[mask, "did"].to_numpy(), T4_DELTA)})
    pl = did(b, h, shift_months=12, min_open="2014-03-01")
    save(pl, "t4_placebo_hubs.csv")
    rows.append({"variant": "PLACEBO: opening moved 12 months earlier", **paired_t(pl["did"].to_numpy(), T4_DELTA)})
    save(pd.DataFrame(rows), "t4_results.csv")
    counts = {"treated_pool_inside_data": len(treated), "eligible_month_range": f"{prim.open_month.min()}..{prim.open_month.max()}",
              "treated_used": len(prim), "controls_pool": len(ctrl), "controls_per_window_min": int(prim.n_controls.min()),
              "controls_per_window_max": int(prim.n_controls.max()), "control_change_sd_across_windows": float(prim.groupby('open_month').control_change.first().std())}
    save(pd.DataFrame([counts]), "t4_counts.csv")
    return {"primary": main, "counts": counts}


def main() -> None:
    b, h = load_base(), load_hubs()
    out = {"T3": run_t3(b, h), "T4": run_t4(b, h)}
    (OUT / "t3_t4.json").write_text(json.dumps(out, indent=2, default=str))
    pd.set_option("display.width", 250, "display.max_columns", 40)
    cols = ["variant", "n", "estimate", "statistic", "df", "p", "ci_low", "ci_high", "verdict"]
    for f in ["t3_results", "t4_results"]:
        t = pd.read_csv(OUT / f"{f}.csv")
        print(f"\n== {f}\n" + t[[c for c in cols + ["spearman", "pct", "wilcoxon_p", "agree_4sf"] if c in t]].to_string(index=False))
    print("\n", pd.read_csv(OUT / "t4_counts.csv").T)


if __name__ == "__main__":
    main()
