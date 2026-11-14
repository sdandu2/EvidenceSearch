#!/usr/bin/env python3
"""Check Git's INDEX for restricted paths or high-confidence secrets (not a legal/security guarantee)."""
from __future__ import annotations
import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = {'.gitignore', '.gitattributes', 'README.md', 'SECURITY.md',
            'requirements_ci.txt', '.github/workflows/evidencesearch-checks.yml',
            'assets/screenshots/evidencesearch-homepage.png',
            'assets/screenshots/evidencesearch-hero-detail.png', 'web/package.json',
            'web/package-lock.json', 'scripts/audit_public_release.py',
            'scripts/stage_public_release.py'}
ROOT_FILES = {'.gitignore', '.gitattributes', 'README.md', 'SECURITY.md',
              'requirements_api.txt', 'requirements_m13.txt', 'requirements_m14.txt',
              'requirements_m15.txt', 'requirements_ci.txt'}
WEB_CONFIG = {'package.json', 'package-lock.json', 'next.config.ts',
              'tsconfig.json', 'postcss.config.mjs', 'next-env.d.ts',
              '.gitignore', '.env.example'}
PRIVATE_DIRS = {'data','reports','artifacts','notebooks','design','checkpoints','models',
                '.venv','venv','.release_review','.local_release','node_modules',
                '.next','index_cache','model_cache','downloads','__pycache__',
                '.ipynb_checkpoints','.pytest_cache'}
PRIVATE_SUFFIXES = {'.csv','.tsv','.jsonl','.npz','.npy','.parquet','.arrow',
                    '.sqlite','.sqlite3','.db','.pt','.pth','.ckpt','.onnx',
                    '.safetensors','.pem','.p12','.pfx','.key','.zip','.ipynb',
                    '.log','.bak','.backup'}
TEXT_SUFFIXES = {'.py','.ps1','.md','.txt','.js','.ts','.tsx','.css',
                 '.svg','.json','.yaml','.yml','.mjs'}
SECRETS = [re.compile(rx) for rx in [
    rb'gh[pousr]_[A-Za-z0-9_]{24,}', rb'github_pat_[A-Za-z0-9_]{30,}',
    rb'\bAKIA[0-9A-Z]{16}\b', rb'\b(?:sk|sk-proj)-[A-Za-z0-9_-]{28,}\b',
    rb'\bhf_[A-Za-z0-9]{30,}\b', rb'xox[baprs]-[A-Za-z0-9-]{20,}',
    rb'-----BEGIN (?:RSA|OPENSSH|EC|DSA) PRIVATE KEY-----',
]]
PERSONAL_PATHS = [
    re.compile(rb'[A-Za-z]:\\(?:Users|Documents and Settings)\\[^\\\r\n\s]+\\', re.I),
    re.compile(rb'[A-Za-z]:/(?:Users|Documents and Settings)/[^/\r\n\s]+/', re.I),
]


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True)


def allowlisted(path: str) -> bool:
    parts = path.replace('\\','/').split('/')
    if len(parts) == 1: return path in ROOT_FILES
    if parts[0] == '.github': return path == '.github/workflows/evidencesearch-checks.yml'
    if parts[0] == 'docs': return len(parts) == 2 and parts[-1].endswith('.md')
    if parts[0] == 'assets': return path in {
        'assets/screenshots/evidencesearch-homepage.png',
        'assets/screenshots/evidencesearch-hero-detail.png'}
    if parts[0] == 'backend': return path.endswith('.py') or path == 'backend/README.md'
    if parts[0] == 'scripts':
        return (len(parts) == 2 and path.endswith(('.py','.ps1')) or
                len(parts) == 3 and parts[1] == 'release_tests' and path.endswith('.py'))
    if parts[0] == 'web':
        if len(parts) == 2: return parts[1] in WEB_CONFIG
        return (parts[1] in {'app','components','lib','public'} and
                Path(path).suffix in {'.ts','.tsx','.css','.svg','.png','.webp','.mjs','.js','.json'})
    return False


def path_reason(path: str) -> str | None:
    path = path.replace('\\','/')
    if any(p.lower() in PRIVATE_DIRS for p in path.split('/')): return 'private/generated directory'
    if any(mark in path.upper() for mark in ('PRIVATE','LOCKED','SECRET')): return 'private filename'
    if Path(path).suffix.lower() in PRIVATE_SUFFIXES: return 'restricted file type'
    if Path(path).name.startswith('.env') and path != 'web/.env.example': return 'environment file'
    if not allowlisted(path): return 'outside public-source allowlist'
    return None


def index_paths() -> list[str]:
    r=git('ls-files','-z')
    if r.returncode: raise RuntimeError('Unable to list staged/indexed paths')
    return sorted(x.decode('utf-8','replace') for x in r.stdout.split(b'\0') if x)


def inspect(paths: list[str], with_history: bool=True) -> list[str]:
    issues=[]
    for path in paths:
        reason=path_reason(path)
        if reason:
            issues.append(f'{path}: {reason}')
            continue
        b=git('show', ':'+path)
        if b.returncode:
            issues.append(f'{path}: could not read indexed blob')
            continue
        content=b.stdout
        if len(content)>4*1024*1024:
            issues.append(f'{path}: exceeds 4 MiB per-file limit')
        if Path(path).suffix.lower() in TEXT_SUFFIXES:
            if any(regex.search(content) for regex in SECRETS):
                issues.append(f'{path}: potential credential or private key')
            if any(regex.search(content) for regex in PERSONAL_PATHS):
                issues.append(f'{path}: specific local user directory')
    if with_history:
        r=git('log','--all','--name-only','--format=')
        if r.returncode==0:
            historical={p for p in r.stdout.decode('utf-8','replace').splitlines() if p.strip()}
            bad=[p for p in historical if path_reason(p)]
            issues.extend(f'HISTORY {p}: excluded path was previously committed' for p in sorted(bad)[:30])
            if len(bad)>30: issues.append(f'HISTORY: {len(bad)-30} more excluded paths')
    return issues


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--allow-incomplete',action='store_true',help='Tests only')
    ap.add_argument('--no-history',action='store_true',help='Tests only')
    args=ap.parse_args()
    rp=git('rev-parse','--show-toplevel')
    if rp.returncode or Path(rp.stdout.decode().strip()).resolve()!=ROOT.resolve():
        print('BLOCKED: Initialize Git in the EvidenceSearch root first.');return 2
    files=index_paths()
    issues=inspect(files, not args.no_history)
    if not args.allow_incomplete:
        issues.extend(f'MISSING required release file: {x}' for x in sorted(REQUIRED-set(files)))
    if not files: issues.append('No tracked/staged source files')
    if issues:
        print('PUBLIC RELEASE AUDIT: BLOCKED')
        for issue in issues: print(' -',issue)
        print('Do not commit or push; audit cannot certify clean historical blobs.')
        return 1
    print(f'PUBLIC RELEASE AUDIT: PASS ({len(files)} indexed files)')
    print('Manual content/security/license review is STILL REQUIRED before making the repository public.')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
