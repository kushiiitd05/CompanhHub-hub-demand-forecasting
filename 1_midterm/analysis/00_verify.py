"""Stage 0: recompute every fact claimed in MASTER_PROMPT §2 from the raw CSVs.

Prints `claim | claimed | recomputed | match` and writes results/verify.csv
plus results/file_hashes.csv. Exit code 1 if any claim mismatches.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from common import DATA, GAP_END, GAP_START, TRAIN_END, TRAIN_START, load_meta, load_test, load_train, moment_kurt, moment_skew, open_days, save, sha256

ROWS: list[dict] = []


def check(claim: str, claimed, got, tol: float = 0.0) -> None:
    """Record one claim. Numbers match within an absolute tolerance."""
    if isinstance(claimed, (int, float)) and not isinstance(claimed, bool):
        ok = abs(float(got) - float(claimed)) <= tol
        got_s = f"{float(got):.6g}" if tol else f"{got}"
    else:
        ok = str(claimed) == str(got)
        got_s = str(got)
    ROWS.append({"claim": claim, "claimed": claimed, "recomputed": got_s, "match": ok})


def runs(flags: np.ndarray) -> list[int]:
    """Lengths of runs of True in a boolean array."""
    out, cur = [], 0
    for f in flags:
        if f:
            cur += 1
        elif cur:
            out.append(cur)
            cur = 0
    if cur:
        out.append(cur)
    return out


def verify_shapes(tr: pd.DataFrame, te: pd.DataFrame, me: pd.DataFrame) -> None:
    ss = pd.read_csv(DATA / "sample_submission.csv")
    check("train shape", "(970379, 9)", tr.shape)
    check("meta shape", "(1115, 10)", me.shape)
    check("test shape", "(46830, 8)", te.shape)
    check("sample_submission shape", "(46830, 2)", ss.shape)
    check("sample_submission all zero", True, bool((ss["OrderVolume"] == 0).all()))
    check("train dates unique", 900, tr["Date"].nunique())
    check("train first date", "2013-01-01", tr["Date"].min().date())
    check("train last date", "2015-06-19", tr["Date"].max().date())
    check("train hubs", 1115, tr["HubID"].nunique())
    yr = tr["Date"].dt.year.value_counts()
    check("rows 2013", 406974, yr[2013]); check("rows 2014", 373855, yr[2014]); check("rows 2015", 189550, yr[2015])
    check("train+test rows = Rossmann train 1,017,209", 1017209, len(tr) + len(te))
    check("weekday mismatches vs Date (1=Mon)", 0, int((tr["Date"].dt.day_of_week + 1 != tr["Weekday"]).sum()))
    check("hub-date duplicates train", 0, int(tr.duplicated(["HubID", "Date"]).sum()))
    check("hub-date duplicates test", 0, int(te.duplicated(["HubID", "Date"]).sum()))
    check("full-row duplicates train", 0, int(tr.duplicated().sum()))
    check("missing cells train", 0, int(tr.isna().sum().sum()))
    check("same hub set train/test/meta", True, set(tr.HubID) == set(te.HubID) == set(me.HubID))


def verify_columns(tr: pd.DataFrame, op: pd.DataFrame) -> None:
    v, ov = tr["OrderVolume"], op["OrderVolume"]
    check("volume min", 0, v.min()); check("volume max", 38722, v.max())
    check("volume mean all rows", 5762.8, v.mean(), 0.05)
    check("volume mean open", 6954.4, ov.mean(), 0.05)
    check("volume median open", 6368, ov.median())
    check("volume skew open (g1)", 1.593, moment_skew(ov), 0.0005)
    check("volume kurtosis open (normal=3)", 7.84, moment_kurt(ov), 0.005)
    pos = ov[ov > 0]
    check("skew log1p(volume>0) open", -0.11, moment_skew(np.log1p(pos)), 0.005)
    check("sessions max", 7388, tr["AppSessions"].max())
    check("sessions mean all", 633.3, tr["AppSessions"].mean(), 0.05)
    check("sessions mean open", 764.2, op["AppSessions"].mean(), 0.05)
    check("r(volume, sessions) all", 0.896, np.corrcoef(v, tr["AppSessions"])[0, 1], 0.0005)
    check("r(volume, sessions) open", 0.825, np.corrcoef(ov, op["AppSessions"])[0, 1], 0.0005)
    check("open rows", 804110, len(op)); check("closed rows", 166269, int((tr.IsOpen == 0).sum()))
    check("open share %", 82.87, 100 * tr.IsOpen.mean(), 0.005)
    check("promo share %", 38.27, 100 * tr.PromoActive.mean(), 0.005)
    check("promo on Sat/Sun rows", 0, int(((tr.Weekday >= 6) & (tr.PromoActive == 1)).sum()))
    sh = tr.RegionalHoliday.value_counts(normalize=True) * 100
    for k, c in zip(range(4), [96.80, 2.09, 0.69, 0.42]):
        check(f"holiday {k} share %", c, sh[k], 0.005)
    oh = op.RegionalHoliday.value_counts()
    for k, c in zip([1, 2, 3], [694, 145, 71]):
        check(f"open on holiday {k}", c, oh.get(k, 0))
    check("easter dates within 03-29..04-21", True, bool(tr.loc[tr.RegionalHoliday == 2, "Date"].dt.strftime("%m-%d").between("03-29", "04-21").all()))
    check("christmas dates 12-25/12-26", "['12-25', '12-26']", sorted(tr.loc[tr.RegionalHoliday == 3, "Date"].dt.strftime("%m-%d").unique()))
    check("school closure share %", 17.35, 100 * tr.SchoolClosureFlag.mean(), 0.005)


def verify_meta(me: pd.DataFrame) -> None:
    check("format counts 1/2/3/4", "[602, 17, 148, 348]", me.HubFormat.value_counts().sort_index().tolist())
    check("tier counts 1/2/3", "[593, 9, 513]", me.AssortmentTier.value_counts().sort_index().tolist())
    t2 = me[me.AssortmentTier == 2]
    check("tier 2 only in format 2", True, bool((t2.HubFormat == 2).all()))
    d = me.CompetitorDistance.dropna()
    check("distance min", 20, d.min()); check("distance max", 75860, d.max()); check("distance median", 2325, d.median())
    check("distance Q1 (linear)", 717.5, d.quantile(0.25)); check("distance Q3 (linear)", 6882.5, d.quantile(0.75))
    check("distance skew g1", 2.93, moment_skew(d), 0.005)
    check("distance missing hubs", "[291, 622, 879]", me.loc[me.CompetitorDistance.isna(), "HubID"].tolist())
    check("comp-open month missing", 354, int(me.CompetitorOpenSinceMonth.isna().sum()))
    check("comp-open year missing", 354, int(me.CompetitorOpenSinceYear.isna().sum()))
    check("comp-open year min/max", "[1900, 2015]", [int(me.CompetitorOpenSinceYear.min()), int(me.CompetitorOpenSinceYear.max())])
    r = me.set_index("HubID")
    check("hub 815 = 1900, month 1", "(1900, 1)", (int(r.loc[815, "CompetitorOpenSinceYear"]), int(r.loc[815, "CompetitorOpenSinceMonth"])))
    check("hub 146 = 1961, month 10", "(1961, 10)", (int(r.loc[146, "CompetitorOpenSinceYear"]), int(r.loc[146, "CompetitorOpenSinceMonth"])))
    ym = pd.to_datetime(dict(year=me.CompetitorOpenSinceYear, month=me.CompetitorOpenSinceMonth, day=1), errors="coerce")
    inside = ((ym >= TRAIN_START) & (ym <= "2015-05-31")).sum()  # whole opening month inside train
    check("competitor opened inside train (opening month 2013-01..2015-05)", 175, int(inside))
    check("... incl. June 2015 (month cut by train end)", 180, int(((ym >= TRAIN_START) & (ym <= TRAIN_END)).sum()))
    check("competitor opened after train end", 11, int((ym > TRAIN_END).sum()))
    check("loyalty yes/no", "[544, 571]", me.LoyaltyProgram.value_counts().sort_index().tolist())
    na = me.LoyaltyProgramSinceWeek.isna()
    check("loyalty NA == no-loyalty (contradictions)", 0, int((na != (me.LoyaltyProgram == 0)).sum()))
    check("loyalty years", "[2009, 2015]", [int(me.LoyaltyProgramSinceYear.min()), int(me.LoyaltyProgramSinceYear.max())])
    check("interval counts", "{'Jan,Apr,Jul,Oct': 335, 'Feb,May,Aug,Nov': 130, 'Mar,Jun,Sept,Dec': 106}", me.LoyaltyProgramInterval.value_counts().to_dict())
    check("hub 1 metadata (3,1,1270,9,2008,0)", "[3, 1, 1270, 9, 2008, 0]", [int(r.loc[1, c]) for c in ["HubFormat", "AssortmentTier", "CompetitorDistance", "CompetitorOpenSinceMonth", "CompetitorOpenSinceYear", "LoyaltyProgram"]])
    check("hub 2 loyalty (13, 2010, Jan,Apr,Jul,Oct)", "[13, 2010, 'Jan,Apr,Jul,Oct']", [int(r.loc[2, "LoyaltyProgramSinceWeek"]), int(r.loc[2, "LoyaltyProgramSinceYear"]), r.loc[2, "LoyaltyProgramInterval"]])
    attrs = [c for c in me.columns if c != "HubID"]
    dup = me[me.duplicated(attrs, keep=False)]
    check("hubs sharing identical metadata (4 pairs)", "[26, 426, 436, 473, 557, 651, 722, 773]", sorted(dup.HubID.tolist()))


def verify_test(te: pd.DataFrame) -> None:
    check("test Id 1..46830", True, te.Id.tolist() == list(range(1, 46831)))
    check("test dates", "2015-06-20..2015-07-31 (42)", f"{te.Date.min().date()}..{te.Date.max().date()} ({te.Date.nunique()})")
    check("test grid complete 1115x42", True, len(te) == 1115 * 42 == len(te.drop_duplicates(["HubID", "Date"])))
    check("test open %", 86.02, 100 * te.IsOpen.mean(), 0.005)
    cl = te[te.IsOpen == 0]
    check("test closures total", 6548, len(cl)); check("test closures on Sunday", 6497, int((cl.Weekday == 7).sum()))
    check("hubs closed on weekdays (test)", 4, cl.loc[cl.Weekday < 7, "HubID"].nunique())
    check("test promo %", 35.71, 100 * te.PromoActive.mean(), 0.005)
    check("test holiday all 0", True, bool((te.RegionalHoliday == 0).all()))
    check("test school %", 28.51, 100 * te.SchoolClosureFlag.mean(), 0.005)


def verify_gap(tr: pd.DataFrame, me: pd.DataFrame) -> None:
    dates = pd.date_range(TRAIN_START, TRAIN_END)
    full = pd.MultiIndex.from_product([sorted(tr.HubID.unique()), dates], names=["HubID", "Date"])
    present = pd.MultiIndex.from_frame(tr[["HubID", "Date"]])
    absent = full.difference(present).to_frame(index=False)
    check("expected hub-dates", 1003500, len(full)); check("absent hub-dates", 33121, len(absent))
    blk = absent[absent.Date.between(GAP_START, GAP_END)]
    check("gap hubs (2014-07-01..12-31)", 180, blk.HubID.nunique())
    check("each gap hub misses exactly 184 days", True, bool((blk.groupby("HubID").size() == 184).all()))
    other = absent[~absent.Date.between(GAP_START, GAP_END)]
    check("other absent = hub 988 on 2013-01-01", "[(988, '2013-01-01')]", [(int(h), str(d.date())) for h, d in zip(other.HubID, other.Date)])
    g = me.assign(gap=me.HubID.isin(blk.HubID)).groupby("HubFormat").gap.sum().tolist()
    check("gap hubs by format 1/2/3/4", "[84, 1, 14, 81]", g)


def verify_quality(tr: pd.DataFrame, op: pd.DataFrame) -> None:
    cl = tr[tr.IsOpen == 0]
    check("closed rows with volume or sessions > 0", 0, int(((cl.OrderVolume > 0) | (cl.AppSessions > 0)).sum()))
    oz = op[op.OrderVolume == 0]
    check("open & volume 0 rows", 54, len(oz)); check("open & volume 0 hubs", 41, oz.HubID.nunique())
    check("open-zero date range", "2013-01-17..2015-05-15", f"{oz.Date.min().date()}..{oz.Date.max().date()}")
    check("open & sessions 0", 52, int((op.AppSessions == 0).sum()))
    check("sessions>0 & volume 0", 2, int(((op.AppSessions > 0) & (op.OrderVolume == 0)).sum()))
    check("volume>0 & sessions 0", 0, int(((op.AppSessions == 0) & (op.OrderVolume > 0)).sum()))
    q1, q3 = op.OrderVolume.quantile([0.25, 0.75])
    iqr = q3 - q1
    check("IQR Q1", 4856, q1); check("IQR Q3", 8360, q3); check("upper fence", 13616, q3 + 1.5 * iqr)
    check("rows above fence", 29307, int((op.OrderVolume > q3 + 1.5 * iqr).sum()))
    check("rows below fence", 0, int((op.OrderVolume < q1 - 1.5 * iqr).sum()))
    z = (op.OrderVolume - op.OrderVolume.mean()) / op.OrderVolume.std(ddof=1)
    for k, c in zip([2, 3, 4], [4.24, 1.59, 0.60]):
        check(f"share |z|>={k} %", c, 100 * (z.abs() >= k).mean(), 0.005)
    pv = op[op.OrderVolume > 0]  # open-zero rows removed first (Q3)
    med = pv.groupby("HubID").OrderVolume.transform("median")
    mad = (pv.OrderVolume - med).abs().groupby(pv.HubID).transform("median")
    rz = 0.6745 * (pv.OrderVolume - med) / mad
    check("robust z |z|>3.5 rows (volume>0)", 6220, int((rz.abs() > 3.5).sum()))
    check("robust z |z|>3.5 hubs (volume>0)", 1040, pv.loc[rz.abs() > 3.5, "HubID"].nunique())
    mx = op.loc[op.OrderVolume.idxmax()]
    check("max row (hub, date, holiday, promo)", "(262, '2015-04-03', 2, 1)", (int(mx.HubID), str(mx.Date.date()), int(mx.RegionalHoliday), int(mx.PromoActive)))
    s = op[op.AppSessions > 0]
    ratio = s.OrderVolume / s.AppSessions
    check("ratio median", 9.23, ratio.median(), 0.005); check("ratio p99.9", 17.19, ratio.quantile(0.999), 0.005)
    check("ratio max", 64.96, ratio.max(), 0.005); check("ratio > 30 rows", 23, int((ratio > 30).sum()))
    rm = s.loc[ratio.idxmax()]
    check("ratio max row", "(897, '2013-09-02', 16954, 261)", (int(rm.HubID), str(rm.Date.date()), int(rm.OrderVolume), int(rm.AppSessions)))
    big = op[op.OrderVolume >= 100]
    dig = (big.OrderVolume % 10).value_counts()
    check("last-digit counts min..max", "80036..81052", f"{dig.min()}..{dig.max()}")
    verify_calendar(tr, op)


def verify_calendar(tr: pd.DataFrame, op: pd.DataFrame) -> None:
    check("hubs open on 2013-01-01", 17, int(op.Date.eq("2013-01-01").sum()))
    check("open holiday rows", 910, int((op.RegionalHoliday > 0).sum()))
    sun = op[op.Weekday == 7]
    check("open Sunday rows", 3400, len(sun)); check("Sunday-open hubs", 33, sun.HubID.nunique())
    m = op.groupby(["Weekday", "PromoActive"]).OrderVolume.mean()
    check("Mon promo mean", 9762, m[(1, 1)], 0.5); check("Mon no-promo mean", 6211, m[(1, 0)], 0.5)
    check("Fri promo mean", 7733, m[(5, 1)], 0.5); check("Fri no-promo mean", 6358, m[(5, 0)], 0.5)
    lens: list[int] = []
    for _, g in tr.sort_values("Date").groupby("HubID"):
        consecutive = g.Date.diff().dt.days.fillna(1).eq(1).to_numpy()
        closed = g.IsOpen.eq(0).to_numpy()
        seg = np.cumsum(~consecutive)          # a calendar gap breaks a run
        for sid in np.unique(seg):
            lens += runs(closed[seg == sid])
    lens_a = np.array(lens)
    check("1-day closure runs", 145746, int((lens_a == 1).sum())); check("2-day closure runs", 9299, int((lens_a == 2).sum()))
    check("closure runs >= 5 days", 88, int((lens_a >= 5).sum())); check("closure runs >= 14 days", 45, int((lens_a >= 14).sum()))
    check("longest closure run", 185, int(lens_a.max()))


def main() -> int:
    tr, te, me = load_train(), load_test(), load_meta()
    op = open_days(tr)
    verify_shapes(tr, te, me); verify_columns(tr, op); verify_meta(me); verify_test(te)
    verify_gap(tr, me); verify_quality(tr, op)
    out = pd.DataFrame(ROWS)
    save(out, "verify.csv")
    hashes = pd.DataFrame([{"file": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)} for p in sorted(DATA.glob("*.csv"))])
    save(hashes, "file_hashes.csv")
    with pd.option_context("display.max_rows", 500, "display.width", 200, "display.max_colwidth", 60):
        print(out.to_string(index=False))
        print(hashes.to_string(index=False))
    bad = out[~out.match]
    print(f"\n{len(out) - len(bad)}/{len(out)} claims match")
    return 1 if len(bad) else 0


if __name__ == "__main__":
    sys.exit(main())
