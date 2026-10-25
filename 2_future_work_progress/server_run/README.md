# server_run: hand-off folder for the server / Max-plan session

| File | Purpose |
|---|---|
| `MAX_PLAN_PROMPT.md` | The prompt to paste into the Claude session on the server |
| `STATUS.md` | Snapshot of everything: repo map, what is merged, what is verified, what is missing |
| `GAP_ANALYSIS.md` | Report vs requirements, test-quality review, EDA to do, ordered task list |
| `SESSION_LOG.md` | Append-only log written by the session (`[date] [phase] [action] [result]`) |

New code and experiment logs for the Kaggle improvement work go in this folder, not in `kaggle_modelling/`.
Large artifacts (weights, packets, OOF files) are git-ignored; record path and SHA-256 in `STATUS.md` instead.
