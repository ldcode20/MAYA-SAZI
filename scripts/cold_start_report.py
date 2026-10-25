"""Measure early-account uncertainty on synthetic later-day test transactions."""
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd,xgboost as xgb
import random
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from evidence_utils import sha256_file,source_fingerprints
from conformal import SET_NAMES,SET_UNSURE,load_conformal,predict_sets
from policy import DEFAULT_THRESHOLDS,PAYMENT_HISTORY_FEATURES,RECEIVING_ACCOUNT_FEATURES,decide
from risk_common import FEATURE_COLUMNS,TARGET,load_features
from online_features import snapshot
from simulation import generate_world
from simulator_service import LiveModel,apply_policy

BUCKETS=((0,10,'0-9 days'),(10,30,'10-29 days'),(30,60,'30-59 days'),(60,10**9,'60+ days'))
def run(features_path,transactions_path,model_path,conformal_path,split='test'):
    f=load_features(features_path,FEATURE_COLUMNS+[TARGET,'txn_id','split','amount']).reset_index(drop=True)
    tx=pd.read_csv(transactions_path,usecols=['txn_id','cohort_tenure_days'])
    df=f.merge(tx,on='txn_id',how='left',validate='one_to_one');df=df[(df.split==split)&(df.cohort_tenure_days>=0)].reset_index(drop=True)
    model=xgb.XGBClassifier();model.load_model(model_path);qf,qs=load_conformal(conformal_path)
    p=model.predict_proba(df[FEATURE_COLUMNS])[:,1];sets=predict_sets(p,qf,qs)
    feats=df[list(PAYMENT_HISTORY_FEATURES+RECEIVING_ACCOUNT_FEATURES)].to_dict('records')
    actions=np.array([decide(SET_NAMES[int(s)],v,None,None,float(a),DEFAULT_THRESHOLDS)['action'] for s,v,a in zip(sets,feats,df.amount)])
    y=df[TARGET].to_numpy(int)==1;rows={}
    for low,high,name in BUCKETS:
        mask=(df.cohort_tenure_days>=low)&(df.cohort_tenure_days<high);honest=mask&~y;scam=mask&y
        rows[name]=dict(rows=int(mask.sum()),honest=int(honest.sum()),scams=int(scam.sum()),
            honest_unsure_share=float(np.mean(sets[honest]==SET_UNSURE)) if honest.any() else None,
            honest_nudge_share=float(np.mean(actions[honest]=='nudge')) if honest.any() else None,
            honest_hold_share=float(np.mean(actions[honest]=='hold')) if honest.any() else None,
            scam_miss_count=int(np.sum(scam&(actions=='release'))),
            scam_miss_rate=float(np.mean(actions[scam]=='release')) if scam.any() else None)
    return dict(schema='maya-synthetic-cold-start-v1',split=split,buckets=rows,
        source_fingerprints=source_fingerprints(features_path,transactions_path),model_sha256=sha256_file(model_path),
        definition='Account tenure is derived from synthetic account creation day; rows are scored from the later-day test split.',
        limits=['Same generator family; not a real newly onboarded customer study.',
                'Do not add a cold-start auto-hold. Thin history should produce readable advice and a measured uncertainty limit.'])


def zero_history_probe(model_path,conformal_path,n_worlds=64,seed=43001):
    """Exercise the production wallet scorer with generated accounts that have no prior payments."""
    model=LiveModel(model_path,conformal_path);rng=random.Random(seed)
    actions={'neutral':{},'refund_claim':{}};scores=[];uncertainty={};endpoint_counts=[]
    for index in range(n_worlds):
        world=generate_world(seed+index,'everyday');sender,recipient=6,70
        at=world['now'];history=[e for e in world['events'] if e['kind']=='payment' and
            e['event_at']<at and e['available_at']<at and
            (e['sender'] in (sender,recipient) or e['receiver'] in (sender,recipient))]
        endpoint_counts.append(len(history))
        amount=rng.randint(500,50000)*100
        features=snapshot(world,sender,recipient,amount,at)
        scored=model.score(features['values']);scores.append(scored['score'])
        uncertainty[scored['uncertainty']]=uncertainty.get(scored['uncertainty'],0)+1
        for name,payment in (
            ('neutral',dict(text='',consent=False,amount_paise=amount)),
            ('refund_claim',dict(text='Approve to receive your refund',consent=True,amount_paise=amount))):
            result,_,_,_=apply_policy(payment,features,scored)
            action=result['action'];actions[name][action]=actions[name].get(action,0)+1
    return dict(status='measured',worlds=n_worlds,seed=seed,endpoint_history_events={
            'min':min(endpoint_counts),'max':max(endpoint_counts),'zero_history_worlds':sum(n==0 for n in endpoint_counts)},
        model_sha256=sha256_file(model_path),calibration_sha256=sha256_file(conformal_path),
        probability_range=[float(min(scores)),float(max(scores))],uncertainty_sets=uncertainty,
        policy_actions=actions,
        definition='Each generated everyday world supplies a sender and recipient with zero prior endpoint payment events. The same live wallet model, online feature snapshot, conformal result and policy are used. The neutral and consented refund-claim variants are advice-flow probes; no scam labels or accuracy are inferred.',
        limits=['This is a deterministic synthetic zero-history exercise, not a cohort study of new UPI users.',
                'The message claim changes policy context only; it is not evidence that a real refund or payment is genuine.',
                'No sandbox balance is changed by this report.'])


def run_full(features_path,transactions_path,model_path,conformal_path,split='test',wallet_model='models/wallet/xgb_model.json',wallet_conformal='models/wallet/conformal.json',probe_worlds=64,probe_seed=43001):
    report=run(features_path,transactions_path,model_path,conformal_path,split)
    wallet_model_path=ROOT/wallet_model;wallet_conformal_path=ROOT/wallet_conformal
    if wallet_model_path.is_file() and wallet_conformal_path.is_file():
        report['zero_history_probe']=zero_history_probe(wallet_model_path,wallet_conformal_path,probe_worlds,probe_seed)
    else:
        report['zero_history_probe']=dict(status='not_run',reason='Wallet model bundle is unavailable.')
    return report
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--features',default='data/features.csv');p.add_argument('--transactions',default='data/transactions.csv');p.add_argument('--model',default='models/xgb_model.json');p.add_argument('--conformal',default='models/conformal.json');p.add_argument('--split',default='test');p.add_argument('--wallet-model',default='models/wallet/xgb_model.json');p.add_argument('--wallet-conformal',default='models/wallet/conformal.json');p.add_argument('--probe-worlds',type=int,default=64);p.add_argument('--probe-seed',type=int,default=43001);p.add_argument('--out',default='reports/cold-start.json');a=p.parse_args()
    report=run_full(a.features,a.transactions,a.model,a.conformal,a.split,a.wallet_model,a.wallet_conformal,a.probe_worlds,a.probe_seed);out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    for name,metrics in report['buckets'].items():print(f"{name}: honest={metrics['honest']} unsure={metrics['honest_unsure_share']} nudge={metrics['honest_nudge_share']} scams={metrics['scams']} missed={metrics['scam_miss_count']}")
    print('Zero-history live path:',report['zero_history_probe']['status'],report['zero_history_probe'].get('policy_actions'))
    print('Report:',out)
if __name__=='__main__':main()
