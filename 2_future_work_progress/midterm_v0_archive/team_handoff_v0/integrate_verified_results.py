#!/usr/bin/env python3
"""Generate an evidence-linked LaTeX fragment from rerun result CSVs.

Never invents team contributions or fills numbers from earlier model versions.
The fragment is included in the report's T1, T2 and data-preparation sections.
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np


def num(x, digits=2):
    if not np.isfinite(float(x)):
        raise ValueError(f'Non-finite statistic: {x}')
    return f'{float(x):,.{digits}f}'


def pformat(x):
    p=float(x)
    if not np.isfinite(p) or p < 0 or p > 1: raise ValueError(f'Invalid p: {p}')
    return '$p<0.001$' if p < .001 else f'$p={p:.3f}$'


def row(repo,p):
    file=repo/'midterm/results'/p
    if not file.exists(): raise FileNotFoundError(f'Missing generated analysis file: {file}. Rerun the pipeline first.')
    df=pd.read_csv(file)
    if len(df)!=1:raise ValueError(f'Expected one row in {file}: {len(df)}')
    return df.iloc[0]


def write(repo):
    fe=row(repo,'t1_hub_fe_corrected_sensitivity.csv')
    hac=row(repo,'t1_date_hac_sensitivity.csv')
    out=row(repo,'outlier_audit.csv')
    t2=row(repo,'t2_effect_ci.csv')
    tr=repo/'midterm/results/test_results.csv'
    tests=pd.read_csv(tr)
    if len(tests)!=4: raise ValueError('Expected four primary tests')
    t2_main=tests.loc[tests['test'].str.startswith('T2_')]
    if len(t2_main)!=1:raise ValueError('Missing T2 result in primary tests')
    if abs(float(t2_main.iloc[0]['effect_estimate'])-float(t2['cramers_v']))>1e-7:
        raise ValueError('T2 effect inconsistent between tests and CI computation')
    if abs(float(t2_main.iloc[0]['ci95_low'])-float(t2['ci95_low']))>.015:
        raise ValueError('T2 primary and independent bootstrap CI differ unexpectedly')
    contrast=float(fe['monday_minus_friday_promotion_association'])
    ci_lo=float(fe['ci95_low']);ci_hi=float(fe['ci95_high'])
    date_contrast=float(hac['interaction_monday_minus_friday_promo'])
    date_ci=(float(hac['ci95_low']),float(hac['ci95_high']))
    if not (ci_lo <= contrast <= ci_hi and date_ci[0]<=date_contrast<=date_ci[1]):
        raise ValueError('Effect estimate outside its confidence interval')
    s1=(r'\textbf{Rerun hub fixed-effects sensitivity.} '
        rf'The corrected hub-fixed-effects estimate, including the Monday main effect, '
        rf'is {num(contrast)} orders (95\% CI [{num(ci_lo)}, {num(ci_hi)}], '
        +pformat(fe['p_value'])+'. '
        +r'Standard errors are clustered by hub. '
        +r'\textbf{Date-level sensitivity.} '
        +rf'Using {int(hac["n_dates"])} calendar dates as the analysis units, hub-centered daily means with HAC('
        +str(int(hac['hac_lags']))+r') standard errors give a Monday-by-promotion contrast of '
        +rf'{num(date_contrast)} orders (95\% CI [{num(date_ci[0])}, {num(date_ci[1])}]), '
        +pformat(hac['p_value'])+r'. This observational check partly addresses shared date shocks but does not remove seasonality or unobserved confounding.' )
    t2text=(r'\textbf{Independent CI verification.} A 5,000-replicate hub-level bootstrap '
            rf"from the observed contingency counts yielded a 95\% CI for Cramer's $V$ of "
            rf'[{num(t2["ci95_low"],3)}, {num(t2["ci95_high"],3)}]; '
            rf'$V={num(t2["cramers_v"],3)}$.')
    outtext=(r'\textbf{Quantified outlier audit.} Across '
             rf'{int(out["n_open_rows"]):,} recorded operating hub-days, '
             rf'{int(out["n_outside_iqr_fences"]):,} ({num(out["pct_outside_iqr_fences"])}\%) order counts '
             r'fall outside the standard 1.5$\times$IQR fences; '
             rf'{int(out["open_zero_order_rows"]):,} operating hub-days had zero orders and '
             rf'{int(out["negative_order_rows"]):,} had negative counts. '
             r'No outliers were automatically removed because extremes can be genuine demand peaks.')
    outdir=repo/'midterm/report'
    for name,body in [('t1_verified_results.tex',s1),('t2_verified_ci.tex',t2text),('outliers_verified.tex',outtext)]:
        (outdir/name).write_text(body+'\n',encoding='utf-8')
        print('GENERATED',outdir/name)
    pd.DataFrame([{'test':'T1_corrected_hubFE','estimate':contrast,'ci_low':ci_lo,'ci_high':ci_hi,'p':float(fe['p_value'])},
                  {'test':'T1_dateHAC','estimate':date_contrast,'ci_low':date_ci[0],'ci_high':date_ci[1],'p':float(hac['p_value'])}]).to_csv(repo/'midterm/results/t1_final_crosscheck.csv',index=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path('.'))
    write(p.parse_args().repo.resolve())
