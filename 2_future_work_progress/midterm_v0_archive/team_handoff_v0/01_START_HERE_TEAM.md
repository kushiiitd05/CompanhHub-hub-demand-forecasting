# CSE558 — FINAL TEAM HANDOFF (READ THIS FIRST)

**Deadline: Tuesday, 27 October 2026, 11:59 PM (India time).** Submission is on **Classroom**. This is a consolidated working folder, **NOT** the file you submit directly.

## What is already completed and independently checked

- Original training, test and metadata CSVs are included under `project/datset_kaggle/` — no 794 MB repository archive needed.
- Training 970,379 × 9; encoded training 970,379 × 35 = **33,963,265 entries**, meeting the 3M criterion.
- All four primary hypothesis tests were independently checked against the raw CSVs; they agree with the saved statistical outputs.
- Corrected Test 1 fixed-effects and date-level sensitivity numbers were checked.
- The LaTeX source has the **fixed** page-4 sensitivity table, corrected narrative, and report fragments. The reported four-page draft meets the eight-page limit, but **you must recompile after adding your real team credits and inspect the output**.
- This package has **no ready-to-submit final PDF** because contributions cannot truthfully be assigned without your team.

## ONLY 3 GROUP ACTIONS ARE NEEDED BEFORE SUBMISSION

### 1) Fill five authentic contributions (mandatory)

Open `project/midterm/member_contributions.csv` in Excel/VS Code/Notepad. Replace `REPLACE_ME` on all five lines with what **each person actually did**, ideally 10–90 characters. Save the file as CSV (keep its column names). All five members must confirm their entries. Do not enter `blah`, `TBD`, or invented work.

Names and IDs are prefilled; if any is incorrect, confirm and update both the CSV and LaTeX author table before proceeding. The automatic script intentionally fails on unexpected names/IDs.

### 2) Generate the two final deliverables

**On Windows:** double-click `DOUBLE_CLICK_TO_FINISH.bat` in this folder (requires Python 3 and a local LaTeX installation with `pdflatex`).

**Or in VS Code terminal, from THIS folder:**

```powershell
python FINISH_AND_PACKAGE.py
```

The tool inserts your contributions, compiles the PDF twice, rejects missing credits, checks the eight-page limit and packs the code/README/results. Success creates:

- `SUBMIT_TO_CLASSROOM/CSE558_Final_Report.pdf` — **mandatory PDF**.
- `SUBMIT_TO_CLASSROOM/CSE558_Code_And_Readme.zip` — compact script/README submission, no large raw files.
- `SUBMIT_TO_CLASSROOM/SUBMISSION_INSTRUCTIONS.txt` — last-mile instructions.

**If you see an error, nothing is submission-approved. Fix it and rerun.** If `pdflatex` is unavailable, follow the Overleaf instructions below. Do not submit any old or preview PDF.

### 3) Final human checks, GitHub and Classroom upload (mandatory)

1. **Open the generated PDF and read every page.** Confirm five real contributions on page 1; check page 4's sensitivity table stays within one column; no clipped tables or missing images; total no more than eight pages. Compare the report style with the original official template under `reference/`.
2. **Update the actual GitHub branch** `cse558-midterm-2026` with the latest `project/midterm/` folder, report, results, scripts and README. The public branch was previously stale. A member with **push permission** must perform this step. See `02_GITHUB_AND_CLASSROOM.md`.
3. Open this URL in an incognito browser to check code and README are visible:
   https://github.com/kushiiitd05/ShadowDsc10-ShadowHub/tree/cse558-midterm-2026
4. In Classroom, submit **`CSE558_Final_Report.pdf`**. Also submit **`CSE558_Code_And_Readme.zip`** (or individual Python scripts if Classroom prohibits ZIP). Confirm both uploads, and submit before **27 Oct 2026, 11:59 PM**.

## If you do not have pdflatex (Overleaf route)

You still only need this package. First edit the five contributions in the CSV, then run:

```powershell
python FINISH_AND_PACKAGE.py
```

The script updates the LaTeX source and stops with a clear `pdflatex` message. Open **Overleaf** and create a blank project. Upload the report source files from `project/midterm/report/` (`main.tex`, `outliers_verified.tex`, `t1_verified_results.tex`, `t2_verified_ci.tex`) and upload four PNGs under the relative folder `../figures/` expectation: safest Overleaf structure is to create `midterm/report/` and `midterm/figures/` within the project, maintaining the same layout, then set `midterm/report/main.tex` as the main file. Compile with pdfLaTeX twice, download the PDF, and save it as `SUBMIT_TO_CLASSROOM/CSE558_Final_Report.pdf`. Then from this extracted folder run:

```powershell
python FINISH_AND_PACKAGE.py --use-existing-pdf
```

You may need `python -m pip install pypdf` if neither `pypdf` nor `pdfinfo` is available. Double-check that the PDF downloaded from Overleaf contains the new five contributions — the offline tool cannot prove it matches the edited LaTeX source.

## What you do NOT submit

- `ShadowDsc10-ShadowHub.zip` (~794 MB) — entire project/data/models.
- Any `FINAL_REMEDIATION_PACKAGE`, `VERIFIED_FINAL_AUDIT`, or earlier correction ZIP.
- This consolidated `CSE558_TEAM_FINAL_HANDOFF.zip` — it's a **working handoff**, not the Classroom deliverable.
- `reference/` template PDF or the teacher's guidelines.
- The raw input CSVs unless the professor separately asks for them.

## What the professor actually requires

The official guidelines require a **PDF report, maximum eight pages, using the LaTeX report template**, an accessible code link and README, and 3–5 well-justified hypothesis tests. The accompanying template additionally instructs students to upload a script or notebook on Classroom. The presentation is separate and has no supplied instructions yet.

## Academic integrity and limitations

Our four tests describe **associations, not causal impacts**. The original raw-data outputs were independently verified, but this handoff cannot assign team contributions or press the Classroom submit button. Only one group member needs to finalize the package; all five must verify their credits.
