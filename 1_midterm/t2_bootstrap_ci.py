"""Reproduce Cramer's V effect estimate and 95% hub-bootstrap CI for Test 2.

Reads only the committed 4x2 hub-format/long-gap contingency table; this is
exactly the same information needed for a non-parametric resampling of hubs.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
from scipy import stats


def compute(input_csv: Path, output_csv: Path, n_boot: int = 5000,
            seed: int = 20261025) -> pd.DataFrame:
    source = pd.read_csv(input_csv)
    if source.shape[1] != 3:
        raise ValueError("Expected HubFormat,False,True contingency table")
    counts = source.iloc[:, 1:3].to_numpy(dtype=int)
    if (counts < 0).any() or counts.sum() < 2:
        raise ValueError("Invalid contingency table")
    n = int(counts.sum())
    stat, p_asym, df, expected = stats.chi2_contingency(counts, correction=False)
    effect = np.sqrt(stat / (n * min(counts.shape[0]-1, counts.shape[1]-1)))
    # Reconstruct one row per hub from the sufficient contingency counts;
    # no synthetic observations are added beyond exactly what is tabulated.
    format_code = np.repeat(np.arange(counts.shape[0]), counts.sum(axis=1))
    long_gap = np.concatenate([np.r_[np.zeros(row[0], dtype=int),
                                      np.ones(row[1], dtype=int)] for row in counts])
    assert len(long_gap) == n
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(n_boot):
        ix = rng.integers(0, n, size=n)
        table = np.zeros_like(counts)
        np.add.at(table, (format_code[ix], long_gap[ix]), 1)
        if np.any(table.sum(axis=0) == 0) or np.any(table.sum(axis=1) == 0):
            continue
        s = stats.chi2_contingency(table, correction=False)[0]
        boot.append(np.sqrt(s / (n * min(table.shape[0]-1, table.shape[1]-1))))
    lo, hi = np.quantile(boot, [0.025, 0.975])
    result = pd.DataFrame([{
        'test':'T2_long_gap_vs_hub_format', 'n_hubs':n,
        'chi2': stat,'degrees_of_freedom':df,
        'p_chi2_asymptotic':p_asym,'minimum_expected':expected.min(),
        'cramers_v':effect,'ci95_low':lo,'ci95_high':hi,
        'ci_method':'hub percentile bootstrap from contingency table',
        'bootstrap_replicates':len(boot),'seed':seed
    }])
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_csv, index=False)
    print(result.to_string(index=False))
    return result


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--repo',type=Path,default=Path('.'))
    p.add_argument('--replicates',type=int,default=5000)
    p.add_argument('--seed',type=int,default=20261025)
    args=p.parse_args()
    table=args.repo/'midterm/results/t2_contingency_table.csv'
    output=args.repo/'midterm/results/t2_effect_ci.csv'
    compute(table,output,args.replicates,args.seed)
