"""Stage 9 audit: every number printed in report/main.tex must trace to a source.

Each number is matched (at its printed precision) against: the r1 result tables, a small set of
explicitly derived values (formula shown), or a design constant fixed in analysis_plan_r1.md.
Writes results/r1/audit_numbers.csv; exit code 1 if any number is unmatched.
"""
from __future__ import annotations

import json
import re
import sys
from decimal import Decimal

import numpy as np
import pandas as pd

from common import OUT, ROOT

TEX = ROOT / "midterm" / "report" / "main.tex"
SKIP_TABLES = {"t1_hub_differences.csv", "t3_hub_data.csv", "t4_did_hubs.csv", "t4_placebo_hubs.csv",
               "desc_hubs_per_date.csv", "t1_placebo.csv", "prep_flagged_rows.csv", "file_hashes.csv", "audit_numbers.csv"}
NUM = re.compile(r"(?<![A-Za-z_\\\d.])[-+]?\d[\d,]*(?:\.\d+)?(?:\\times10\^\{-?\d+\})?")

# design constants: value -> where it is fixed
CONSTANTS = {
    "0.05": "alpha / delta (analysis_plan_r1.md)", "0.0125": "Bonferroni alpha/4", "0.10": "T3 delta", "0.03": "T4 delta",
    "3": "T4 delta 3% / df formula", "5": "delta 5%, expected-count rule, closure run >= 5 days",
    "4": "four tests / cells >= 4 days / one-hot levels", "56": "T4 window (days)", "30": "T4 min rows; ratio threshold",
    "14": "reopen window (days)", "28": "sensitivity window / reopening comparison (days)", "84": "sensitivity window",
    "12": "placebo shift (months)", "100": "last-digit check applies to volume >= 100", "100000": "permutations",
    "200": "placebo replicates", "3.5": "robust z cut-off", "0.975": "t quantile", "0.95": "chi2 quantile",
    "1": "codes / Monday=1", "2": "codes / formats", "7": "Sunday=7 / weekday levels", "9": "raw columns / digits",
    "10": "deciles", "46": "encoded attributes (prep_encoded_schema.csv)", "8": "flags / pages / hubs in 4 pairs",
    "0": "codes / H0 value", "95": "confidence level", "6": "section", "2013": "data years", "2014": "data years", "2015": "data years",
    "2012": "control rule (analysis_plan_r1.md)", "2008": "hub 1 metadata (verify.csv)", "2010": "hub 2 metadata (verify.csv)",
    "13": "hub 2 loyalty week (verify.csv)", "1270": "hub 1 distance (verify.csv)", "3.0": "Lecture 3", "2026": "course year",
    "11": "Lecture 11", "1.5": "IQR fence multiplier", "250": "closest decile upper edge (t3_deciles_posthoc.csv)",
    "115": "2015 - 1900", "31": "date", "19": "date", "20": "date", "36": "180 - 144 (t4_counts.csv)",
}


