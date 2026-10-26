# GitHub + Classroom: exact upload procedure

## GitHub (one team member with repository WRITE access)

The branch must include the corrected files, because the PDF links to it. The link is:

https://github.com/kushiiitd05/ShadowDsc10-ShadowHub/tree/cse558-midterm-2026

### Option A: VS Code + Git

Clone or open an existing checkout on the branch. In a NEW empty parent directory:

```powershell
git clone --branch cse558-midterm-2026 --single-branch https://github.com/kushiiitd05/ShadowDsc10-ShadowHub.git
cd ShadowDsc10-ShadowHub
git branch --show-current
```

**Back up existing changes if the checkout already contains uncommitted work.** Copy the corrected contents of the `project/midterm/` folder in THIS handoff over the checkout's `midterm/` folder. Copy the top-level `.py` files and `requirements-midterm.txt` from the handoff's `project/` folder to the checkout. You do **not** need to recopy raw CSVs or heavy model caches.

From inside your Git checkout:

```powershell
git status
git add midterm *.py requirements-midterm.txt
git commit -m "Finalize CSE558 midterm report and verified inference scripts"
git push origin cse558-midterm-2026
```

Review `git status` before committing; avoid staging large generated `.parquet` files, stale PDFs, secrets or temporary LaTeX logs. The `midterm/report/ShadowHub_demand.pdf` should be the **newly generated** PDF; if your build only created `SUBMIT_TO_CLASSROOM/CSE558_Final_Report.pdf`, copy that file to the report location before pushing. Do not push unless contributors' real details are present.

If `git push` fails for permissions, ask the repository owner or a collaborator with write access to push these files. It is not necessary to upload the 794MB ZIP to GitHub again.

### Option B: GitHub web UI

A collaborator with write access can choose the `cse558-midterm-2026` branch in GitHub and upload the updated report, README, code and results into their corresponding directories. Check the actual file paths carefully. The Git command method is safer for preserving the folder structure.

**Verify:** Open the branch URL in a private/incognito window and confirm the latest commit, new PDF, and README are accessible. The current report must link to this same branch.

## Classroom

The official guidelines say **PDF, at most eight pages, due 27 Oct 2026 at 11:59 PM**, using the LaTeX template and with a code link/README. The provided template also asks for a script/notebook upload.

1. Upload `SUBMIT_TO_CLASSROOM/CSE558_Final_Report.pdf` to the midterm project submission.
2. Upload `SUBMIT_TO_CLASSROOM/CSE558_Code_And_Readme.zip` if permitted, or provide the required code scripts separately if the assignment page specifies a different extension. Include the GitHub branch link if there is a text response field.
3. Review attachments in Classroom, click the FINAL **Turn in / Submit** action, and verify the status changed to submitted before 11:59 PM.

**Do not substitute a ZIP for the required PDF.**
