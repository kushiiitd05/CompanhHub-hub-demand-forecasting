"""One command regenerates every r1 table and figure:  python analysis/run_all.py

Order matters: 00 verifies the raw facts, 01 writes the cleaned frames used by 02-06.
Stops at the first failing step.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ["00_verify.py", "01_prepare.py", "02_tests_t1_t2.py", "03_tests_t3_t4.py", "04_summary.py",
         "05_descriptives.py", "06_figures.py", "08_audit_numbers.py", "07_validate.py"]


def main() -> int:
    for step in STEPS:
        print(f"\n=== {step}", flush=True)
        rc = subprocess.run([sys.executable, step], cwd=HERE).returncode
        if rc != 0:
            print(f"{step} exited with {rc}; stopping.")
            return rc
    return 0


if __name__ == "__main__":
    sys.exit(main())