def pool() -> list[tuple[float, str]]:
    """All numeric values in the summary-level result tables (and numbers embedded in text cells)."""
    out: list[tuple[float, str]] = []
    files = sorted(p for p in OUT.glob("*.csv") if p.name not in SKIP_TABLES)
    files += [ROOT / "midterm" / "results" / "test_results.csv"]           # v0 numbers quoted as 'earlier version'
    for f in files:
        df = pd.read_csv(f)
        for col in df.columns:
            for i, v in enumerate(df[col]):
                tag = f"{f.name}:{col}:row{i}"
                if isinstance(v, (int, float, np.integer, np.floating)) and np.isfinite(v):
                    out.append((float(v), tag))
                elif isinstance(v, str):
                    out += [(float(x), tag) for x in re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", v.replace(",", ""))]
    for name in ("t1_t2.json", "t3_t4.json"):
        def walk(o, path):
            if isinstance(o, dict):
                for k, v in o.items():
                    walk(v, f"{path}.{k}")
            elif isinstance(o, (int, float)) and not isinstance(o, bool):
                out.append((float(o), f"{name}{path}"))
        walk(json.loads((OUT / name).read_text()), "")
    return out + derived()


def derived() -> list[tuple[float, str]]:
    """Values computed from table entries; the formula is the source."""
    rz = pd.read_csv(OUT / "prep_robust_z_context.csv").groupby("explained_by")["share_of_flagged_%"].sum()
    dec = pd.read_csv(OUT / "t3_deciles_posthoc.csv")
    t3 = pd.read_csv(OUT / "t3_results.csv").iloc[0]
    v = pd.read_csv(OUT / "verify.csv").set_index("claim")["recomputed"]
    return [(100 * 180 / 1115, "derived: 100*180/1115 (t2_contingency.csv)"),
            (100 * 29307 / 804110, "derived: 100*29307/804110 (prep_waterfall/verify)"),
            (100 - rz["none of these"], "derived: 100 - share 'none of these' (prep_robust_z_context.csv)"),
            *[(float(s), f"derived: sum of shares '{k}' (prep_robust_z_context.csv)") for k, s in rz.items()],
            (100 * dec.loc[dec.decile > 1, "pct_vs_deciles_2_10"].abs().max(), "derived: max |pct| deciles 2-10 (t3_deciles_posthoc.csv)"),
            (t3.estimate**2, "derived: r^2 (t3_results.csv)"), (100 * t3.ci_low**2, "derived: 100*ci_low^2 (t3_results.csv)"),
            (180 * 184, "derived: 180*184"), (2015 - 1900, "derived"), (1115 * 900, "derived: grid"),
            (float(v["volume skew open (g1)"]), "verify.csv")]


def parse(tok: str) -> tuple[Decimal, int, int]:
    """Printed number -> (mantissa, decimals, power of ten)."""
    m = re.match(r"([-+]?[\d,]*\.?\d*)(?:\\times10\^\{(-?\d+)\})?", tok)
    mant = m.group(1).replace(",", "")
    exp = int(m.group(2)) if m.group(2) else 0
    dec = len(mant.split(".")[1]) if "." in mant else 0
    return Decimal(mant), dec, exp


PREFER = {"T1": ("t1_", "desc_t1_week", "desc_weekday"), "T2": ("t2_",), "T3": ("t3_", "test_results"),
          "T4": ("t4_",), "S1": ("verify", "prep_encoded", "prep_before"), "S2": ("prep_", "verify", "desc_reopening"),
          "S3": ("prep_",), "S4": ("desc_", "t2_contingency", "t3_deciles", "verify", "derived"), "S5": ("tests_summary",)}


def matches(tok: str, values: list[tuple[float, str]], section: str, pct: bool) -> str:
    """First match at printed precision, searching the section's own tables first."""
    mant, dec, exp = parse(tok)
    target = float(mant)
    pref = PREFER.get(section, ())
    ordered = [x for x in values if x[1].startswith(pref)] + [x for x in values if not x[1].startswith(pref)] if pref else values
    for v, tag in ordered:
        scales = (100 * v, v) if pct else (v, 100 * v)
        for cand in scales:
            cand = cand / 10**exp
            for c in (cand, -cand):
                if round(c, dec) == target or (dec == 0 and abs(target) >= 1000 and round(c) == target):
                    return tag
    return ""


def section_of(body: str, pos: int) -> str:
    """Which part of the report a position falls in (tests T1-T4, or section S1-S6)."""
    marks = [(m.start(), f"T{m.group(1)}") for m in re.finditer(r"subsection\*\{Test (\d)", body)]
    marks += [(m.start(), f"S{i + 1}") for i, m in enumerate(re.finditer(r"\\section\{", body))]
    marks += [(m.start(), "S5") for m in re.finditer(r"All four tests together", body)]
    before = [t for t in sorted(marks) if t[0] <= pos]
    return before[-1][1] if before else "header"


def tex_numbers() -> list[tuple[str, str, str, bool]]:
    body = TEX.read_text().split(r"\begin{document}")[1]
    body = re.sub(r"\\url\{[^}]*\}", "", body)
    body = re.sub(r"%.*", "", body.replace("\\%", "PCT"))
    body = body.replace("{,}", ",").replace("$-$", "-")
    body = re.sub(r"\d{4}-\d{2}-\d{2}", "", body)                 # ISO dates
    body = re.sub(r"\d+(\.\d+)?(cm|pt|mm|em)", "", body)          # layout lengths
    body = "\n".join(l for l in body.splitlines() if "@iiitd" not in l)  # member table (roll numbers)
    out = []
    for m in NUM.finditer(body):
        tok = m.group(0).rstrip(",")
        after = body[m.end(): m.end() + 6]
        ctx = body[max(0, m.start() - 40): m.end() + 20].replace("\n", " ").replace("PCT", "%")
        out.append((tok, ctx, section_of(body, m.start()), "PCT" in after))
    return out


def main() -> int:
    vals = pool()
    rows = []
    for tok, ctx, sec, pct in tex_numbers():
        key = tok.lstrip("+-").replace(",", "")
        src = matches(tok, vals, sec, pct) if "." in tok or "times" in tok or len(key) > 3 else ""
        src = src or (CONSTANTS.get(key) and f"constant: {CONSTANTS[key]}") or matches(tok, vals, sec, pct)
        rows.append({"section": sec, "number": tok, "context": ctx, "source": src or "UNMATCHED"})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "audit_numbers.csv", index=False)
    bad = df[df.source.eq("UNMATCHED")]
    print(f"{len(df)} numbers in main.tex; {len(df) - len(bad)} traced; {len(bad)} unmatched")
    if len(bad):
        print(bad.to_string(index=False, max_colwidth=70))
    return 1 if len(bad) else 0


if __name__ == "__main__":
    sys.exit(main())
