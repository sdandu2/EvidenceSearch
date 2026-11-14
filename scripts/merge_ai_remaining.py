"""Safely merge the remaining 80 provisional development labels.

Only fills blank grade+note pairs, validates full-question/abstract hashes,
backs up changed files, and NEVER accesses the locked holdout.
"""
from __future__ import annotations
import argparse
import collections
import csv
from datetime import datetime
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data' / 'research' / 'relevance_ai_remaining_seed31.csv'
TARGETS = [ROOT / 'data' / 'research' / 'relevance_dev_expanded_PRIVATE.csv',
           ROOT / 'data' / 'research' / 'relevance_review_PRIVATE.csv']


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def sha(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def write_atomic(path, columns, rows):
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', newline='',
          prefix='.evidencesearch_', suffix='.tmp', dir=path.parent,
          delete=False) as f:
        tmp = Path(f.name)
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def merge(dry_run):
    if not SOURCE.is_file():
        raise FileNotFoundError(f'Missing AI label file: {SOURCE}')
    columns, incoming = read(SOURCE)
    required = {'question_id','paper_id','relevance_grade','reviewer_notes','question','abstract_sha256'}
    assert len(incoming)==80 and required.issubset(columns), 'Expected precisely 80 reviewed pairs and mandatory fields'
    suggestions={}
    for row in incoming:
        key=(row['question_id'],row['paper_id'])
        if key in suggestions or row['relevance_grade'] not in ('0','1','2'):
            raise ValueError(f'Duplicate or invalid incoming label for {key}')
        if not row['reviewer_notes'].startswith('AI-provisional;'):
            raise ValueError(f'Missing AI provenance for {key}')
        suggestions[key]=row

    all_work=[]
    for path in TARGETS:
        if not path.exists():
            if path.name=='relevance_review_PRIVATE.csv':
                print('Optional original review not present:',path)
                continue
            raise FileNotFoundError(f'Development review missing: {path}')
        names, rows = read(path)
        missing = {'question_id','paper_id','question','abstract_PRIVATE','relevance_grade','reviewer_notes'}-set(names)
        if missing:
            raise ValueError(f'Invalid CSV {path.name}; missing {sorted(missing)}')
        matches=0; applied=0; preserved=0; keys=set()
        for row in rows:
            key=(row['question_id'],row['paper_id'])
            if key in keys:
                raise ValueError(f'Duplicate ID in {path.name}: {key}')
            keys.add(key)
            src=suggestions.get(key)
            if not src:
                continue
            matches+=1
            if row['question'].strip()!=src['question'].strip() or sha(row['abstract_PRIVATE'])!=src['abstract_sha256']:
                raise ValueError(f'Dataset changed for {key} in {path.name}; refusing unsafe merge')
            if (row['relevance_grade'] or '').strip() or (row['reviewer_notes'] or '').strip():
                preserved+=1
                continue
            row['relevance_grade']=src['relevance_grade']
            row['reviewer_notes']=src['reviewer_notes']
            applied+=1
        all_work.append((path,names,rows,matches,applied,preserved))

    # Validate all targets and primary-label coverage before changing anything.
    primary=next((work for work in all_work if work[0].name=='relevance_dev_expanded_PRIVATE.csv'),None)
    if not primary or primary[3]!=80:
        raise ValueError(f'Expected all 80 proposed pairs in primary development CSV; matched {primary[3] if primary else 0}')
    for path,names,rows,matched,applied,preserved in all_work:
        grades=collections.Counter(str(r.get('relevance_grade','')).strip() for r in rows)
        print(f'{path.name}: {matched} matched; {applied} new; {preserved} preserved; grades 2={grades["2"]}, 1={grades["1"]}, 0={grades["0"]}, ?={grades["?"]}, blank={grades[""]}')
    if dry_run:
        print('DRY RUN: no files changed.')
        return
    for path,names,rows,matched,applied,preserved in all_work:
        if not applied:
            print('Unchanged:',path.name)
            continue
        backup_dir=path.parent/'backups'
        backup_dir.mkdir(parents=True,exist_ok=True)
        stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        backup=backup_dir/(f'{path.stem}_before_AI_completion_{stamp}.csv')
        shutil.copy2(path,backup)
        write_atomic(path,names,rows)
        print(f'Updated {path}; backup at {backup}')
    print('AI provisional development labels only. Locked holdout unmodified. One bibliographic-only question/paper is expected to remain uncertain.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true')
    merge(parser.parse_args().dry_run)
