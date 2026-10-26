> **Historical snapshot.** Paths refer to the layout before the 26 Oct restructure. See `../STATUS.md` for the current state.

# GAP ANALYSIS: midterm report vs requirements

Sources compared: `1_midterm/reference/MASTER_PROMPT_CSE558_Midterm.md` (the plan, R1–R8, S1–S11, Q1–Q18), the course guidelines/template PDF, `1_midterm/midterm/report/main.tex` (+ `*_verified.tex`), `midterm/results/*.csv`, `validate_midterm.py` output. Report is currently 4 pages; the limit is 8, so there is room for about 4 more.

Legend: **P0** must fix before submitting · **P1** strong grade gain · **P2** nice to have.

## A. Hard requirements (R1–R8)
| Req | Status | Evidence / gap |
|---|---|---|
| R1 size ≥ 3M with arithmetic | **Met** | 970,379 × 35 = 33,963,265 (Table 1) |
| R1 name features + meaning | **Partial (P1)** | Prose list only in repo `main.tex`. The newer 5-page PDF has a key-features table (type + meaning); its source is missing from the repo |
| R2 prep: encoding, outliers, missing, duplicates, and *why not the alternative* | **Partial (P1)** | Table has 6 rows. Master ledger has 18 (Q1–Q18). Alternatives rejected (mean/median imputation, kNN, deletion) are not named |
| R3 before vs after | **Weak (P1)** | Only size and missing-cell counts. No skewness/kurtosis raw vs log, no flagged-anomaly counts, no second outlier pass |
| R4 basic questions, novelty, EDA plots with one-line takeaway | **Partial (P1)** | 4 figures, captions are descriptions, not takeaways with a number. No Q-Q plot, no gap strip, no log-scale histogram paired with the boxplot |
| R5(a) per test, before running: H0, H1, α, side, test, smallest meaningful difference | **Partial** | H0/H1/α present. All tests two-sided. Practical benchmarks (350 orders, V ≥ 0.10, ρ ≥ 0.10) are stated as "illustrative, not preregistered": honest, but no real-world reason is given |
| R5(b) other tests considered and why not | **Mostly met** | Present for T1–T4 (Wilcoxon, Fisher–Freeman–Halton, Pearson, Welch-style) |
| R5(c) statistic, **df**, p, decision, estimate + 95% CI, practical verdict | **Partial (P1)** | T3 gives no df/test statistic form; no formula with numbers substituted (S4); no critical values (S7) |
| R6 code link + README | **Met, but see D** | Branch link in header; branch is stale until pushed |
| R7 PDF ≤ 8 pp, **given LaTeX template**, 4 h early | **At risk (P0)** | `main.tex` already matches the template's class, geometry and six sections, but it is not built from the template file (no `\showhints` switch, own header). Diff against `CSE558_Project_Report_Template.tex` and align. Not yet rebuilt: the repo PDF is stale and has `blah` |
| R8 limitations | **Met** | 6 bullets. Add provenance and test-window shift (see B) |

## B. Content the master prompt wants that the report lacks
| # | Gap | Priority |
|---|---|---|
| B1 | **Contributions are `blah 1..5`**; `member_contributions.csv` is `REPLACE_ME`. Only the five members can fill these. Never invent them | **P0** |
| B2 | **Invented description:** "restaurant-service hubs". Nothing in the data says restaurants. Remove | **P0** |
| B3 | **Title says "Forecasting"** but the midterm has no model. The plan forbids model content. Retitle (e.g. "Hub Order Demand: Data Preparation and Hypothesis Tests") | **P0** |
| B4 | **Provenance not disclosed.** Master §2.2: the files match public Rossmann Store Sales with renamed columns (1,115 hubs; 970,379 + 46,830 = 1,017,209 rows). One honest sentence in §1 | P1 |
| B5 | **`OrderVolume` described as "recorded number of orders".** Median OrderVolume / AppSessions on open days is 9.23 (99.9th pct 17.19): implausible for a count of orders. Call it "daily volume (units unstated)" and report the inconsistency | P1 |
| B6 | Ledger rows missing: Q3 open-with-zero (54 rows: only a count is in the table), Q4/Q5 per-hub robust-z outliers (6,220 rows, 1,040 hubs), Q6 Chebyshev check, Q7 closure runs and reopening windows, Q8 conversion-ratio anomalies, Q12 `CompetitorOpenSinceYear` = 1900 sentinel, Q13 8 hubs with identical metadata (not duplicates), Q16 last-digit χ² integrity check, Q17 train-vs-test schedule shift (school closure 17.35% → 28.51%) | P1 |
| B7 | **No replication check** (rerun each test on 2013 vs 2014–15 or odd/even HubID) and **no placebo** (T1 permute promo within hub × weekday; T4 shift opening date 12 months) | P1 |
| B8 | **No pre-registration.** Cannot be created retroactively. Say plainly in the report that the tests were chosen after EDA (already stated as "not preregistered"), and do not backdate a file | P2 |
| B9 | Master requires `AppSessions` to appear; the report barely uses it | P2 |
| B10 | Provide the second pass "does an outlier still exist after the fix?" (Lecture 3) | P2 |

