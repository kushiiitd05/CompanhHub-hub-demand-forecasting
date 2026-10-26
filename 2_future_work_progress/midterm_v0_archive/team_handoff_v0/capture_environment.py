#!/usr/bin/env python3
"""Record versions of the actual analysis runtime for reproducibility."""
from pathlib import Path
import json
import argparse
import platform
from importlib import metadata

PACKAGES=['numpy','pandas','scipy','matplotlib','seaborn','statsmodels','linearmodels','pyarrow','pypdf']

def capture(repo):
    d={'python':platform.python_version(),'platform':platform.platform(),'packages':{}}
    for p in PACKAGES:
        try:d['packages'][p]=metadata.version(p)
        except metadata.PackageNotFoundError:d['packages'][p]=None
    out=repo/'midterm/results/environment_versions.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(d,indent=2),encoding='utf-8');print('Environment:',out)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path('.'))
    capture(p.parse_args().repo.resolve())
