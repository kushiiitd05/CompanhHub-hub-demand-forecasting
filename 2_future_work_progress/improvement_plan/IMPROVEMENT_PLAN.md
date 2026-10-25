# Improvement Plan: Hub Order Forecasting (CH'27 Celebal × IIITD)

Written 2026-10-17. Current public LB: **0.06976** (CatBoost + LightGBM + LightGBM-Tweedie, log-mean blend).
Target: **< 0.06** public LB, gated by local CV.

This plan covers the Kaggle model only. The CSE558 midterm report is separate and has no models
(see `~/Desktop/Dsc/dsc proj/MASTER_PROMPT_CSE558_Midterm.md`).

---

## 1. Audit findings (measured on the saved OOF predictions, 2026-10-17)

| # | Finding | Evidence | Where |
|---|---|---|---|
| F1 | **Models under-predict.** Mean log residual (pred − actual) on open days with volume > 0 is −0.028 / −0.080 / −0.068 on folds 2 / 3 / 4. | Bias² is 5% / 24% / 24% of the fold MSE. Removing the bias alone gives fold 3 0.163 → 0.142, fold 4 0.140 → 0.122. | `walk_forward_all_oof.csv.gz`, `lightgbm_all` |
| F2 | **The bias correction is a no-op.** `c` is the mean of the *training* residuals, which is ≈ 0 by construction for an RMSE fit. | `catboost_all` and `catboost_all_corrected` are both 0.1451 on fold 1. | `src/model_pipeline.py` `walk_forward_models`; `scripts/kaggle_kernel/kaggle_end_to_end.py` |
| F3 | **The submitted 3-model ensemble was validated on fold 1 only**, and there it lost to LightGBM alone (0.1288 vs 0.1250). Equal weights were never tested. | `walk_forward_all_catboost_lightgbm_lightgbm_tweedie_metrics.csv` has fold 1 only. | `artifacts/models/` |
| F4 | **The walk-forward crashes on folds 2–4.** The training-origin parquet files are stale: they lack `DayBeforeClosed`, which the fold tables have. | `walk_forward.log`: `ArrowInvalid: No match for FieldRef.Name(DayBeforeClosed)` | `data/processed/training_origins/*.parquet` |
| F5 | **The HubID target encoding leaks.** `TargetEncoder.fit(X, y).transform(X)` skips the cross-fitting that `fit_transform` does, so each training row is encoded with its own target. | The scikit-learn docs say the two calls differ and recommend `fit_transform` for training data. | `walk_forward_models`, kernel |
| F6 | **Early stopping is on the wrong data.** In CV it stops on the validation fold itself, so CV is optimistic. In the final kernel it stops on `train.sample(frac=0.05)`, which is in-sample, so the stopping point is arbitrary. | Code read. | `fit_*` functions, kernel |
| F7 | **Single rows dominate fold scores.** One open-but-zero row is about 10% of a fold's MSE (folds 1, 2, 4). The top 50 rows are 5–23%. | OOF decomposition. | — |
| F8 | **Per-hub bias is unstable** (correlation 0.13 for fold 2 → 3, 0.51 for fold 3 → 4; SD ≈ 0.04). Per-hub correction would overfit, so use a global correction only. | OOF decomposition. | — |
| F9 | **The bias holds at every horizon** (weeks 1–6: −0.087, −0.066, −0.078, −0.023, −0.044, −0.053). It is a level problem, not a horizon problem. | OOF decomposition. | — |

Most likely cause of F1: volume trends upward and tree models cannot extrapolate past the target
range they were trained on. The Rossmann winner hit the same problem and fixed it with a ridge trend
adjustment (see §2).

---

## 2. Research consensus

