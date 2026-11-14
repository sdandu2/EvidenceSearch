"""Merge provisional AI development relevance grades into local EvidenceSearch CSVs.

Does not overwrite human-entered labels or notes and never reads/writes the locked holdout.
Run from any directory: python scripts/merge_ai_relevance.py
"""
from __future__ import annotations
import argparse
import collections
import csv
import datetime
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data' / 'research' / 'relevance_ai_priority_seed31.csv'
TARGETS = [
    ROOT / 'data' / 'research' / 'relevance_dev_expanded_PRIVATE.csv',
    ROOT / 'data' / 'research' / 'relevance_review_PRIVATE.csv',
]
REQUIRED = {'question_id','paper_id','question','abstract_PRIVATE','relevance_grade','reviewer_notes'}
VALID_GRADES = {'0','1','2','?'}


def read_csv(path: Path):
    with path.open('r', newline='', encoding='utf-8-sig') as fh:
        reader=csv.DictReader(fh)
        names=reader.fieldnames or []
        return names, list(reader)


def write_csv_atomic(path: Path, names: list[str], rows: list[dict]):
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',newline='',dir=path.parent,prefix='.ai_merge_',suffix='.csv',delete=False) as fh:
        temp=Path(fh.name)
        w=csv.DictWriter(fh,fieldnames=names,extrasaction='ignore')
        w.writeheader(); w.writerows(rows)
        fh.flush();os.fsync(fh.fileno())
    os.replace(temp,path)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run',action='store_true',help='Show changes without modifying any files')
    args=ap.parse_args()
    if not SOURCE.is_file():
        raise SystemExit(f'Missing packaged AI labels: {SOURCE}')
    _,incoming=read_csv(SOURCE)
    if len(incoming)!=100:
        raise SystemExit(f'Expected 100 reviewed pairs; found {len(incoming)}')
    suggestions={}
    for r in incoming:
        key=(r['question_id'],r['paper_id'])
        if key in suggestions or r['relevance_grade'] not in VALID_GRADES:
            raise SystemExit(f'Duplicate/invalid suggested label: {key}')
        if not r.get('reviewer_notes','').startswith('AI-provisional;'):
            raise SystemExit(f'Missing AI provenance note: {key}')
        suggestions[key]=r

    work=[]
    for path in TARGETS:
        if not path.exists():
            if path.name=='relevance_review_PRIVATE.csv':
                print(f'Optional original review not found, skipped: {path}')
                continue
            raise SystemExit(f'Required development review missing: {path}')
        names,rows=read_csv(path)
        if not REQUIRED.issubset(set(names)):
            raise SystemExit(f'Missing required columns in {path}: {sorted(REQUIRED-set(names))}')
        seen=set();apply=collections.Counter();skip_existing=0;unmatched=0
        for row in rows:
            key=(row['question_id'],row['paper_id'])
            if key in seen:
                raise SystemExit(f'Duplicate question/paper key in {path}: {key}')
            seen.add(key)
            info=suggestions.get(key)
            if info is None:
                unmatched+=1
                continue
            if row['question'].strip()!=info['question'].strip() or hashlib.sha256(row['abstract_PRIVATE'].encode('utf-8')).hexdigest()!=info['abstract_sha256']:
                raise SystemExit(f'Question or abstract changed for {key} in {path}; refusing to apply a mismatched grade')
            if (row.get('relevance_grade') or '').strip() or (row.get('reviewer_notes') or '').strip():
                skip_existing+=1
                continue
            row['relevance_grade']=info['relevance_grade']
            row['reviewer_notes']=info['reviewer_notes']
            apply[info['relevance_grade']]+=1
        work.append((path,names,rows,apply,skip_existing))

    # Validate ALL targets before modifying ANY, to avoid partial updates on validation failure.
    for path, names, rows, applied, skip_existing in work:
        print(f'{path.name}: {sum(applied.values())} new AI grades, {skip_existing} preserved edits, grades {dict(applied)}')
    if args.dry_run:
        print('DRY RUN: nothing changed.')
        return
    for path,names,rows,applied,_ in work:
        if not sum(applied.values()):
            print(f'No changes required: {path.name}')
            continue
        backup_dir=path.parent/'backups'
        backup_dir.mkdir(parents=True,exist_ok=True)
        stamp=datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup=backup_dir/(f'{path.stem}_before_AI_{stamp}.csv')
        shutil.copy2(path,backup)
        write_csv_atomic(path,names,rows)
        print(f'Updated: {path}')
        print(f'Backup:  {backup}')
    print('\nDevelopment labels are AI-provisional, not verified ground truth.')
    print('The locked holdout is deliberately untouched. Keep evaluation gated while labels remain incomplete.')

if __name__=='__main__':
    main()
