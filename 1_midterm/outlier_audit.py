"""Characterize outliers without arbitrarily deleting operational demand spikes."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd


def audit(repo: Path):
    data = pd.read_csv(repo/'datset_kaggle/orders_train.csv',parse_dates=['Date'])
    required=['HubID','Date','OrderVolume','IsOpen']
    assert set(required).issubset(data)
    opened=data.loc[data.IsOpen.eq(1)].copy()
    if opened.empty: raise ValueError('No operating day records')
    q1,q3=opened.OrderVolume.quantile([.25,.75])
    iqr=q3-q1
    hi=q3+1.5*iqr
    lo=q1-1.5*iqr
    extreme = opened[(opened.OrderVolume<lo)|(opened.OrderVolume>hi)]
    zero_open=int((opened.OrderVolume==0).sum())
    no_neg=int((data.OrderVolume<0).sum())
    out=pd.DataFrame([{
        'n_raw_rows':len(data),'n_open_rows':len(opened),
        'open_q1':q1,'open_q3':q3,'open_iqr':iqr,'lower_fence':lo,
        'upper_fence':hi,'n_outside_iqr_fences':len(extreme),
        'pct_outside_iqr_fences':100*len(extreme)/len(opened),
        'open_zero_order_rows':zero_open,'negative_order_rows':no_neg,
        'min_open':opened.OrderVolume.min(),'max_open':opened.OrderVolume.max(),
        'n_removed_by_outlier_policy':0,
        'policy':'retain extremes; outlier fences descriptive, not automatic deletion'
    }])
    output=repo/'midterm/results/outlier_audit.csv'
    output.parent.mkdir(parents=True,exist_ok=True)
    out.to_csv(output,index=False)
    print(out.to_string(index=False))
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path('.'))
    audit(p.parse_args().repo)
