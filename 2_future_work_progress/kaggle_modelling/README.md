# Hub Order Demand Forecasting —

Time-series demand forecasting for 1,115 retail hubs over a 42-day horizon. Built for the
**Shadow Hub Data Science** competition, and reused here as our
group's Data Science course project. Leaderboard metric is **RMSLE**.

**Final public leaderboard score: `0.06976` RMSLE** (down from an initial baseline submission of
`0.08528`), against a local rolling-origin CV estimate of `~0.12–0.13`.

> This repo is the **actual working project** — every script, notebook, EDA artifact, trained-model
> output, and dataset file used to get that score, not a cleaned-up retelling. Read `JOURNEY.md` for
> the honest blow-by-blow (bugs, dead ends, fixes included); `SUMMARY.md` for the short official
> write-up; this file for a guided tour of what's here and how to run it.

---

## 1. Problem

Each of 1,115 hubs needs a forecast for its own contiguous 42-day test window. Two of the most
predictive signals — `OrderVolume` (the target) and `AppSessions` — are **never known ahead of
time**: for every forecast origin, both are hidden for the full 42 days ahead, exactly mirroring how
the real test set is built. That constraint, plus exact-zero rows on closed hub-days and an RMSLE
metric, drives every modelling choice below.

| | |
|---|---|
| Hubs | 1,115 |
| Training rows | 970,379 (across 900 dates) |
| Test set | Complete 1,115 × 42 panel |
| Target | `OrderVolume` (log1p-transformed for training) |
| Metric | RMSLE |
| Missing data | 33,121 absent hub-date rows; 180 hubs share a 184-day renovation gap (2014-07-01 → 2014-12-31), kept as missing history — never zero-filled |

## 2. Data

Raw competition files live in [`datset_kaggle/`](datset_kaggle/):

- `orders_train.csv` — daily hub-level orders/sessions history with calendar flags
- `orders_test.csv` — the 42-day forecast panel to predict
- `hub_metadata.csv` — per-hub format, assortment tier, competitor distance/tenure, loyalty program
- `sample_submission.csv` — submission format reference

Everything downstream (`data/processed/`, `artifacts/`) is generated from these three files — nothing
else external was used. See `data/processed/README` context in §5 below for what's cached there and
how to regenerate it.

## 3. EDA — what we found

Full findings: [`artifacts/eda/EDA_FINDINGS.md`](artifacts/eda/EDA_FINDINGS.md). Generated tables in
[`artifacts/eda/tables/`](artifacts/eda/tables/), figures in
[`artifacts/eda/figures/`](artifacts/eda/figures/), and full auto-profiling reports (YData Profiling +
Sweetviz, browsable HTML) in [`artifacts/eda/reports/`](artifacts/eda/reports/).

Highlights:

- Closed rows (`IsOpen==0`) have **zero** non-zero order/session violations — closure is a clean,
  trustworthy signal.
- Order/session correlation is strong (Pearson 0.896 overall, 0.825 on open rows) but not directly
  usable at test time since `AppSessions` isn't given for the forecast window — motivates
  history-derived conversion ratios instead of a naive two-stage sessions forecast.
- The 180-hub, 184-day renovation gap needed explicit cohort handling (flag + days-since-reopening
  ramp) rather than being dropped or zero-filled.

## 4. Feature engineering (leakage-safe by construction)

Built in [`src/eda_pipeline.py`](src/eda_pipeline.py). For **every** forecast origin — train or test —
a frozen 42-day forecast table is built from strictly-prior history:

- **History-only rolling aggregates**: mean/median/std/trend of `OrderVolume` and `AppSessions` over
  7/28/56/84/90/180/182/365/730-day windows, computed before the origin only.
- **Legal target lags**: 7/14/28/42/364/728-day lags, each with an `_Available` flag so the model can
  learn to fall back when a lag isn't legally observable at that horizon.
- **Conversion / volume-per-session ratios**: history-derived, so the sessions signal is exploited
  without ever peeking at future sessions.
- **Day-counters**: streak-length / days-since / days-until for `Open`, `PromoActive`,
  `RegionalHoliday`, `SchoolClosureFlag` — right-censored at the visible schedule boundary.
- **Renovation cohort**: explicit flag + reopening ramp for the 180-hub gap.
- **Metadata**: hub format, assortment tier, loyalty program refresh-month flags, competitor
  distance/tenure — missing-indicator + neutral-fill throughout (missing is informative here, e.g.
  "no known competitor").

**347 engineered columns per forecast origin.**

