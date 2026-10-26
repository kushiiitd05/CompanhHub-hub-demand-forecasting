#!/usr/bin/env python3
"""Package final PDF, source, figures and results after passing strict validation.
Large raw CSVs and old model artifacts remain available through the linked repo.
"""
from pathlib import Path
import argparse
import hashlib
import json
from zipfile import ZipFile, ZIP_DEFLATED

SOURCES=['requirements-midterm.txt','capture_environment.py','audit_structure.py','preprocess_audit.py','build_encoded_data.py',
         'outlier_audit.py','run_eda.py','run_hypothesis_tests.py',
         't2_bootstrap_ci.py','run_t1_fixed_effects.py','t1_date_robustness.py',
         'run_sensitivity_analysis.py','integrate_verified_results.py',
         'validate_midterm.py','complete_midterm.py','make_submission_archive.py',
         'midterm/README.md','midterm/report/main.tex',
         'midterm/report/ShadowHub_demand.pdf']

def build(repo):
    repo=repo.resolve()
    filelist=[repo/p for p in SOURCES]
    filelist+=list((repo/'midterm/figures').glob('*.png'))
    filelist+=list((repo/'midterm/results').glob('*.csv'))
    filelist+=list((repo/'midterm/results').glob('*.json'))
    filelist+=list((repo/'midterm/report').glob('*_verified*.tex'))
    filelist+=list((repo/'midterm/report').glob('outliers_verified.tex'))
    filelist=sorted(set(filelist))
    missing=[str(p) for p in filelist if not p.is_file()]
    if missing:raise FileNotFoundError(str(missing))
    if not (repo/'midterm/report/ShadowHub_demand.pdf').is_file():
        raise FileNotFoundError('No final compiled PDF')
    out=repo/'midterm/submission/CSE558_final_submission.zip'
    out.parent.mkdir(parents=True,exist_ok=True)
    manifest={'branch':'cse558-midterm-2026','files':[]}
    with ZipFile(out,'w',ZIP_DEFLATED,compresslevel=6) as z:
        for p in filelist:
            arc=str(p.relative_to(repo))
            digest=hashlib.sha256(p.read_bytes()).hexdigest()
            manifest['files'].append({'path':arc,'bytes':p.stat().st_size,'sha256':digest})
            z.write(p,arc)
        z.writestr('SUBMISSION_MANIFEST.json',json.dumps(manifest,indent=2))
    print('Created',out,'(',len(filelist),'verified files )')
    return out

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path('.'))
    build(p.parse_args().repo)
