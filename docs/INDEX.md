# Which file says what

## Start here
| File | Says |
|---|---|
| `README.md` | Repo map, layers, status |
| `2_future_work_progress/server_run/MAX_PLAN_PROMPT.md` | The prompt for the server (Max-plan) session |
| `2_future_work_progress/server_run/STATUS.md` | Current state of all work |
| `2_future_work_progress/server_run/GAP_ANALYSIS.md` | What is missing in the report, test review, task list |
| `2_future_work_progress/server_run/RESEARCH_PROTOCOL.md` | Full-marks plan: rubric matrix, research agenda, writing guide, review loop |
| `2_future_work_progress/server_run/REVIEW_REQUEST_TEMPLATE.md` | Hand-over form the Max session fills for Mac review |

## Layer 1: `1_midterm/` (CSE558 midterm)
| File | Says |
|---|---|
| `01_START_HERE_TEAM.md` | Team's three actions: contributions, build, GitHub + Classroom |
| `02_GITHUB_AND_CLASSROOM.md` | Exact push and upload steps for branch `cse558-midterm-2026` |
| `INDEPENDENT_AUDIT.md`, `independent_audit.json` | Independent recheck of the four tests against raw CSVs |
| `SEND_THIS_MESSAGE_TO_TEAM.txt` | Short message for teammates |
| `midterm/README.md` | Midterm method, tests T1–T4, how to reproduce |
| `midterm/report/main.tex` (+ `*_verified.tex`) | The report source |
| `midterm/results/*.csv` | Every number in the report |
| `reference/MASTER_PROMPT_CSE558_Midterm.md` | Full spec: requirements R1–R8, standards S1–S11, data ledger Q1–Q18, test menu |
| `reference/CSE558_Project_Report_{Guidelines,Template}` | Course rules and LaTeX template |

## Layer 2: `2_future_work_progress/`
| File | Says |
|---|---|
| `kaggle_modelling/README.md` | Guided tour of the finished Kaggle work (LB 0.06976) |
| `kaggle_modelling/JOURNEY.md` | Blow-by-blow history incl. bugs and dead ends |
| `kaggle_modelling/SUMMARY.md` | Short official write-up |
| `kaggle_modelling/artifacts/eda/EDA_FINDINGS.md` | EDA findings from the pipeline |
| `improvement_plan/IMPROVEMENT_PLAN.md` | Audit of the model + phased plan to reach LB < 0.06 |
| `server_run/` | Hand-off files for the server session |

Paths inside `kaggle_modelling/` docs and `IMPROVEMENT_PLAN.md` such as `src/…` and `artifacts/…` are relative to `kaggle_modelling/`.
