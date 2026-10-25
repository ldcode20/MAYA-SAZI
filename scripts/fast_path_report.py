"""Measure a candidate known-payee/low-value fast path; does not change serving."""
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from evidence_utils import sha256_file

def run(transactions_path,split='test',amount_cap=2000):
    cols=['txn_id','ts','sender_id','receiver_id','amount','status','split','is_scam']
    tx=pd.read_csv(transactions_path,usecols=cols,parse_dates=['ts']).sort_values(['ts','txn_id']).reset_index(drop=True)
    successful=tx.status.astype(str).eq('SUCCESS')
    previous=tx.loc[successful].groupby(['sender_id','receiver_id'],sort=False).cumcount()
    tx['known_pair']=False;tx.loc[successful,'known_pair']=previous.to_numpy()>0
    test=tx[tx.split==split]
    eligible=(test.known_pair&(test.amount<=amount_cap))
    scams=test.is_scam.astype(bool);bypass_scams=int((eligible&scams).sum());total_scams=int(scams.sum())
    return dict(schema='maya-candidate-fast-path-v1',split=split,transactions_sha256=sha256_file(transactions_path),
        definition=dict(known_payee='prior successful transaction by same sender to same receiver in this generated file',amount_cap_inr=amount_cap),
        transactions=len(test),eligible_count=int(eligible.sum()),eligible_share=float(eligible.mean()) if len(test) else 0,
        eligible_scam_count=bypass_scams,total_scam_count=total_scams,
        share_of_scam_transactions_bypassed=bypass_scams/total_scams if total_scams else None,
        decision='measurement only; fast-path bypass is not enabled',
        limitations=['Synthetic dataset only.','Equal timestamps are ordered by transaction id and count as prior only when earlier in that order.',
                     'Does not establish a safe bank production bypass threshold.'])

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--transactions',default='data/transactions.csv');p.add_argument('--split',default='test');p.add_argument('--amount-cap',type=float,default=2000);p.add_argument('--out',default='reports/fast-path.json');a=p.parse_args()
    report=run(a.transactions,a.split,a.amount_cap);out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f"Candidate eligible={report['eligible_share']:.1%}; scams bypassed={report['eligible_scam_count']}/{report['total_scam_count']} ({report['share_of_scam_transactions_bypassed']})")
    print('Measurement only; no fast path enabled. Report:',out)
if __name__=='__main__':main()