| Question | Consensus | Confidence | Source |
|---|---|---|---|
| What wins tabular retail forecasting? | Global GBDT (one model over all series) with heavy feature engineering. M5 top entries mostly used LightGBM; NNs (N-BEATS, seq2seq) were secondary. | High | M5 findings (Makridakis et al. 2022); Bojer & Meldgaard 2020 |
| How do GBDTs handle trend? | They cannot extrapolate. The Rossmann winner added a ridge-regression trend adjustment on top of XGBoost. | High | Bojer & Meldgaard 2020 review |
| Ensembles? | Global ensembles beat local single models. Gains come from members that make *different* errors. | High | Bojer & Meldgaard 2020 |
| Entity embeddings? | Rossmann 3rd place: an MLP with learned store/day embeddings, competitive with GBDT and useful in a blend. | Medium-high | Guo & Berkhahn 2016 |
| Time-series foundation models? | Chronos-2 handles past and known-future covariates (including categorical) zero-shot and uses Rossmann as its in-context example. No published head-to-head against a tuned LightGBM on retail daily data was found. | Medium (vendor paper) | Chronos-2 paper (arXiv 2510.15821); Decathlon/AWS case study |
| Target encoding | Use `fit_transform` (cross-fitted) on train and `transform` on validation/test. | High (official docs) | scikit-learn TargetEncoder docs |
| External data | Rossmann top teams used state mapping, weather and Google Trends. **Off-limits here** unless the competition rules allow outside data. | — | Rossmann forum lore |

### Does TabTune (Lexsi-Labs/TabTune) help?

Mostly no.

- **Tabular foundation models (TabPFN, TabICL, Mitra, …):** no. These models learn from examples held in context. We have about 804k open training rows per refit, and the one documented row limit (EXAONE) subsamples to 100k. A panel with strong hub identity and seasonality favours our GBDT.
- **`TimeSeriesPipeline` → Chronos-2:** maybe, as a convenience wrapper. It supports past and known covariates, including categorical, with an 8,192-step context (our history is about 900 days). Calling Amazon's `chronos-forecasting` package directly does the same with fewer dependencies, so use the wrapper only if it saves time.
- **ShiftEvaluator / calibration / fairness modules:** not needed. We already validate on time-ordered folds, and calibration does not change RMSLE.
- **Cost:** Python 3.10+ and PyTorch 2.6+, an A100 job, no tagged releases. Pin a commit if used.

---

## 3. Gate rule (applies to every change)

A change is **kept** only if:

1. mean CV RMSLE over all folds improves by **≥ 0.002**, **and**
2. it improves on **at least 3 of the 5 folds** (§4, step 0.3 adds the fifth), **and**
3. the improvement still holds with open-but-zero rows removed (F7).

Log each experiment as one row in `artifacts/models/experiments.csv`: `date, change, fold1..fold5,
mean, mean_excl_open0, kept`. Never decide on the public LB. It is a subset of the test set and is
easy to overfit.

**Integrity:** the true test labels are public (the last six weeks of Rossmann `train.csv`). Never use
them for training, tuning or checking.

---

## 4. Phased plan

### Phase 0: Make CV trustworthy (Mac, about 1 day). Do this first, since everything else depends on it.

| Step | Change | File / function |
|---|---|---|
| 0.1 | Rebuild the training origins so their schema matches the folds (fixes F4). | `python -m src.eda_pipeline build-training-origins --root .` |
| 0.2 | Add a schema assertion in `load_origin_training`: every requested column must exist in each parquet, with a clear error naming the missing column. | `src/model_pipeline.py` |
| 0.3 | Add a **season-matched fold**, origin `2014-06-19` (window 2014-06-20 → 07-31, the same calendar as the test). Score it only on rows with actuals. The 180 gap hubs drop out after 2014-07-01, so it scores mostly the 935 non-gap hubs; report that row count. *(This replaces the earlier 2013 suggestion: a 2013 origin has no eligible training origins and no 364-day lags.)* | `FOLD_ORIGINS` in `src/eda_pipeline.py`; `metric_rows` must mask missing actuals |
| 0.4 | Fix the target encoding: `train["HubID_TargetEncoded"] = encoder.fit_transform(...)` on the training open rows; `transform` for validation/test. Closed training rows get `transform`. | `walk_forward_models`, kernel |
| 0.5 | Fix early stopping. In CV, carve the *last training origin* out as the early-stopping set, never the validation fold. Record `best_iteration` per fold. In the final kernel, train for a fixed `n_estimators = median(best_iteration) × 1.1`, with no eval set. | `fit_catboost`, `fit_lightgbm`, `fit_lightgbm_tweedie`, kernel |
| 0.6 | Add `rmsle_excl_open0` and bias (mean log residual on open rows) to `metric_rows`. | `metric_rows` |
| 0.7 | Re-run the **full** 3-model walk-forward on all 5 folds. This becomes the new baseline row in `experiments.csv`. | `python -m src.model_pipeline walk-forward --backend both --folds 1,2,3,4,5` |
| 0.8 | **Check that CV agrees with the LB.** We have two LB points: CatBoost full-history single = 0.08528 and the 3-model ensemble = 0.06976. Run both configs through the fixed CV. If CV does not rank them the same way, the gate rule (§3) can't be trusted: stop and investigate before Phase 1. Also add a "kernel-mirror" CV mode that trains exactly as the final kernel does (all eligible origins, fixed iterations), because the CV and kernel configs differ today. | `walk_forward_models` flag `--mirror-kernel` |
| 0.9 | **Write the tests first** (TDD): (a) the encoded training values differ from `fit().transform()` and are not each row's own target; (b) the origin-parquet schema contains every fold column; (c) the detrend round-trip `expm1(log1p(V) − log1p(L) + log1p(L)) == V`; (d) closed rows predict exactly 0; (e) no fold's training origin has `target_end > validation_origin`. | `tests/test_model_pipeline.py` |

