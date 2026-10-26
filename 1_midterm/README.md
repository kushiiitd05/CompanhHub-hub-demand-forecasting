# CSE558 Midterm (Monsoon 2026), group DSC 10: code and README

The report is `report/main.pdf`, built from `report/main.tex` on the official course template. Paths below are relative to `1_midterm/`.
This README covers how to reproduce every number in it, the raw-file hashes, the full data-cleaning ledger and
the list of flagged rows.

The report covers data, preparation, EDA and four hypothesis tests only. It contains no forecasting model.

## 1. Reproduce

```bash
# Python 3.11; packages: numpy pandas scipy matplotlib pyarrow pytest
python -m pip install -r requirements.txt
cd analysis
python run_all.py            # about 6 minutes on a laptop; stops at the first failing step
cd .. && pytest -q tests     # 9 unit tests
cd report && pdflatex main.tex && pdflatex main.tex   # or: tectonic main.tex
```

| Step | Script | What it writes (`results/`) |
|---|---|---|
| 0 | `00_verify.py` | `verify.csv`: 125 claimed facts recomputed from the raw CSVs (all match); `file_hashes.csv` |
| 1 | `01_prepare.py` | ledger outputs `prep_*.csv`; `derived/` (cleaned hub-day parquet, hub-level table; git-ignored, regenerated) |
| 2 | `02_tests_t1_t2.py` | `t1_*.csv`, `t2_*.csv`, `t1_t2.json` |
| 3 | `03_tests_t3_t4.py` | `t3_*.csv`, `t4_*.csv`, `t3_t4.json` |
| 4 | `04_summary.py` | `tests_summary.csv` (one row per test; Bonferroni and Holm) |
| 5 | `05_descriptives.py` | `desc_*.csv` (dependence, schedule shift, weekday lifts, week-level T1 check, reopening) |
| 6 | `06_figures.py` | `figures/*.pdf` |
| 8 | `08_audit_numbers.py` | `audit_numbers.csv`: every number in `main.tex` mapped to a table, a derived formula or a design constant |
| 7 | `07_validate.py` | the submission gate (page count, placeholders, banned words, figures, audit) |

The analysis choices for the tests were fixed in `docs/analysis_plan_r1.md`, which was committed before the test
scripts were run. `inference.py` computes each statistic both with `scipy.stats` and with the textbook formula and
checks that they agree to 4 significant figures (`agree_4sf` column).

Seeds are fixed (558) for permutations, bootstraps and placebos.

## 2. Raw files (never modified)

| File | Bytes | SHA-256 |
|---|---|---|
| `data/raw/orders_train.csv` | 32,418,040 | `bc0bf2521d2cc1912bfe97c3d2ac2c4ad17c7849e21bcae8a139a1fdf84e11b6` |
| `data/raw/hub_metadata.csv` | 47,028 | `7f65b8749b8253b7bd61975b9792e5b42574d3437d03c0283227bd32cc8fe527` |
| `data/raw/orders_test.csv` | 1,441,035 | `f8478bbe5c89986ab441987db64bf02fc520d5aaf9c85b72c0d85a972c13d5a5` |
| `data/raw/sample_submission.csv` | 363,549 | `6a045a5edb836800b1ef946cb956a8ebae432c20b9fd005243a8b00544120cfd` |

