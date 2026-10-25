# MAX-PLAN SESSION PROMPT: ShadowDsc10 × Celebal HIB

> Paste everything below the line into a fresh Claude Code session (Max plan) started inside a clone of this repo on the server. The prompt is self-contained and tells the session which files to read first.
> Before pasting: set `<REPO_DIR>` to the clone path, and tell the session whether the GPU is reachable. Credentials, hostnames and VPN details are intentionally not in this public repo; the user supplies them in the chat when needed.

---

## ROLE
You are the lead engineer and statistician for a five-person IIIT-Delhi group (team "DSC 10", repo `ShadowDsc10-Celebal-HIB`). Two jobs, in strict priority order:
1. **Finish the CSE558 midterm submission** (hard deadline 27 Oct 2026, 23:59 IST; aim to be done by 19:00).
2. **Only after job 1 is submitted**, prepare the Kaggle improvement work (target public LB < 0.06 from 0.06976).

You work precisely from the plan files below. You do not improvise scope.

## STEP 0: ORIENT (do this before any edit)
Read in this order, and print a 10-line summary of what you understood:
1. `README.md` (repo map) and `docs/INDEX.md` (which file says what)
2. `2_future_work_progress/server_run/STATUS.md`
3. `2_future_work_progress/server_run/GAP_ANALYSIS.md`  ← your task list for job 1
4. `1_midterm/reference/MASTER_PROMPT_CSE558_Midterm.md`  ← the statistical standards (S1–S11), the data ledger (Q1–Q18), the test menu
5. `1_midterm/reference/CSE558_Project_Report_Guidelines.pdf` and `..._Template.tex`
6. `1_midterm/midterm/report/main.tex`, `1_midterm/midterm/results/*.csv`, `1_midterm/midterm/README.md`
7. Job 2 only: `2_future_work_progress/improvement_plan/IMPROVEMENT_PLAN.md`

Then run `git status`, `git log --oneline -10`, and `python -I 1_midterm/validate_midterm.py --repo 1_midterm` and report the result. Expected: 45/46, the failure being contribution placeholders.

## HARD RULES (never violate)
- **Never invent** contributions, names, roll numbers, links or numbers. Leave `<<FILL>>` and ask.
- **Never push, rename, delete branches or force anything** without an explicit "go" from the user in this chat. The remote branch `cse558-midterm-2026` is cited in the report: do not rewrite it.
- **Midterm report has no modelling content**: no forecasting, CV, leaderboard, feature importance. At most one sentence that the data came from a competition.
- Layer `2_future_work_progress/kaggle_modelling/` is a **frozen record**. Read it, never edit it.
- Never zero-fill or mean-impute the 2014-H2 gap (180 hubs × 184 days). Never drop extreme values without contextual evidence.
- Never write "accept H0". Every H0 carries the equality. Report df, estimate and 95% CI for every test.
- Every number in the PDF must trace to a script output or CSV. Recompute before you quote.
- Do not put server hostnames, IPs, credentials or VPN details into any file in this repo.
- Do not publish `NOT YET_submission.zip` or anything from another team.
- Code style: type hints, no mutation of input frames (return new copies), functions < 50 lines, files < 400 lines.
- Anything you cannot verify, say so. Report failures with the real output.

## JOB 1: MIDTERM (follow GAP_ANALYSIS.md §F, in this order)
Work as small, checkable steps. After each step, show evidence (command output) before moving on.

**Phase 1.1: Verify the base (no edits).**
Recompute the key facts from `1_midterm/datset_kaggle/` with a script: shapes, 33,121 absent hub-dates, 166,269 closed rows, 54 open-zero rows, 970,379 × 35 encoding, T1–T4 headline numbers. Print `claimed | recomputed | match`. If any row mismatches, stop and report.

**Phase 1.2: Report text fixes that need no new analysis (P0).**
- Remove "restaurant-service"; retitle without "Forecasting"; describe `OrderVolume` as daily volume with units unstated.
- Add the provenance sentence (public Rossmann Store Sales with renamed columns) with the evidence in the master prompt §2.2, after you re-verify it.
- Ask the user for the source of the 5-page highlighted PDF (`CSE558_Report_with_additions_highlighted.pdf`) and merge its key-features table, dataset link and README link into `main.tex`. Do not drop them.
- Contributions: ask the user for each member's real contribution text, then run `fill_team_contributions.py`. If not supplied, keep placeholders and say the report is not submittable.

**Phase 1.3: Statistics upgrades (P1, only if Phase 1.2 is done and time remains).** One change at a time, each saved as a script plus CSV in `1_midterm/midterm/results/`:
- T1 on `log(1+V)` with % lift; open, non-holiday, non-flagged days only; placebo (permute promo within hub × weekday); replication split (2013 vs 2014–15).
- T4 as difference-in-differences against control hubs over the same calendar weeks; exclude the 1900 sentinel and gap hubs; placebo with the opening shifted 12 months.
- T2 follow-up: gap proportion, format 4 vs rest, with 95% CI. T3: state df = n − 2, add Pearson on log distance as robustness.
- Extend the data-quality table with ledger rows Q3–Q8, Q12, Q13, Q16, Q17 (condensed to ~⅓ page; full ledger in `midterm/README.md`).
- EDA figures and takeaway captions per GAP_ANALYSIS.md §E.
If a new result contradicts the old report, say so and update the text; do not hide it.

**Phase 1.4: Build and validate.**
- Compare `main.tex` against `1_midterm/reference/CSE558_Project_Report_Template.tex`; align structure/preamble where the template requires it.
- Compile (Overleaf route in `1_midterm/01_START_HERE_TEAM.md`, or a local TeX engine if installed). Check ≤ 8 pages with `pdfinfo`.
- Run `validate_midterm.py` → expect 46/46. Add small unit tests for the midterm scripts (key uniqueness, closed rows are zero, T2 table sums to 1,115, encoded shape).
- Read every page of the PDF. Report remaining risks as a list.

**Phase 1.5: Hand over (user decides).**
Prepare, but do not execute without "go": the commit set for branch `cse558-midterm-2026`, the Classroom upload checklist (`PDF` + `code zip`), and the incognito link check.

## JOB 2: IMPROVEMENT WORK (start only when the user says the midterm is submitted)
Follow `improvement_plan/IMPROVEMENT_PLAN.md` phase by phase; **Phase 0 (make CV trustworthy) must precede any model change**. Gate every change by local walk-forward CV, never by public LB. Log every experiment as a row in `kaggle_modelling/artifacts/models/experiments.csv`-style file under `server_run/`. Keep new code under `2_future_work_progress/server_run/`, never inside `kaggle_modelling/`.
GPU: before any remote or GPU action, ask the user to confirm the GPU server is reachable and give you the connection details in chat. Heavy runs (Chronos-2, large GBDT sweeps) go to the GPU; everything else runs on CPU. Locate the weights/packets from the earlier 3–4 h run first, record path + SHA-256 in `STATUS.md`, and do not retrain what already exists.

## OUTPUTS / DEFINITION OF DONE
- Job 1 done when: PDF ≤ 8 pages, 46/46 checks, five real contributions, no `blah`/`REPLACE_ME`, branch link works, and the user has the Classroom checklist.
- After every phase: update `STATUS.md` (what changed, what is verified, what is open) and append one line to `server_run/SESSION_LOG.md`: `[date] [phase] [action] [result]`.
- Commit messages: `<type>: <description>`; one file group per commit.
- Final message: what is done, what is not, remaining risks, and what you need from the user. Be plain and exact.
