# STATUS (snapshot 2026-10-26, after the restructure and the r1 merge)

## Deadlines
| What | When |
|---|---|
| CSE558 midterm report (PDF, ≤ 8 pages), Classroom | **27 Oct 2026, 23:59 IST**; aim to submit by 19:00 |
| Presentation | separate, guidelines not yet shared |
| Improvement work (target public LB < 0.06) | after the midterm is submitted |

## Repo map (`main`)
| Path | What | State |
|---|---|---|
| `1_midterm/` | **The submission:** `data/raw`, `analysis`, `tests`, `results`, `figures`, `report`, `docs`, `reference`, `README.md` | Report built, 6 pages |
| `2_future_work_progress/kaggle_modelling/` | Earlier modelling work (public LB 0.06976) | Frozen |
| `2_future_work_progress/improvement_plan/` | Audit of the model and a phased plan | Not started |
| `2_future_work_progress/midterm_v0_archive/` | First report version and its tools | Archive only |
| `2_future_work_progress/server_run/` | Hand-off files for the server session | Active |

## Midterm: done
- Four tests rerun on the log scale with replication, placebo and Bonferroni/Holm; T4 is a difference-in-differences against control hubs.
- 125 data facts recomputed from the raw files (all match); 9 unit tests pass; one command (`analysis/run_all.py`) rebuilds every table and figure.
- Independent review on the Mac matched T1–T3 and the key counts, and a full rerun reproduced every result to 3e-13.
- Report text: no competition names; dataset link is the repo's `1_midterm/data/raw`; key values highlighted in colour; the T1 wording is corrected (ratio of promotion multipliers 1.600 / 1.222 = 1.309).

## Midterm: open
1. **Contributions:** the five lines in the header of `1_midterm/report/main.tex` are drafts marked `<<CONFIRM: …>>`. Each member must confirm or rewrite theirs. Do not invent them.
2. Names and emails were copied from the first report (`Kush23296@…` has a capital K): confirm.
3. Rebuild the PDF after step 1 (`tectonic main.tex` or Overleaf); check ≤ 8 pages.
4. Push the final state to branch `cse558-midterm-2026`, check the link logged out, upload the PDF and a code zip to Classroom.

## Improvement work (later)
- Weights and packets from the earlier 3–4 h GPU run are not in this repo. Locate them on the server, then record path and SHA-256 here.
- Follow `improvement_plan/IMPROVEMENT_PLAN.md`; Phase 0 (trustworthy CV) comes first.
