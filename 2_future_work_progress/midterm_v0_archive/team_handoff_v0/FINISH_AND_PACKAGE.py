#!/usr/bin/env python3
"""Finalize the independently checked CSE558 midterm using *real* team contributions.

This deliberately DOES NOT rerun statistical analyses (already independently checked
from original raw data) or push to GitHub / upload to Classroom. The team must do
those real-world actions after examining the new PDF.

Usage from the extracted CSE558_TEAM_FINAL_HANDOFF directory:
    python FINISH_AND_PACKAGE.py
"""
from __future__ import annotations
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

HERE=Path(__file__).resolve().parent
ROOT=HERE
REPORT=ROOT/'midterm'/'report'
CSV=ROOT/'midterm'/'member_contributions.csv'
OUT=HERE/'SUBMIT_TO_CLASSROOM'
PEOPLE=[('2023312','Manya Chaturvedi'),('2023296','Kush Tokas'),('2024053','Akash Adur'),('2023114','Anusha Rana'),('2023483','Sanjeev')]
BAD=re.compile(r'(?i)\b(?:blah(?:\s*\d+)?|tbd|todo|pending|replace[ _-]?me|fill[ _-]?me|unknown|unverified|not[ _-]?sure|example)\b')
SOURCES=['audit_structure.py','preprocess_audit.py','build_encoded_data.py','run_eda.py','run_hypothesis_tests.py','run_sensitivity_analysis.py','run_t1_fixed_effects.py','outlier_audit.py','t1_date_robustness.py','t2_bootstrap_ci.py','integrate_verified_results.py','fill_team_contributions.py','validate_midterm.py','capture_environment.py','complete_midterm.py','make_submission_archive.py','requirements-midterm.txt','midterm/README.md','midterm/member_contributions.csv','midterm/report/main.tex','midterm/report/outliers_verified.tex','midterm/report/t1_verified_results.tex','midterm/report/t2_verified_ci.tex']

def die(msg):
    print('\nERROR: '+msg+'\n',file=sys.stderr)
    raise SystemExit(1)

def latex_escape(s):
    m={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}'}
    return ''.join(m.get(c,c) for c in s)

def load_contribs():
    if not CSV.exists(): die(f'Cannot find {CSV}')
    with CSV.open(newline='',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
    d={str(r.get('roll_no','')).strip():r for r in rows}
    if set(d)!=set(k for k,_ in PEOPLE):die('member_contributions.csv must have exactly the five assigned roll numbers.')
    answer={}
    for roll,name in PEOPLE:
        row=d[roll]
        if str(row.get('name','')).strip()!=name:die(f'Name mismatch for {roll}; expected {name}. Confirm with team if this is wrong.')
        value=str(row.get('contribution','')).strip()
        if not value or BAD.search(value) or len(value)<10 or len(value)>90:die(f'{name}: replace contribution placeholder with 10–90 characters of truthful, specific work.')
        answer[roll]=value
    return answer

def fill_tex(original, contrib):
    lines=[]
    matched=set()
    for line in original.splitlines(keepends=True):
        bare=line.rstrip('\r\n')
        eol=line[len(bare):]
        m=re.match(r'^(\s*[1-5]\s*&\s*[^&]+\s*&\s*(\d{7})\s*&\s*[^&]+\s*&).*?(\\\\)\s*$',bare)
        if m and m.group(2) in contrib:
            roll=m.group(2)
            line=m.group(1)+' '+latex_escape(contrib[roll])+' '+m.group(3)+eol
            matched.add(roll)
        lines.append(line)
    if matched!=set(contrib):die('Could not find every team member row in LaTeX; review the report header.')
    return ''.join(lines)

def pdf_pages(pdf):
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(pdf)).pages)
    except ImportError:
        pass
    if shutil.which('pdfinfo'):
        p=subprocess.run(['pdfinfo',str(pdf)],capture_output=True,encoding='utf-8',errors='replace')
        m=re.search(r'(?m)^Pages:\s*(\d+)',p.stdout)
        if m:return int(m.group(1))
    die('Need pypdf (python -m pip install pypdf) or pdfinfo installed to check 8-page limit.')

def compile_pdf():
    exe=shutil.which('pdflatex')
    if not exe:
        print('\nSTOP: pdflatex is not installed. The LaTeX source has been updated with real contributions.')
        print('Open the generated project/midterm/report/main.tex in Overleaf and upload the figures plus')
        print('the other *.tex files from that report folder. Compile twice using pdfLaTeX.')
        print('Copy the resulting PDF to SUBMIT_TO_CLASSROOM/CSE558_Final_Report.pdf, then run')
        print('  python FINISH_AND_PACKAGE.py --use-existing-pdf')
        die('Cannot generate the final submission until the PDF has been compiled.')
    for passno in (1,2):
        p=subprocess.run([exe,'-interaction=nonstopmode','-halt-on-error','main.tex'],cwd=REPORT,capture_output=True,encoding='utf-8',errors='replace')
        if p.returncode:
            log=(REPORT/'main.log')
            die(f'LaTeX pass {passno} failed; inspect {log} or the output below:\n'+p.stdout[-3000:])
    pdf=REPORT/'main.pdf'
    if not pdf.exists():die('LaTeX did not produce main.pdf')
    return pdf

