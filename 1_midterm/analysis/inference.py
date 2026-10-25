"""Inference helpers: each returns a flat dict so every test reports the same items.

Every helper computes the statistic twice, with scipy and with the textbook formula,
and stores both so the 4-significant-figure agreement can be checked.
"""
from __future__ import annotations

import numpy as np
from scipy import stats

from common import ALPHA, N_TESTS


def sig4(a: float, b: float) -> bool:
    """True if a and b agree to 4 significant figures."""
    if a == b:
        return True
    return f"{a:.4g}" == f"{b:.4g}" or abs(a - b) <= 5e-4 * max(abs(a), abs(b))


def verdict(lo: float, hi: float, delta: float) -> str:
    """Practical significance: compare the whole CI with +-delta."""
    if lo >= delta or hi <= -delta:
        return f"whole CI beyond +-{delta:g}: large enough to matter"
    if -delta <= lo and hi <= delta:
        return f"whole CI inside +-{delta:g}: no effect large enough to matter"
    return f"CI straddles +-{delta:g}: practical importance uncertain"


def _pct(x: float) -> float:
    """e^x - 1 for log-scale effects; NaN for raw-scale values."""
    return float(np.expm1(x)) if abs(x) < 5 else float("nan")


def paired_t(d: np.ndarray, delta: float) -> dict:
    """Two-sided one-sample t on paired differences d_i (H0: mu_d = 0)."""
    d = np.asarray(d, dtype=float)
    n = d.size
    dbar, sd = d.mean(), d.std(ddof=1)
    se = sd / np.sqrt(n)
    t_manual = (dbar - 0.0) / se
    df = n - 1
    p_manual = 2 * stats.t.sf(abs(t_manual), df)
    res = stats.ttest_1samp(d, 0.0)
    crit = stats.t.ppf(1 - ALPHA / 2, df)
    lo, hi = dbar - crit * se, dbar + crit * se
    w = stats.wilcoxon(d)
    sign = stats.binomtest(int((d > 0).sum()), int((d != 0).sum()))
    return {"n": n, "estimate": dbar, "sd": sd, "se": se, "statistic": float(res.statistic), "statistic_manual": t_manual,
            "df": df, "crit_two_sided": crit, "p": float(res.pvalue), "p_manual": p_manual,
            "ci_low": lo, "ci_high": hi, "pct": _pct(dbar), "pct_low": _pct(lo), "pct_high": _pct(hi),
            "cohen_dz": dbar / sd, "wilcoxon_p": float(w.pvalue), "sign_test_p": float(sign.pvalue),
            "n_positive": int((d > 0).sum()), "verdict": verdict(lo, hi, delta),
            "agree_4sf": sig4(float(res.statistic), t_manual) and sig4(float(res.pvalue) + 1e-300, p_manual + 1e-300)}


def pearson_t(x: np.ndarray, y: np.ndarray, delta: float) -> dict:
    """Two-sided t-test of H0: rho = 0, with a Fisher-z 95% CI."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    n = x.size
    r_manual = float(np.sum((x - x.mean()) * (y - y.mean())) / np.sqrt(np.sum((x - x.mean())**2) * np.sum((y - y.mean())**2)))
    res = stats.pearsonr(x, y)
    df = n - 2
    t_manual = r_manual * np.sqrt(df) / np.sqrt(1 - r_manual**2)
    p_manual = 2 * stats.t.sf(abs(t_manual), df)
    z, zse = np.arctanh(r_manual), 1 / np.sqrt(n - 3)
    zc = stats.norm.ppf(1 - ALPHA / 2)
    lo, hi = np.tanh(z - zc * zse), np.tanh(z + zc * zse)
    ci = res.confidence_interval(0.95)
    sp = stats.spearmanr(x, y)
    return {"n": n, "estimate": float(res.statistic), "statistic": t_manual, "df": df, "crit_two_sided": stats.t.ppf(1 - ALPHA / 2, df),
            "p": float(res.pvalue), "p_manual": p_manual, "ci_low": lo, "ci_high": hi, "scipy_ci_low": ci.low, "scipy_ci_high": ci.high,
            "spearman": float(sp.statistic), "spearman_p": float(sp.pvalue), "verdict": verdict(lo, hi, delta),
            "agree_4sf": sig4(float(res.statistic), r_manual) and sig4(float(res.pvalue), p_manual)}


def chi2_independence(table: np.ndarray, n_perm: int, rng: np.random.Generator,
                      rows: np.ndarray, cols: np.ndarray) -> dict:
    """Pearson chi-square of independence with a Monte Carlo permutation p-value.

    rows/cols are the per-unit category codes that built `table`; shuffling cols
    keeps both margins fixed.
    """
    obs = np.asarray(table, float)
    exp_manual = obs.sum(1, keepdims=True) @ obs.sum(0, keepdims=True) / obs.sum()
    chi_manual = float(((obs - exp_manual)**2 / exp_manual).sum())
    chi, p_asym, df, exp = stats.chi2_contingency(obs, correction=False)
    r, c = obs.shape
    hits = 0
    for _ in range(n_perm):
        perm = np.zeros_like(obs)
        np.add.at(perm, (rows, rng.permutation(cols)), 1)
        e = perm.sum(1, keepdims=True) @ perm.sum(0, keepdims=True) / perm.sum()
        hits += ((perm - e)**2 / e).sum() >= chi - 1e-9
    n = obs.sum()
    return {"n": int(n), "statistic": float(chi), "statistic_manual": chi_manual, "df": int(df),
            "crit": stats.chi2.ppf(1 - ALPHA, df), "p_asymptotic": float(p_asym), "p": (hits + 1) / (n_perm + 1),
            "n_perm": n_perm, "min_expected": float(exp.min()), "cramers_v": float(np.sqrt(chi / (n * min(r - 1, c - 1)))),
            "agree_4sf": sig4(float(chi), chi_manual)}


def two_prop_diff(k1: int, n1: int, k2: int, n2: int, delta: float) -> dict:
    """Difference of proportions p1 - p2 with a Wald 95% CI and Newcombe hybrid-score CI."""
    p1, p2 = k1 / n1, k2 / n2
    se = np.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    zc = stats.norm.ppf(1 - ALPHA / 2)
    l1, u1 = stats.binomtest(k1, n1).proportion_ci(0.95, "wilson")
    l2, u2 = stats.binomtest(k2, n2).proportion_ci(0.95, "wilson")
    d = p1 - p2
    nl = d - np.sqrt((p1 - l1)**2 + (u2 - p2)**2)
    nu = d + np.sqrt((u1 - p1)**2 + (p2 - l2)**2)
    pooled = (k1 + k2) / (n1 + n2)
    z = d / np.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    return {"p1": p1, "p2": p2, "estimate": d, "se": se, "ci_low": d - zc * se, "ci_high": d + zc * se,
            "newcombe_low": nl, "newcombe_high": nu, "z_pooled": z, "p_z": 2 * stats.norm.sf(abs(z)),
            "verdict": verdict(d - zc * se, d + zc * se, delta)}


def multiplicity(pvals: dict[str, float]) -> dict[str, dict]:
    """Bonferroni (alpha/m) and Holm step-down decisions."""
    m = len(pvals)
    order = sorted(pvals, key=pvals.get)
    out, running = {}, 0.0
    for i, k in enumerate(order):
        running = max(running, min(1.0, (m - i) * pvals[k]))
        out[k] = {"p_holm": running, "bonferroni_reject": pvals[k] < ALPHA / N_TESTS, "holm_reject": running < ALPHA}
    return out
