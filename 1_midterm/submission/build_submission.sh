#!/usr/bin/env bash
# Rebuilds the two Classroom files from the current tree. Run from anywhere:  bash 1_midterm/submission/build_submission.sh
set -euo pipefail
cd "$(dirname "$0")/.."
cp report/main.pdf submission/CSE558_Final_Report.pdf
rm -f submission/CSE558_code.zip
zip -rq submission/CSE558_code.zip analysis tests README.md requirements.txt docs results report/main.tex report/main.pdf figures \
  -x 'results/derived/*' '*/__pycache__/*' '*.DS_Store'
echo "built: submission/CSE558_Final_Report.pdf ($(pdfinfo submission/CSE558_Final_Report.pdf 2>/dev/null | awk '/Pages/{print $2}') pages) and submission/CSE558_code.zip"