The leakage contract (from `README` history, kept verbatim since it's load-bearing):

- Both `OrderVolume` and `AppSessions` are hidden for every 42-day validation block.
- Historical state is frozen at each forecast origin.
- Forward schedule features only inspect the visible 42-day schedule.
- Missing hub-date observations stay missing history, never become zero.
- Validation targets are attached only *after* feature generation, under `Actual*` names.

## 5. Modelling & validation

Modelling code: [`src/model_pipeline.py`](src/model_pipeline.py).

- **Validation**: rolling-origin CV, 4 folds (2015-01-02 / 02-13 / 03-27 / 05-08), each scored on its
  own frozen 42-day block. A purge/embargo gap equal to the full 42-day label window keeps any
  training row's feature window from overlapping a validation label window.
- **Family**: gradient-boosted trees on `log1p(OrderVolume)`. Raw categoricals fed natively to
  CatBoost/LightGBM plus an out-of-fold-style smoothed target encoding of `HubID`.
- **Closed-row handling**: dropped from training, hard-set to exactly 0 at inference.
- **Ensemble**: CatBoost (depth 8, 1,500 iters) + LightGBM (63 leaves, 3,000 iters) + LightGBM/Tweedie
  (`variance_power=1.1`, for the zero-inflated right-skewed target). Each model's log-space bias is
  corrected with an additive offset fit on its own residuals, then combined via a **log-space
  (geometric) mean** — the RMSLE-correct analogue of the RMSPE literature's harmonic-mean trick.

### Results

| Model | Local CV RMSLE (pooled) | Public leaderboard |
|---|---|---|
| Hierarchical mean baseline | ~0.144 | — |
| CatBoost, full feature set | ~0.130 | — |
| CatBoost + LightGBM, log-mean blend + offset | ~0.123 | — |
| CatBoost, full-history retrain (single model) | — | 0.08528 |
| **Target-encoded HubID + CatBoost + LightGBM + LightGBM-Tweedie, log-mean ensemble** | — | **0.06976** |

Raw metrics/OOF predictions/submissions: [`artifacts/models/`](artifacts/models/). The CV-vs-leaderboard
gap (favorable direction, larger than expected) is flagged as an open question in `SUMMARY.md` rather
than assumed to be free improvement — most likely explanation is the CV folds sitting in a harder,
sparser stretch of history (adjacent to the renovation gap) than the test window.

## 6. What we tried and what failed

The full account — including three separate "crash" root-causes (stale Parquet schema after a feature
change, a `status` shell reserved-word collision, a subprocess `PYTHONPATH` gap), the Kaggle-kernel
iteration failures (hardcoded paths, missing `PYTHONPATH` in subprocesses, a `str`-vs-`Path` bug), and
why the ensembling idea was validated for free on cached OOF predictions before spending an hour of
Kaggle compute on it — is in **[`JOURNEY.md`](JOURNEY.md)**. Worth reading before repeating any of it.

Research consulted mid-project (Rossmann 1st-place writeup, entity embeddings, M5's Tweedie/LightGBM
findings, Montero-Manso & Hyndman on global models, Duan smearing): most of what it recommended was
already implemented; the two genuinely new levers it contributed were `HubID` target encoding and the
Tweedie-objective LightGBM.

## 7. Repo structure

```
datset_kaggle/          raw competition CSVs (train, test, hub metadata, sample submission)
data/processed/         generated feature tables — training origins, CV folds, test features
                         (regenerate from raw CSVs, see §8; kept here so the group doesn't
                         have to re-run a ~50min pipeline just to inspect results)
artifacts/eda/          EDA findings doc, figures, tables, YData/Sweetviz HTML reports
artifacts/models/       walk-forward CV metrics, OOF predictions, final submissions
src/                    eda_pipeline.py (audit→preprocess→folds→reports),
                         model_pipeline.py (walk-forward CV harness, CatBoost/LightGBM fitters)
scripts/                submission builders + the Kaggle-kernel-ready end-to-end pipeline
                         (scripts/kaggle_kernel/, scripts/kaggle_final/) used for the final run
notebooks/               exploratory scaffolding (01–05); NOT the source of truth — the
                         authoritative, reproducible pipeline is src/ + scripts/kaggle_kernel/
tests/                   leakage/contract tests for the EDA pipeline
README.md               this file — guided tour
SUMMARY.md              short official competition write-up (approach/validation/results)
JOURNEY.md              full honest project history — debugging, research, dead ends
```

## 8. Reproducing it

Uses the `eda311` conda environment from the project root.

```bash
# Full EDA + feature pipeline (audit → preprocess → build folds → reports), ~50 min
MPLCONFIGDIR=/tmp/kaggle_comp_mpl XDG_CACHE_HOME=/tmp/kaggle_comp_cache \
  conda run -n eda311 python -m src.eda_pipeline all

# Individual stages: audit | preprocess | build-folds | reports
# Add --skip-automated to reports/all to skip YData Profiling + Sweetviz

# Leakage/contract tests
MPLCONFIGDIR=/tmp/kaggle_comp_mpl XDG_CACHE_HOME=/tmp/kaggle_comp_cache \
  conda run -n eda311 python -m unittest discover -s tests -v

# Walk-forward CV / model training
conda run -n eda311 python -m src.model_pipeline walk-forward --feature-group all --backend both
```

The exact end-to-end pipeline (raw CSVs → features → trained ensemble → submission) that produced the
final `0.06976` score runs standalone as a Kaggle kernel from
[`scripts/kaggle_kernel/kaggle_end_to_end.py`](scripts/kaggle_kernel/kaggle_end_to_end.py) — no manual
steps once started. All randomness is seeded with the single disclosed value `20260807`.

## 9. Team / how to work in this repo

Shared privately with the group for our Data Science course project (originally solo Kaggle work,
70–80% of it done before the group picked it up). If you're extending this:

- Read `JOURNEY.md` first — it'll save you re-discovering bugs already fixed.
- `src/eda_pipeline.py` and `src/model_pipeline.py` are the source of truth; the `notebooks/` are
  unexecuted scaffolding, don't treat them as documentation of what actually ran.
- New experiments → new script under `scripts/` or a fold onto `model_pipeline.py`; keep the leakage
  contract in §4 intact (run `tests/` before trusting any change).
- Large generated files (`data/processed/`, `artifacts/`) are committed so everyone can inspect results
  without re-running the pipeline — if you regenerate them, expect a large diff, that's normal.

## 10. Competition links

Private per competition rules (visible to reviewers granted access):
- Pipeline kernel: `kaggle.com/code/kushtokas/solari-full-pipeline`
- Write-up notebook: `kaggle.com/code/kushtokas/solari-writeup`
