"""Date-level HAC sensitivity for the Monday-vs-Friday promotion contrast.

Why: promotion is common across all hubs on a date, so hub-level standard
errors cannot fully capture common shocks. Analysis here uses calendar dates
as the primary independent units. This is a sensitivity check, NOT causal.
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import statsmodels.api as sm


def run(repo:Path, hac_lags:int=8):
    df=pd.read_csv(repo/'datset_kaggle/orders_train.csv', parse_dates=['Date'])
    x=df.loc[df.IsOpen.eq(1)&df.Weekday.isin([1,5]),
             ['HubID','Date','Weekday','PromoActive','OrderVolume']].copy()
    # Hub demeaning removes differences in hub demand levels before aggregation.
    x['hub_mean']=x.groupby('HubID')['OrderVolume'].transform('mean')
    x['hub_centered_orders']=x['OrderVolume']-x['hub_mean']
    day=x.groupby('Date').agg(
        centered_order_mean=('hub_centered_orders','mean'),
        open_hubs=('HubID','nunique'),
        promo=('PromoActive','first'),
        monday=('Weekday',lambda z:int(z.iloc[0]==1)),
        n_promo_values=('PromoActive','nunique'),
        n_weekday_values=('Weekday','nunique')
    ).reset_index().sort_values('Date')
    if (day.n_promo_values>1).any() or (day.n_weekday_values>1).any():
        raise ValueError('Promotion/weekday not common within some dates; re-examine date model')
    if day.groupby(['monday','promo']).size().min()<8:
        raise ValueError('Insufficient date replicates in at least one weekday x promotion cell')
    day['interaction']=day.monday*day.promo
    # HAC across consecutive observed Mon/Fri calendar dates; 8 dates ~4 weeks.
    X=sm.add_constant(day[['monday','promo','interaction']],has_constant='add')
    fit=sm.OLS(day['centered_order_mean'],X).fit(
        cov_type='HAC',cov_kwds={'maxlags':hac_lags})
    key='interaction'
    ci=fit.conf_int().loc[key]
    result=pd.DataFrame([{
        'method':'date-level hub-centered OLS with Newey-West HAC SE',
        'n_dates':len(day),'n_hubs':x.HubID.nunique(),
        'n_open_hub_date_rows':len(x),'hac_lags':hac_lags,
        'interaction_monday_minus_friday_promo':fit.params[key],
        'standard_error':fit.bse[key],'ci95_low':ci.iloc[0],
        'ci95_high':ci.iloc[1],'p_value':fit.pvalues[key],
        'n_mon_promo':int(((day.monday==1)&(day.promo==1)).sum()),
        'n_mon_no_promo':int(((day.monday==1)&(day.promo==0)).sum()),
        'n_fri_promo':int(((day.monday==0)&(day.promo==1)).sum()),
        'n_fri_no_promo':int(((day.monday==0)&(day.promo==0)).sum()),
        'caveat':'Date-level observational sensitivity; potential secular time and seasonality confounding remains.'
    }])
    outdir=repo/'midterm/results';outdir.mkdir(parents=True,exist_ok=True)
    result.to_csv(outdir/'t1_date_hac_sensitivity.csv',index=False)
    day.drop(columns=['n_promo_values','n_weekday_values']).to_csv(
        outdir/'t1_date_hac_daily.csv',index=False)
    print(result.to_string(index=False))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--repo',type=Path,default=Path('.'))
    parser.add_argument('--hac-lags',type=int,default=8)
    args=parser.parse_args();run(args.repo,args.hac_lags)