## C. Statistical design: are the tests good?
Verdict: **T2 and T3 are sound. T1 needs a scale fix. T4 is the weak one.**

| Test | Assessment | Improvement |
|---|---|---|
| **T1** Monday vs Friday promo lift, paired by hub, n = 1,115, t(1114) = 64.84 | Good unit of analysis (hub, not hub-day). But the effect is in **raw orders**, and Monday volume is larger than Friday volume, so equal *percentage* lift gives a larger raw difference. The master plan uses log(1 + V) and a % lift. Also confirm closed rows (zeros) and holidays are excluded; the stated filter is only "hubs with all four groups". Date-level HAC check exists (+2,015, CI [1,546, 2,484]) and agrees | Rerun on log scale; report % lift; restrict to open, non-holiday, non-flagged days; add placebo |
| **T2** long gap × format, χ²(3) = 21.42, permutation p = 0.0002, V = 0.139 (CI 0.086–0.201) | Good. Correct handling of sparse cell (min expected 2.74), permutation p, bootstrap CI | Add the follow-up "format 4 vs rest" proportion difference with CI; state that gaps are non-random, so any 2014-H2 comparison is biased toward non-gap formats |
| **T3** Spearman, n = 1,112, ρ = −0.032, CI [−0.091, 0.030] | Good. The CI sits inside ±0.10, so the finding is "no association large enough to matter" | State Spearman's t-approximation df = n − 2 = 1110; add Pearson on log distance as a robustness check; mention the 3 hubs with missing distance |
| **T4** pre/post opening, paired t, n = 120, Δ = −482 orders, p = 9e-8 | **Weak.** No contemporaneous control: seasonality and the 2013–15 trend are confounded with "after". Opening date is the 15th of the month. 1900/1961 sentinel years not discussed. The small p is largely a design artefact | Difference-in-differences against control hubs over the same calendar weeks (master §5 P4); log scale; placebo with the date shifted 12 months; handling of Q12 sentinel years; downgrade the language |

Multiplicity: Holm across 4 tests is correct and stated. All four tests are two-sided; the master plan wants one-sided for T1 and T4 with the direction fixed in advance. Since no pre-registration exists, keep two-sided and say why. Do not switch sides after seeing the data.

## D. Code and reproducibility
- `validate_midterm.py`: 45/46 pass. The one failure is B1.
- There are **no unit tests for the midterm scripts** (the repo's pytest suite covers only the Kaggle pipeline; it passes, 6 tests). Add small tests: key uniqueness, closed rows have zero volume, row waterfall sums, T2 contingency table sums to 1,115, encoded shape equals 970,379 × 35.
- Code link in the PDF header points to the branch `cse558-midterm-2026`. That branch must be updated with the final report, scripts and README (see `1_midterm/02_GITHUB_AND_CLASSROOM.md`). Public branch is currently stale.
- If the repo is renamed, GitHub redirects the old URL; update the link in `main.tex` to the new name anyway.
- No LaTeX on the Mac: use Overleaf, or `brew install tectonic`.

## E. EDA still to do (ordered)
1. Log-scale histogram of open-day volume next to the boxplot (kurtosis 7.84 raw vs skew −0.11 on log).
2. Missingness strip: hubs × dates showing the 180-hub, 184-day gap (feeds T2).
3. Promo lift by weekday with hub-level CIs (feeds T1).
4. Per-hub mean log volume vs log competitor distance with Spearman line (feeds T3).
5. Q-Q plot of the per-hub paired differences for T1 and T4.
6. Train vs test schedule-shift table (school closure 17.35% → 28.51%, no holidays in test).
7. Conversion ratio (volume / sessions) histogram with the 23 rows above 30 marked.
8. Rewrite every caption as a one-sentence takeaway containing a number.

## F. Ordered task list (what to do, with gates)
**P0, before anything else**
1. Four members write truthful contributions into `1_midterm/midterm/member_contributions.csv`; run `fill_team_contributions.py`.
2. Recover the source of the 5-page highlighted PDF; merge its additions into `main.tex`.
3. Remove "restaurant-service"; retitle (B2, B3).
4. Build the PDF (Overleaf or tectonic); run `validate_midterm.py` (expect 46/46); read every page; ≤ 8 pages.
5. Push the final report, code and README to branch `cse558-midterm-2026` (needs push rights; owner approval). Check the link in an incognito window.
6. Upload PDF + code zip to Classroom before 27 Oct 19:00.

**P1, if time**: B4–B7, C (T1 log scale, T4 difference-in-differences), E, align with the official template.
**P2**: B8–B10, midterm unit tests, presentation outline.

Rules while editing: every number in the PDF must trace to a script output or CSV; never "accept H0"; no modelling, CV or leaderboard content in the report; never zero-fill or mean-impute the 2014-H2 gap.
