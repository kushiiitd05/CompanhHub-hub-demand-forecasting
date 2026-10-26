# Submission files (Classroom, due 27 Oct 2026, 11:59 pm)

| File | What it is |
|---|---|
| `CSE558_Final_Report.pdf` | The report (6 pages, official LaTeX template). Upload this as the PDF. |
| `build_submission.sh` | Builds `CSE558_Final_Report.pdf` and `CSE558_code.zip` from the current tree. The zip is for Classroom only and is not stored in git. |

The report links to the code on GitHub: <https://github.com/kushiiitd05/ShadowDsc10-ShadowHub/tree/cse558-midterm-2026>.

## Verify everything: clone only `1_midterm/` (about 7 minutes)
The data (`data/raw/`) is inside `1_midterm/`, so nothing else from the repository is needed.
```bash
git clone --depth 1 --branch cse558-midterm-2026 --filter=blob:none --sparse \
    https://github.com/kushiiitd05/ShadowDsc10-ShadowHub.git shadowhub
cd shadowhub && git sparse-checkout set 1_midterm && cd 1_midterm
python -m pip install -r requirements.txt
cd analysis && python run_all.py     # recomputes every number, table and figure; the last step prints "30/30 checks pass"
cd .. && pytest -q tests             # 9 unit tests
```
`run_all.py` runs, in order: `00_verify` (125 data facts), `01_prepare`, `02`/`03` (tests T1-T4), `04_summary`, `05_descriptives`,
`06_figures`, `08_audit_numbers` (every number in the report traced to a file), `07_validate` (submission gate).
Rebuild the PDF with `cd report && tectonic main.tex` (or `pdflatex main.tex` twice).
Hashes of the raw files and the full data-cleaning ledger are in `../README.md`.

## Verify from the Classroom zip
`CSE558_code.zip` has no data (33 MB). Unzip it, put the four files from `1_midterm/data/raw/` on GitHub into `data/raw/`, then run the
same commands from `pip install` onward.
