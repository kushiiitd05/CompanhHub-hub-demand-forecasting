"""Descriptive evidence (no tests): dependence (S5), schedule shift (Q17), weekday lift profile,
hubs observed per date, reopening surge. Writes results/desc_*.csv.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from common import DERIVED, load_test, load_train, save


def base() -> pd.DataFrame:
    c = pd.read_parquet(DERIVED / "hubday_clean.parquet")
    b = c[c["IsOpen"].eq(1) & c["OrderVolume"].gt(0)].copy()
    b["y"] = np.log1p(b["OrderVolume"])
    return b


def lag_correlations(b: pd.DataFrame) -> pd.DataFrame:
    """Median over hubs of corr(y_t, y_{t-k}) on calendar lags: the evidence that hub-days are not iid."""
    wide = b.pivot(index="Date", columns="HubID", values="y").asfreq("D")
    rows = []
    for k in (1, 7, 14, 364):
        a, s = wide, wide.shift(k)
        ok = a.notna() & s.notna()
        am, sm = a.where(ok), s.where(ok)
        cov = ((am - am.mean()) * (sm - sm.mean())).mean()
        r = cov / (am.std(ddof=0) * sm.std(ddof=0))
        rows.append({"lag_days": k, "median_within_hub_r": float(r.median()), "q1": float(r.quantile(0.25)), "q3": float(r.quantile(0.75)), "hubs": int(r.notna().sum())})
    return pd.DataFrame(rows)


def schedule_shift(tr: pd.DataFrame, te: pd.DataFrame) -> pd.DataFrame:
    last = tr[tr["Date"] > tr["Date"].max() - pd.Timedelta(days=42)]
    def prof(d: pd.DataFrame) -> dict:
        return {"rows": len(d), "open_%": 100 * d.IsOpen.mean(), "promo_%": 100 * d.PromoActive.mean(),
                "school_closed_%": 100 * d.SchoolClosureFlag.mean(), "holiday_%": 100 * d.RegionalHoliday.gt(0).mean()}
    same_window_2014 = tr[tr["Date"].between("2014-06-20", "2014-07-31")]
    same_window_2013 = tr[tr["Date"].between("2013-06-20", "2013-07-31")]
    out = pd.DataFrame([{"set": "train, all 900 days", **prof(tr)}, {"set": "train, last 42 days", **prof(last)},
                        {"set": "train, 2013-06-20..07-31", **prof(same_window_2013)},
                        {"set": "train, 2014-06-20..07-31", **prof(same_window_2014)}, {"set": "test (no outcome)", **prof(te)}])
    obs = np.array([te.SchoolClosureFlag.sum(), (1 - te.SchoolClosureFlag).sum()])
    p0 = tr.SchoolClosureFlag.mean()
    chi = stats.chisquare(obs, [p0 * len(te), (1 - p0) * len(te)])
    out["note"] = ""
    out.loc[out.index[-1], "note"] = f"school share vs train rate: chi2(1)={chi.statistic:.1f}, descriptive only (rows not independent)"
    return out


def weekday_lift(b: pd.DataFrame) -> pd.DataFrame:
    """Per weekday Mon-Fri: mean over hubs of the hub's promo lift on log scale, with a t CI across hubs."""
    r = b[b["Weekday"].le(5) & b["RegionalHoliday"].eq(0) & b["reopen_window"].eq(0)]
    g = r.groupby(["HubID", "Weekday", "PromoActive"])["y"].mean().unstack("PromoActive").dropna()
    lift = (g[1] - g[0]).rename("lift").reset_index()
    rows = []
    for wd, s in lift.groupby("Weekday")["lift"]:
        m, se = s.mean(), s.std(ddof=1) / np.sqrt(len(s))
        h = stats.t.ppf(0.975, len(s) - 1) * se
        rows.append({"weekday": wd, "hubs": len(s), "mean_log_lift": m, "ci_low": m - h, "ci_high": m + h,
                     "pct": np.expm1(m), "pct_low": np.expm1(m - h), "pct_high": np.expm1(m + h)})
    return pd.DataFrame(rows)


def hubs_per_date(tr: pd.DataFrame) -> pd.DataFrame:
    return tr.groupby("Date").agg(hubs_observed=("HubID", "nunique"), hubs_open=("IsOpen", "sum")).reset_index()


