> **Historical snapshot.** Paths refer to the layout before the 26 Oct restructure. See `../STATUS.md` for the current state.

# REVIEW REQUEST: midterm revision r1

- **Date / phase:** 2026-10-26; Job 1, phases 1.1–1.4 (verify, P0 fixes, statistics upgrades, build and validate).
- **Branch:** `max/midterm-r1` (local only, never pushed), cut from `main` at `f511b34`. See `git log main..max/midterm-r1`.
- **Summary:**
  - The report is rebuilt on the official template. It is a 6-page PDF; the validator passes 30 of 31 checks, and the
    only failure is the contribution placeholders.
  - All 125 data facts in the master prompt were recomputed from the raw CSVs. Four tests were rerun under a plan
    committed first. T1, T3 and T4 changed design (log scale, Pearson on logs, difference-in-differences).
  - **Before submission:** the five members must confirm their contributions, and someone with push rights must
    update `cse558-midterm-2026`.

## How to review (on the Mac)
```bash
git clone <bundle or repo> && git checkout max/midterm-r1
python -m pip install numpy pandas scipy matplotlib pyarrow pytest
cd 1_midterm/analysis && python run_all.py         # ~5 min; the last step exits 1 only for the placeholders
pytest -q test_midterm_r1.py                        # 9 tests
cd ../midterm/report && pdflatex main.tex && pdflatex main.tex   # or Overleaf: upload report/ and figures/r1/
```

## Changed files
| File | What changed | Why |
|---|---|---|
| `1_midterm/analysis/` (new) | `00_verify`, `01_prepare`, `02`/`03` tests, `04_summary`, `05_descriptives`, `06_figures`, `07_validate`, `08_audit_numbers`, `inference.py`, `common.py`, `run_all.py`, `test_midterm_r1.py` | One command reproduces every number. Each statistic is computed by scipy and by formula. |
| `1_midterm/midterm/analysis_plan_r1.md` (new) | Analysis choices for r1, committed before the test scripts ran | Honest stand-in for pre-registration (it does not backdate anything) |
| `1_midterm/midterm/results/r1/` (new) | Every table behind the report, plus `audit_numbers.csv` (576 numbers → source) | Traceability (S11) |
| `1_midterm/midterm/figures/r1/` (new) | 5 vector figures | Captions are takeaways with numbers |
| `1_midterm/midterm/report/main.tex`, `main.pdf` | Rewritten on `CSE558_Project_Report_Template.tex` (same preamble, `\showhintsfalse`, no `\eg`) | R7; gaps B1–B7 and C |
| `1_midterm/midterm/report/archive_v0/` | The old `main.tex`, fragments and stale PDF, moved with `git mv` | Kept for diffing |
| `1_midterm/README_MIDTERM.md` (new) | Run steps, SHA-256 hashes, full Q1–Q18 ledger, all 78 flagged rows, v0→r1 changes | R6 |
| `.gitignore` | ignores `results/r1/derived/` (regenerated parquet) | size |

Untouched: `kaggle_modelling/`, raw CSVs, the v0 scripts in `1_midterm/*.py`. Note that the v0 tools
`validate_midterm.py`, `FINISH_AND_PACKAGE.py` and `fill_team_contributions.py` expect the **old** `main.tex` and will
not work on r1. The r1 gate is `analysis/07_validate.py`.

