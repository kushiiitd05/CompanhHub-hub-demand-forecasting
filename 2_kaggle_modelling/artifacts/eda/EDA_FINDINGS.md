# EDA Findings and Modelling Contract

## Confirmed structure

- Training contains 970,379 rows across 1,115 hubs and 900 dates.
- Test is a complete 1,115 × 42 panel and is ordered date-major, hub-minor.
- Training ends one day before test begins.
- Metadata covers every train and test hub exactly once.

## Data-quality findings

- The training panel has 33,121 absent hub-date rows.
- 180 hubs share a 184-day missing block from 2014-07-01 through 2014-12-31; one additional hub-date is absent.
- These are unknown observations, not evidence of closure, and must never be zero-filled.
- Closed rows have zero nonzero-order violations and zero nonzero-session violations.
- Open rows contain a very small number of zero targets/sessions; retain and flag them rather than dropping them.
- Metadata nulls are structurally aligned with unavailable competitor or loyalty start information.

## Demand and traffic signal

- Mean open-day orders are 6,954.4; median open-day orders are 6,368.0.
- Mean open-day sessions are 764.2.
- Order/session Pearson correlation is 0.896 across all rows and 0.825 on open rows.
- Median historical OrderVolume/AppSessions ratio on valid open rows is 9.227.
- Open-day promotion rows average 8,216.0 orders versus 5,930.7 without promotion, a raw 38.5% difference that is descriptive rather than causal.

## Temporal and distribution shift

- Calendar-aligned hub-level lag correlations are strongest around 14, 28, and 364 days; exact values are in `tables/lag_correlations.csv`.
- Test weekday and promotion schedules closely resemble the final training window.
- School-closure prevalence changes materially in test; holiday is constant zero and therefore has no direct test-period discriminating power.
- `tables/drift_metrics.csv` reports Jensen-Shannon distance and PSI against both full history and the final 42 training days.

## Leakage contract

- For every validation origin, hide both OrderVolume and AppSessions for all 42 future days.
- Historical summaries end at the forecast origin and remain frozen across horizons 1–42.
- Forward schedule features may inspect only the supplied 42-day window and are right-censored at its boundary.
- Validation actuals are reattached only under `Actual*` names after feature construction.

## Modelling implications to validate later

- AppSessions is strongly associated with OrderVolume historically, but only historical or separately forecast sessions are legal.
- Closed test rows support a hard prediction override of zero.
- RegionalHoliday has no direct test-period variance.
- RMSLE makes log1p target diagnostics and nonnegative predictions the natural default.
- Target, session, conversion, closure phase, promotion phase, and metadata feature families should be added through the fixed CV experiment ladder.
