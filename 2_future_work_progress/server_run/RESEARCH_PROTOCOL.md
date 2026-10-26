# RESEARCH PROTOCOL: midterm, aimed at full marks

Companion to `MAX_PLAN_PROMPT.md` (Job 1). The Max-plan session follows this file for *how to research, write and hand over*; `history/GAP_ANALYSIS_r0.md` says *what is missing*.

**How we are graded (guidelines, verbatim):** "graded on how much you could dig into and infer from the data, not on whether a test rejects H0." So depth, correct method choice, honest effect sizes and a clear comparison with alternative tests earn marks. A significant result earns nothing extra. A rigorous non-significant result is a full-credit finding.

## 1. Rubric → evidence matrix (every row must be answerable by a page/table in the PDF)
| Guideline item | Evidence the grader looks for | Where | Status (see GAP_ANALYSIS) |
|---|---|---|---|
| 1 Source, rows × cols, ≥ 3M after encoding, arithmetic shown | Source sentence + provenance, shape table, 970,379 × 35 = 33,963,265, key-feature table with real-world meaning | §1 | Met; add feature table + provenance |
| 2 Preparation: encoding, outliers, missing, duplicates, *why* | Issue → action → why, **and why not the alternative** (deletion, mean/median/kNN/regression imputation; trimming/winsorising) | §2 | Partial |
| 3 Before vs after | Table: rows, cols, missing cells, flagged anomalies, skew/kurtosis raw vs log, duplicates; 3-sentence observation | §3 | Weak |
| 4 Basic questions, novelty, EDA plots with one-line takeaway | 4–5 plots; each caption = one sentence with a number; novelty sentence | §4 | Partial |
| 5a Before the test: H0 (with equality), H1, α, side, test, smallest difference that matters | A boxed block per test written *before* the result; the smallest difference has a real-world reason | §5 | Partial |
| 5b Other tests considered and why not | A line per rejected alternative, with the reason tied to the data (dependence, skew, sparse cells, pairing) | §5 | Mostly met |
| 5c Statistic, **df**, p, decision, estimate + 95% CI, does it matter | One results line per test with all six items; verdict against the smallest difference | §5 | Partial (df, formula) |
| 6 Link to code + README | Working branch link; README with run steps and file hashes | header | Met after push |
| 7 PDF ≤ 8 pp, LaTeX template, on time | `pdfinfo` ≤ 8; template structure (our preamble already matches it); submitted ≥ 4 h early | — | At risk until built |

Page budget (A4, two-column, 8 max): header + §1 0.8 · §2 1.1 · §3 0.6 · §4 1.5 · §5 3.2 · §6 0.5 = 7.7 pages. Keep ~0.3 page free for LaTeX drift.

## 2. Research agenda (what to dig into)
Use the data's own structure. Everything below is a hypothesis to **verify with code before it is written down**; the numbers come from the master prompt §2 and must be recomputed (Phase 1.1).

**Core four (already run; upgrade them, section C of GAP_ANALYSIS):**
- T1 promo lift Monday vs Friday → log scale, % lift, open/non-holiday days, placebo, replication.
- T2 data-gap mechanism vs hub format → add format-4-vs-rest proportion CI; implication for bias.
- T3 competitor distance vs mean demand → df, Pearson-on-log robustness, 3 missing hubs.
- T4 competitor opening → difference-in-differences with control hubs, placebo, sentinel-year handling.

**Candidate fifth test (pick at most one; 5 is the cap; otherwise put in repo README as supplementary):**
- **Reopening surge:** hubs with a closure run ≥ 14 days (45 runs; longest 185 days). Per hub, paired difference of mean log volume in the 14 days after reopening vs the 14 days before closing. Within-hub, uses an event nobody records directly. Paired t, hub as unit.
- **School-closure effect:** per hub × weekday, volume with `SchoolClosureFlag` on vs off; paired across hubs. Motivated by the test window having 28.51% school closure vs 17.35% in train.
- **Promo volatility:** F-test / paired log-variance ratio, promo vs non-promo weekdays (master §5 P5).

**Descriptive digs that strengthen §2–§4 without adding a test:**
- Provenance evidence (hub 1 and 2 metadata, 180-hub gap, 54 open-zero rows, max AppSessions 7,388).
- `OrderVolume`/`AppSessions` on open days: median 9.23, 99.9th pct 17.19, max 64.96 → name/behaviour mismatch.
- Outliers in context: pooled IQR fence flags 29,307 rows (3.64%), mostly big hubs; per-hub robust z flags 6,220 rows in 1,040 hubs; cross-tabulate with holidays/promo/reopening before keeping or flagging. Example: 38,722 = hub 262, Good Friday, promo on → genuine.
- Chebyshev check (|z| ≥ 2, 3, 4: 4.24%, 1.59%, 0.60% vs bounds 25%, 11.1%, 6.25%) to justify not using a normal 3σ rule.
- Last-digit χ² (df 9) as an integrity check; MLE p̂ = 54/804,110 for the open-zero rate with CI.
- 8 hubs with identical metadata are *not* duplicates.
- Train vs test schedule shift table.

