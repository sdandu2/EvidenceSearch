#!/usr/bin/env python3
"""Explicitly stage public source files, never private research outputs. No commit or push."""
from __future__ import annotations
import argparse
import subprocess
from pathlib import Path
from audit_public_release import ROOT, allowlisted, path_reason

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--stage',action='store_true',help='Stage allowlisted files instead of preview')
    args=ap.parse_args()
    p=subprocess.run(['git','rev-parse','--show-toplevel'],cwd=ROOT,capture_output=True,text=True)
    if p.returncode or Path(p.stdout.strip()).resolve()!=ROOT.resolve():
        print('Initialize Git at the EvidenceSearch root first.');return 2
    found=[]
    # os.walk avoids recursively entering large private caches (and is faster than rglob).
    import os
    for here,dirs,files in os.walk(ROOT):
        here=Path(here)
        rel=here.relative_to(ROOT)
        dirs[:]=[d for d in dirs if d not in {'.git','data','reports','artifacts','models','notebooks','design','checkpoints','.venv','venv','node_modules','.next','__pycache__','.pytest_cache','.release_review','.local_release'}]
        for f in files:
            name=(rel/f).as_posix()
            if allowlisted(name) and path_reason(name) is None:
                found.append(name)
    found.sort()
    print(f'Public-source candidate files: {len(found)}')
    for name in found: print(' +',name)
    if not args.stage:
        print('Preview only. Add --stage to stage these paths.');return 0
    if not found: return 2
    for i in range(0,len(found),80):
        subprocess.run(['git','add','--',*found[i:i+80]],cwd=ROOT,check=True)
    print('Staged allowlisted files. Run scripts/audit_public_release.py before committing.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
