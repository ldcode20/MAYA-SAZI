"""Retrain with each scam type absent from fitting/calibration, then test it."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from evidence_utils import sha256_file,source_fingerprints
from conformal import SET_NAMES,load_conformal,predict_sets  # noqa: E402
from policy import DEFAULT_THRESHOLDS,PAYMENT_HISTORY_FEATURES,RECEIVING_ACCOUNT_FEATURES,decide  # noqa: E402
from risk_common import FEATURE_COLUMNS,TARGET,load_features  # noqa: E402

TYPES=('investment','digital_arrest','sextortion')


def cmd(args):
    print('+',' '.join(map(str,args)),flush=True)
    subprocess.run(list(map(str,args)),cwd=ROOT,check=True)


def run(features_path,transactions_path,types=TYPES,seed=42,n_estimators=None):
    source=load_features(features_path,FEATURE_COLUMNS+[TARGET,'txn_id','split','amount']).reset_index(drop=True)
    labels=pd.read_csv(transactions_path,usecols=['txn_id','scam_type','campaign_id','stage'])
    source=source.merge(labels,on='txn_id',how='left',validate='one_to_one')
    folder=ROOT/'tmp'/'rubric-heldout'; folder.mkdir(parents=True,exist_ok=True)
    result=[]
    for held in types:
        model=folder/f'{held}.json';meta=folder/f'{held}-meta.json';conf=folder/f'{held}-conformal.json'
        train=[sys.executable,'src/train_xgb.py','--features',features_path,'--transactions',transactions_path,
               '--exclude-scam-type',held,'--model-out',model,'--meta-out',meta,'--seed',seed]
        calibration=[sys.executable,'src/conformal.py','--features',features_path,'--transactions',transactions_path,
                     '--exclude-scam-type',held,'--model',model,'--out',conf]
        if n_estimators is not None:train+=['--n-estimators',n_estimators]
        cmd(train);cmd(calibration)
        test=source[(source['split']=='test')&(source['is_scam']==1)&(source['scam_type'].astype(str)==held)].copy()
        if test.empty:raise ValueError(f'No held-out {held} positives in test split')
        classifier=xgb.XGBClassifier();classifier.load_model(model)
        qf,qs=load_conformal(conf)
        probabilities=classifier.predict_proba(test[FEATURE_COLUMNS])[:,1]
        sets=predict_sets(probabilities,qf,qs)
        feats=test[list(PAYMENT_HISTORY_FEATURES+RECEIVING_ACCOUNT_FEATURES)].to_dict('records')
        actions=np.array([decide(SET_NAMES[int(s)],f,None,None,float(a),DEFAULT_THRESHOLDS)['action']
                          for s,f,a in zip(sets,feats,test['amount'])])
        removed=int(((source['split']=='train')&(source['is_scam']==1)&(source['scam_type'].astype(str)==held)).sum())
        result.append(dict(held_out_type=held,training_positive_rows_removed=removed,
            train_seed=seed,test_transactions=len(test),test_campaigns=int(test['campaign_id'].nunique()),
            model_sha256=sha256_file(model),conformal_sha256=sha256_file(conf),
            detected_before_release=float(np.mean(actions!='release')),
            hold_rate=float(np.mean(actions=='hold')),nudge_rate=float(np.mean(actions=='nudge')),
            released_count=int(np.sum(actions=='release')),
            named_misses=[dict(txn_id=int(test.iloc[i]['txn_id']),campaign_id=str(test.iloc[i]['campaign_id']),
                               stage=int(test.iloc[i]['stage']),action=str(actions[i]),p_scam=float(probabilities[i]))
                          for i in np.flatnonzero(actions=='release')[:20]],
            calibration=json.loads(conf.read_text(encoding='utf-8'))))
    return dict(schema='maya-heldout-scam-type-v1',source_fingerprints=source_fingerprints(features_path,transactions_path),
        dataset=dict(feature_rows=len(source),split_rows={k:int((source['split']==k).sum()) for k in ('train','val','calib','test')}),
        results=result,
        methodology='For each run, all rows of the selected scam type are removed from model fitting, validation threshold selection and conformal calibration. Evaluation uses only later-day test transactions of that type.',
        limitations=['Synthetic labels and one generator family.',
                     'The type taxonomy is small and does not cover real scam variation.',
                     'Nudge is counted as an interruption, not as proof that money was saved.'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--features',default='data/features.csv');p.add_argument('--transactions',default='data/transactions.csv')
    p.add_argument('--types',nargs='+',choices=TYPES,default=list(TYPES));p.add_argument('--seed',type=int,default=42)
    p.add_argument('--n-estimators',type=int,default=None);p.add_argument('--out',default='reports/heldout-types.json')
    a=p.parse_args();report=run(a.features,a.transactions,a.types,a.seed,a.n_estimators)
    out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    for row in report['results']:
        print(f"{row['held_out_type']}: n={row['test_transactions']} detected={row['detected_before_release']:.1%} released={row['released_count']}")
    print('Report:',out)


if __name__=='__main__':main()
