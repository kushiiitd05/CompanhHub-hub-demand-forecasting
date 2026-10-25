"""Stage 6, part 3: one summary row per test, with Bonferroni and Holm decisions.

Reads the per-test CSVs written by 02/03 and writes results/r1/tests_summary.csv.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from common import ALPHA, N_TESTS, OUT, save
from inference import multiplicity


def first(name: str) -> pd.Series:
    return pd.read_csv(OUT / name).iloc[0]


def log10_p_t(t: float, df: int) -> float:
    """log10 of a two-sided t p-value, valid where the p-value underflows to 0."""
    v = float((np.log(2) + stats.t.logsf(abs(t), df)) / np.log(10))
    return v if np.isfinite(v) else -300.0   # report as p < 1e-300 (double-precision underflow)


def main() -> None:
    t1, t2, t3, t4 = first("t1_results.csv"), first("t2_results.csv"), first("t3_results.csv"), first("t4_results.csv")
    f2 = first("t2_followup_format4_vs_rest.csv")
    rows = [
        {"test": "T1", "test_used": "paired t on d_i", "n": t1.n, "statistic": t1.statistic, "df": t1.df, "crit": t1.crit_two_sided,
         "p": t1.p, "log10_p": log10_p_t(t1.statistic, int(t1.df)), "estimate": t1.estimate, "ci_low": t1.ci_low, "ci_high": t1.ci_high,
         "natural_units": f"{100*t1.pct:.1f}% [{100*t1.pct_low:.1f}, {100*t1.pct_high:.1f}]", "verdict": t1.verdict},
        {"test": "T2", "test_used": "chi-square independence, permutation p", "n": t2.n, "statistic": t2.statistic, "df": t2.df, "crit": t2.crit,
         "p": t2.p, "log10_p": np.log10(t2.p), "estimate": f2.estimate, "ci_low": f2.ci_low, "ci_high": f2.ci_high,
         "natural_units": f"{100*f2.estimate:.1f} pp [{100*f2.ci_low:.1f}, {100*f2.ci_high:.1f}]; V={t2.cramers_v:.3f} [{t2.v_ci_low:.3f}, {t2.v_ci_high:.3f}]", "verdict": f2.verdict},
        {"test": "T3", "test_used": "t on Pearson r", "n": t3.n, "statistic": t3.statistic, "df": t3.df, "crit": t3.crit_two_sided,
         "p": t3.p, "log10_p": np.log10(t3.p), "estimate": t3.estimate, "ci_low": t3.ci_low, "ci_high": t3.ci_high,
         "natural_units": f"r={t3.estimate:.3f} [{t3.ci_low:.3f}, {t3.ci_high:.3f}]", "verdict": t3.verdict},
        {"test": "T4", "test_used": "paired t on DiD_i", "n": t4.n, "statistic": t4.statistic, "df": t4.df, "crit": t4.crit_two_sided,
         "p": t4.p, "log10_p": np.log10(t4.p), "estimate": t4.estimate, "ci_low": t4.ci_low, "ci_high": t4.ci_high,
         "natural_units": f"{100*t4.pct:.1f}% [{100*t4.pct_low:.1f}, {100*t4.pct_high:.1f}]", "verdict": t4.verdict},
    ]
    s = pd.DataFrame(rows)
    adj = multiplicity(dict(zip(s.test, s.p.clip(lower=1e-300))))
    s["reject_at_0.05"] = s.p < ALPHA
    s["bonferroni_alpha"] = ALPHA / N_TESTS
    s["bonferroni_reject"] = [adj[k]["bonferroni_reject"] for k in s.test]
    s["p_holm"] = [adj[k]["p_holm"] for k in s.test]
    s["holm_reject"] = [adj[k]["holm_reject"] for k in s.test]
    save(s, "tests_summary.csv")
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 80)
    print(s.T.to_string())


if __name__ == "__main__":
    main()