## 3. Analysis variables and tooling (midterm: no model features)
Allowed derived variables, each from a pure function returning a new frame: `log1p_volume`, hub-level aggregates (mean log volume on open days), flags `gap_hub`, `open_zero`, `long_closure`, `reopen_window`, `ratio_anomaly`, `sentinel_year`, calendar fields (year, month, ISO week), event-window indicators. **Forbidden in the midterm:** lag/rolling features, target encoding, model fits, CV, leaderboard numbers.
Environment: `/opt/anaconda3/envs/eda311` locally; on the server use a fresh venv from `1_midterm/requirements-midterm.txt` plus `scipy`, `statsmodels`, `pandas`, `matplotlib`. Compile: Overleaf, or `tectonic`/TeX Live. Tests: `pytest`. Cross-check every test with `scipy.stats` **and** a manual formula (agree to 4 s.f.).

## 4. How to write the submission (section by section)
- **Header:** group "DSC 10", dataset + Kaggle link, code + README links, five members with real contributions.
- **§1 Dataset:** source, provenance sentence, shape table, arithmetic, 8-row feature table (type per Lecture 2, meaning), response definition with the units caveat.
- **§2 Preparation:** one condensed table (issue | evidence | action | why, not alternative). Closed rows are structural zeros, not outliers. The 2014-H2 gap is unobserved, never zero-filled. Full 18-row ledger goes in `midterm/README.md`.
- **§3 Before/after:** one table + 3 sentences. Show the second outlier pass.
- **§4 Questions + EDA:** 4–5 figures (log histogram beside boxplot, gap strip, promo lift CIs, distance scatter, Q-Q). Captions are takeaways with numbers. Boxed problem statements P1–P4; one novelty sentence.
- **§5 Tests:** per test, in this order: *(a)* pre-test block, *(b)* alternatives considered, *(c)* result line "statistic = (estimate − null) / SE = …, df, p, decision, estimate [95% CI], verdict vs smallest difference". Then replication + placebo in one line. Close with the Holm line and "what would change our mind".
- **§6 Limitations:** association not cause; excluded rows; provenance/units; month-level event dates; multiplicity; test-window shift; tests chosen after EDA (not pre-registered).
- **Language rules:** "reject / fail to reject H0", never "accept"; define every symbol before use; one-sided vs two-sided matched to the critical value; counts with thousands separators; estimates 3 s.f.
- **Smallest difference that matters:** give a reason, e.g. "a promotion must lift volume ≥ 5% to cover its cost" — and say it is our assumption.

## 5. Review loop (Max session ↔ Mac session)
**Why:** the server session does research and drafting; the Mac session reviews independently, then pushes. Two sets of eyes, and nothing reaches the cited branch unreviewed.

**Max session must:**
1. Work on a local branch `max/midterm-r1` cut from `main`. Never commit to `main` or `cse558-midterm-2026`.
2. Commit per file group; never commit `.aux/.log`, raw zips or secrets.
3. After each phase update, in the repo: `STATUS.md` (done/verified/open), `SESSION_LOG.md` (`[date] [phase] [action] [result]`), and a filled copy of `REVIEW_REQUEST_TEMPLATE.md` saved as `REVIEW_REQUEST.md`.
4. Save every new number as a CSV in `1_midterm/results/` with the script that made it; list `old → new` for every number that changed in the report.
5. Hand over as the branch (push only on an explicit "go") or as `git bundle create review.bundle main..max/midterm-r1`.

**What is shown to the reviewer:** the branch diff, `REVIEW_REQUEST.md`, `1_midterm/analysis/07_validate.py` output, the built PDF, and the `audit_numbers.csv` (number in PDF → source file:line).

**Mac review checklist (I run this):**
- [ ] `git diff main...max/midterm-r1` read in full; no changes in `kaggle_modelling/`; no secrets or hostnames.
- [ ] Re-run `1_midterm/analysis/07_validate.py` (all pass) and `pytest`.
- [ ] Recompute 5 random numbers from raw CSVs independently; spot-check each test with `scipy`.
- [ ] Compile the PDF; read all pages; ≤ 8 pp; no clipped tables; all figures present.
- [ ] Every rubric row in §1 above answered in the PDF.
- [ ] No "accept H0", no modelling content, no invented text (`restaurant`, `blah`, `REPLACE_ME`).
- [ ] Code link works in a logged-out window; README present and accurate.
- [ ] Then, with the user's go: merge to `main`, update `cse558-midterm-2026`, hand the Classroom checklist.

## 6. Stop conditions (the session must stop and ask)
- Any recomputed fact differs from the master prompt.
- A new result contradicts a number already in the report (explain, do not silently change).
- Missing contributions, missing highlighted-PDF source, or unclear dataset provenance claim.
- Anything needing network access to unknown hosts, credentials, or a push.
