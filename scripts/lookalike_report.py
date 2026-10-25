"""Report honest-lookalike interventions on the chronological synthetic test set."""
import argparse,json,sys,math
from pathlib import Path
import numpy as np,pandas as pd,xgboost as xgb
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts'))
from evidence_utils import sha256_file,source_fingerprints
from conformal import SET_NAMES,load_conformal,predict_sets
from policy import DEFAULT_THRESHOLDS,PAYMENT_HISTORY_FEATURES,RECEIVING_ACCOUNT_FEATURES,decide
from risk_common import FEATURE_COLUMNS,TARGET,load_features

KINDS=('wedding_festival','first_time_merchant','rent_increase','genuine_refund_credit','large_known_contact_proxy')

def wilson(k,n,z=1.96):
    if not n:return [None,None]
    p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return [max(0,c-h),min(1,c+h)]

def run(features_path,transactions_path,model_path,conformal_path):
    f=load_features(features_path,FEATURE_COLUMNS+[TARGET,'txn_id','split','amount']).reset_index(drop=True)
    tx=pd.read_csv(transactions_path,usecols=['txn_id','lookalike_type','category'])
    df=f.merge(tx,on='txn_id',how='left',validate='one_to_one')
    df=df[(df.split=='test')&(df[TARGET]==0)&df.lookalike_type.isin(KINDS)].reset_index(drop=True)
    model=xgb.XGBClassifier();model.load_model(model_path);qf,qs=load_conformal(conformal_path)
    probabilities=model.predict_proba(df[FEATURE_COLUMNS])[:,1];sets=predict_sets(probabilities,qf,qs)
    feats=df[list(PAYMENT_HISTORY_FEATURES+RECEIVING_ACCOUNT_FEATURES)].to_dict('records')
    actions=np.array([decide(SET_NAMES[int(s)],v,None,None,float(a),DEFAULT_THRESHOLDS)['action'] for s,v,a in zip(sets,feats,df.amount)])
    results={}
    for kind in KINDS:
        mask=df.lookalike_type.to_numpy()==kind;n=int(mask.sum());hold=int(np.sum(mask&(actions=='hold')));nudge=int(np.sum(mask&(actions=='nudge')))
        results[kind]=dict(support=n,held=hold,nudged=nudge,released=int(np.sum(mask&(actions=='release'))),
            any_intervention_rate=(hold+nudge)/n if n else None,hold_rate=hold/n if n else None,
            any_intervention_rate_95ci=wilson(hold+nudge,n),
            scope=('incoming-credit counterfactual stress check; outside outgoing pre-authorization scope'
                   if kind=='genuine_refund_credit' else 'outgoing synthetic pre-authorization control'),
            note=('synthetic delayed incoming credit; not a live refund or payment authorization'
                  if kind=='genuine_refund_credit' else
                  'large_known_contact_proxy is a synthetic P2P proxy, not a labelled family relationship'
                  if kind=='large_known_contact_proxy' else 'synthetic lookalike control, not a real customer distribution'))
    return dict(schema='maya-lookalike-report-v1',split='later-day test',total_lookalike_rows=len(df),
        source_fingerprints=source_fingerprints(features_path,transactions_path),model_sha256=sha256_file(model_path),results=results,
        provenance='Generated synthetic controls tagged outside the model feature contract.',
        limits=['These are simulator-specific controls, not real customer distributions.',
                'genuine_refund_credit is an incoming-credit counterfactual feature stress check, not an outgoing pre-authorization or live bank refund.',
                'A high intervention rate in that incoming-credit row must not be presented as a false-positive rate for outbound UPI payments.'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--features',default='data/features.csv');p.add_argument('--transactions',default='data/transactions.csv');p.add_argument('--model',default='models/xgb_model.json');p.add_argument('--conformal',default='models/conformal.json');p.add_argument('--out',default='reports/lookalikes.json');a=p.parse_args()
    report=run(a.features,a.transactions,a.model,a.conformal);out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    for name,metrics in report['results'].items():print(f"{name}: n={metrics['support']} held={metrics['held']} nudged={metrics['nudged']} intervention={metrics['any_intervention_rate']}")
    print('Report:',out)
if __name__=='__main__':main()
