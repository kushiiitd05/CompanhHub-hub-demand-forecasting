# MASTER PROMPT — CSE558 Midterm Project Report (Monsoon 2026)

> Paste everything below the line into a fresh Claude session that has file and shell access to
> `~/Desktop/Kaggle_comp_clebal/` and `~/Desktop/Dsc/`. The prompt is self-contained.
> Built on 2026-10-15 from: the midterm guidelines, `CSE558_Project_Report_Template.tex`, Lectures 1–12,
> Quiz 1 rubric and Quiz 2 solutions, our Celebal repo (`Kaggle_comp_clebal`), and a scan of the
> All-India #20 entity-resolution submission (team NOT YET). Every number in §2 was recomputed from the raw CSVs
> on 2026-10-15. Re-verify them anyway (Stage 0).

---

## ROLE

You are the statistician and data steward of a five-person CSE558 group, writing the midterm report for a professor
who is strict about mathematical notation and exact values. You treat the data as evidence: every claim carries a
number you computed, every number traces to a line of code, and no point gets labelled an "outlier" and dropped
until the evidence says what it is. You write in plain, exact English. You never inflate a finding.

## MISSION

Produce a **midterm report (PDF, at most 8 pages, LaTeX template given)** whose core is **statistical inference by
hypothesis testing**. It covers the data from the raw files through preparation, before and after, EDA, problem
statements and 3–5 pre-registered hypothesis tests. Also produce the code and README that reproduce every number.

**This is the preliminary, midterm submission. It contains NO forecasting model, NO feature engineering for models,
NO CV scores and NO leaderboard results.** Our Kaggle modelling work (CatBoost/LightGBM, RMSLE 0.06976) exists, but it
stays out of this report. At most one sentence in §1 may say the data came from a competition. Everything else is data
→ preparation → EDA → inference.

Grading reality (guidelines, verbatim): *"you will be graded based on how much you could dig into and infer from the
data, not on whether a test rejects H0."* Depth of evidence beats positive results.

---

## 1. HARD REQUIREMENTS (from the guidelines and the template; never violate)

| # | Requirement | Where |
|---|---|---|
| R1 | Data source, rows, columns, and **#instances × #attributes ≥ 3,000,000 after encoding, with the arithmetic shown**. Name features and their real-world meaning. | §1 |
| R2 | Preparation: encoding, outliers, missing values, duplicates, **and why** each step (and why not the alternative). | §2 |
| R3 | Before vs after preparation, with observations. | §3 |
| R4 | Basic questions; how our problem statement is **novel** relative to them; a few EDA plots, **each with a one-line takeaway**. | §4 |
| R5 | **3–5 hypothesis tests.** For each: (a) **before running**: H0 (carries the equality), H1, α, one- or two-sided, the test, and the **smallest difference that matters in the real world**; (b) other tests considered and why not used; (c) test statistic, **degrees of freedom**, p-value, decision, **estimate with 95% CI**, and whether the difference is large enough to matter. | §5 |
| R6 | Link to our code and a README. | header table |
| R7 | PDF, **≤ 8 pages**, the given LaTeX template, due **27 Oct 2026, 11:59 pm** on Classroom. Lecture 1 rule: submit **at least 4 hours early**; last-hour Classroom issues are not considered. | — |
| R8 | Template §6 = Limitations (association vs cause, dropped rows, approximate assumptions, groups not covered). | §6 |

**Conflict to resolve:** the template's hint says "2–3 tests"; the guidelines say "3–5". **The guidelines win: run 4
tests** (3 is the floor, 5 is too many for 8 pages).

---

## 2. THE DATA — VERIFIED FACTS (recompute each in Stage 0; stop and report if any differs)

### 2.1 Files (`~/Desktop/Kaggle_comp_clebal/datset_kaggle/`)

| File | Shape | Role in this report |
|---|---|---|
| `orders_train.csv` | 970,379 × 9 | **The analysis dataset.** All tests run on it. |
| `hub_metadata.csv` | 1,115 × 10 | Hub-level attributes; joined on `HubID`. |
| `orders_test.csv` | 46,830 × 8 (no target) | Used **only** for EDA of schedule shift. It has no outcome, so no test uses it. |
| `sample_submission.csv` | 46,830 × 2 (all zeros) | Not used. Mention once as a file, not as data. |

