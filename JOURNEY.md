# The Full Journey — Hub Order Forecasting

*Not the official 1-2 page submission (that's `SUMMARY.md`, kept short per the rules). This is the
complete, honest record of how we got here: the research, the crash, the debugging, the decisions —
for our own reference and to actually show the work, not just the result.*

## Phase 0 — What was already built before this session

Before this conversation started, a leakage-safe EDA + feature-engineering pipeline already existed:
`src/eda_pipeline.py` (audit → preprocess → build-training-origins → build-folds → reports) and
`src/model_pipeline.py` (walk-forward CV harness, baselines, CatBoost/LightGBM fitters). 347 engineered
features per forecast origin — history-only rolling aggregates, legal target lags with availability
flags, day-counters, conversion/volume-per-session ratios, renovation-cohort handling. This was
already close to a full implementation of the Rossmann-competition playbook (drop closed rows,
log1p target, history-derived session signal instead of a naive two-stage forecast) — a strong
foundation, not a from-scratch start.

## Phase 1 — Diagnosing "the crash"

The user's laptop battery had died mid-run at some point before this session. On resuming, the
picture was confusing: `notebooks/03_global_gbdt_experiments.ipynb` had never actually executed
(`execution_count: None` on every cell), yet `artifacts/models/` already contained metrics files —
turned out those predated the crash, from an earlier successful run. Digging into `walk_forward.log`
found the real root cause: `pyarrow.lib.ArrowInvalid: No match for FieldRef.Name(DayBeforeClosed)` —
the feature-engineering code had been extended with new day-counter columns *after* the cached
training-origin Parquet files were built, so the stale cache didn't match the new schema. Between the
crash and this session, the data had already been correctly rebuilt from scratch on the new schema
(visible from file mtimes: `eda_pipeline.py` edited 23:42, all Parquets regenerated 00:12-00:37).

A live orphaned background process (PID 43874, running since 1:14 AM, eventually 6+ hours old) turned
out to be re-running the walk-forward CV on the corrected schema with an upgraded model recipe —
target encoding, a Tweedie-objective LightGBM, per-model log-space bias correction, and a log-mean
ensemble — none of which existed in the version of `model_pipeline.py` read earlier in the session.
That mismatch was the clue that part of this work had happened in an earlier, since-summarized part of
the same conversation. The process had **zero per-fold checkpointing** — `walk_forward_models()` only
writes output after all requested folds finish — so under time pressure it was killed and a fast,
simpler CatBoost-only full-history retrain was launched instead as a safety net.

## Phase 2 — Research injection

Mid-session, external research on the Rossmann-style demand-forecasting literature was supplied
(Jacobusse's 1st-place writeup, Guo & Berkhahn's entity embeddings, M5's LightGBM/Tweedie findings,
Montero-Manso & Hyndman on global models, Duan smearing for retransformation bias). Cross-checked
against what already existed in the codebase: almost everything recommended was already implemented
(day-counters, drop-closed-rows, log1p target, history-derived session ratios, purged rolling-origin
CV). The two genuinely new levers taken from the research: **target encoding for `HubID`** (in place
of raw high-cardinality categorical splits) and a **Tweedie-objective LightGBM** as ensemble diversity,
plus doing the **log-space (geometric) mean** ensemble correctly rather than blindly copying the
RMSPE-literature's harmonic mean — RMSLE calls for the additive/log-space analogue, not the
multiplicative 0.985-style RMSPE correction.

A quick, free experiment on already-computed OOF predictions (no retraining) validated the ensembling
idea before committing more compute: blending CatBoost + LightGBM in log-space plus fitting an
additive offset dropped RMSLE from 0.1305 (CatBoost solo) to 0.1230 — a real, cheap win, confirming
the direction before spending an hour of Kaggle compute on the full 3-model version.

## Phase 3 — Getting *something* on the board fast

Given explicit time pressure, priority flipped from "best possible model" to "valid submission, now."
A single CatBoost model, retrained on the full legal training history (~1.73M rows), predicted on the
real test set, hard-zeroed on closed hub-days, validated against `sample_submission.csv` (row count,
Id order, no NaN/negatives) — then submitted via the `kaggle competitions submit` CLI (installed fresh,
API token supplied by the user, saved to `~/.kaggle/access_token`).

**Result: 0.08528 public RMSLE.** Notably *better* than the local rolling-origin CV estimate
(~0.12-0.13) — flagged in `SUMMARY.md` as an open question rather than assumed free lunch; most likely
explanation is that the CV folds sit in a harder, sparser stretch of history than the test window.

## Phase 4 — Trying to close the gap to the target further with the full ensemble

Wanted the upgraded target-encoding + 3-model ensemble on the board too. First attempt: hand the user
a Kaggle-notebook cell to paste into their browser. Ran into a real, instructive series of failures:

1. **Indentation errors on paste** — Kaggle's editor mangled multi-line pasted code. Fixed by
   base64-encoding the whole script into a single `exec(base64.b64decode(...))` call, chunked into
   short (76-char) quoted-string lines so nothing could be line-wrapped by a clipboard or chat UI.
2. Realized copy-pasting into a browser notebook by hand doesn't scale for iteration — switched to
   **driving Kaggle directly via its API** (`kaggle kernels push`), so fixes could be pushed and rerun
   without any manual browser steps at all.
3. **v1 failed**: hardcoded `/kaggle/input/solari-pipeline` path assumption. Fixed by making the script
   auto-discover its own code location via `glob`.
4. **v1 (fixed) failed differently**: `ModuleNotFoundError: No module named 'src'` inside a *subprocess*
   — `build_training_origins()` shells out to a fresh `python3 -m src.eda_pipeline build-one` per origin,
   and that child process doesn't inherit `sys.path.insert()` from the parent. Fixed by also exporting
   `PYTHONPATH` into `os.environ` so the subprocess can find the code too.
5. **v2 failed after ~59 minutes** (the entire data-rebuild phase completed successfully first) on a
   trivial bug: `Paths(work_root)` was passed a plain string instead of a `pathlib.Path` — worked
   everywhere else because `argparse(type=Path)` did the conversion automatically for CLI-style calls,
   but this one direct call bypassed that. One-line fix.
6. Before pushing v3, ran a full **local smoke test** of everything downstream of that bug (target
   encoding → CatBoost → LightGBM → LightGBM-Tweedie → bias correction → ensemble → submission assembly)
   against a small slice of real data, in under a minute, to catch anything else before burning another
   hour of Kaggle compute. It passed clean.
7. **v3 pushed — completed successfully after ~4.5 hours total wall time.** Session interruptions along
   the way (the terminal/monitoring process got killed mid-wait, unrelated to the kernel itself, which
   runs on Kaggle's servers regardless) meant the autonomous monitor had to be relaunched once, but the
   kernel run itself was continuous and unaffected. Output validated (row count, Id order, no
   NaN/negatives against `sample_submission.csv`) and auto-submitted.
   **Result: 0.06976 public RMSLE** — down from 0.08528, and within ~10% of the 0.0634 target, versus
   the >2x gap the very first local CV estimate (~0.13) had suggested.

Also split the pipeline into two separate Kaggle notebooks (`kaggle_phase1_build_data.py` /
`kaggle_phase2_train.py`) as a fallback path the user could run by hand in their own browser session if
the API-driven kernel kept failing — phase 1 does the slow ~50-minute data rebuild once and saves its
output as a reusable dataset; phase 2 reads that and does only the fast model-training part, so any
future debugging iteration wouldn't have to re-pay the full rebuild cost.

## Phase 5 — Handling being unattended

The user needed to step away with the run still in flight. Set up `caffeinate -dimsu` to prevent the
Mac from idle-sleeping (explicitly flagged that this does *not* survive a physically closed laptop
lid — that forces sleep regardless), and launched a fully autonomous background pipeline: poll the
Kaggle kernel until it's no longer `RUNNING`/`QUEUED`, download its output, validate the resulting CSV
against the same checks used for the first submission, and only submit it if every check passes —
otherwise leave the existing 0.08528 submission untouched and report back. Scope was kept deliberately
narrow (validate-then-submit-or-don't) rather than broad "do whatever" autonomy, matching what was
actually asked for.

## What this demonstrates, methodologically

- **Diagnose before treating**: three different "crashes" over this session turned out to be a stale
  Parquet schema, a shell reserved-word collision (`status` in zsh), and a subprocess `PYTHONPATH` gap
  — none of them were what they first looked like, and guessing would have wasted far more time than
  reading the actual traceback each time.
- **Cheap experiments before expensive ones**: validating the ensembling idea on already-computed OOF
  predictions (free, instant) before committing an hour of Kaggle compute to it.
- **Smoke-test the untested path locally** before re-running something that takes an hour, whenever
  that's possible — caught nothing that time, but would have saved an hour if it had.
- **Match tooling to the actual constraint**: browser copy-paste doesn't scale for iterative debugging;
  driving the same platform via its API does.
