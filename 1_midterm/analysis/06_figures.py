"""Figures for the r1 report (vector PDF, one-column width). Reads only saved r1 outputs.

Palette: reference categorical slots 1-4 (blue, orange, aqua, yellow), validated as a set;
identity is never colour-alone (direct labels / legends); recessive grey axes and grid.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from common import DERIVED, FIG, OUT, moment_kurt, moment_skew

BLUE, ORANGE, AQUA, GREY, INK, INK2 = "#2a78d6", "#eb6834", "#1baf7a", "#b9b8b3", "#0b0b0b", "#52514e"
W = 3.3
plt.rcParams.update({"font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7, "xtick.labelsize": 6.5, "ytick.labelsize": 6.5,
                     "axes.edgecolor": INK2, "axes.linewidth": 0.6, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
                     "axes.labelcolor": INK, "axes.grid": True, "grid.color": "#e6e5e1", "grid.linewidth": 0.5,
                     "axes.spines.top": False, "axes.spines.right": False, "font.family": "DejaVu Sans", "pdf.fonttype": 42})


def save(fig: plt.Figure, name: str) -> None:
    fig.savefig(FIG / name, bbox_inches="tight", pad_inches=0.02, metadata={"CreationDate": None})
    plt.close(fig)


def fig_volume(v: np.ndarray) -> None:
    """Histogram paired with a boxplot, raw vs log scale (open days)."""
    lv = np.log1p(v[v > 0])
    fig, ax = plt.subplots(2, 2, figsize=(W, 1.9), gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08, "wspace": 0.25}, sharex="col")
    for j, (x, lab) in enumerate([(v, "OrderVolume (open days)"), (lv, "log(1 + OrderVolume)")]):
        ax[0, j].hist(x, bins=80, color=BLUE, edgecolor="white", linewidth=0.2)
        ax[0, j].set_yticks([]); ax[0, j].grid(False)
        ax[0, j].text(0.98 if j == 0 else 0.02, 0.95, f"skewness {moment_skew(x):.2f}\nkurtosis {moment_kurt(x):.2f}", transform=ax[0, j].transAxes, ha="right" if j == 0 else "left", va="top", fontsize=6, color=INK2)
        ax[1, j].boxplot(x, orientation="horizontal", widths=0.6, flierprops={"marker": ".", "markersize": 1, "markeredgecolor": GREY},
                         medianprops={"color": ORANGE, "linewidth": 1.2}, boxprops={"linewidth": 0.6}, whiskerprops={"linewidth": 0.6})
        ax[1, j].set_yticks([]); ax[1, j].set_xlabel(lab)
    save(fig, "fig_volume.pdf")


def fig_gap() -> None:
    d = pd.read_csv(OUT / "desc_hubs_per_date.csv", parse_dates=["Date"])
    t = pd.read_csv(OUT / "t2_contingency.csv")
    fig, ax = plt.subplots(1, 2, figsize=(W, 1.55), gridspec_kw={"width_ratios": [1.25, 1], "wspace": 0.4})
    ax[0].plot(d["Date"], d["hubs_observed"], color=BLUE, linewidth=1)
    ax[0].axvspan(pd.Timestamp("2014-07-01"), pd.Timestamp("2014-12-31"), color=GREY, alpha=0.3, linewidth=0)
    ax[0].text(pd.Timestamp("2014-09-30"), 1000, "180 hubs\nabsent\n184 days", ha="center", fontsize=6, color=INK2)
    ax[0].set_ylim(900, 1130); ax[0].set_ylabel("hubs with a row")
    ax[0].xaxis.set_major_locator(matplotlib.dates.YearLocator()); ax[0].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
    n = t["no_gap"] + t["gap"]
    lo, hi = map(np.array, zip(*[stats.binomtest(int(k), int(m)).proportion_ci(0.95, "wilson") for k, m in zip(t["gap"], n)]))
    p = t["gap"] / n
    x = np.arange(len(t))
    ax[1].bar(x, 100 * p, color=[BLUE, BLUE, BLUE, ORANGE], width=0.6)
    ax[1].errorbar(x, 100 * p, yerr=[100 * (p - lo), 100 * (hi - p)], fmt="none", ecolor=INK2, elinewidth=0.6, capsize=1.5)
    ax[1].set_xticks(x, [f"F{f}\n({m})" for f, m in zip(t["HubFormat"], n)], fontsize=6); ax[1].set_ylabel("gap hubs, %"); ax[1].set_ylim(0, 40)
    ax[1].grid(axis="x", visible=False)
    save(fig, "fig_gap.pdf")


def fig_promo() -> None:
    d = pd.read_csv(OUT / "desc_weekday_lift.csv")
    fig, ax = plt.subplots(figsize=(W, 1.45))
    x = d["weekday"].to_numpy()
    ax.plot(x, 100 * d["pct"], color=BLUE, linewidth=1.2, marker="o", markersize=4)
    ax.vlines(x, 100 * d["pct_low"], 100 * d["pct_high"], color=INK2, linewidth=0.8)
    for xi, v in zip(x, d["pct"]):
        ax.text(xi + 0.1, 100 * v + 1.5, f"{100*v:.0f}%", fontsize=6, color=INK)
    ax.set_xticks(x, ["Mon", "Tue", "Wed", "Thu", "Fri"]); ax.set_ylabel("promo lift, %"); ax.set_ylim(15, 68); ax.set_xlim(0.7, 5.5)
    save(fig, "fig_promo_weekday.pdf")


def fig_distance() -> None:
    h = pd.read_csv(OUT / "t3_hub_data.csv")
    dec = h.assign(q=pd.qcut(h["log_distance"], 10, labels=False)).groupby("q")[["log_distance", "mean_log1p"]].mean()
    fig, ax = plt.subplots(figsize=(W, 1.75))
    ax.scatter(h["log_distance"], h["mean_log1p"], s=3, color=GREY, linewidths=0, label="one hub")
    ax.plot(dec["log_distance"], dec["mean_log1p"], color=BLUE, marker="o", markersize=4, linewidth=1, label="decile mean")
    b = np.polyfit(h["log_distance"], h["mean_log1p"], 1)
    xs = np.linspace(h["log_distance"].min(), h["log_distance"].max(), 2)
    ax.plot(xs, np.polyval(b, xs), color=ORANGE, linewidth=1.2, label="least-squares line")
    ticks = [20, 100, 1000, 10000, 75000]
    ax.set_xticks(np.log(ticks), [f"{t:,}" for t in ticks]); ax.set_xlabel("competitor distance (log scale, units unstated)")
    ax.set_ylabel("hub mean log(1+V)"); ax.set_ylim(7.6, 10.4)
    ax.legend(frameon=False, fontsize=6, loc="upper right", markerscale=1.5)
    save(fig, "fig_distance.pdf")


def fig_qq() -> None:
    d1 = pd.read_csv(OUT / "t1_hub_differences.csv")["d"]
    d4 = pd.read_csv(OUT / "t4_did_hubs.csv")["did"]
    fig, ax = plt.subplots(1, 2, figsize=(W, 1.5), gridspec_kw={"wspace": 0.35})
    for a, x, title in [(ax[0], d1, f"T1: $d_i$ (n = {len(d1):,})"), (ax[1], d4, f"T4: DiD$_i$ (n = {len(d4)})")]:
        (osm, osr), (sl, ic, _) = stats.probplot(x, dist="norm")
        a.scatter(osm, osr, s=2, color=BLUE, linewidths=0)
        a.plot(osm, sl * osm + ic, color=ORANGE, linewidth=1)
        a.set_title(title, loc="left"); a.set_xlabel("normal quantile")
    ax[0].set_ylabel("sample quantile")
    save(fig, "fig_qq.pdf")


def main() -> None:
    c = pd.read_parquet(DERIVED / "hubday_clean.parquet", columns=["IsOpen", "OrderVolume"])
    fig_volume(c.loc[c["IsOpen"].eq(1), "OrderVolume"].to_numpy())
    fig_gap(); fig_promo(); fig_distance(); fig_qq()
    print(sorted(p.name for p in FIG.glob("*.pdf")))


if __name__ == "__main__":
    main()
