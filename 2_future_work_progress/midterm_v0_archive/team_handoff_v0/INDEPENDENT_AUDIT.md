# CSE558 Midterm: Independent verification and last-mile fixes

Audit date: 25 October 2026. Evidence: user-uploaded `CSE558_RAW_INPUTS.zip` (orders_train.csv, orders_test.csv, hub_metadata.csv), user-uploaded `midterm.zip`, the official guidelines/template, and the public `cse558-midterm-2026` GitHub branch as inspected in this conversation.

## Independent verification results

| Check | Result |
|---|---|
| Raw train | 970,379 rows × 9 columns |
| Test | 46,830 rows × 8 columns |
| Hub metadata | 1,115 rows × 10 columns |
| Unique hubs/dates | 1,115 hubs; 900 dates |
| Unique hub-date keys | 970,379; 0 duplicate keys |
| Missing training cells | 0 |
| Correct weekday coding | Monday=1, Sunday=7 verified |
| Open/closed hub days | 804,110 / 166,269 |
| Open zero-order days | 54 |
| Closed nonzero-order days | 0 |
| Encoded training table | 970,379 × 35 = 33,963,265 entries |
| IQR extreme open-order observations | 29,307 (3.64%), retained |

All four primary statistical estimates were recomputed independently from raw CSVs and matched saved outputs:

- T1 (hub-level paired Monday-Friday promotion contrast): n=1,115; mean +2,168.766 orders, t(1114)=64.84286, 95% CI [2,103.1408, 2,234.3913], p reported <0.001 (floating underflow to zero in scipy).
- T1 corrected one-way hub fixed-effects sensitivity: interaction +2,183.580 orders. Independently reproduces coefficient; confidence interval differs by around 0.03 order due to cluster sandwich correction implementation. Date-level hub-centered HAC(8) sensitivity: +2,015.064, CI [1,545.868, 2,484.260], p=3.846e-17.
- T2 (4×2 hub format by >=100-day historical gap): χ²(3)=21.416493, Cramer's V=0.138592; 5,000-replicate bootstrap CI [0.086187,0.201415] reproduced. Conditional permutation check using 50,000 draws gives p approximately 0.00018 (sampling variability explains difference from 20,000-draw recorded p~0.00020).
- T3: n=1,112, Spearman rho=-0.0316874, p=0.291084, Kendall tau=-0.0192645, p=0.336364.
- T4: n=120, mean post-minus-pre=-482.4243 orders, t(119)=-5.693427, 95% CI [-650.2052,-314.6434], p=9.133e-08.

These are **observational** analyses, not causal promotion/competitor effects.

## What still blocks submission

1. **Real team-member contributions.** The report and `midterm/member_contributions.csv` contain `blah 1` through `blah 5`. An earlier automatic validator incorrectly passed this. The included corrected validator now fails until these are replaced with real, truthful contributions.
2. **Layout.** The original report's Table 5 overlapped the next column. The included corrected LaTeX source and preview PDF fix this with a column-width resize and remain four pages. The preview still contains the old contribution placeholders, so **DO NOT SUBMIT THE PREVIEW**.
3. **Stale report wording.** Corrected here: T1's text no longer says the already-computed HAC sensitivity still needs examination. Test 2 long gap now explicitly says >=100 consecutive missing days; mathematical null equalities are explicit; duplicate Test 2 CI sentence is removed.
4. **GitHub branch not updated.** Last observed branch head 246235ef, dated 23 October 2026, predates the latest `midterm.zip`. Push the corrected midterm files, current analysis scripts and `midterm/README.md`. You need repository write access.
5. **Final recompile and visual check.** Generate the final PDF after completing actual contributors and re-run the improved validator. Keep PDF <=8 pages and submit on Classroom by **27 October 2026, 11:59 PM**.

## Exactly what to do next

1. Extract this ZIP. Open your repository's `cse558-midterm-2026` checkout. The repository must contain the latest `midterm` folder and the associated Python scripts, not just the old GitHub branch.
2. Run `python apply_final_layout_fixes.py --repo "C:\\full\\path\\to\\ShadowDsc10-ShadowHub"` from the extracted ZIP folder. It patches `midterm/report/main.tex` and updates the existing `validate_midterm.py`.
3. Open `<repo>/midterm/member_contributions.csv` and replace `blah 1`–`blah 5` with the actual work of each member. From `<repo>` run `python fill_team_contributions.py --repo .`. Verify `main.tex` no longer contains `blah`, `TBD`, or other placeholders.
4. From `<repo>`, run `python complete_midterm.py --repo .`. This re-runs the analysis, generates PDF and builds the submission ZIP **only if checks pass**. `linearmodels`, `pypdf`, `pdflatex` and other packages from `requirements-midterm.txt` must be available. If a script errors, fix it before submitting; do not reuse previous generated PDF.
5. Open all PDF pages and look for overlaps or missing figures; verify corrected page-4 Table 5. If you have not confirmed the professor's provided LaTeX styling is satisfied, compare visually with the template's example before submission.
6. Push actual corrected scripts, README and latest `midterm` report/results to the GitHub `cse558-midterm-2026` branch. Inspect the link in an incognito browser to verify access.
7. Submit the **final PDF** on Classroom before the deadline. The supplied template also asks for a script/notebook upload on Classroom; provide the compact script ZIP or individual scripts as permitted by Classroom. The official guidelines require an accessible code link and README. Do not upload a massive entire repo unless asked.

## Source integrity / important limitations

The analyses are verified numerically on the supplied raw data. This patch does **not** assert authorship or invent contribution roles. The code has an actual `linearmodels` dependency; ensure environment installs the listed dependencies. This independent audit does not turn observational associations into causal claims. The user-uploaded report and source package were not yet pushed to GitHub as of the observed commit.
