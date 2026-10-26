# Analysis plan, revision r1 (fixed before any r1 test statistic was computed)

**Honest status.** This is not a pre-registration in the strict sense. The four questions were chosen after
exploratory analysis, and an earlier version of all four tests (raw-order scale, report v0) had already been run
and its results were known. What this file fixes *before* computing the r1 statistics is every analysis choice
of the revised tests: scale, unit, exclusions, windows, sides, thresholds, merge rules, robustness and placebo
plans. Its git commit precedes the commit of `analysis/02_tests.py` results. Because the v0 directions were
already known, **all four tests are two-sided**; picking a side now would be choosing it after seeing the data.

Common rules
- α = 0.05 per test; multiplicity: Bonferroni α/4 = 0.0125 and Holm, both reported; decisions stated at α = 0.05.
- Analysis scale: y = log(1 + OrderVolume). Base rows: IsOpen = 1 and OrderVolume > 0 (excludes 166,269 closed
  rows, structural zeros, and the 54 open-zero rows). The 2014-H2 gap is never filled.
- Independence (S5): consecutive days of a hub are correlated, so **the hub is the unit**; every test has one
  number per hub.
- Each test is cross-checked with `scipy.stats` and with a manual formula (agree to 4 s.f.).
- Language: reject / fail to reject H0. Practical verdict: compare the whole 95% CI with the smallest meaningful
  difference δ (entirely beyond, straddling, or entirely inside ±δ).
- δ values are our assumptions, with the reason given; no business partner supplied them.

## T1 (P1, primary): is the promotion lift different on Monday and Friday?
- Rows: base rows on Mondays and Fridays with RegionalHoliday = 0 and reopen_window = 0.
- Per hub i: L_i,Mon = mean y on promo Mondays − mean y on non-promo Mondays; L_i,Fri likewise;
  d_i = L_i,Mon − L_i,Fri. A hub enters if each of its 4 cells has ≥ 4 days.
- H0: μ_d = 0; H1: μ_d ≠ 0; two-sided. Test: paired t (one-sample t on d_i), t = d̄ / (s_d/√n), df = n − 1.
- Effect in natural units: e^{d̄} − 1 = ratio of the Monday to the Friday multiplicative lift, minus 1.
- δ = 0.05 log points (≈ 5% of volume). Reason: below a 5% difference the choice of which weekday carries the
  promotion budget would not change.
- Alternatives named: Welch on pooled hub-days (ignores pairing and dependence); pooled two-sample t (groups are
  paired); z-test (σ unknown); Wilcoxon signed-rank and sign test (reported as robustness).
- Checks: Q-Q plot of d_i; Wilcoxon; sign test; raw-scale version (v0 comparability).
- Replication: 2013 vs 2014-15 rows; odd vs even HubID.
- Placebo: within each hub × weekday, permute the promo labels (seed 558), recompute the test; 200 replicates,
  report the share with p < 0.05 (expected ≈ 0.05) and the first replicate's t, p.

## T2 (P2): is the 184-day data gap independent of hub format?
- Unit: hub, n = 1,115. G_i = 1 if hub i has no rows 2014-07-01..2014-12-31.
- H0: P(G = 1 | format f) equal for f = 1..4; H1: not all equal. Pearson χ² on the 4 × 2 table, df = 3.
- Sparse-cell rule (fixed now): min expected count is < 5 (format 2 has 17 hubs), so the primary p-value is the
  Monte Carlo permutation p (100,000 label shuffles, margins fixed, seed 558); the asymptotic χ²(3) p is also
  reported; check: merge format 2 into format 1 (the largest) → 3 × 2, df = 2.
- Estimate: Cramér's V with hub-bootstrap 95% CI (5,000) and the follow-up contrast p̂_4 − p̂_rest (format 4 vs
  the other formats) with a Wald 95% CI (Newcombe hybrid score as a check).
- δ = 5 percentage points in a format's gap rate (overall rate is 16.1%). Reason: a 5-point difference changes the
  format mix of hubs observed in 2014-H2 enough to bias any format-level comparison over that period.
- Alternatives: two-proportion z (only one contrast); G-test (same asymptotics); Fisher exact (2 × 2 only; the
  permutation test is its Monte Carlo analogue for 4 × 2); goodness-of-fit χ² (wrong question).
- Replication: odd vs even HubID.

## T3 (P3): is competitor distance associated with a hub's typical volume?
- Unit: hub with known distance, n = 1,112 (hubs 291, 622, 879 have no distance; complete-case).
- x_i = ln(CompetitorDistance); y_i = mean y over the hub's base rows.
- H0: ρ = 0; H1: ρ ≠ 0. Pearson r, t = r √(n−2) / √(1 − r²), df = n − 2 = 1,110. CI by Fisher z.
- δ = |ρ| ≥ 0.10 (1% of between-hub variance). Reason: a smaller association would not inform siting decisions.
- Robustness: Spearman ρ_s; y without reopen windows; within-format Pearson r (density/format confounding).
- Alternatives: regression slope t (identical t); Spearman/Kendall (robustness); Welch on a near/far split (throws
  away information); raw-scale Pearson (skewness 2.93 of distance; outliers dominate).
- Replication: y from 2013 rows vs 2014-15 rows.

## T4 (P4): does a competitor's opening change a hub's volume? (difference-in-differences)
- Treated hubs: competitor opening month m_i known (sentinel 1900 removed) with m_i in 2013-03..2015-03, so that
  the pre window (56 days before the first day of m_i) and post window (56 days after the last day of m_i) both
  lie inside 2013-01-01..2015-06-19. The opening month itself is excluded (month precision only).
- Controls: hubs whose competitor opened in or before 2011-12 or after 2015-06-19 (date known); hubs with an
  unknown date are excluded from both groups.
- Per treated hub: Δ_i = ȳ_post − ȳ_pre (base rows; ≥ 30 rows in each window, otherwise excluded, which removes
  gap hubs whose windows hit the gap). C_i = mean of the same change over control hubs with ≥ 30 rows in each of
  the same two windows. DiD_i = Δ_i − C_i. Seasonality, holidays and the shared promo calendar cancel.
- H0: μ_DiD = 0; H1: μ_DiD ≠ 0; paired t (one-sample t on DiD_i), df = n − 1. Effect: e^{mean} − 1.
- δ = 3% (0.03 log points). Reason: a fall below 3% is within normal week-to-week noise of a hub's level and
  would not justify a response.
- Alternatives: before/after without control (v0; seasonality-confounded); Welch treated vs control (ignores the
  pairing in time); Wilcoxon on DiD_i (robustness).
- Sensitivity: windows of 28 and 84 days; controls restricted to the same HubFormat; reopen windows excluded.
- Replication: odd vs even HubID; openings in 2013 vs 2014-15.
- Placebo: move every opening 12 months earlier (eligible months 2014-03..2015-03 → 2013-03..2014-03), rerun;
  expected μ ≈ 0.

## Not tested (descriptive only, to avoid multiplicity)
Schedule shift train vs test; reopening surge after long closures; school-closure effect; volume/session ratio.