SHA-256 hashes are in `artifacts/eda/audit_summary.json`. Report them in the README.

### 2.2 Provenance: the truth must be stated

- Source: the Kaggle competition **CH'27 Celebal Technologies × IIITD** (hub order forecasting).
- **Evidence the data is a renamed version of the public Rossmann Store Sales dataset (Kaggle, 2015):**
  - hub 1 metadata (1270, Sep 2008, no loyalty) and hub 2 (570, Nov 2007, loyalty since week 13 of 2010, "Jan,Apr,Jul,Oct")
    match Rossmann stores 1 and 2;
  - 1,115 hubs; 180 hubs missing exactly 2014-07-01 to 2014-12-31;
  - 54 open days with zero target;
  - `AppSessions` max 7,388;
  - CompetitorOpenSinceYear 1900 and 1961.
  - Train ends 2015-06-19 and test covers 2015-06-20 to 2015-07-31. 970,379 + 46,830 = 1,017,209, which equals
    Rossmann's train row count.
- Verify what you can. Then state it in §1 in one honest sentence, e.g. "The competition data matches the public
  Rossmann Store Sales data with renamed columns (evidence: …)". Hiding provenance from a strict examiner is a risk;
  disclosing it costs nothing.
- **Semantic finding (the data speaks):** median `OrderVolume/AppSessions` on open days is **9.23**, and the 99.9th
  percentile is 17.19. Nine orders per app session is implausible if `OrderVolume` is a count of orders. The ratio
  behaves like revenue per customer (Rossmann's `Sales/Customers`). Report it as an observed inconsistency between the
  column name and the column's behaviour. Interpret `OrderVolume` as "daily volume (units unstated)". Never call it
  "number of orders" without that caveat.

### 2.3 Every raw column: type (Lecture 2 taxonomy), meaning, verified values

**orders_train.csv** (2013-01-01 → 2015-06-19, 900 dates, 1,115 hubs; 2013: 406,974 rows, 2014: 373,855, 2015: 189,550)

| Column | Lecture-2 type | Meaning | Verified facts |
|---|---|---|---|
| `HubID` | nominal (identifier) | the retail hub | 1–1,115; every hub appears in train, test and metadata exactly as expected |
| `Weekday` | ordinal, cyclic; encode as nominal | day of week, **1 = Monday … 7 = Sunday** | 0 mismatches against `Date` (2013-01-01 is a Tuesday and is coded 2) |
| `Date` | time index (interval) | calendar day | 900 unique; no hub-date duplicates |
| `OrderVolume` | discrete (count-like) | **the response** | 0–38,722; all-rows mean 5,762.8; **open-day mean 6,954.4, median 6,368**; open-day skewness 1.593; kurtosis 7.84 (normal = 3, the Lecture 3 convention); skewness of log(1+x) on positive values −0.11 |
| `AppSessions` | discrete | app sessions (traffic) | 0–7,388; mean 633.3; open-day mean 764.2; Pearson r with orders 0.896 (all rows), 0.825 (open rows) |
| `IsOpen` | nominal (binary) | hub open that day | 804,110 open (82.87%), 166,269 closed |
| `PromoActive` | nominal (binary) | promotion running | 38.27% of rows; **never on Saturday or Sunday (0 rows)** |
| `RegionalHoliday` | nominal, 4 levels | 0 none, 1 public holiday, 2 Easter (dates 03-29 … 04-21: Good Friday and Easter Monday), 3 Christmas (12-25, 12-26) | 96.80 / 2.09 / 0.69 / 0.42%. Open on a holiday: 694 / 145 / 71 rows |
| `SchoolClosureFlag` | nominal (binary) | schools closed | 17.35% of rows |

**hub_metadata.csv** (1,115 rows, one per hub)

| Column | Type | Meaning | Verified facts |
|---|---|---|---|
| `HubFormat` | nominal, 4 levels (do **not** treat as numeric; Lecture 2, "zip code as integer" warning) | store format | 1: 602, 2: 17, 3: 148, 4: 348 hubs |
| `AssortmentTier` | ordinal, 3 levels | product range breadth | 1: 593, 2: 9, 3: 513. **Tier 2 exists only in format 2** (9 of 17 hubs), so format × tier is sparse |
| `CompetitorDistance` | continuous (units unstated; metres in Rossmann) | distance to nearest competitor | 20–75,860; median 2,325; Q1 717.5; Q3 6,882.5; skewness 2.93; **3 missing (hubs 291, 622, 879)** |
| `CompetitorOpenSinceMonth` | discrete/ordinal | competitor opening month | **354 missing (31.7%)** |
| `CompetitorOpenSinceYear` | discrete | competitor opening year | **354 missing**; range 1900–2015; **1900 (hub 815, month 1) is a sentinel or error**; **1961 (hub 146, Oct) is plausible but extreme**; 175 hubs got a competitor inside the train window; 11 after train end |
| `LoyaltyProgram` | nominal (binary) | hub runs the loyalty programme | 571 yes, 544 no |
| `LoyaltyProgramSinceWeek` | discrete | programme start week | 544 missing = **exactly** the 544 hubs with LoyaltyProgram = 0 (0 contradictions either way) |
| `LoyaltyProgramSinceYear` | discrete | programme start year | 2009–2015; same 544 |
| `LoyaltyProgramInterval` | nominal, 3 levels | refresh months | "Jan,Apr,Jul,Oct" 335, "Feb,May,Aug,Nov" 130, "Mar,Jun,Sept,Dec" 106, NA 544 |

**orders_test.csv**: `Id` (1–46,830, date-major, hub-minor), `HubID`, `Weekday`, `Date` (2015-06-20 → 2015-07-31,
complete 1,115 × 42 grid), `IsOpen` (86.02% open; 6,497 of 6,548 closures are Sundays; 4 hubs closed on weekdays),
`PromoActive` (35.71%), `RegionalHoliday` (**all 0**), `SchoolClosureFlag` (**28.51%, vs 17.35% in train**).

### 2.4 Data-quality ledger: every issue found (each becomes a row of the §2 table)

Each row: evidence, then decision, then **why, and why not the alternative**. "No data point is just an outlier":
every extreme gets investigated against its calendar and hub context before any decision.

| # | Issue (verified count) | Diagnosis | Decision and justification |
|---|---|---|---|
| Q1 | **33,121 absent hub-dates** (1,115 × 900 = 1,003,500 expected; 970,379 present) = **180 hubs × 184 days (2014-07-01 → 2014-12-31) + hub 988 on 2013-01-01** | **systematic** block missingness (Lecture 3: "far more dangerous"); the hubs are not closed, they are unobserved | keep them as missing and flag `gap_hub`. **Never zero-fill** (that would invent 33k closures). **Never mean-impute** (it shrinks variance and fakes data inside the very tests that use it). Test the mechanism formally (Test B). Gap hubs by format: 84/602, 1/17, 14/148, 81/348, which hints that format 4 is over-represented. |
| Q2 | **166,269 closed rows**: `OrderVolume` = 0 and `AppSessions` = 0 in all of them (0 violations) | **structural zeros**, not missing values and not outliers | exclude from every test on volume. Analysis base = 804,110 open rows. Including them would mix "is it open?" with "how much?" and give a bimodal mixture. |
| Q3 | **Open with zero volume: 54 rows, 41 hubs**, 2013-01-17 → 2015-05-15; open with zero sessions: 52; sessions > 0 and volume = 0: **2 rows**; volume > 0 and sessions = 0: 0 | logically inconsistent records (an open day with no activity) | flag `open_zero`, exclude from tests (54 / 804,110 = 0.0067%), and list them in the appendix/README. Sensitivity: rerun one test with them included. Optional Lecture 9 link: MLE p̂ = 54/804,110 for the anomaly rate, with a CI. |
| Q4 | **Global IQR fence on open-day volume**: Q1 4,856; Q3 8,360; IQR 3,504; upper fence 13,616; **29,307 rows above (3.64%), 0 below** (lower fence −400) | the pooled fence mixes hub scale with anomaly: format-2/tier-3 hubs average 18,001 on normal days. Right skew 1.59 | **do not delete.** Show that the pooled fence mostly flags large hubs, which is a **wrong-unit** problem, not an outlier problem. Analyse on log(1+x) and on hub-level aggregates. |
| Q5 | **Per-hub robust z** (median/MAD, \|z\| > 3.5): **6,220 rows across 1,040 hubs** | within-hub extremes; investigate by context | cross-tabulate them against holidays, promo, the days before and after a closure run, and reopening after Q7. Expectation (verify): most are explained by calendar events, so they are genuine. Keep genuine ones. Winsorise only in a labelled sensitivity check. **Example:** the maximum, 38,722 (hub 262, Fri 2015-04-03, Good Friday, holiday code 2, promo on), is a genuine Easter peak, not an error. |
| Q6 | **Lecture 11 Chebyshev check**: share of open days with \|z\| ≥ 2, 3, 4 is 4.24%, 1.59%, 0.60%, against Chebyshev bounds of 25%, 11.1%, 6.25% | the distribution-free bound holds with room to spare; the "3σ ⇒ 0.3%" rule assumes normality, which fails (kurtosis 7.84) | use this to justify **why a normal-theory 3σ rule is not our outlier rule**. Brief, one sentence plus numbers. |
| Q7 | **Closure runs** (gap-aware): 1-day 145,746; 2-day 9,299; **88 runs of ≥ 5 days at 85 hubs; 45 runs ≥ 14 days; longest 185 days** | multi-week weekday closures = refurbishments (not Sundays or holidays) | flag `long_closure` and the 14 days after each reopening (`reopen_window`). Inspect the post-reopening surge. Exclude reopen windows in a sensitivity rerun of the volume tests. |
| Q8 | **Conversion ratio** volume/sessions: median 9.23, 99.9th percentile 17.19, **max 64.96** (hub 897, Mon 2013-09-02: 16,954 / 261); **23 rows > 30** | sessions under-recorded (or volume mis-keyed) on a few days | flag `ratio_anomaly`. It only matters for tests that use sessions. Show 2–3 rows as evidence. |
| Q9 | `CompetitorDistance` missing for 3 hubs | unknown; too few to diagnose a mechanism | complete-case for distance tests (n = 1,112). State it. Median imputation would place 3 hubs at an invented distance in a correlation test. |
| Q10 | `CompetitorOpenSince*` missing for 354 hubs (31.7%); distance known for all but 3 of them | opening date unknown (competitor exists, date not recorded) | keep as NA plus an indicator. **No year imputation**: a guessed date would corrupt the competitor-opening analysis (Test D). |
| Q11 | `LoyaltyProgramSince*` / `Interval` NA for 544 hubs = exactly LoyaltyProgram = 0 | **not missing: not applicable** | encode as the level "None". Quiz 1, Q8(e): treating missing as its own category is legitimate. |
| Q12 | `CompetitorOpenSinceYear` = 1900 (hub 815), 1961 (hub 146) | 1900 = sentinel/error; 1961 = plausible | 1900 → NA plus a flag (an "1900 opening" would be a 115-year tenure). Keep 1961 and flag it. Show both rows. |
| Q13 | 8 hubs share identical metadata with another hub (473, 722, 651, 773, 426, 557, 26, 436); their volume series are **not** identical | **not duplicates**: distinct hubs with the same attributes | keep all. Say so explicitly, because the professor checks duplicate handling. Full-row duplicates: 0. Hub-date duplicates: 0 (train and test). |
| Q14 | 17 hubs open on 2013-01-01 (a holiday); 910 open holiday rows; 3,400 open Sunday rows at **33 hubs** | genuine operating patterns | keep. Stratify: any weekday comparison excludes Sunday, or else restricts to the 33 Sunday hubs. |
| Q15 | PromoActive is never on a weekend; Monday promo means 9,762 vs 6,211 without (+57%), Friday 7,733 vs 6,358 (+22%) (descriptive, `tables/weekday_promo_target.csv`) | promo is confounded with weekday | every promo comparison runs **within weekday, Mon–Fri only**. |
| Q16 | Last digit of open-day volume (≥ 100): counts 80,036–81,052 per digit | integrity check: no heaping or rounding | Lecture 8 χ² goodness of fit against uniform (df = 9) **as a data-integrity check**, not one of the 4 tests. One line in §2. |
| Q17 | Train vs test schedule: SchoolClosureFlag 17.35% → 28.51%; RegionalHoliday has no non-zero values in test; IsOpen 82.87% → 86.02% | the summer window differs from the history | EDA plot or table only (the test file has no outcome). Takeaway: the test window is a school-holiday period. |
| Q18 | Types: `HubFormat` and `RegionalHoliday` stored as integers but nominal; `Weekday` cyclic | encoding must match type (Lecture 2) | one-hot `HubFormat` (4), `RegionalHoliday` (4), `Weekday` (7), `LoyaltyProgramInterval` (3 + None). Integer-code `AssortmentTier` (ordinal). Derive Year/Month/DayOfMonth/ISOWeek from `Date`. Binary flags stay 0/1. Log-transform only as an **analysis scale**, never by overwriting the raw column. |

### 2.5 Size check (R1): compute exactly, show the arithmetic

- Raw: 970,379 × 9 = **8,733,411** ≥ 3,000,000 (already met before encoding).
- After preparation: (rows kept) × (attributes after the metadata join, one-hot encoding and flags) = the exact number.
  Count the attributes in code and list them in the README. Do not hand-count.
- State the unit of analysis honestly. Size is counted on hub-days, but **inference uses hubs as the independent unit**
  (see §3, rule S5).

### 2.6 Existing work to reuse (re-run, don't trust blindly)

`~/Desktop/Kaggle_comp_clebal/`: `src/eda_pipeline.py` (audit), `tests/test_eda_pipeline.py`,
`artifacts/eda/{EDA_FINDINGS.md, audit_summary.json, tables/*.csv, figures/*.png}`. The tables include
`lag_correlations.csv`: median within-hub correlation at lag 7 = 0.54, lag 14 = 0.70, lag 364 = 0.70. That is the
evidence that hub-days are **not independent**. Python: `/opt/anaconda3` base, or the `eda311` conda env. Do not create
new environments. The data is ~70 MB, so a laptop is enough and no GPU is needed.

---

## 3. STATISTICAL STANDARDS (the professor's rules plus ours; enforce in every line)

- **S1 Notation.** Define every symbol before use ($\mu$, $\bar{x}$, $s$, $n$, $d_i$, $\bar d$, $s_d$, $r$, $p$, $\hat p$).
  Population parameters are Greek; estimates are Latin or hatted. Sample variance uses $n-1$ (Lecture 6).
  Moment-based skewness and kurtosis follow the Lecture 3 convention (normal kurtosis = 3); say which skewness coefficient
  you use. State the quartile convention (Quiz 1 notes that conventions differ).
- **S2 Hypotheses.** H0 carries the equality (=, ≤ or ≥). H1 is the claim under study. α = 0.05 is fixed in advance.
  The side is fixed in advance and justified by the problem statement (Lecture 5: "decide the direction before you see
  the data"). The smallest meaningful difference is stated in units with a real-world reason.
- **S3 Language.** "Reject H0" or "fail to reject H0". **Never "accept H0"** (Lecture 5). A non-significant result
  plus a CI inside ± the meaningful difference = "no effect large enough to matter", which is a finding.
- **S4 Master pattern.** Show each statistic as (estimate − null value) ÷ (standard error), except χ² and F, which are
  ratios (Lecture 6). Write the formula you used, with numbers substituted, in one line.
- **S5 Independence.** Consecutive days of one hub are correlated (lag-7 r ≈ 0.54). **Never run a test treating
  ~800k hub-days as iid**: the p-values would be meaninglessly small. **Aggregate to one value per hub** (n ≈ 1,115) or
  use within-hub paired differences. Explain this in one sentence in the test's part (b). This is the strongest rigour
  signal the report can send.
- **S6 Degrees of freedom.** Report them for every test. Welch: Satterthwaite df (non-integer is allowed; give the
  formula). Pooled: $n_1+n_2-2$. Paired: $n-1$. Correlation: $n-2$. χ² independence: $(r-1)(c-1)$. χ² GOF: $k-1$.
  F: $(n_1-1, n_2-1)$.
- **S7 Critical values.** Match one-sided vs two-sided correctly. (Quiz 2's key prints 1.860, the **one-sided**
  df = 8 value, under a two-sided label; the two-sided value is 2.306. Do not repeat that slip.) Report exact p-values
  from software, plus the critical value.
- **S8 Assumption checks.** Before a pooled t, run the F-test on variances (Lecture 8 does exactly this). For χ²,
  check expected counts ≥ 5 and merge sparse levels if needed (format 2 has 17 hubs). For t-tests, state normality of
  the **sample mean** via the CLT (Lecture 4) on hub-level n ≈ 1,000, and show a Q-Q plot of the per-hub differences.
- **S9 Effect sizes.** Every test gets an estimate + 95% CI in natural units: % change via $e^{\bar d}-1$ for
  log-scale differences; r for correlations; the difference in proportions. Then compare it with the pre-stated
  smallest meaningful difference: is the **whole CI** beyond it, straddling it, or inside it?
- **S10 Multiplicity.** We run 4 tests. Report raw p-values, and also state whether each decision survives Bonferroni
  (α/4 = 0.0125). One line; don't overclaim.
- **S10b Lecture 3 practices to apply visibly:**
  - pair every boxplot with a histogram, since boxplots hide bimodality (closed + open days are bimodal);
  - before any correlation test, check outliers and approximate normality first (log-transform distance and volume);
  - for each missing-value decision, name the Lecture 3 alternatives rejected: deletion, mean/median/mode imputation,
    kNN-average, regression imputation;
  - for noise, name binning/smoothing and regression residuals as considered options;
  - re-ask "does an outlier still exist?" after each fix (Lecture 3: cleaning is iterative), and show that second
    pass.
- **S10c Lectures 9–12 (use lightly, only where they add rigour):**
  - MLE p̂ for the open-but-zero anomaly rate (Q3);
  - Chebyshev for the distribution-free outlier argument (Q6);
  - optionally a Chebyshev/Chernoff sample-size argument that n ≈ 1,000 hubs gives a tight estimate of a proportion
    (Quiz 2, Q13c style).
  - Do not force MAP or Bayes in; there is no natural prior here.
- **S11 Every number traceable.** Each number in the PDF appears in a script's printed output or a saved CSV. Round
  only at the end (estimates 3 significant figures, p-values 2 s.f. or "< 10⁻ᵏ"). Counts are exact with thousands
  separators.

---

## 4. METHOD IMPORTS from the All-India #20 submission (team NOT YET, entity resolution, macro F0.5 0.990794)

Their problem (record matching, LightGBM stacks, cross-encoders) is **not** ours. Copy their **measurement
discipline**, not their models:

| Their practice | Our adaptation (midterm-legal, no modelling) |
|---|---|
| "Inverting the generator": they reverse-engineered how the organisers corrupted the data | provenance check against Rossmann (§2.2); the semantic ratio finding; the last-digit integrity χ² (Q16); a hunt for injected noise. If you find any field that differs from Rossmann structure (e.g. renamed or shifted codes), **report it** |
| Label-free "generator-rate" check: the test-set rate per category should equal the train rate | the schedule-shift table, train vs last 42 train days vs test (Q17), with χ² goodness of fit or PSI as EDA |
| Split halves and a standard error for every rate they used | **replication check**: rerun each test separately on 2013 and on 2014–15 (or odd vs even HubID) and report whether the direction and decision hold. One line per test |
| A calibration set with a known answer (the 1,287 "known ~92% decoy" pairs) | **placebo / A-A check** for the event and promo tests: shift the competitor-opening date back by 12 months, or permute promo labels within hub × weekday. The test should then reject at about rate α. Report the placebo's p-value |
| Ten tested-and-rejected hypotheses reported honestly | a short "what did not hold" list in §4/§6. Failed hypotheses are findings |
| Break-even cost (a false merge costs 0.21, a missed copy 0.09) set their thresholds | the smallest meaningful difference comes from a real-world cost (e.g. a promotion must lift volume ≥ 5% to pay for itself); write that reasoning |
| md5 at every step; byte-identical rebuild | SHA-256 of the raw files in the README; one command regenerates all tables and figures; a row-waterfall table shows where each removed row went |
| Hash-based hold-out buckets (crc32) so nothing tuned saw the hold-out | fix every analysis choice (windows, exclusions, thresholds) in `preregistration.md` **before** computing any test statistic; commit it first (git timestamp = proof) |

---

## 5. PROBLEM STATEMENTS AND TEST MENU (pick 4; at least 3 must use different lecture tests)

Basic questions (for §4; descriptive, not novel): Does promo raise volume? Which format sells most? Are Sundays
different? Do volume and sessions move together?

Novelty angle: our statements need **within-hub contrasts, events in time, or missingness itself**, none of which a
single row records.

**P1 (primary): Does a promotion's lift decay across the working week?**
- *Test A, paired t-test (Lecture 7).* For each hub *i*, $d_i$ = (mean log(1+V) on promo Mondays − non-promo Mondays)
  − (same for Fridays), using open, non-holiday, non-flagged days.
- H0: $\mu_d \le 0$; H1: $\mu_d > 0$ (Monday lift larger); one-sided; α = 0.05; df = n − 1.
- Smallest meaningful difference: 5 percentage points of lift (≈ 0.05 on the log scale). Justify it.
- Alternatives:
  - Welch on pooled days: ignores pairing and S5;
  - z: σ unknown;
  - pooled two-sample t: the groups are paired;
  - sign test: discards magnitude. Mention it as a robustness check.

**P2: Is the 184-day data gap random with respect to hub type (missingness mechanism, Lecture 3)?**
- *Test B, χ² test of independence (Lecture 8/9)* on HubFormat × gap (4 × 2, df = 3). Format 2 has an expected count of
  ≈ 2.7, so merge it with the nearest format (or report Fisher's exact test as a check). State the merge rule before
  running.
- Follow-up in the same test block, as the estimate: the difference in gap proportion, format 4 vs the rest, with a
  95% CI. Alternatives: two-proportion z (Lecture 7: only one contrast); goodness of fit (wrong question).
- Implication either way: if missingness is not random, any 2014-H2 comparison is biased toward the non-gap formats.
  This test **justifies our Q1 decision**.

**P3: Do hubs with closer competitors have lower volume?**
- *Test C, t-test on the correlation coefficient (Lecture 7).* Hub-level: r between log(CompetitorDistance) and the
  hub's mean log(1+V) on open days; n = 1,112; df = n − 2; two-sided. Smallest meaningful: |r| ≥ 0.10.
- Alternatives: Spearman (report as a robustness check, since distance has skewness 2.93); a regression slope t
  (equivalent); two-group Welch on a distance split (throws away information).
- If the sign is **positive** (close competitors ↔ higher volume), explain urban density as a hidden third factor
  (Lecture 3 "spot the fake correlation"). That is a strong "data speaks" moment.

**P4: Does a competitor's opening reduce a hub's volume (event study)?**
- *Test D, paired t-test on a difference-in-differences.* Use the ~175 hubs whose competitor opened inside the window.
  Per hub: the change in mean log(1+V) from the 8 weeks before to the 8 weeks after the opening month (excluding the
  month itself), minus the same change for the same calendar weeks at control hubs without a new competitor.
  Seasonality cancels out.
- H0: $\mu_{\Delta} \ge 0$; H1: $\mu_{\Delta} < 0$; one-sided; smallest meaningful −3%.
- State the exclusions: month precision only; hubs in the 2014-H2 gap; 1900/1961 years. Run the placebo (shift 12
  months).
- Alternatives: before/after without a control (seasonality-confounded); Welch between treated and control (ignores
  pairing).

**P5 (optional; use if one of A–D is infeasible): Does a promotion change day-to-day volatility?**
- *F-test for two variances (Lecture 7).* Per hub, take the variance of log(1+V) residuals on promo vs non-promo
  weekdays. Test H0: σ²_promo = σ²_none at the hub level with a paired log-variance-ratio t, or run an F-test on one
  pre-chosen format. Use it as the variance-equality check that decides pooled vs Welch.

Every test: run the replication split (§4) and, where defined, the placebo. Add one line on what would change our mind.

---

## 6. EXECUTION PROTOCOL (prompt chaining; finish and show each stage's output before the next)

**Stage 0: Verify.**
- Recompute every number in §2 with one script (`analysis/00_verify.py`). Print a table: claimed | recomputed | match.
- **If any mismatch, stop and report.** Do not proceed on stale numbers.

**Stage 1: Dataset (§1).**
- Source sentence, provenance sentence, raw shape table, size arithmetic (§2.5), 6–8 key features table with types and
  meanings, and the response variable.

**Stage 2: Preparation (§2).**
- Implement Q1–Q18 in `analysis/01_prepare.py` as **pure functions returning new DataFrames** (never mutate the raw
  frames).
- Output: the cleaned hub-day table, a hub-level table, a flag table, a **row waterfall** (raw → after each step, with
  counts), and the condensed §2 LaTeX table (one row per issue: issue found | what we did | why, and not the
  alternative).
- Merge minor rows so the table fits about ⅓ of a page. The full ledger goes in the README.

**Stage 3: Before / after (§3).**
- Table of rows, attributes, missing cells per column, flagged anomalies, duplicates, skewness/kurtosis of volume
  (raw vs log scale), and the share of the IQR fence flags explained by calendar context.
- Close with a 3-sentence observation paragraph.

**Stage 4: EDA, questions, problem statements (§4).**
- Make 3–4 figures (PDF vectors, readable in one column). Suggested:
  1. volume distribution, raw vs log, open days;
  2. the gap/missingness heat strip (hubs × dates), or the gap share by format;
  3. promo lift by weekday with hub-level CIs;
  4. per-hub mean volume vs log competitor distance.
- Each caption is a **single-sentence takeaway with a number**. Use a colour-blind-safe palette.
- Then the basic questions, the boxed problem statements (P1 primary), and the novelty sentence.

**Stage 5: Pre-registration.**
- Write `preregistration.md` containing, for each chosen test: hypotheses, α, side, test, smallest meaningful
  difference with its reason, unit of analysis, exclusions, windows, sparse-level merge rules, robustness and placebo
  plans.
- **Commit it before Stage 6.** Do not compute any test statistic before this exists.

**Stage 6: Run the tests (§5).**
- `analysis/02_tests.py` prints, per test: n, the statistic with the formula substituted, df, critical value, p, the
  decision, the estimate, the 95% CI, the practical-significance verdict, the Bonferroni line, replication, placebo and
  the assumption checks.
- Cross-check each test against `scipy.stats` **and** a manual formula. They must agree to 4 significant figures.

**Stage 7: Limitations (§6).**
- Cover:
  - association vs cause (promo timing is chosen by the business; competitor openings are not random);
  - the excluded rows and flags;
  - provenance (a renamed public dataset, units unstated);
  - month-level precision of the event dates;
  - multiplicity;
  - test-window shift (schools closed).
- 5–6 bullets.

**Stage 8: Write the LaTeX.**
- Fill `CSE558_Project_Report_Template.tex`: set `\projecttitle`, set `\showhintsfalse`, and **replace every `\eg{}`
  and `\egblock{}` example** with our content as plain text. No light-blue example text may remain.
  `grep -c '\\eg' report.tex` must return 0 matches of example usage.
- Header table: group name, dataset (Kaggle competition URL + the Rossmann note), code link (GitHub repo with README),
  and members, roll numbers, emails and contributions as **placeholders `<<FILL>>`** (do not invent names).
- Compile with pdfLaTeX twice. **≤ 8 pages**: check with `pdfinfo`.

**Stage 9: Audit (Reflexion pass).**
- Act as the strict professor:
  - every symbol defined;
  - every H0 has the equality;
  - every test has all of (a), (b), (c);
  - every number matches the script output (build `audit_numbers.csv`: number in PDF → source file:line);
  - no "accept H0";
  - no modelling content;
  - no claim without a number;
  - no number without a source.
- Fix, recompile, report the page count, and list remaining risks.

---

## 7. CONSTRAINTS

- No modelling, forecasting, feature importance, CV or leaderboard content in the PDF.
- No invented numbers, names, roll numbers or links. Use `<<FILL>>` placeholders for anything unknown.
- Do not delete raw files or overwrite `datset_kaggle/`. Write everything new under `~/Desktop/Dsc/dsc proj/midterm/`
  (`analysis/`, `figures/`, `tables/`, `report/`, `README.md`, `preregistration.md`).
- Do not zero-fill or mean-impute the 2014-H2 gap. Do not drop extremes without contextual evidence.
- Do not mention internal infrastructure (servers, GPUs, cluster paths) in the report or README.
- Keep code files under 400 lines and functions under 50 lines; use type hints; never mutate input frames.

## 8. DELIVERABLES (in this order, each shown before moving on)

1. `00_verify` table (Stage 0).
2. Cleaning ledger + row waterfall + before/after table.
3. Figures + captions.
4. `preregistration.md` (committed).
5. Test results block, one per test.
6. `report.tex` + `report.pdf` (≤ 8 pages) + `README.md` (how to run, file hashes, the full cleaning ledger, the list
   of flagged rows).
7. Audit report: `audit_numbers.csv`, remaining risks, `<<FILL>>` items the team must complete.
