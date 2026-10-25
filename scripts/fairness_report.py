"""Measure synthetic-cohort gaps without feeding cohort tags into inference."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence_utils import sha256_file, source_fingerprints
from conformal import SET_NAMES, load_conformal, predict_sets  # noqa: E402
from policy import DEFAULT_THRESHOLDS, PAYMENT_HISTORY_FEATURES, RECEIVING_ACCOUNT_FEATURES, decide  # noqa: E402
from risk_common import FEATURE_COLUMNS, TARGET, load_features  # noqa: E402

COHORTS = ('cohort_age_band', 'cohort_language', 'cohort_phone_type')


def wilson(k, n, z=1.96):
    if not n: return [None, None]
    p = k / n
    d = 1 + z*z/n
    center = (p + z*z/(2*n))/d
    half = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n))/d
    return [max(0.0, center-half), min(1.0, center+half)]


def evaluate(features_path, transactions_path, model_path, conformal_path, split='test', min_scam=20):
    features = load_features(features_path, FEATURE_COLUMNS + [TARGET, 'txn_id', 'split', 'amount']).reset_index(drop=True)
    tx = pd.read_csv(transactions_path, usecols=['txn_id', *COHORTS])
    frame = features.merge(tx, on='txn_id', how='left', validate='one_to_one')
    frame = frame[frame['split'] == split].reset_index(drop=True)
    if frame.empty: raise ValueError(f'No rows in split {split!r}')
    model = xgb.XGBClassifier(); model.load_model(model_path)
    qf, qs = load_conformal(conformal_path)
    probabilities = model.predict_proba(frame[FEATURE_COLUMNS])[:, 1]
    sets = predict_sets(probabilities, qf, qs)
    feats = frame[list(PAYMENT_HISTORY_FEATURES + RECEIVING_ACCOUNT_FEATURES)].to_dict('records')
    actions = np.array([decide(SET_NAMES[int(s)], f, None, None, float(a), DEFAULT_THRESHOLDS)['action']
                        for s, f, a in zip(sets, feats, frame['amount'])])
    y = frame[TARGET].to_numpy(int) == 1
    results = {}
    for column in COHORTS:
        groups = {}
        for label, indexes in frame.groupby(column, dropna=False).groups.items():
            if pd.isna(label) or label == 'not_applicable': continue
            idx = np.asarray(list(indexes), dtype=int)
            scam = y[idx]
            benign = ~scam
            missed = int(np.sum(scam & (actions[idx] == 'release')))
            interrupted = int(np.sum(scam & (actions[idx] != 'release')))
            interventions = int(np.sum(benign & (actions[idx] != 'release')))
            groups[str(label)] = dict(rows=len(idx), scam_count=int(scam.sum()),
                scam_misses=missed, scam_miss_rate=missed/int(scam.sum()) if scam.any() else None,
                scam_intercept_rate=interrupted/int(scam.sum()) if scam.any() else None,
                honest_interventions=interventions,
                honest_intervention_rate=interventions/int(benign.sum()) if benign.any() else None,
                scam_miss_rate_95ci=wilson(missed, int(scam.sum())))
        eligible = {k:v for k,v in groups.items() if v['scam_count'] >= min_scam and v['scam_miss_rate'] is not None}
        rates = [v['scam_miss_rate'] for v in eligible.values()]
        gap = max(rates)-min(rates) if len(rates) >= 2 else None
        results[column] = dict(groups=groups, eligible_group_count=len(eligible),
            scam_miss_rate_gap=gap, gate_percentage_points=3.0,
            gate=('insufficient_support' if gap is None else 'pass' if gap <= .03 else 'review'))
    return dict(schema='maya-synthetic-fairness-v1', data_split=split, cohort_source='synthetic generator metadata',
        model=Path(model_path).name, rows=len(frame), scams=int(y.sum()),
        source_fingerprints=source_fingerprints(features_path,transactions_path),model_sha256=sha256_file(model_path),
        feature_contract_columns=len(FEATURE_COLUMNS), cohort_columns_excluded_from_features=True,
        minimum_scams_per_group=min_scam, reports=results,
        limits=['Synthetic cohort distributions are not demographic evidence.',
                'A 3-point gate is descriptive only; it is not a fairness certification.',
                'Groups below the support threshold are shown but not scored against the gap gate.'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--features',default='data/features.csv'); p.add_argument('--transactions',default='data/transactions.csv')
    p.add_argument('--model',default='models/xgb_model.json'); p.add_argument('--conformal',default='models/conformal.json')
    p.add_argument('--split',default='test'); p.add_argument('--min-scam',type=int,default=20)
    p.add_argument('--out',default='reports/fairness.json'); a=p.parse_args()
    report=evaluate(a.features,a.transactions,a.model,a.conformal,a.split,a.min_scam)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    for column,item in report['reports'].items():
        gap=item['scam_miss_rate_gap']
        print(f"{column}: gate={item['gate']} gap={('insufficient support' if gap is None else f'{gap*100:.2f} pp')}")
        for group,values in item['groups'].items():
            print(f"  {group}: scams={values['scam_count']} missed={values['scam_misses']} honest-intervention={values['honest_intervention_rate']}")
    print(f"Synthetic-only report: {out}")


if __name__=='__main__': main()