**Source:** the Shadow Hub database (training, test, hub metadata and a sample-submission file), received by our group through a private data-science competition. The files are in `data/raw/`.
**Provenance:** the files match the public Rossmann Store Sales data (<https://www.kaggle.com/c/rossmann-store-sales>)
with renamed columns. Evidence:
- 1,115 hubs;
- 970,379 + 46,830 = 1,017,209 rows;
- hubs 1 and 2 reproduce Rossmann stores 1 and 2;
- the same 180 hubs are missing in 2014-H2.

`OrderVolume` has no stated unit. Its median per app session is 9.23, so it is not a count of orders.

## 3. Full cleaning ledger (Q1-Q18)

No raw value is overwritten. Every decision adds a flag or a new column. Counts come from `verify.csv` and `prep_*.csv`.

| # | Issue (count) | Diagnosis | Decision; why, and why not the alternative |
|---|---|---|---|
| Q1 | 33,121 absent hub-dates = 180 hubs × 184 days (2014-07-01..12-31) + hub 988 on 2013-01-01 | systematic block, not random | Left absent; flag `gap_hub`; tested in T2. Zero-fill would invent closures. Mean, median, kNN or regression imputation would fabricate sales for a non-random subset (T2). |
| Q2 | 166,269 closed rows; volume = sessions = 0 in all | structural zeros | Kept; excluded from volume tests. Mixing open and closed rows gives a bimodal mixture. |
| Q3 | 54 open rows with volume 0 (41 hubs); 52 with sessions 0; 2 with sessions > 0 and volume 0 | inconsistent records | Flag `open_zero`; excluded; listed in section 4. MLE rate 6.7e-5 (Wilson CI 5.1e-5 to 8.8e-5). |
| Q4 | Pooled IQR fence on open-day volume (Q1 4,856, Q3 8,360, fence 13,616): 29,307 rows (3.64%) | 88.3% of them are at the 189 hubs whose own median is above Q3 | Not deleted; the tests use the log scale and per-hub contrasts. The fence measures hub size, not error. |
| Q5 | Per-hub robust z (median/MAD, \|z\| > 3.5, volume > 0): 6,220 rows at 1,040 hubs | 97.0% explained by calendar context (`prep_robust_z_context.csv`) | Kept as genuine demand. Example: the maximum, 38,722, is hub 262 on Good Friday 2015 with a promotion. |
| Q6 | \|z\| ≥ 2 / 3 / 4: 4.24% / 1.59% / 0.60% of open days; Chebyshev bounds 25% / 11.1% / 6.25%; normal 4.55% / 0.27% / 0.006% | heavy tails (kurtosis 7.84) | A normal 3σ rule is not used; the Chebyshev bound holds. |
| Q7 | Closure runs: 145,746 of 1 day; 9,299 of 2 days; 88 of ≥ 5 days at 85 hubs; 45 of ≥ 14 days; longest 185 | refurbishment-like | Flags `long_closure` (≥ 5 days) and `reopen_window` (14 days after). Excluded in a sensitivity rerun. Volume after reopening is 44% above before closing. |
| Q8 | Volume/sessions: median 9.23; 99.9th percentile 17.19; max 64.96 (hub 897, 2013-09-02); 23 rows > 30 | sessions under-recorded | Flag `ratio_anomaly`; kept, since no test uses sessions. |
| Q9 | `CompetitorDistance` missing for hubs 291, 622, 879 | too few to diagnose | Complete case in T3 (n = 1,112). |
| Q10 | Competitor opening date missing for 354 hubs | date not recorded | Left NA with an indicator; excluded from both T4 groups; no imputation. |
| Q11 | Loyalty start and interval NA for 544 hubs = exactly the hubs without the programme | not applicable | Level "None". |
| Q12 | Opening year 1900 (hub 815); 1961 (hub 146) | sentinel; plausible but extreme | 1900 set to NA with flag `sentinel_year`; 1961 kept. |
| Q13 | 8 hubs in 4 pairs (473/722, 651/773, 426/557, 26/436) share identical metadata | different daily series | Kept: distinct hubs. Duplicate hub-dates: 0. Duplicate rows: 0. |
| Q14 | 17 hubs open on 2013-01-01; 910 open holiday rows; 3,400 open Sunday rows at 33 hubs | genuine | Kept. T1 uses Monday and Friday only and drops holidays. |
| Q15 | Promotion never at weekends; set per date for all hubs (alternate Mon-Fri weeks) | confounded with weekday and date | Promotion compared within weekday (T1); week-level check. |
| Q16 | Last digit of volume (≥ 100) | integrity | χ²(9) = 11.10, p = 0.27: uniform, no heaping. |
| Q17 | Test window: school closure 28.5% vs 17.4% in train; no holidays | summer break; 27.6% in the same weeks of 2014 | Described only (no outcome in test). |
| Q18 | Nominal integers (`HubFormat`, `RegionalHoliday`, `Weekday`, interval) | Lecture 2 types | One-hot. Tier as ordinal code. Date split into Year/Month/Day/ISO week. log1p as an analysis scale. 970,379 × 46 = 44,637,434 (`prep_encoded_schema.csv`). |

## 4. Flagged rows

Every `open_zero` row (54), every `ratio_anomaly` row (23) and the maximum (1) are in
`results/prep_flagged_rows.csv`. The table below is generated from that file.

| flag | HubID | Date | Weekday | OrderVolume | AppSessions | PromoActive | RegionalHoliday |
|---|---|---|---|---|---|---|---|
| open_zero | 25 | 2014-02-12 | 3 | 0 | 0 | 0 | 0 |
| open_zero | 25 | 2014-02-13 | 4 | 0 | 0 | 0 | 0 |
| open_zero | 28 | 2014-09-02 | 2 | 0 | 0 | 1 | 0 |
| open_zero | 28 | 2014-09-03 | 3 | 0 | 0 | 1 | 0 |
| open_zero | 28 | 2014-09-04 | 4 | 0 | 0 | 1 | 0 |
| open_zero | 57 | 2014-07-01 | 2 | 0 | 0 | 1 | 0 |
| open_zero | 102 | 2014-07-12 | 6 | 0 | 0 | 0 | 0 |
| open_zero | 102 | 2014-07-24 | 4 | 0 | 0 | 0 | 0 |
| open_zero | 227 | 2014-09-11 | 4 | 0 | 0 | 0 | 0 |
| open_zero | 232 | 2013-01-24 | 4 | 0 | 0 | 1 | 0 |
| open_zero | 238 | 2014-07-24 | 4 | 0 | 0 | 0 | 0 |
| open_zero | 259 | 2013-02-07 | 4 | 0 | 0 | 1 | 0 |
| open_zero | 303 | 2014-07-24 | 4 | 0 | 0 | 0 | 0 |
| open_zero | 327 | 2014-03-12 | 3 | 0 | 0 | 0 | 0 |
| open_zero | 339 | 2013-01-30 | 3 | 0 | 0 | 0 | 0 |
| open_zero | 339 | 2013-01-31 | 4 | 0 | 0 | 0 | 0 |
| open_zero | 353 | 2013-03-16 | 6 | 0 | 0 | 0 | 0 |
| open_zero | 357 | 2014-09-22 | 1 | 0 | 0 | 0 | 0 |
| open_zero | 364 | 2013-05-07 | 2 | 0 | 0 | 0 | 0 |
| open_zero | 364 | 2013-05-08 | 3 | 0 | 0 | 0 | 0 |
| open_zero | 387 | 2014-07-24 | 4 | 0 | 0 | 0 | 0 |
| open_zero | 391 | 2013-08-28 | 3 | 0 | 0 | 1 | 0 |
| open_zero | 548 | 2014-09-05 | 5 | 0 | 0 | 1 | 0 |
| open_zero | 589 | 2013-04-29 | 1 | 0 | 0 | 1 | 0 |
| open_zero | 623 | 2014-01-24 | 5 | 0 | 0 | 1 | 0 |
| open_zero | 623 | 2014-01-25 | 6 | 0 | 0 | 0 | 0 |
| open_zero | 661 | 2014-04-04 | 5 | 0 | 0 | 1 | 0 |
| open_zero | 663 | 2013-09-02 | 1 | 0 | 0 | 0 | 0 |
| open_zero | 665 | 2013-06-28 | 5 | 0 | 0 | 0 | 0 |
| open_zero | 665 | 2013-06-29 | 6 | 0 | 0 | 0 | 0 |
| open_zero | 674 | 2015-03-26 | 4 | 0 | 0 | 0 | 0 |
| open_zero | 681 | 2013-05-10 | 5 | 0 | 0 | 0 | 0 |
| open_zero | 699 | 2015-02-05 | 4 | 0 | 0 | 1 | 0 |
| open_zero | 700 | 2013-06-05 | 3 | 0 | 0 | 1 | 0 |
| open_zero | 708 | 2014-10-01 | 3 | 0 | 0 | 1 | 0 |
| open_zero | 762 | 2013-01-17 | 4 | 0 | 0 | 0 | 0 |
| open_zero | 835 | 2014-09-10 | 3 | 0 | 0 | 0 | 0 |
| open_zero | 835 | 2014-09-11 | 4 | 0 | 0 | 0 | 0 |
| open_zero | 850 | 2014-03-29 | 6 | 0 | 0 | 0 | 0 |
| open_zero | 882 | 2014-07-23 | 3 | 0 | 0 | 0 | 0 |
| open_zero | 887 | 2014-07-23 | 3 | 0 | 0 | 0 | 0 |
| open_zero | 925 | 2014-07-03 | 4 | 0 | 0 | 1 | 0 |
| open_zero | 927 | 2013-08-08 | 4 | 0 | 0 | 0 | 0 |
| open_zero | 948 | 2013-04-25 | 4 | 0 | 5 | 1 | 0 |
| open_zero | 971 | 2015-05-15 | 5 | 0 | 0 | 0 | 0 |
| open_zero | 983 | 2014-01-17 | 5 | 0 | 0 | 0 | 0 |
| open_zero | 983 | 2014-01-18 | 6 | 0 | 0 | 0 | 0 |
| open_zero | 986 | 2014-03-18 | 2 | 0 | 0 | 1 | 0 |
| open_zero | 1017 | 2014-06-04 | 3 | 0 | 0 | 1 | 0 |
| open_zero | 1017 | 2014-06-05 | 4 | 0 | 0 | 1 | 0 |
| open_zero | 1039 | 2013-07-09 | 2 | 0 | 0 | 0 | 0 |
| open_zero | 1039 | 2013-07-10 | 3 | 0 | 0 | 0 | 0 |
| open_zero | 1100 | 2014-04-29 | 2 | 0 | 3 | 1 | 0 |
| open_zero | 1100 | 2014-04-30 | 3 | 0 | 0 | 1 | 0 |
| ratio_anomaly | 126 | 2013-08-28 | 3 | 20209 | 571 | 1 | 0 |
| ratio_anomaly | 126 | 2013-09-03 | 2 | 21585 | 529 | 0 | 0 |
| ratio_anomaly | 126 | 2013-09-09 | 1 | 24134 | 731 | 1 | 0 |
| ratio_anomaly | 126 | 2013-09-12 | 4 | 20701 | 562 | 1 | 0 |
| ratio_anomaly | 126 | 2013-09-16 | 1 | 16115 | 502 | 0 | 0 |
| ratio_anomaly | 126 | 2013-09-20 | 5 | 21242 | 496 | 0 | 0 |
| ratio_anomaly | 126 | 2013-09-27 | 5 | 27050 | 613 | 1 | 0 |
| ratio_anomaly | 126 | 2013-10-14 | 1 | 25049 | 475 | 0 | 0 |
| ratio_anomaly | 126 | 2013-10-17 | 4 | 18697 | 458 | 0 | 0 |
| ratio_anomaly | 126 | 2013-10-22 | 2 | 30619 | 554 | 1 | 0 |
| ratio_anomaly | 126 | 2013-10-24 | 4 | 33071 | 574 | 1 | 0 |
| ratio_anomaly | 126 | 2013-10-29 | 2 | 20295 | 474 | 0 | 0 |
| maximum | 262 | 2015-04-03 | 5 | 38722 | 5132 | 1 | 2 |
| ratio_anomaly | 897 | 2013-04-25 | 4 | 11805 | 244 | 1 | 0 |
| ratio_anomaly | 897 | 2013-05-08 | 3 | 17148 | 319 | 0 | 0 |
| ratio_anomaly | 897 | 2013-06-19 | 3 | 9687 | 238 | 1 | 0 |
| ratio_anomaly | 897 | 2013-08-16 | 5 | 17649 | 386 | 1 | 0 |
| ratio_anomaly | 897 | 2013-09-02 | 1 | 16954 | 261 | 0 | 0 |
| ratio_anomaly | 897 | 2013-09-17 | 2 | 11166 | 216 | 0 | 0 |
| ratio_anomaly | 897 | 2013-10-02 | 3 | 20167 | 467 | 0 | 0 |
| ratio_anomaly | 897 | 2013-10-11 | 5 | 16092 | 402 | 1 | 0 |
| ratio_anomaly | 897 | 2013-10-19 | 6 | 16558 | 331 | 0 | 0 |
| ratio_anomaly | 897 | 2013-10-26 | 6 | 17298 | 413 | 0 | 0 |
| ratio_anomaly | 897 | 2013-11-05 | 2 | 15991 | 353 | 1 | 0 |

## 5. Earlier version (v0) and what changed

The previous report and its scripts are kept in `2_future_work_progress/midterm_v0_archive/` for comparison. Revision r1 changed the following:
- **T1** moved to the log scale, with a placebo, a replication and a week-level check.
- **T3** changed from Spearman on raw volume (fail to reject, p = 0.29) to Pearson on log distance and log volume,
  as fixed in the plan (reject, p = 0.0063; the CI straddles the 0.10 threshold). Both are reported.
- **T4** became a difference-in-differences design with control hubs and a placebo.
- The encoded size changed from 35 to 46 attributes (8 data-quality flags were added).
