#!/usr/bin/env python3
"""Strict CSE558 submission gate: code, data, statistics, template and final PDF.

Requires actual full-data rerun. Does not accept missing inputs or blank member credit.
"""
from pathlib import Path
import argparse
import re
import shutil
import subprocess
import sys
import pandas as pd
import numpy as np


def run_text(command):
    """Run a PDF utility without relying on the Windows locale codec.

    Some Poppler builds emit bytes that are invalid in the active CP1252
    code page.  Replacement decoding is sufficient here because validation
    only searches ASCII labels and counts output lines.
    """
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        check=False,
    )


def validate(repo:Path):
    repo=repo.resolve(); errors=[];checks=[]
    def check(label,ok,details=''):
        checks.append((label,bool(ok),details))
        if not ok:errors.append(label)
    report=repo/'midterm/report/main.tex'
    if not report.exists():raise FileNotFoundError(f'Missing {report}')
    tex=report.read_text(encoding='utf-8')
    required_files={
        'raw train':'datset_kaggle/orders_train.csv',
        'runtime package manifest':'midterm/results/environment_versions.json',
        'requirements':'requirements-midterm.txt',
        'raw metadata':'datset_kaggle/hub_metadata.csv',
        'midterm README':'midterm/README.md',
        'hypothesis code':'run_hypothesis_tests.py',
        'encoded schema':'midterm/results/encoded_schema.csv',
        'preprocessing before/after':'midterm/results/preprocess_comparison.csv',
        'preprocessing key audit':'midterm/results/preprocess_key_audit.csv',
        'outlier audit':'midterm/results/outlier_audit.csv',
        'test results':'midterm/results/test_results.csv',
        'T2 effect bootstrap CI':'midterm/results/t2_effect_ci.csv',
        'T1 corrected hub FE':'midterm/results/t1_hub_fe_corrected_sensitivity.csv',
        'T1 date-level HAC sensitivity':'midterm/results/t1_date_hac_sensitivity.csv',
        'T4 window sensitivity':'midterm/results/t4_event_window_sensitivity.csv',
        'recalculated T1 report fragment':'midterm/report/t1_verified_results.tex',
        'recalculated T2 report fragment':'midterm/report/t2_verified_ci.tex',
        'outlier report fragment':'midterm/report/outliers_verified.tex'
    }
    for label,p in required_files.items(): check(label,(repo/p).is_file(),p)
    for name in ['order_distribution.png','daily_order_trend.png','promotion_by_weekday.png','competitor_distance.png']:
        p=repo/'midterm/figures'/name
        check('figure: '+name,p.exists() and p.stat().st_size>10_000 if p.exists() else False,str(p))
    check('uses 10pt A4 two-column LaTeX instructor layout',
          r'\documentclass[10pt,a4paper,twocolumn]{article}' in tex)
    check('repo links to midterm branch', '/tree/cse558-midterm-2026' in tex)
    check('3M threshold arithmetic', '33{,}963{,}265' in tex)
    check('all four hypothesis sections',all(f'Test {i}' in tex for i in range(1,5)))
    check('practical impact thresholds', 'Practical importance' in tex and '350 orders' in tex)
    check('explicit T4 hypothesis',r'\Hnull:E[D_h]=0' in tex)
    check('reported degrees of freedom', all(t in tex for t in ['$t(1114)', '$t(119)', '3 degrees of freedom']))
    check('no invalid earlier T1 estimate claimed', 'Its Monday-by-promotion interaction was $+2{,}030.74$' not in tex)
    check('generated sensitivity snippets linked', all(r'\input{'+s+'}' in tex for s in
          ['t1_verified_results.tex','t2_verified_ci.tex','outliers_verified.tex']))
    empty=[]
    for line in tex.splitlines():
        if re.match(r'^\s*[1-5]\s*&',line):
            parts=line.split('&')
            if len(parts)==5 and parts[-1].strip().startswith(r'\\'):empty.append(parts[0].strip())
    check('all group contributions filled', len(empty)==0 and len([l for l in tex.splitlines() if re.match(r'^\s*[1-5]\s*&',l)])>=5,
          'missing or blank rows '+','.join(empty))

    contribution_rows=[l for l in tex.splitlines() if re.match(r'^\s*[1-5]\s*&',l)]
    forbidden=re.compile(r'(?i)\b(?:blah(?:\s*\d+)?|tbd|todo|pending|to\s+be\s+confirmed|replace\s+me|unverified)\b')
    found=[l.strip() for l in contribution_rows if forbidden.search(l.split('&')[-1])]
    check('no fabricated or unverified contribution placeholders',len(found)==0,
          'invalid rows: '+ '; '.join(found))

    if (repo/'midterm/results/preprocess_comparison.csv').exists():
        try:
            d=pd.read_csv(repo/'midterm/results/preprocess_comparison.csv')
            ok=({'stage','rows','columns','rows_times_columns','missing_cells'}<=set(d.columns)) and len(d)==3
            check('three-stage before/after audit',ok)
            if ok:
                r=d.loc[d.stage=='Encoded'].iloc[0]
                check('encoded scale from genuine generated table', int(r['rows'])*int(r['columns'])==int(r['rows_times_columns']) and int(r['rows_times_columns'])>=3_000_000)
        except Exception as exc:check('three-stage before/after audit',False,str(exc))
    if (repo/'midterm/results/test_results.csv').exists():
        try:
            d=pd.read_csv(repo/'midterm/results/test_results.csv')
            check('exactly four separate primary tests',len(d)==4 and d.test.nunique()==4)
            check('all tests have 95% CIs and effects',d[['effect_estimate','ci95_low','ci95_high']].notna().all().all())
            check('all tests have p, corrected p, decisions and statistic',d[['statistic','p_raw','p_holm','significant_holm_0_05']].notna().all().all())
            check('CI contains its own effect estimate',all(d.ci95_low<=d.effect_estimate) and all(d.effect_estimate<=d.ci95_high))
            t2=d[d.test.str.startswith('T2_')]
            t4=d[d.test.str.startswith('T4_')]
            check('T2 permutation p and df=3 recorded',len(t2)==1 and 'df=3' in str(t2.iloc[0].notes))
            check('T4 sample of eligible hubs',len(t4)==1 and int(t4.iloc[0].n_units)>=30)
            ci_file=repo/'midterm/results/t2_effect_ci.csv'
            if ci_file.exists() and len(t2)==1:
                b=pd.read_csv(ci_file).iloc[0]
                check('T2 bootstrap agrees with primary result',abs(t2.iloc[0].effect_estimate-b.cramers_v)<1e-8 and abs(t2.iloc[0].ci95_low-b.ci95_low)<0.015 and abs(t2.iloc[0].ci95_high-b.ci95_high)<0.015)
        except Exception as exc:check('statistical CSV validation',False,str(exc))
    else:check('statistical CSV validation',False)
    pdf=repo/'midterm/report/CompanhHub_hub_demand_forecasting.pdf'
    check('compiled final PDF exists and is non-empty',pdf.exists() and pdf.stat().st_size>50_000 if pdf.exists() else False)
    if pdf.exists():
        pages=None
        if shutil.which('pdfinfo'):
            x=run_text(['pdfinfo',str(pdf)])
            m=re.search(r'^Pages:\s*(\d+)',x.stdout,re.M)
            if m:pages=int(m.group(1))
        if pages is None:
            try:
                from pypdf import PdfReader
                pages=len(PdfReader(str(pdf)).pages)
            except Exception:pass
        check('PDF is at most eight pages',pages is not None and 1<=pages<=8,f'{pages} pages')
        pdf_text=None
        if shutil.which('pdftotext'):
            p=run_text(['pdftotext',str(pdf),'-'])
            if p.returncode == 0:
                pdf_text=p.stdout
        if pdf_text is None:
            try:
                from pypdf import PdfReader
                pdf_text='\n'.join(
                    page.extract_text() or '' for page in PdfReader(str(pdf)).pages
                )
            except Exception:
                pass
        check('no figure placeholders in PDF',pdf_text is not None and not any(
            x in pdf_text for x in ['Figure file not found','Your plot:']))

        image_count=None
        if shutil.which('pdfimages'):
            p=run_text(['pdfimages','-list',str(pdf)])
            if p.returncode == 0:
                image_count=max(0,len(p.stdout.splitlines())-2)
        if image_count is None or image_count < 4:
            try:
                from pypdf import PdfReader
                pypdf_count=sum(
                    len(page.images) for page in PdfReader(str(pdf)).pages
                )
                image_count=max(image_count or 0,pypdf_count)
            except Exception:
                pass
        check('PDF actually embeds four or more plot assets',
              image_count is not None and image_count>=4,
              f'{image_count} image objects')
    for name,passed,notes in checks:
        print(('PASS' if passed else 'FAIL')+' | '+name+(f' — {notes}' if notes else ''))
    print(f'\n{sum(ok for _,ok,_ in checks)}/{len(checks)} checks passed.')
    print('The PDF still needs visual human inspection for legibility and attribution confirmation.')
    return 0 if not errors else 1

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path('.'))
    sys.exit(validate(p.parse_args().repo))
