#!/usr/bin/env python3
"""Insert confirmed, user-supplied contributions into the instructor's team table.

Never guesses credit attribution from commit history.
"""
from pathlib import Path
import argparse
import csv
import re

NAMES={
 '2023312':'Manya Chaturvedi',
 '2023296':'Kush Tokas',
 '2024053':'Akash Adur',
 '2023114':'Anusha Rana',
 '2023483':'Sanjeev',
}

def tex_escape(s):
    chars={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_',
           '{':r'\{','}':r'\}'}
    return ''.join(chars.get(c,c) for c in s)

def run(repo, roles_file):
    with open(roles_file,encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    roles={str(r['roll_no']).strip():str(r['contribution']).strip() for r in rows}
    for k in NAMES:
        if not roles.get(k) or roles[k].lower() in ('tbd','pending','unknown','todo') or 'blah' in roles[k].lower() or 'replace_me' in roles[k].lower():
            raise ValueError(f'Please enter actual contribution for {NAMES[k]} ({k}) in {roles_file}')
        if len(roles[k])>125:
            raise ValueError(f'Team contribution too long for report table: {k}')
    source=repo/'midterm/report/main.tex'
    s=source.read_text(encoding='utf-8')
    lines=[];seen=set()
    for line in s.splitlines(keepends=True):
        matching=[k for k in NAMES if ('& '+k+' &' in line) and line.lstrip()[:1].isdigit()]
        if matching:
            k=matching[0]
            before=line.rstrip('\r\n');after=line[len(before):]
            if not before.rstrip().endswith('\\\\'):
                raise ValueError(f'Unexpected team table row for {k}: {line!r}')
            parts=before.split('&')
            if len(parts)!=5: raise ValueError('Expected five columns in team row')
            parts[-1]=' '+tex_escape(roles[k])+r' \\'
            line='&'.join(parts)+after
            seen.add(k)
        lines.append(line)
    if seen != set(NAMES):raise ValueError(f'Team rows not found: {set(NAMES)-seen}')
    source.write_text(''.join(lines),encoding='utf-8')
    print('Contributions filled for',len(seen),'people. Verify exact roles with all members.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--repo',type=Path,default=Path('.'));p.add_argument('--csv',type=Path,default=Path('midterm/member_contributions.csv'))
    args=p.parse_args();run(args.repo.resolve(),args.repo.resolve()/args.csv)
