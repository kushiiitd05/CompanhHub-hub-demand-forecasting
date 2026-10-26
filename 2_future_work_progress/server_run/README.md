# server_run: hand-off folder for the server / Max-plan session

| File | Purpose |
|---|---|
| `MAX_PLAN_PROMPT.md` | The prompt to paste into the Claude session on the server |
| `STATUS.md` | Current state: repo map, what is done, what is open |
| `RESEARCH_PROTOCOL.md` | Full-marks plan: rubric matrix, research agenda, writing guide, Max ↔ Mac review loop |
| `REVIEW_REQUEST_TEMPLATE.md` | Hand-over form for review |
| `MASTER_PROMPT_CSE558_Midterm.md` | Full statistical spec for the midterm |
| `history/` | Earlier gap analysis, status and review request |
| `SESSION_LOG.md` | Append-only log written by the session (`[date] [phase] [action] [result]`) |

New code and experiment logs for the Kaggle improvement work go in this folder, not in `kaggle_modelling/`.
Large artifacts (weights, packets, OOF files) are git-ignored; record path and SHA-256 in `STATUS.md` instead.
