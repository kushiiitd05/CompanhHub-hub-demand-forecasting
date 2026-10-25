[2026-10-26] [1.1 verify] 00_verify.py recomputes 125 master-prompt facts from raw CSVs [125/125 match after fixing 3 definitions on our side: 175 vs 180 openings, 4 metadata pairs, robust z on volume>0]
[2026-10-26] [1.2 P0] report rebuilt on official template; title without "Forecasting"; "restaurant" removed; provenance + units caveat added; contributions drafted as <<CONFIRM>> [done]
[2026-10-26] [1.3 plan] analysis_plan_r1.md committed (8135148) before r1 test statistics [done]
[2026-10-26] [1.3 tests] T1 log + placebo + week-level; T2 + follow-up CI; T3 Pearson-on-log (reverses v0: now reject, p=0.0063); T4 DiD + placebo [all 4 reject; Bonferroni and Holm]
[2026-10-26] [1.4 build] main.pdf 6 pages (TeX Live, pdfLaTeX x2); validator 30/31 (placeholders only); pytest 9/9; audit 576/576 numbers traced
[2026-10-26] [1.4 rerun] run_all.py from scratch reproduces every table (only diff: inf->blank in a raw-scale pct column); figures now byte-identical across runs
[2026-10-26] [1.5 handover] REVIEW_REQUEST.md filled; branch max/midterm-r1 local; bundle at kush_work/review_midterm_r1.bundle; no push
