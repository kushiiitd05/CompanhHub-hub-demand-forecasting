#!/usr/bin/env python3
"""One-command reproducible CSE558 midterm build on a local GitHub checkout.

Runs actual raw data and halts on a failure. No fictitious generated findings.
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPTS=['capture_environment.py','audit_structure.py','preprocess_audit.py','build_encoded_data.py',
         'outlier_audit.py','run_eda.py','run_hypothesis_tests.py',
         't2_bootstrap_ci.py','run_t1_fixed_effects.py','t1_date_robustness.py',
         'run_sensitivity_analysis.py','integrate_verified_results.py']

def main(repo:Path,build_pdf=True):
    repo=repo.resolve()
    assert (repo/'datset_kaggle/orders_train.csv').exists(), 'Missing real orders_train.csv'
    assert (repo/'datset_kaggle/hub_metadata.csv').exists(), 'Missing real hub_metadata.csv'
    for name in SCRIPTS:
        print('\n=== RUN',name,'===',flush=True)
        cmd=[sys.executable,str(repo/name)]
        if name in ['capture_environment.py','t2_bootstrap_ci.py','t1_date_robustness.py','integrate_verified_results.py']:
            cmd += ['--repo',str(repo)]
        subprocess.run(cmd,cwd=repo,check=True)
    if build_pdf:
        if not shutil.which('pdflatex'):
            raise RuntimeError('pdflatex not installed; compile midterm/report/main.tex in Overleaf instead')
        for run in range(2):
            print('\n=== LATEX PASS',run+1,'===',flush=True)
            subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','main.tex'],
                           cwd=repo/'midterm/report',check=True,stdout=subprocess.DEVNULL)
        output=repo/'midterm/report/CompanhHub_hub_demand_forecasting.pdf'
        shutil.copy2(repo/'midterm/report/main.pdf',output)
        print('PDF GENERATED',output)
    subprocess.run([sys.executable,str(repo/'validate_midterm.py'),'--repo',str(repo)],cwd=repo,check=True)
    from make_submission_archive import build as build_zip
    build_zip(repo)
    print('\nALL AUTOMATABLE VALIDATION PASSED; final ZIP generated. Check attribution and upload the PDF on Classroom.')

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,default=Path('.'))
    ap.add_argument('--skip-pdf',action='store_true')
    args=ap.parse_args();main(args.repo,build_pdf=not args.skip_pdf)
