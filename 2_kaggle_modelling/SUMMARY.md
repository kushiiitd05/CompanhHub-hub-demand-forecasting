# Hub Order Forecasting — Approach, Validation, and Findings

**Competition:** CH'27 — Celebal Technologies × IIITD hub order forecasting (42-day horizon, RMSLE)
**Author:** Kush Tokas · **Fixed seed (disclosed):** `20260807`
**Environment:** Python 3.11.13, pandas 2.3.3, numpy 1.25.2, scikit-learn 1.7.2, CatBoost 1.2.10, LightGBM 4.7.0

## 1. Problem framing

Each of 1,115 hubs must be forecast for a contiguous 42-day test window. Two target-adjacent
signals — `OrderVolume` and `AppSessions` — are only ever known as *history*: for every forecast
origin (train or test), both are hidden for the full 42-day window ahead, mirroring exactly how the
real test set is constructed. The evaluation metric (RMSLE) and the presence of exact-zero rows on
closed hub-days shaped every downstream choice.

## 2. Data audit (summary)

- 970,379 training rows across 1,115 hubs and 900 dates; test is a complete 1,115×42 panel.
- 33,121 absent hub-date rows in training; 180 hubs share a 184-day missing block
  (2014-07-01 to 2014-12-31) — retained as missing history, never zero-filled.
- Closed rows (`IsOpen==0`) have zero non-zero order/session violations — closure is a clean signal.
- Order/session Pearson correlation: 0.896 overall, 0.825 on open rows — strong but not
  test-time-usable directly (`AppSessions` isn't given for the test window).
- Full findings: `artifacts/eda/EDA_FINDINGS.md`.

## 3. Leakage-safe feature construction

For every forecast origin (train or test), a frozen 42-day forecast table is built (`src/eda_pipeline.py`):

- **History-only aggregates**: rolling mean/median/std/trend of `OrderVolume` and `AppSessions`
  over 7/28/56/84/90/180/182/365/730-day windows, split by open/all/present-count, computed strictly
  before the origin.
- **Legal target lags**: 7/14/28/42/364/728-day lags, each with an `_Available` flag so the model can
  learn to fall back when a lag isn't legally observable at that horizon.
- **Conversion & volume-per-session ratios**: history-derived `OrderVolume/AppSessions` ratios —
  the safe way to exploit the sessions signal without ever seeing future sessions (per Rossmann
  precedent: naive two-stage session forecasting risks compounding two error sources).
- **Day-counters**: streak length / days-since / days-until for `Open`, `PromoActive`,
  `RegionalHoliday`, `SchoolClosureFlag`, all right-censored at the visible schedule boundary.
- **Renovation cohort**: explicit flag + days-since-reopening ramp for the 180-hub missing block.
- **Metadata**: `HubFormat`, `AssortmentTier`, `LoyaltyProgram`/interval-derived refresh-month flags,
  competitor distance (log1p) and tenure, all with missing-indicator + neutral-fill (missing here is
  informative, e.g. "no known competitor").
- 347 total engineered columns per origin table.

## 4. Model

- **Family**: gradient-boosted trees on `log1p(OrderVolume)`. Rejected PCA on the (categorical,
  high-missingness) metadata table in favour of feeding raw categoricals natively to CatBoost/LightGBM,
  plus an out-of-fold-style smoothed **target encoding** of `HubID` (`sklearn.TargetEncoder`,
  `smooth="auto"`).
- **Closed-row handling**: dropped from training entirely; hard-set to exactly 0 at inference
  (`IsOpen==0`).
- **Ensemble**: CatBoost (depth 8, 1,500 iters) + LightGBM (63 leaves, 3,000 iters) + LightGBM with a
  Tweedie objective (`variance_power=1.1`, suited to the zero-inflated, right-skewed target). Each
  model's log-space bias is corrected with an additive offset fit on its own training residuals, then
  the three corrected predictions are combined via a **log-space (geometric) mean** — the RMSLE-correct
  analogue of the RMSPE literature's harmonic-mean/0.985-multiplier trick.

## 5. Validation design

Rolling-origin CV with four validation folds (2015-01-02, 2015-02-13, 2015-03-27, 2015-05-08), each
scored on its own frozen 42-day block. For every fold, only training origins whose 42-day target
window ends **at or before** the validation origin are eligible — a purge/embargo gap equal to the
full label window, preventing any training row's feature-computation window from overlapping the
validation label window. RMSLE is reported both pooled ("all") and per 7-day horizon bucket.

## 6. Results

| Model | Local CV RMSLE (pooled) | Public leaderboard |
|---|---|---|
| Hierarchical mean baseline | ~0.144 | — |
| CatBoost, full feature set | ~0.130 | — |
| CatBoost + LightGBM, log-mean blend + offset | ~0.123 | — |
| CatBoost (full history retrain, single model) | — | 0.08528 |
| Target-encoded HubID + CatBoost + LightGBM + LightGBM-Tweedie, log-mean ensemble | — | **0.06976** |

The gap between local rolling-origin CV (~0.12-0.13) and the public leaderboard (~0.07-0.09) is larger
than expected in the favorable direction, most likely because the CV folds intentionally sit in a
harder, sparser stretch of history (adjacent to the 180-hub renovation gap) than the test window.
This is flagged as an open question rather than assumed to be free improvement.

## 7. Reproducibility

Entire pipeline (raw CSVs → engineered features → trained models → submission) runs end-to-end from
only the competition's provided files, with no external data, no manual steps once started, via
`scripts/kaggle_kernel/kaggle_end_to_end.py` — pushed and executed as a Kaggle kernel:
`kaggle.com/code/kushtokas/solari-full-pipeline`. All randomness (`CatBoostRegressor`, `LGBMRegressor`,
`TargetEncoder` validation split) is seeded with the single disclosed value `20260807`. This kernel run
(version 3) is the artifact behind the final submitted score of 0.06976.

**Links** (private — visible to reviewers granted access, per competition rules against public sharing):
- Pipeline kernel: `kaggle.com/code/kushtokas/solari-full-pipeline`
- This write-up as a notebook: `kaggle.com/code/kushtokas/solari-writeup`
