> **Historical snapshot.** Paths refer to the layout before the 26 Oct restructure. See `../STATUS.md` for the current state.

# STATUS: where everything stands

## Update 2026-10-26 (server session, branch `max/midterm-r1`, local only)
- **Midterm r1 built:** `1_midterm/midterm/report/main.pdf`, 6 pages, on the official template. The analysis is in
  `1_midterm/analysis/` (`run_all.py`), the tables in `1_midterm/midterm/results/r1/`, and the README in
  `1_midterm/README_MIDTERM.md`.
- **Verified:** 125/125 data facts. Validator 30/31 checks; the only failure is the contribution placeholders. pytest
  9/9. 576 numbers in the PDF traced to a source.
- **Open:**
  - the five members must confirm their contribution lines (`<<CONFIRM: ...>>` in `main.tex`);
  - review on the Mac;
  - push to `cse558-midterm-2026` (fast-forward possible);
  - Classroom upload by 27 Oct 19:00.
- Everything is described in `REVIEW_REQUEST.md`. **The T3 decision reversed** (now rejects, weak effect); see there.
- The v0 tools (`validate_midterm.py`, `FINISH_AND_PACKAGE.py`) target the old report and no longer apply.

---

# (previous snapshot) snapshot 2026-10-26, before r1

## Deadlines
| What | When |
|---|---|
| CSE558 midterm report (PDF, ≤ 8 pages) on Classroom | **27 Oct 2026, 23:59 IST**. Lecture 1 rule: submit ≥ 4 h early, so aim for **27 Oct 19:00** |
| Midterm presentation | separate, no instructions supplied yet |
| Kaggle improvement plan | no deadline; start only after the midterm is submitted |

## Repo map (this repo, branch `main`)
| Path | What it is | State |
|---|---|---|
| `1_midterm/` | Midterm project: raw data, scripts, results, figures, report, finish tooling | Report builds only after contributions are filled; see GAP_ANALYSIS.md |
| `1_midterm/datset_kaggle/` | The 4 raw CSVs (single copy for the whole repo) | Final |
| `1_midterm/midterm/` | `report/`, `results/`, `figures/`, `member_contributions.csv`, `README.md` | Results verified; report has gaps |
| `2_future_work_progress/kaggle_modelling/` | Finished Kaggle work, public LB 0.06976 | **Frozen record. Do not edit** |
| `2_future_work_progress/improvement_plan/` | `IMPROVEMENT_PLAN.md`: audit + phased plan to reach LB < 0.06 | Not started |
| `2_future_work_progress/server_run/` | This folder: hand-off for the server (Max plan) session | Active |

Branch `cse558-midterm-2026` (remote) is cited inside the report as the code link. It holds Anusha's 23 Oct commit, which is **older** than what is now in `main`. It has not been updated yet. Do not rewrite or delete it.

## What was merged into `main`
1. Anusha's branch `cse558-midterm-2026` (commit `246235e`): merged, history kept.
2. Team zip `CSE558_ONE_ZIP_FOR_TEAM` (25 Oct): overlaid on `1_midterm/`. It wins where files overlap. It adds the verified T1/T2 results, robustness scripts, `validate_midterm.py`, `FINISH_AND_PACKAGE.py`, audit docs, and the newer `main.tex`.
3. The raw CSVs in the zip differ from the repo copies only by CRLF line endings. Repo copies kept.

## Midterm: what is verified, what is not
Verified (numbers recomputed from raw CSVs by the team audit, and `validate_midterm.py` passes 45/46 checks):
- Shapes: train 970,379 × 9; metadata 1,115 × 10; test 46,830 × 8; encoded 970,379 × 35 = 33,963,265 entries (≥ 3M).
- Four tests (Holm-adjusted): T1 Monday vs Friday promo lift (rejects), T2 long-gap vs hub format (rejects), T3 competitor distance vs mean demand (fails to reject), T4 pre/post competitor opening (rejects).

Not done / failing:
- The single failing check: **contribution placeholders** (`blah 1` … `blah 5` in `main.tex`; `REPLACE_ME` in `member_contributions.csv`). Only the five members can write these truthfully.
- The PDF in the repo (`midterm/report/ShadowHub_demand.pdf`, 4 pages) is **stale** and still carries `blah`.
- A newer 5-page PDF (`CSE558_Report_with_additions_highlighted.pdf`, kept locally, not in git) has a key-features table, a Kaggle link and a README link that the repo's `main.tex` lacks. **Its LaTeX source is not in the repo.** Find the source before editing `main.tex`, or the additions get lost.
- No LaTeX on the author's Mac (`pdflatex` not found). Build via Overleaf, or `brew install tectonic` (small).

## Kaggle modelling (frozen) and what is missing locally
- Present: pipeline (`src/`), scripts, notebooks, OOF predictions, two submission CSVs, processed folds and origins, EDA artifacts.
- **Not present locally: trained model weights.** The 3–4 h A100 run that produced the 0.0678-ish score should have output on the GPU server. Needs VPN to inspect. When found, pull into `server_run/artifacts/` (git-ignored if large) and record the path and a checksum in this file.
- Known defects in the finished work are listed in `improvement_plan/IMPROVEMENT_PLAN.md` §1 (level bias, no-op bias correction, 1-fold-only ensemble validation, walk-forward crash on stale parquet, target-encoding leak, early-stopping on wrong data).

## Other local items (not in git)
- `~/Desktop/Dsc/` lecture PDFs, quiz rubric/solutions, `dsc proj/` zips. `NOT YET_submission.zip` belongs to another team: method reference only, never publish.
- Course guidelines PDF is in `1_midterm/reference/`.
