"""Safely resolve Milestone-12 development judgments; never accesses locked holdout.

Applies only to the five frozen question–paper pairs in m12_missing_judgments_PRIVATE.csv.
Preserves existing manual grades and notes. Appends newly judged neural papers to
relevance_dev_neural_augmented_PRIVATE.csv so nDCG ideals / recall denominators
include every judged candidate. Patches Notebook 11's queue re-run assertion.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'research'
QUEUE = DATA / 'm12_missing_judgments_PRIVATE.csv'
LABELS = DATA / 'm12_ai_gap_labels_seed31.csv'
AUGMENTED = DATA / 'relevance_dev_neural_augmented_PRIVATE.csv'
CORPUS = DATA / 'corpus_pilot_PRIVATE.jsonl'
NOTEBOOK = ROOT / 'notebooks' / '11_fair_dev_evaluation_and_gap_audit.ipynb'
VALID = {'0', '1', '2'}
ALLOWED = VALID | {'', '?'}
KEYS = ('question_id', 'paper_id')


def read_csv(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f'Prerequisite missing: {path}')
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        columns = reader.fieldnames or []
    if not rows:
        raise ValueError(f'No rows found: {path}')
    return rows, columns


def key(row):
    return tuple(str(row[k]) for k in KEYS)


def index_unique(rows, what):
    result = {}
    for row in rows:
        k = key(row)
        if k in result:
            raise ValueError(f'{what} contains duplicate pair {k}')
        result[k] = row
    return result


def hash_abstract(value):
    return hashlib.sha256(value.strip().encode('utf-8')).hexdigest()


def required_columns(columns, expected, label):
    missing = set(expected) - set(columns)
    if missing:
        raise ValueError(f'{label}: missing columns {sorted(missing)}')


def prepare_notebook():
    if not NOTEBOOK.is_file():
        raise FileNotFoundError(f'Notebook 11 missing; preserve it and reinstall Milestone 12: {NOTEBOOK}')
    notebook = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
    old_block = """    assert set(map(tuple,queue[['question_id','paper_id']].values)) == set(map(tuple,queue_new[['question_id','paper_id']].values)), (
        'Existing queue has a different set of pairs. Preserve your edits; reconcile manually.')"""
    new_block = """    required_keys = set(map(tuple, queue_new[['question_id','paper_id']].values))
    stored_keys = set(map(tuple, queue[['question_id','paper_id']].values))
    assert required_keys.issubset(stored_keys), (
        'New missing judgments are not covered by the saved queue; reconcile manually.')
    # Previously missing pairs may now be resolved in the augmented review.
    # Preserve the existing audit queue, but require those extra entries to
    # match completed grades in the augmented review.
    for row in queue.itertuples(index=False):
        pair = (row.question_id, row.paper_id)
        if pair not in required_keys:
            assert original.get(pair, '') in VALID, f'Unexpected extra pending queue item: {pair}'
            assert original[pair] == row.relevance_grade, f'Augmented/queue grade conflict: {pair}'"""
    found_old = found_new = False
    for cell in notebook.get('cells', []):
        if cell.get('cell_type') != 'code':
            continue
        source = ''.join(cell.get('source', []))
        if old_block in source:
            source = source.replace(old_block, new_block)
            cell['source'] = source.splitlines(keepends=True)
            found_old = True
        elif new_block in source:
            found_new = True
    if not (found_old or found_new):
        raise ValueError('Notebook 11 has been modified; cannot safely patch without reviewing the current code.')
    # Syntax verification of all executable cells before changing any project file.
    for cell in notebook['cells']:
        if cell.get('cell_type') == 'code':
            compile(''.join(cell.get('source', [])), '<Notebook 11 cell>', 'exec')
    return (json.dumps(notebook, indent=1, ensure_ascii=False) + '\n').encode('utf-8') if found_old else None


def load_corpus():
    if not CORPUS.is_file():
        raise FileNotFoundError(f'Need private source corpus to verify document identity: {CORPUS}')
    docs = {}
    with CORPUS.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                record = json.loads(line)
                pid = str(record['paper_id'])
                if pid in docs:
                    raise ValueError('Duplicate corpus paper ID')
                docs[pid] = record
    return docs


def csv_bytes(rows, columns):
    import io
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return ('\ufeff' + buf.getvalue()).encode('utf-8')


def atomic_replace(path: Path, content: bytes, stamp: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        backup = path.with_name(f'{path.stem}.backup_{stamp}{path.suffix}')
        shutil.copy2(path, backup)
        print('Backup:', backup)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.m12_', suffix='.tmp', delete=False) as f:
        tmp = Path(f.name)
        f.write(content)
    try:
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    print('Updated:', path)


def run(dry_run=False):
    queue_rows, qcols = read_csv(QUEUE)
    labels_rows, lcols = read_csv(LABELS)
    augmented_rows, acols = read_csv(AUGMENTED)
    required_columns(qcols, {'question_id','paper_id','question','title','domain','abstract_PRIVATE','relevance_grade','reviewer_notes','reviewer_provenance'}, 'queue')
    required_columns(lcols, {'question_id','paper_id','question','title','domain','abstract_sha256','proposed_grade','reviewer_notes'}, 'label patch')
    required_columns(acols, {'question_id','paper_id','question','title','domain','abstract_PRIVATE','relevance_grade','reviewer_notes'}, 'augmented')
    queue_map = index_unique(queue_rows, 'queue')
    label_map = index_unique(labels_rows, 'label patch')
    aug_map = index_unique(augmented_rows, 'augmented review')
    if len(label_map) != 5 or set(queue_map) != set(label_map):
        raise ValueError('Expected precisely five previously audited development pairs; stop on mismatched input')
    for row in queue_rows+augmented_rows:
        if row['relevance_grade'].strip() not in ALLOWED:
            raise ValueError('Unexpected relevance grade: ' + str(key(row)))
    docs = load_corpus()
    notebook_patch = prepare_notebook()
    changes = {'queued_new_numeric_grades': 0, 'queued_uncertain': 0, 'new_augmented_rows': 0,
               'existing_manual_grades_preserved': 0, 'newly_scored_question_ids': ['genetics_02'],
               'climate_science_01_unresolved': True, 'locked_holdout_opened': False}
    for k, ann in label_map.items():
        q = queue_map[k]
        pid = k[1]
        doc = docs.get(pid)
        if doc is None:
            raise ValueError(f'Paper missing from local corpus: {k}')
        for field in ['domain', 'question', 'title']:
            if q[field].strip() != ann[field].strip():
                raise ValueError(f'{field} mismatch for {k}; refusing unsafe merge')
        if str(doc.get('title','')).strip() != q['title'].strip():
            raise ValueError(f'Corpus title differs for {k}')
        corpus_text = str(doc.get('abstract', '')).strip()
        if hash_abstract(q['abstract_PRIVATE']) != ann['abstract_sha256'] or hash_abstract(corpus_text) != ann['abstract_sha256']:
            raise ValueError(f'Abstract identity mismatch for {k}')
        domains = {d.strip() for d in str(doc.get('domains','')).split('|')}
        if q['domain'].strip() not in domains:
            raise ValueError(f'Paper outside requested field for {k}')
        proposed = ann['proposed_grade'].strip()
        if proposed not in VALID|{'?'}:
            raise ValueError(f'Invalid proposed grade for {k}')
        original = aug_map.get(k)
        old_q = q['relevance_grade'].strip()
        old_aug = original['relevance_grade'].strip() if original else ''
        if old_q in VALID and old_aug in VALID and old_q != old_aug:
            raise ValueError(f'Conflicting existing human/queue grades for {k}; reconcile manually')
        if old_q in VALID or old_aug in VALID:
            chosen = old_q if old_q in VALID else old_aug
            changes['existing_manual_grades_preserved'] += 1
        else:
            chosen = proposed
            if chosen in VALID:
                changes['queued_new_numeric_grades'] += 1
        if chosen == '?':
            changes['queued_uncertain'] += 1
        q['relevance_grade'] = chosen
        if not q.get('reviewer_notes','').strip():
            q['reviewer_notes'] = ann['reviewer_notes']
        if not q.get('reviewer_provenance','').strip() or q['reviewer_provenance'] == 'pending':
            q['reviewer_provenance'] = ann.get('label_provenance', 'AI_provisional_abstract_review')
        if original is not None:
            for field in ('domain','question','title','abstract_PRIVATE'):
                if original[field].strip() != q[field].strip():
                    raise ValueError(f'Augmented review {field} differs from queue at {k}')
            if original['relevance_grade'].strip() not in VALID:
                original['relevance_grade'] = chosen
                if not original.get('reviewer_notes','').strip():
                    original['reviewer_notes'] = q['reviewer_notes']
                if 'label_provenance' in acols and not original.get('label_provenance', '').strip():
                    original['label_provenance'] = ann.get('label_provenance', '')
        else:
            if chosen not in VALID:
                raise ValueError(f'Cannot introduce ungraded new paper into augmented pool: {k}')
            created = {field:'' for field in acols}
            for field in ('domain','question_id','question','paper_id','title','source_url','abstract_PRIVATE','reviewer_notes','relevance_grade'):
                if field in acols:
                    created[field] = q.get(field,'')
            for field in ('year','authors'):
                if field in acols:
                    value = doc.get(field,'')
                    created[field] = ' | '.join(map(str,value)) if isinstance(value,list) else str(value or '')
            if 'label_provenance' in acols:
                created['label_provenance'] = q['reviewer_provenance']
            if 'source_review_flag' in acols:
                created['source_review_flag']=''
            augmented_rows.append(created)
            aug_map[k]=created
            changes['new_augmented_rows'] += 1
    # Validate shared grades and the full augmented schema after the staged update.
    index_unique(augmented_rows,'augmented review after merge')
    for k in label_map:
        qgrade=queue_map[k]['relevance_grade']
        agrade=aug_map[k]['relevance_grade']
        if qgrade != agrade:
            raise ValueError(f'Post-merge grade mismatch at {k}: {qgrade}/{agrade}')
    files = [(QUEUE, csv_bytes(queue_rows,qcols)), (AUGMENTED,csv_bytes(augmented_rows,acols))]
    if notebook_patch is not None:
        files.append((NOTEBOOK,notebook_patch))
    changes['notebook_patch_required'] = notebook_patch is not None
    print('Review summary:', json.dumps(changes, indent=2))
    if dry_run:
        print('Dry run successful: no local files changed; locked holdout never accessed.')
        return
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    wrote = 0
    for path, content in files:
        if path.read_bytes() == content:
            continue
        atomic_replace(path, content, stamp)
        wrote += 1
    print(f'Changed {wrote} files. Locked holdout NOT opened. Re-run Notebook 11 from the first cell.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    options = parser.parse_args()
    run(options.dry_run)