Expected effect: CV gets *slightly worse*, because the optimism from F5 and F6 is gone. That is the honest baseline.

### Phase 1: Remove the level bias (Mac, 1–2 days). Biggest expected gain.

| Step | Change | Detail |
|---|---|---|
| 1.1 | **Predict relative to the hub's recent level.** `L = Orders_90D_MedianOpen`, falling back to `Orders_180D_MedianOpen` → `Orders_365D_MedianOpen` → `HistHubDOWOrdersMean`. Train on `y' = log1p(V) − log1p(L)` and predict `V̂ = expm1(ŷ' + log1p(L))`. Keep the raw-level features as inputs too. | `L` is computed only from history before the origin, so no leakage. For Tweedie, keep a raw-scale target and pass `init_score = log(L)` (LightGBM offset). |
| 1.2 | **Bias offset from held-out predictions.** Replace the training-residual `c` with the mean log residual from the two most recent folds' predictions, one global constant per model. Apply it to the test. | Fixes F2. Re-measure after 1.1, because the bias may mostly be gone by then. |
| 1.3 | **Recency weights.** `sample_weight = 0.5 ** (days_between(origin, validation_origin) / H)`, trying `H ∈ {180, 365}`. | Both CatBoost and LightGBM accept `sample_weight`. |
| 1.4 | *(Optional, if 1.1 leaves a residual trend)* **Per-hub ridge trend**, Rossmann-winner style. Fit `log V ~ t + weekday` per hub on the last 365 open days before the origin and extrapolate into the window as feature `TrendPred`, or use it as the base level `L`. | Watch the gap hubs: fit on available days only. |

Expected effect: measured bias² is 5–24% of the fold MSE. If 1.1–1.3 remove most of it, a CV drop of
roughly 3–12% per fold is plausible. This is an estimate, not a promise.

### Phase 1b: Rossmann-winner features we are missing (research 2026-10-17, primary sources)

Ranked by expected gain against the level bias. Each one goes through the gate rule.

| Step | Technique | How to add it | Leakage risk |
|---|---|---|---|
| 1b.1 | **Per-hub ridge trend prediction as a feature** (1st place: "the best of both worlds"; 26th place called it "crucial"). Our `_OpenTrend` is only a slope, fitted against row position rather than calendar day, on raw values, with no weekday or promo controls. | `add_ridge_trend()` in `build_forecast_frame`: fit `log1p(V) ~ day number + weekday + promo` per hub on open rows over the last 91 and 365 days before the origin. Output `Ridge91_Pred` and `Ridge365_Pred` per target date, plus the ratio to `Orders_90D_MedianOpen`. Require a minimum row count (gap hubs). | Low |
| 1b.2 | **Training origins drop summer 2014.** `build_training_origins` keeps only full 46,830-row blocks, so every origin from 2014-05-18 to 2015-01-02 is dropped, and the test season (summer) is missing from training. | Accept incomplete blocks (the 935 hubs that have data). Optionally add a model trained only on windows overlapping May–Sep (the 1st place did this). | Low; keep `target_end ≤ validation origin` |
| 1b.3 | **Recent-window weekday × promo (× school-closure) medians.** `_conditional_history` uses all history back to 2013, so it trails growth by a year or more. | Add a `window` argument (91, 182, 365), medians alongside means, and a `SchoolClosureFlag` split. | Low |
| 1b.4 | **Bias correction fitted on held-out data** (1st place picked his factor on the holdout; 4th place regressed actual on predicted). | Same as 1.2: `log1p(y) ≈ a + b·ŷ` on stacked fold OOF predictions. **For RMSLE the correction goes up, not down**: the 0.985/0.995 multipliers were for RMSPE and do not transfer. | None if fitted on OOF only |
| 1b.5 | **Holiday and school-closure counts for this, last and next week, plus the nearest one within ±7 days.** | Rolling sums in `_visible_future_schedule_features`. | Low |
| 1b.6 | **Hub ratio features:** promo lift, Saturday/weekday ratio, holiday ratio, school-closure share, open share. | Add to `historical_state`. | Low |
| 1b.7 | **Long-closure (refurbishment) counters per target date**: days until or since a closure of 3+ days that is not a Sunday or holiday. `DaysUntilInactive` currently fires on Sundays, and `DaysSinceRenovationReopen` is constant per origin. | `_schedule_features_for_group` | Low |
| 1b.8 | **Region proxy:** group hubs whose `RegionalHoliday` and `SchoolClosureFlag` dates are identical (about 12 groups), then add region-level mean, trend and ridge prediction (4th place). | `hub_region_clusters()` merged on HubID. **Check the rules first:** it uses only competition columns, but it effectively recovers the state. | Low |
| 1b.9 | **Ensemble diversity:** random feature subsets with `colsample ≈ 0.3` (1st place's biggest ensemble gain). **Bug:** our LightGBM `subsample=0.85` does nothing without `subsample_freq > 0`. | `fit_lightgbm` | Selection overfits if done on scored folds |
| 1b.10 | **Per-HubFormat models blended with the global one** (23rd/33rd place: per-store 0.113 vs global 0.120; M5 winner used store-level models). | Group loop in `walk_forward_models` | Low |

Off-limits (external data): weather, Google Trends, state mapping, holiday CSVs, store coordinates.
Sources: [1st-place documentation (PDF)](https://storage.googleapis.com/kaggle-forum-message-attachments/102102/3454/Rossmann_nr1_doc.pdf) ·
[1st-place thread](https://www.kaggle.com/c/rossmann-store-sales/discussion/18024) ·
[solutions thread](https://www.kaggle.com/c/rossmann-store-sales/discussion/17896) ·
[entity embeddings](https://arxiv.org/abs/1604.06737) ·
[M5 A1 code](https://github.com/Mcompetitions/M5-methods/tree/master/Code%20of%20Winning%20Methods/A1)

### Phase 2: Make the ensemble earn its place (Mac, about 1 day)

| Step | Change |
|---|---|
| 2.1 | Average 3 seeds per backend (seed = `SEED + k`). |
| 2.2 | Fit blend weights on the stacked fold predictions in log space, with weights ≥ 0 that sum to 1 (`scipy.optimize.nnls`, then normalise). Use leave-one-fold-out to check the weights generalise. Drop any member whose weight is about 0. |
| 2.3 | Compare against single-best LightGBM. Keep the blend only if it passes the gate (F3). |
| 2.4 | **Light hyperparameter search** (Optuna, at most 40 trials per backend), scored on folds 3–5 only, after Phase 1. Search `num_leaves`, `min_child_samples`, `learning_rate`, `l2`, `colsample`. The gate rule applies to the best trial, re-checked on folds 1–2, which the search never saw. |

### Phase 3: Diverse members (A100). **Connect the FortiClient VPN before starting.**

| Step | Member | Notes |
|---|---|---|
| 3.1 | **Chronos-2 zero-shot** with known-future covariates `IsOpen, PromoActive, SchoolClosureFlag, RegionalHoliday` and past target `log1p(OrderVolume)` | Run it for every training origin plus the folds and the test, so it can be (a) a blend member and (b) a feature `Chronos2Pred` for the GBDT. About 39 origins × 1,115 series fits on one A100. Check how it handles the 184-day gap (NaN context); if unsupported, fill with the hub weekday median and add a mask covariate. Use `chronos-forecasting` directly; TabTune `TimeSeriesPipeline` is the fallback. |
| 3.1b | **TabPFN-TS (v2 weights, which allow commercial use)** on 8–10 origins first | Best model on fev-bench `rossmann_1D` (WAPE 0.100 vs Chronos-2 0.120 vs generic LightGBM 0.113). Learns like a tabular model, so its errors should differ from both the GBDTs and Chronos-2. It costs about 17.5 min per origin (about 11 h for all 39), so start with a subset. Accepts known-future covariates only. |
| 3.2 | **Global NN** (`neuralforecast`: TiDE or NHITS with `futr_exog_list` for the same 4 covariates, `stat_exog` from hub metadata), trained on the Phase 1 detrended target | A different inductive bias from trees, which is good for the blend. Skip TFT: on fev it took about 1 h per task and scored WAPE 0.269. |

**Phase 3 research notes (2026-10-17, fev-bench and the chronos-forecasting source):**

- **Chronos-2 setup:**
  - pin `chronos-forecasting==2.3.0` (or 2.3.2);
  - load with `Chronos2Pipeline.from_pretrained("amazon/chronos-2")`;
  - call `predict_df(df, future_df=…, prediction_length=42, quantile_levels=[0.1,0.5,0.9], cross_learning=False)`;
  - columns that appear in both `df` and `future_df` are treated as known-future; pass `RegionalHoliday` as a string so it is treated as categorical.
- **Reindex to a full daily calendar first.** The library does not check for missing dates, so the 184-day hole would be silently squeezed out and the weekly pattern would no longer line up. Fill the gap's target with NaN, which the model masks. A/B against cutting the 180 gap hubs' context to start at 2015-01-01.
- **Closed days:** give the target as NaN in the context, keep `IsOpen` as a known covariate, and force the forecast to 0 where `IsOpen = 0`. Check against feeding raw zeros on 3–4 origins.
- **Target:** feed `log1p(OrderVolume)` and use the 0.5 quantile. Add `DayOfWeek` and the event-distance features as covariates; Chronos-2 makes no calendar features itself.
- **Cost:** about 10 s per origin for all 1,115 series, so all 39 origins take roughly 7 min.
- **Fine-tuning (LoRA available):** zero-shot first, since no published retail evidence shows fine-tuning wins. If you fine-tune, refit per expanding fold, or the OOF predictions leak.
- **Leakage:** cut `df` at each origin, covariate history included. Group the stacking CV by origin. **Never load fev's `rossmann_1D` or Kaggle Rossmann data: they contain our test answers.**
- **Expectation:** Chronos-2 alone will probably score worse than 0.0698. Its value is variety in the blend, judged by the gate rule.
| 3.3 | **Entity-embedding MLP** (Guo & Berkhahn): embeddings for HubID, weekday, month, day of month, promo and holiday, plus the top 50 GBDT features | The Rossmann 3rd-place approach. |
| 3.4 | Re-run Phase 2 blending with the new members. | Gate rule applies. |

### Phase 4: Error analysis loop (Mac, runs alongside Phases 1–3)

After each kept change, regenerate:

- RMSLE and bias by `HubFormat`, `AssortmentTier`, weekday, horizon week, gap-hub flag, reopen window (14 days after a closure of 14+ days), and the days before and after a holiday;
- the 20 worst hubs and the 50 worst rows, each checked by eye against the calendar.

A segment-level bias that is stable across folds (unlike F8) justifies a targeted feature, not a
per-hub hack.

**Feature pruning:** run permutation importance on the fold predictions (LightGBM, fold 4 and
fold 5). Drop features whose importance is ≤ 0 on both folds, then re-run the gate. 347 columns is
a lot of noise, and fewer columns also eases the memory limit (§5).

### Phase 5: Final submission

1. Retrain on all origins with the chosen config, a fixed iteration count (0.5), held-out-prediction offsets (1.2) and blend weights (2.2).
2. Run sanity checks:
   - closed rows exactly 0;
   - no NaN or negative values;
   - `Id` order matches `sample_submission.csv`;
   - the distribution of test predictions is close to the last 42 training days (ratio of means within ±10%).
3. Push the Kaggle kernel and record the version number, config hash and data SHA-256 in `SUMMARY.md`.
4. Pick final submissions by **CV**, not by the public LB. If the competition lets you select two
   final submissions, choose (a) the CV-best config and (b) a conservative one (the current
   0.06976 config with only the Phase 0 fixes). That hedges against the public/private split.
5. **LB probe budget:** check the daily submission limit in the rules. Use at most one probe per
   kept phase (0, 1, 2, 3); probes check CV agreement and never choose configs.

---

## 5. Compute, workflow and rollback

- **Memory risk on the 8 GB Mac:** 37 origins × 46,830 rows × 347 columns is about **4.8 GB as
  float64** before CatBoost and LightGBM make their own copies. Fixes:
  - downcast numeric features to float32 at load time (about 2.4 GB);
  - read only the selected columns;
  - after pruning (Phase 4), fewer columns.
- **Where to run:**
  - single-fold experiments on the Mac;
  - full 5-fold × 3-model × 3-seed runs on the Kaggle kernel (CPU sessions have far more RAM than the Mac) or on vinayak-server (VPN first).
  - Run long jobs in the background and log with `tee`.
- **Git:**
  - tag the current state `lb-0.06976` before any change (rollback point);
  - work on branch `improve/phase-N`, one commit per file (conventional commits);
  - merge a phase only when its gate passes.
- **Reproducibility:** each experiment row records the git commit, config JSON and data SHA-256 (already in `training_origin_manifest.csv`).
- **Time-box:** the competition deadline is not recorded here. Fill it in: `DEADLINE = <<FILL>>`.
  If time runs short, do Phase 0 → 1 → 5 and skip Phases 2–3.

## 5b. Run commands (Mac, `eda311` env)

```bash
cd ~/Desktop/Kaggle_comp_clebal
PY=/opt/anaconda3/envs/eda311/bin/python

# Phase 0
$PY -m src.eda_pipeline build-training-origins --root .
$PY -m src.eda_pipeline build-folds --root .          # after adding the 2014-06-19 fold
$PY -m pytest tests -q
$PY -m src.model_pipeline walk-forward --backend both --folds 1,2,3,4,5 2>&1 | tee walk_forward.log

# each later experiment: same walk-forward command, then append a row to artifacts/models/experiments.csv
```

### Server runbook (vinayak-server, for full runs and Phase 3)

Not run yet; this is for later.

1. Connect the FortiClient VPN (IIITD) and confirm the server is up.
2. Set up the project folder and copy everything except data:
   ```bash
   ssh vinayak-server 'mkdir -p /home/vinayak23597/Kush/celebal_improve'
   rsync -av --exclude data/processed --exclude .git ~/Desktop/Kaggle_comp_clebal/ \
       vinayak-server:/home/vinayak23597/Kush/celebal_improve/
   ```
3. On the server, rebuild the processed data there instead of copying it: run `preprocess`, `build-training-origins` and `build-folds`, then the walk-forward. Use `nohup … &> run.log &` or `tmux`.
4. Use the GPU only for Phase 3 (Chronos-2, neuralforecast, embedding MLP). Pin it with `CUDA_VISIBLE_DEVICES=0`; the GBDT runs use CPU.
5. Pull results back to the Mac:
   ```bash
   rsync -av vinayak-server:/home/vinayak23597/Kush/celebal_improve/artifacts/models/ \
       ~/Desktop/Kaggle_comp_clebal/artifacts/models/
   ```
6. Append the run to `experiments.csv` with the server's git commit and data SHA-256.

---

## 6. Honest expectations

- Getting under 0.06 needs about 14% lower error than 0.06976. Phase 1 targets the one error source that is clearly measurable (bias²: 5–24% of the fold MSE). Phases 2–3 usually add a few percent more.
- How CV maps to the LB is unknown. CV is about 0.12–0.14 while the LB is 0.07, and the gap is unexplained (see `SUMMARY.md` §6). A CV gain does not translate one-for-one to the LB.
- Phase 0 will probably make the CV numbers look worse first. That is expected and correct.

## Sources

- Bojer & Meldgaard 2020, *Kaggle forecasting competitions: An overlooked learning opportunity*: https://arxiv.org/abs/2009.07701
- Makridakis, Spiliotis & Assimakopoulos 2022, *M5 accuracy competition: Results, findings, and conclusions*: https://pure.unic.ac.cy/en/publications/m5-accuracy-competition-results-findings-and-conclusions/
- Guo & Berkhahn 2016, *Entity Embeddings of Categorical Variables*: https://arxiv.org/abs/1604.06737
- Ansari et al. 2025, *Chronos-2: From Univariate to Universal Forecasting*: https://arxiv.org/abs/2510.15821
- AWS, *How Decathlon runs demand forecasting at scale with Chronos-2*: https://aws.amazon.com/blogs/machine-learning/how-decathlon-runs-demand-forecasting-at-scale-with-chronos-2/
- TabTune repo and paper: https://github.com/Lexsi-Labs/TabTune, https://arxiv.org/abs/2511.02802
- scikit-learn `TargetEncoder` docs: https://scikit-learn.org/stable/modules/generated/sklearn.preprocessing.TargetEncoder.html