## Numbers that changed in the report (old v0 → new r1)
| Quantity | Old | New | Source | Reason |
|---|---|---|---|---|
| Title | "ShadowHub: Hub Order Demand Forecasting" | "Promotion timing, missing data and competitors: four hypothesis tests on 1,115 retail hubs" | main.tex | B3: no model in the midterm |
| "restaurant-service hubs" | present | removed; `OrderVolume` = daily volume, units unstated (9.23 per session) | verify.csv | B2, B5 |
| Encoded size | 970,379 × 35 = 33,963,265 | 970,379 × 46 = 44,637,434 | prep_encoded_schema.csv | 8 data-quality flags and a fuller one-hot encoding |
| T1 | +2,168.77 orders, t(1114)=64.84 | log scale: d̄=0.269 [0.263, 0.275] = +30.9%, t(1114)=90.47; raw scale on the r1 rows +2,169 | t1_results.csv | log scale, holidays and reopen windows out (C) |
| T2 | χ²(3)=21.42, p≈0.0002, V=0.139 | unchanged; permutation p = 2.1e-4 (100k); follow-up format 4 vs rest +10.4 pp [5.3, 15.4] | t2_*.csv | gap now defined as the exact 2014-H2 block (same 180 hubs) |
| **T3** | **Spearman ρs=−0.032, p=0.29, fail to reject** | **Pearson on log scale r=−0.082 [−0.140, −0.023], t(1110)=−2.74, p=0.0063, reject**; Spearman −0.037 (p=0.21) as robustness | t3_results.csv | The plan fixed Pearson on logs as primary (master §5 P3). **This reverses the decision.** The CI straddles 0.10. Post hoc: the effect comes from the closest decile only. Reported openly in §5. |
| T4 | before/after, n=120, −482 orders, t(119)=−5.69 | DiD vs 498 controls, n=144, −8.8% [−10.5, −7.0], t(143)=−9.45; placebo −0.7% (p=0.28) | t4_results.csv | C: v0 had no control. Without a control the effect is −5.6%; seasonality is as large as the effect. |
| Multiplicity | Holm | Bonferroni α/4 and Holm; all 4 still reject | tests_summary.csv | S10 |
| Lag-7 dependence | master prompt: 0.54 | 0.02 on open-day log volume (lag-1 0.65, lag-14 0.55) | desc_lag_correlations.csv | The master's figure came from a table that included closed days. The near-zero lag 7 is caused by the alternating promo weeks. |
| Competitor openings in window | master prompt: 175 | 175 (opening month ≤ 2015-05) or 180 (incl. June 2015); 144 used | verify.csv, t4_counts.csv | definition |

## Evidence
- `00_verify.py`: **125/125** claims match.
- `07_validate.py`: **30/31**. The failure is `<<CONFIRM: ...>>` in the contributions.
- `pytest`: 9 passed.
- `pdfinfo`: **6 pages**; 0 overfull boxes; Carlito font embedded.
- scipy vs manual formula: the `agree_4sf` column is True for T1–T4 (and for every robustness row).
- `audit_numbers.csv`: 576 numbers, 0 unmatched. **Caveat:** matching is by value at the printed precision, searching
  the section's own tables first, so a short number can map to the wrong row of the right table. Key numbers were
  spot-checked by hand.
- Full rerun from scratch: see `SESSION_LOG.md`.

## Rubric rows (RESEARCH_PROTOCOL §1)
1. Source, size: met (provenance, 46-attribute arithmetic, 9-row key-feature table).
2. Preparation with "why not": met (13-row table).
3. Before/after: met (incl. skewness and kurtosis, a second outlier pass).
4. EDA: 5 figures with takeaway captions, a novelty statement, a schedule table.
5. Tests (a), (b), (c): met for all 4 (H0 with equality, δ with reason, alternatives, formula with numbers substituted,
   df, critical value, p, CI, verdict), plus replication and placebo.
6. Code link: met once the branch is pushed.
7. ≤ 8 pages on the template: met.

## Open questions for the user / reviewer
1. **Contributions:** the drafts split the work by section and are marked `<<CONFIRM: ...>>` in the header of
   `main.tex`. Each member must confirm or rewrite their line. Then delete the `<<CONFIRM: ` and `>>` markers and rebuild.
2. **Names and emails** were copied from v0 (`Kush23296@…` has a capital K). Please confirm.
3. **Push:** `origin/cse558-midterm-2026` is an ancestor of `max/midterm-r1`, so a fast-forward works:
   `git push origin max/midterm-r1:cse558-midterm-2026`. That brings the repo's `1_midterm/` layout, which the report's
   code link points into. Alternatively, merge into `main` first.
4. **T3 reversal:** we kept the pre-planned primary test and reported both versions. Please confirm you are
   comfortable with this.
5. **Classroom code upload:** suggested `cd 1_midterm && zip -r CSE558_code.zip analysis README_MIDTERM.md midterm/analysis_plan_r1.md midterm/results/r1 -x 'midterm/results/r1/derived/*'`.

## Known risks
- Hub-level standard errors ignore cross-hub date correlation. This is checked for T1 (week level) and absorbed by
  T4's controls; it is stated in the limitations.
- The Rossmann provenance comparison relies on public knowledge of that dataset. Its internal evidence (counts, hubs
  1 and 2, the 180-hub gap) was verified.
- The δ values are our assumptions; the report says so.
- Compiled with TeX Live 2026 (pdfLaTeX). Overleaf should give the same output, but check the page count after
  editing the contributions.
