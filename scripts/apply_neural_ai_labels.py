"""Safely merge provisional AI relevance labels into the LOCAL development-only files.

Never reads, writes, or evaluates locked holdout data.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'research'
INPUT = DATA / 'neural_disagreement_review_PRIVATE.csv'
LABELS = DATA / 'neural_disagreement_ai_labels_seed31.csv'
DEV = DATA / 'relevance_dev_expanded_PRIVATE.csv'
AUGMENTED = DATA / 'relevance_dev_neural_augmented_PRIVATE.csv'
KEYS = ['question_id', 'paper_id']
FIELDS = ['domain','question_id','question','paper_id','title','year','authors','source_url','abstract_PRIVATE','relevance_grade','reviewer_notes']
ACCEPTED = {'', '?', '0', '1', '2'}


def read(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f'Required project file is missing: {path}')
    return pd.read_csv(path, dtype=str, keep_default_na=False, encoding='utf-8-sig')


def check_unique(frame: pd.DataFrame, path: Path, required: set[str]):
    missing=required-set(frame.columns)
    if missing:
        raise ValueError(f'Missing columns in {path.name}: {sorted(missing)}')
    if frame.duplicated(KEYS).any():
        raise ValueError(f'Duplicate question/paper keys in {path.name}')
    if 'relevance_grade' in frame and not set(frame.relevance_grade).issubset(ACCEPTED):
        raise ValueError(f'Unexpected grade in {path.name}')


def fingerprint(text: str) -> str:
    return hashlib.sha256(str(text).strip().encode('utf-8')).hexdigest()


def validate_same(a: pd.Series, b: pd.Series, path: str):
    for col in ['domain','question','title','abstract_PRIVATE']:
        av = str(a.get(col,'')).strip()
        bv = str(b.get(col,'')).strip()
        if av != bv:
            raise ValueError(f'{path}: {col} mismatch at {a.question_id}/{a.paper_id}; stop rather than reassign a label')


def atomic_csv(df: pd.DataFrame, path: Path, stamp: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        backup=path.with_name(path.stem + f'.backup_{stamp}' + path.suffix)
        shutil.copy2(path, backup)
        print('Backup:', backup)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8-sig', suffix='.csv', dir=path.parent, delete=False, newline='') as h:
        tmp=Path(h.name)
        df.to_csv(h,index=False)
    try:
        os.replace(tmp,path)
    finally:
        tmp.unlink(missing_ok=True)
    print('Saved:',path)


def run(dry_run: bool) -> dict:
    q=read(INPUT); labels=read(LABELS); dev=read(DEV)
    check_unique(q,INPUT,set(FIELDS));check_unique(dev,DEV,set(FIELDS))
    check_unique(labels,LABELS,{'question_id','paper_id','title','domain','abstract_sha256','relevance_grade','reviewer_notes','reviewer_type'})
    if len(labels)!=59 or len(q)!=59:
        raise ValueError(f'Expected 59 candidates and labels; got {len(q)} and {len(labels)}')
    labelkeys=set(zip(labels.question_id,labels.paper_id)); qkeys=set(zip(q.question_id,q.paper_id))
    if qkeys != labelkeys:
        raise ValueError('Label keys differ from local neural review queue; do not use this ZIP on another run')
    devkeys=set(zip(dev.question_id,dev.paper_id))
    if qkeys & devkeys:
        raise ValueError('A neural candidate already exists in the base development review; resolve duplicates manually')
    labelmap={(r.question_id,r.paper_id):r for r in labels.itertuples(index=False)}
    reviewed=q.copy()
    if 'label_provenance' not in reviewed.columns:
        reviewed['label_provenance']=''
    if 'source_review_flag' not in reviewed.columns:
        reviewed['source_review_flag']=''
    added=0; preserved=0; differences=[]
    for i,r in q.iterrows():
        ann=labelmap[(r.question_id,r.paper_id)]
        if r.domain != ann.domain or str(r.title).strip() != str(ann.title).strip():
            raise ValueError(f'Question/title mismatch: {r.question_id}/{r.paper_id}')
        if fingerprint(r.abstract_PRIVATE) != ann.abstract_sha256:
            raise ValueError(f'Abstract text has changed for {r.question_id}/{r.paper_id}; no labels were applied')
        if ann.relevance_grade not in ('0','1','2'):
            raise ValueError('Invalid generated grade')
        if getattr(ann,'source_review_flag','') and not str(reviewed.at[i,'source_review_flag']).strip():
            reviewed.at[i,'source_review_flag']=ann.source_review_flag
        grade=str(r.relevance_grade).strip()
        if grade == '':
            reviewed.at[i,'relevance_grade']=ann.relevance_grade
            reviewed.at[i,'reviewer_notes']=ann.reviewer_notes if not str(r.reviewer_notes).strip() else r.reviewer_notes
            reviewed.at[i,'label_provenance']='AI_provisional_abstract_review'
            added+=1
        else:
            preserved+=1
            if grade!=ann.relevance_grade:
                differences.append((r.question_id,r.paper_id,grade,ann.relevance_grade))
    # Augmented review is a new dataset; the original dev file is never edited.
    augmented=pd.concat([dev.copy(),reviewed[FIELDS].copy()],ignore_index=True)
    augmented['label_provenance']=''
    augmented.loc[len(dev):,'label_provenance']=reviewed.label_provenance.to_numpy()
    augmented['source_review_flag']=''
    augmented.loc[len(dev):,'source_review_flag']=reviewed.source_review_flag.to_numpy()
    if AUGMENTED.exists():
        old=read(AUGMENTED)
        check_unique(old,AUGMENTED,set(FIELDS))
        lookup={(r.question_id,r.paper_id):r for _,r in old.iterrows()}
        rowlist=[]
        for _,row in augmented.iterrows():
            key=(row.question_id,row.paper_id)
            if key in lookup:
                existing=lookup[key]
                validate_same(row,existing,AUGMENTED.name)
                for c in old.columns:
                    if c not in row.index: row[c]=''
                # Respect independent/manual edits in either local file. If both files
                # contain different manual grades, fail rather than silently choose.
                is_neural = key in qkeys
                candidate_manual = (is_neural and str(row.relevance_grade).strip()
                                    and not str(row.reviewer_notes).startswith('AI-provisional'))
                old_manual = (str(existing.relevance_grade).strip()
                              and not str(existing.reviewer_notes).startswith('AI-provisional'))
                if candidate_manual and old_manual and str(row.relevance_grade) != str(existing.relevance_grade):
                    raise ValueError(f'Conflicting manual grades for {key}; reconcile queue and augmented review')
                if candidate_manual:
                    pass  # Keep the authoritative reviewed queue's manual grade and notes.
                elif old_manual or str(existing.relevance_grade).strip():
                    row['relevance_grade']=existing.relevance_grade
                    row['reviewer_notes']=existing.reviewer_notes
                    row['label_provenance']=str(existing.get('label_provenance',''))
                elif str(existing.reviewer_notes).strip():
                    row['reviewer_notes']=existing.reviewer_notes
            rowlist.append(row.to_dict())
        newkeys=set(zip(augmented.question_id,augmented.paper_id))
        extras=old[[ (r.question_id,r.paper_id) not in newkeys for _,r in old.iterrows()]]
        if len(extras):
            print(f'Keeping {len(extras)} extra existing augmented records')
            rowlist.extend(extras.to_dict('records'))
        augmented=pd.DataFrame(rowlist).fillna('')
    check_unique(augmented,AUGMENTED,set(FIELDS))
    report={'source_review_rows':len(q),'new_grades_added':added,'existing_grades_preserved':preserved,
            'grade_disagreements_preserved':len(differences),'augmented_development_rows':len(augmented),
            'augmented_grades':augmented.relevance_grade.value_counts().to_dict(),
            'dry_run':dry_run}
    print('Planned update:',report)
    if differences:
        print('Existing grades differ from AI review; preserved without overwriting:',differences[:8])
    if not dry_run:
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        atomic_csv(reviewed,INPUT,stamp)
        atomic_csv(augmented,AUGMENTED,stamp)
        print('Original development review was NOT modified:',DEV)
        print('Locked holdout was NOT opened or modified.')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--dry-run',action='store_true',help='Validate and preview without writing')
    args=parser.parse_args()
    run(args.dry_run)
