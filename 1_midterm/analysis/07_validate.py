"""Submission gate for the r1 report. Prints PASS/FAIL per check; exit 1 if any check fails.

Expected before the team fills in contributions: everything passes except 'no placeholders'.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys

import pandas as pd

from common import FIG, OUT, ROOT

REPORT = ROOT / "midterm" / "report"
TEX, PDF = REPORT / "main.tex", REPORT / "main.pdf"
BANNED = [r"restaurant", r"blah", r"REPLACE_ME", r"accept(ed)?\s*(the\s*)?\$?H_?\{?0", r"\\eg\{", r"\\egblock\{",
          r"forecast", r"leaderboard", r"CatBoost", r"LightGBM", r"RMSLE", r"cross-validation"]
FIGS = ["fig_volume.pdf", "fig_gap.pdf", "fig_promo_weekday.pdf", "fig_distance.pdf", "fig_qq.pdf"]
CHECKS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((label, bool(ok), detail))


def pdf_pages() -> int:
    if shutil.which("pdfinfo"):
        out = subprocess.run(["pdfinfo", str(PDF)], capture_output=True, text=True).stdout
        return int(re.search(r"Pages:\s+(\d+)", out).group(1))
    from pypdf import PdfReader
    return len(PdfReader(str(PDF)).pages)


def git_time(path: str, grep: str = "") -> int:
    args = ["git", "log", "--format=%ct", "--reverse", "--", path]
    out = subprocess.run(args, capture_output=True, text=True, cwd=ROOT).stdout.split()
    return int(out[0]) if out else 0


def main() -> int:
    v = pd.read_csv(OUT / "verify.csv")
    check("00 verify: all claimed facts match", v["match"].all(), f"{int(v['match'].sum())}/{len(v)}")
    for t in ("t1", "t2", "t3", "t4"):
        row = pd.read_csv(OUT / f"{t}_results.csv").iloc[0]
        check(f"{t.upper()} scipy vs manual formula agree to 4 s.f.", bool(row["agree_4sf"]))
    s = pd.read_csv(OUT / "tests_summary.csv")
    check("4 tests (guidelines 3-5), each with df, p, CI", len(s) == 4 and s[["df", "p", "ci_low", "ci_high"]].notna().all().all())
    for f in FIGS:
        check(f"figure {f}", (FIG / f).exists())
    tex = TEX.read_text()
    body = tex.split(r"\begin{document}")[1]
    check("template switch \\showhintsfalse", r"\showhintsfalse" in tex)
    for pat in BANNED:
        hits = re.findall(pat, re.sub(r"\\url\{[^}]*\}", "", body), flags=re.I)  # repo URL contains "forecasting"
        check(f"no '{pat}' in report body", not hits, f"{len(hits)} hits")
    check("six template sections", len(re.findall(r"\\section\{", body)) == 6)
    check("no placeholders (<<...>>): contributions confirmed", "<<" not in body, "team must replace <<CONFIRM: ...>>")
    a = pd.read_csv(OUT / "audit_numbers.csv")
    check("every number in main.tex traced (audit_numbers.csv)", (a["source"] != "UNMATCHED").all(), f"{len(a)} numbers")
    check("main.pdf exists", PDF.exists())
    if PDF.exists():
        n = pdf_pages()
        check("PDF at most 8 pages", n <= 8, f"{n} pages")
        check("PDF newer than main.tex", PDF.stat().st_mtime >= TEX.stat().st_mtime)
    plan, res = git_time("midterm/analysis_plan_r1.md"), git_time("midterm/results/r1/t1_results.csv")
    check("analysis plan committed before test results", plan and (not res or plan <= res), f"plan {plan}, results {res}")
    for label, ok, detail in CHECKS:
        print(f"{'PASS' if ok else 'FAIL'}  {label}  {detail}")
    failed = [c for c in CHECKS if not c[1]]
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
