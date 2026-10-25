"""Train/evaluate independent synthetic worlds with later-day test splits."""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from evidence_utils import sha256_file


def command(args):
    print('+', ' '.join(map(str,args)), flush=True)
    subprocess.run(list(map(str,args)), cwd=ROOT, check=True)


def run(seeds, users=20_000, days=120, n_estimators=None):
    rows=[]
    root=ROOT/'tmp'/'rubric-seed-sweep'
    for seed in seeds:
        folder=root/f'seed-{seed}'; data=folder/'data'; model=folder/'xgb_model.json'; meta=folder/'metrics.json'
        command([sys.executable,'src/journey_generator.py','--seed',seed,'--users',users,'--days',days,'--out-dir',data])
        command([sys.executable,'src/features.py','--txns',data/'transactions.csv','--edges',data/'graph_edges.csv',
                 '--labels',data/'labels.csv','--out',data/'features.csv','--days',days])
        train=[sys.executable,'src/train_xgb.py','--features',data/'features.csv','--model-out',model,
               '--meta-out',meta,'--seed',seed]
        if n_estimators is not None: train += ['--n-estimators',n_estimators]
        command(train)
        result=json.loads(meta.read_text(encoding='utf-8'))
        rows.append(dict(seed=seed, users=users, days=days,
            train_rows=result['train_rows'], validation_rows=result['val_rows'], test_rows=int(result['test_rows']) if 'test_rows' in result else None,
            test_auprc=result['test_auprc'], test_auroc=result['test_auroc'],
            recall_at_1pct_fpr=result['test_recall_at_1pct_fpr'],
            fpr_at_validation_threshold=result['test_fpr_at_val_threshold'],
            test_positive_count=result.get('test_pos'),
            file_hashes=dict(transactions_sha256=sha256_file(data/'transactions.csv'),
                             features_sha256=sha256_file(data/'features.csv'),
                             model_sha256=sha256_file(model)),
            split_policy='contiguous later-day test block; threshold chosen on validation'))
    keys=('test_auprc','test_auroc','recall_at_1pct_fpr','fpr_at_validation_threshold')
    ranges={k:dict(min=min(r[k] for r in rows),max=max(r[k] for r in rows),mean=statistics.mean(r[k] for r in rows)) for k in keys}
    return dict(schema='maya-seed-sweep-v1', configuration=dict(users=users,days=days,seeds=list(seeds),
                generator_source_sha256=sha256_file(ROOT/'src/journey_generator.py'),
                feature_source_sha256=sha256_file(ROOT/'src/features.py')),
        seeds=rows, ranges=ranges,
        interpretation='Different synthetic-world seeds from the same generator family; not a real-UPI estimate or independent population sample.',
        limitations=['Same simulator family and labeling rules across seeds.',
                     'Every model is tested only on its later-day block.',
                     'No confidence interval across these few generator seeds.'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seeds',nargs='+',type=int,default=[42,2026,2027])
    p.add_argument('--users',type=int,default=20_000);p.add_argument('--days',type=int,default=120)
    p.add_argument('--n-estimators',type=int,default=None);p.add_argument('--out',default='reports/seed-sweep.json')
    a=p.parse_args()
    if len(set(a.seeds)) != len(a.seeds): p.error('Seeds must be unique')
    result=run(a.seeds,a.users,a.days,a.n_estimators)
    out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result['ranges'],indent=2));print('Report:',out)


if __name__=='__main__':main()