def build(use_existing_pdf=False):
    contrib=load_contribs()
    texfile=REPORT/'main.tex'
    original=texfile.read_text(encoding='utf-8')
    if '33{,}963{,}265' not in original or '/tree/cse558-midterm-2026' not in original:
        die('Report source is not the audited version: missing encoding check or correct branch link.')
    for filename in ['outliers_verified.tex','t1_verified_results.tex','t2_verified_ci.tex']:
        if not (REPORT/filename).is_file():die(f'Missing report fragment: {filename}')
    new=fill_tex(original,contrib)
    for member in PEOPLE:
        if member[1] not in new:die('Name disappeared from team table.')
    if BAD.search('\n'.join(l for l in new.splitlines() if re.match(r'^\s*[1-5]\s*&',l))):
        die('Contribution table still contains placeholder text.')
    texfile.write_text(new,encoding='utf-8')
    print('Filled all five team contributions in the LaTeX source.')
    OUT.mkdir(exist_ok=True)
    if use_existing_pdf:
        candidate=OUT/'CSE558_Final_Report.pdf'
        if not candidate.is_file():die(f'Compile final PDF in Overleaf and save to {candidate}')
        # We cannot guarantee an externally provided PDF matches current source.
        print('WARNING: using an externally compiled PDF. Team MUST inspect page 1 contributor table and figures.')
    else:
        candidate=compile_pdf()
    pages=pdf_pages(candidate)
    if not 1<=pages<=8:die(f'PDF has {pages} pages, exceeding the official 8-page limit.')
    if candidate.stat().st_size<60_000:die('PDF is implausibly small; inspect the build.')
    final=OUT/'CSE558_Final_Report.pdf'
    if candidate.resolve()!=final.resolve():shutil.copy2(candidate,final)
    print(f'Compiled final PDF: {pages} pages, {final.stat().st_size:,} bytes.')
    if shutil.which('pdftotext'):
        p=subprocess.run(['pdftotext',str(final),'-'],capture_output=True,encoding='utf-8',errors='replace')
        text=p.stdout if p.returncode==0 else ''
        if any(w in text.lower() for w in ['blah 1','blah 2','blah 3','blah 4','blah 5','figure file not found']):
            die('Placeholders found in compiled PDF. DO NOT SUBMIT.')
    # The strict source/data/PDF validator expects this canonical report location.
    shutil.copy2(final,REPORT/'ShadowHub_demand.pdf')
    validation=subprocess.run([sys.executable,str(ROOT/'validate_midterm.py'),'--repo',str(ROOT)],cwd=ROOT,
                              capture_output=True,encoding='utf-8',errors='replace')
    print('\n--- INDEPENDENT SOURCE AND PDF VALIDATION ---')
    print(validation.stdout[-4500:])
    if validation.returncode:
        die('Strict validation FAILED. Review every FAIL line above before submitting.\n'+validation.stderr[-900:])
    files=[ROOT/p for p in SOURCES]
    files += sorted((ROOT/'midterm/figures').glob('*.png'))
    files += sorted((ROOT/'midterm/results').glob('*.csv'))
    files += sorted((ROOT/'midterm/results').glob('*.json'))
    files=[x for x in sorted(set(files)) if x.is_file()]
    missing=[p for p in SOURCES if not (ROOT/p).is_file()]
    if missing:die(f'Missing source files from code package: {missing}')
    arch=OUT/'CSE558_Code_And_Readme.zip'
    manifest={'created_utc':datetime.now(timezone.utc).isoformat(),'description':'CSE558 inference report code and supporting outputs; raw CSV excluded from Classroom code ZIP','files':[]}
    with ZipFile(arch,'w',ZIP_DEFLATED,compresslevel=7) as z:
        for f in files:
            arc=f.relative_to(ROOT).as_posix()
            z.write(f,arc)
            manifest['files'].append({'file':arc,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
        z.writestr('SUBMISSION_MANIFEST.json',json.dumps(manifest,indent=2))
    (OUT/'SUBMISSION_INSTRUCTIONS.txt').write_text(
        'CSE558 Data Science Midterm — Deadline 27 October 2026, 11:59 PM\n'
        '1) Manually READ all pages of CSE558_Final_Report.pdf; confirm real contributor credits, no overlaps, and template styling.\n'
        '2) Push latest midterm report + code + README to the public GitHub cse558-midterm-2026 branch; open link in incognito.\n'
        '3) On Classroom upload CSE558_Final_Report.pdf (mandatory).\n'
        '4) Also upload CSE558_Code_And_Readme.zip, or scripts separately if Classroom requires it.\n'
        '5) Include/confirm a link to the midterm branch and the readable README.\n'
        'DO NOT upload the original 794MB repository ZIP or correction kits.\n',encoding='utf-8')
    print('\nSUCCESS: Created precisely the two submission outputs in:')
    print(' ',final)
    print(' ',arch)
    print('\nMANDATORY HUMAN CHECKS: open PDF, inspect all pages (especially page 1 and Table 5), push current GitHub code, submit to Classroom.')

if __name__=='__main__':
    use='--use-existing-pdf' in sys.argv[1:]
    build(use_existing_pdf=use)
