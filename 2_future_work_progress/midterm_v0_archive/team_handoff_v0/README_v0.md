# CSE558 Midterm: ShadowHub Hub-Order Demand Forecasting

**Course:** IIIT-Delhi CSE558 Data Science, Monsoon 2026. **Report deadline:** 27 October 2026, 11:59 PM. **Branch:** [`cse558-midterm-2026`](https://github.com/kushiiitd05/ShadowDsc10-ShadowHub/tree/cse558-midterm-2026).

## What is inside the handoff

`project/datset_kaggle/` contains the supplied competition training/test CSVs and hub metadata; `midterm/report/` contains the LaTeX source and previously verified results as TeX inputs; `midterm/figures/` has four EDA visuals; `midterm/results/` has numeric results and diagnostic tables; root Python scripts regenerate the analyses.

The handoff's **`FINISH_AND_PACKAGE.py`** (one directory above `project/`) is the easiest way to generate the final PDF and Classroom code ZIP after adding genuine member contributions to `midterm/member_contributions.csv`. It compiles the PDF and runs the strict validator. A separate full analysis rerun is optional, since all primary test numbers and the corrected T1 sensitivity estimates have already been independently compared against original raw inputs. Do not change numbers without rerunning and reconciling them.

## Dataset, encoding and questions

The original files are from the supplied Shadow Hub hub-demand competition dataset. The exact public original dataset URL should be linked only if verified. Training has **970,379 observed hub-date rows × nine columns**; metadata contains **1,115 hubs × 10 columns**; outcome-free test data contain **46,830 rows × eight columns**. After joining metadata, adding missingness indicators and encoding categorical variables, the training representation contains **970,379 × 35 = 33,963,265** entries (required ≥3M).

Hypothesis tests at α=0.05 with Holm multiple-testing correction:

- **T1:** Within each hub, does Monday's promotion-associated demand difference exceed Friday's? Two-sided paired hub-level t-test; independent hub fixed-effects and date-level HAC sensitivity checks. Shared calendar shocks limit causal interpretation.
- **T2:** Is a gap of at least 100 consecutive unobserved hub-dates associated with hub format? χ²(3) with permutation p-value owing to sparse cells; report Cramér's V with bootstrap 95% CI.
- **T3:** Is competitor distance monotonically associated with mean operating-day orders per hub? Spearman rank correlation and 95% bootstrap CI; Kendall check.
- **T4:** Do average orders differ before versus after a competitor's recorded opening month? Paired event-window t-test with approximate mid-month event date, 15-day buffer, and alternative-window/Wilcoxon checks; not causal.

Practical-effect benchmarks and rationale are written in `midterm/report/main.tex`. These are exploratory, **not preregistered**. Do not interpret rejected null hypotheses as causal effects or nonrejection as proof of equality.

## Reproduce from raw data (optional audit)

Use Python 3.11+ from `project/`, and install the exact dependencies:

```bash
python -m pip install -r requirements-midterm.txt
```

For a complete regeneration, use `python complete_midterm.py --repo .` **only if** `pdflatex` is installed and your member contributions and report are ready. It runs:

```text
capture_environment.py
 audit_structure.py
 preprocess_audit.py
 build_encoded_data.py
 outlier_audit.py
 run_eda.py
 run_hypothesis_tests.py
 t2_bootstrap_ci.py --repo .
 run_t1_fixed_effects.py
 t1_date_robustness.py --repo .
 run_sensitivity_analysis.py
 integrate_verified_results.py --repo .
 validate_midterm.py --repo .
```

Some methods use `linearmodels`, `statsmodels`, and `pyarrow`; the full rerun needs those packages. The automated full rerun writes `midterm/results/encoded_training.parquet` (large generated file, excluded from the compact Classroom code archive). Training and metadata CSVs are **not** transformed into synthetic outcomes; absent hub-days are not imputed as zero.

## Final submission

Submit the **final <=8-page PDF report using the instructor's LaTeX template**, accessible code link and README, and a script/notebook uploaded to Classroom as specified by the instructor's accompanying template. Check the generated PDF visually. See the outer handoff's `01_START_HERE_TEAM.md` and `02_GITHUB_AND_CLASSROOM.md` for exact steps.