def reopening(b: pd.DataFrame) -> pd.DataFrame:
    """Mean y in the 14 days after a >= 5-day closure minus the 28 days before it (descriptive)."""
    c = pd.read_parquet(DERIVED / "hubday_clean.parquet", columns=["HubID", "Date", "long_closure"])
    runs = c[c["long_closure"].eq(1)].sort_values(["HubID", "Date"])
    rid = (runs["HubID"].ne(runs["HubID"].shift()) | runs["Date"].diff().dt.days.ne(1)).cumsum()
    ev = runs.groupby(rid).agg(HubID=("HubID", "first"), start=("Date", "min"), end=("Date", "max"))
    diffs = []
    for hub, s, e in ev[["HubID", "start", "end"]].itertuples(index=False):
        hb = b[b["HubID"].eq(hub)]
        pre = hb[hb["Date"].between(s - pd.Timedelta(days=28), s - pd.Timedelta(days=1))]["y"]
        post = hb[hb["Date"].between(e + pd.Timedelta(days=1), e + pd.Timedelta(days=14))]["y"]
        if len(pre) >= 10 and len(post) >= 5:
            diffs.append(post.mean() - pre.mean())
    d = np.array(diffs)
    m, se = d.mean(), d.std(ddof=1) / np.sqrt(len(d))
    return pd.DataFrame([{"closures": len(ev), "usable": len(d), "mean_log_diff": m, "pct": np.expm1(m),
                          "pct_low": np.expm1(m - 1.96 * se), "pct_high": np.expm1(m + 1.96 * se), "share_positive": (d > 0).mean()}])


def t1_week_level(b: pd.DataFrame) -> pd.DataFrame:
    """Post-hoc robustness for T1: promo is set per date for all hubs, so use the WEEK as the unit.

    c_w = (cross-hub mean y on Monday of week w) - (same on Friday); compare promo weeks with
    non-promo weeks by Welch t. Weeks with a holiday or missing Monday/Friday are dropped.
    """
    r = b[b["Weekday"].isin([1, 5]) & b["RegionalHoliday"].eq(0) & b["reopen_window"].eq(0)]
    day = r.groupby(["Date", "Weekday"]).agg(y=("y", "mean"), promo=("PromoActive", "first")).reset_index()
    day["week"] = day["Date"] - pd.to_timedelta(day["Weekday"] - 1, unit="D")
    w = day.pivot(index="week", columns="Weekday", values=["y", "promo"]).dropna()
    w = w[w[("promo", 1)] == w[("promo", 5)]]
    c = w[("y", 1)] - w[("y", 5)]
    a, n0 = c[w[("promo", 1)] == 1], c[w[("promo", 1)] == 0]
    res = stats.ttest_ind(a, n0, equal_var=False)
    va, vb = a.var(ddof=1) / len(a), n0.var(ddof=1) / len(n0)
    df = (va + vb) ** 2 / (va**2 / (len(a) - 1) + vb**2 / (len(n0) - 1))
    est, se = a.mean() - n0.mean(), np.sqrt(va + vb)
    h = stats.t.ppf(0.975, df) * se
    f = stats.levene(a, n0)
    F = a.var(ddof=1) / n0.var(ddof=1)
    pF = 2 * min(stats.f.cdf(F, len(a) - 1, len(n0) - 1), stats.f.sf(F, len(a) - 1, len(n0) - 1))
    return pd.DataFrame([{"promo_weeks": len(a), "non_promo_weeks": len(n0), "estimate": est, "se": se, "t": res.statistic,
                          "welch_df": df, "p": res.pvalue, "ci_low": est - h, "ci_high": est + h, "pct": np.expm1(est),
                          "var_ratio": a.var(ddof=1) / n0.var(ddof=1), "levene_p": f.pvalue, "F_df1": len(a) - 1, "F_df2": len(n0) - 1, "F_p_two_sided": pF}])


def format_volume(b: pd.DataFrame) -> pd.DataFrame:
    """Basic question: which format sells most? Hub-level means, then averaged per format."""
    m = pd.read_csv(DERIVED / "hub_level.csv")[["HubID", "HubFormat"]]
    hub = b.groupby("HubID")["OrderVolume"].mean().rename("hub_mean").reset_index().merge(m, on="HubID")
    out = hub.groupby("HubFormat")["hub_mean"].agg(hubs="size", mean_of_hub_means="mean", median_of_hub_means="median").reset_index()
    sun = b[b["Weekday"].eq(7)]
    out["note"] = f"Sunday-open rows {len(sun)} at {sun.HubID.nunique()} hubs"
    return out


def main() -> None:
    tr, te, b = load_train(), load_test(), base()
    outs = {"desc_lag_correlations.csv": lag_correlations(b), "desc_schedule_shift.csv": schedule_shift(tr, te),
            "desc_weekday_lift.csv": weekday_lift(b), "desc_hubs_per_date.csv": hubs_per_date(tr), "desc_reopening.csv": reopening(b), "desc_t1_week_level_posthoc.csv": t1_week_level(b), "desc_format_volume.csv": format_volume(b)}
    pd.set_option("display.width", 250, "display.max_columns", 30)
    for name, df in outs.items():
        save(df, name)
        if name != "desc_hubs_per_date.csv":
            print(f"\n== {name}\n{df.to_string(index=False)}")


if __name__ == "__main__":
    main()
