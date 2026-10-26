# Submission files (Classroom, due 27 Oct 2026, 11:59 pm)

| File | What it is |
|---|---|
| `CSE558_Final_Report.pdf` | The report (6 pages, official LaTeX template). Upload this as the PDF. |
| `CSE558_code.zip` | Code, tests, results, figures, README and report source. Upload this as the code. |
| `build_submission.sh` | Rebuilds both files from the current tree (run it after any change to `report/main.tex`). |

The PDF and zip are copies of `report/main.pdf` and of the folders in `1_midterm/`. The report links to the code on GitHub:
<https://github.com/kushiiitd05/ShadowDsc10-ShadowHub/tree/cse558-midterm-2026>.

## Verify everything from the zip (about 7 minutes)
```bash
unzip CSE558_code.zip -d check && cd check
# The zip has no data (33 MB). Download the 4 files into data/raw/ from:
# https://github.com/kushiiitd05/ShadowDsc10-ShadowHub/tree/cse558-midterm-2026/1_midterm/data/raw
python -m pip install -r requirements.txt
cd analysis && python run_all.py     # recomputes every number, table and figure; the last step prints "30/30 checks pass"
cd .. && pytest -q tests             # 9 unit tests
```
`run_all.py` runs, in order: `00_verify` (125 data facts), `01_prepare`, `02`/`03` (tests T1-T4), `04_summary`, `05_descriptives`,
`06_figures`, `08_audit_numbers` (every number in the report traced to a file), `07_validate` (submission gate).
Rebuild the PDF with `cd report && tectonic main.tex` (or `pdflatex main.tex` twice).
Full details, file hashes and the data-cleaning ledger are in `README.md` one level up.

## Verify from the GitHub clone
```bash
git clone --branch cse558-midterm-2026 https://github.com/kushiiitd05/ShadowDsc10-ShadowHub.git
cd ShadowDsc10-ShadowHub/1_midterm/analysis && python run_all.py
```
The clone already contains `data/raw/`.
