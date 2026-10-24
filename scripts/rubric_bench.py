"""Rubric benchmark: model + Two-Signal policy on rows the model never trained on.

usage: python rubric_bench.py FEATURES_CSV TRANSACTIONS_CSV SPLITS(comma list or 'all') LABEL
Run from the repo root (imports src/).
"""
import math
import sys
import time

import numpy as np
import pandas as pd
import xgboost as xgb

sys.path.insert(0, "src")
from conformal import SET_NAMES, load_conformal, predict_sets  # noqa: E402
from policy import (DEFAULT_THRESHOLDS, PAYMENT_HISTORY_FEATURES,  # noqa: E402
                    RECEIVING_ACCOUNT_FEATURES, decide)
from risk_common import FEATURE_COLUMNS, load_features  # noqa: E402


def wilson(k, n, z=1.96):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (100 * max(0, c - h), 100 * min(1, c + h))


feat_path, tx_path, splits, label = sys.argv[1:5]
df = load_features(feat_path, FEATURE_COLUMNS + ["amount", "ts", "sender_id"]).reset_index(drop=True)
if splits != "all":
    df = df[df["split"].isin(splits.split(","))].reset_index(drop=True)
tx = pd.read_csv(tx_path, usecols=["txn_id", "scam_type", "campaign_id", "stage"])
df = df.merge(tx, on="txn_id", how="left").reset_index(drop=True)

model = xgb.XGBClassifier()
model.load_model("models/xgb_model.json")
qf, qs = load_conformal("models/conformal.json")

t0 = time.perf_counter()
p = model.predict_proba(df[FEATURE_COLUMNS])[:, 1]
batch_ms = (time.perf_counter() - t0) * 1000
sets = predict_sets(p, qf, qs)
feats = df[list(PAYMENT_HISTORY_FEATURES + RECEIVING_ACCOUNT_FEATURES)].to_dict("records")
amt = df["amount"].to_numpy(float)
act = np.array([decide(SET_NAMES[int(s)], f, None, None, a, DEFAULT_THRESHOLDS)["action"]
                for s, f, a in zip(sets, feats, amt)])
y = df["is_scam"].to_numpy(int) == 1
legit = ~y
n, npos, nneg = len(df), int(y.sum()), int(legit.sum())

print(f"=== {label}: {n:,} payments, {npos} scams, {nneg:,} honest "
      f"(batch scoring {batch_ms / max(n, 1) * 1000:.2f} µs/payment)")
hold, nudge, rel = act == "hold", act == "nudge", act == "release"
stopped = ~rel
for name, m in (("hold", hold), ("nudge", nudge), ("release", rel)):
    print(f"  {name:<8} scams {int(m[y].sum()):>5} ({m[y].mean() * 100:6.2f}%)   honest {int(m[legit].sum()):>7,} "
          f"({m[legit].mean() * 100:6.3f}%)")
k = int(stopped[y].sum())
lo, hi = wilson(k, npos)
print(f"  scams intercepted (hold or nudge): {k}/{npos} = {k / max(npos, 1) * 100:.2f}%  (95% CI {lo:.1f}-{hi:.1f}%)")
kh = int(hold[y].sum())
lo, hi = wilson(kh, npos)
print(f"  scams held: {kh}/{npos} = {kh / max(npos, 1) * 100:.2f}%  (95% CI {lo:.1f}-{hi:.1f}%)")
print(f"  confusion (positive = hold): TP={kh} FN={npos - kh} FP={int(hold[legit].sum())} "
      f"TN={int((~hold)[legit].sum())}  hold precision={kh / max(int(hold.sum()), 1) * 100:.1f}%")
print(f"  false-positive rates: honest held {hold[legit].mean() * 100:.3f}%, honest nudged "
      f"{nudge[legit].mean() * 100:.3f}%, honest interrupted at all {stopped[legit].mean() * 100:.3f}%")

# per scam type (one row per type) and conformal coverage
print("  by scam type:")
for st, g in df[y].groupby(df.loc[y, "scam_type"].fillna("?")):
    m = act[g.index.to_numpy() if False else df.index.get_indexer(g.index)]
    print(f"    {st:<16} n={len(g):>4}  held {np.mean(m == 'hold') * 100:5.1f}%  intercepted "
          f"{np.mean(m != 'release') * 100:5.1f}%  released {int((m == 'release').sum())}")
cov_s = np.isin(sets[y], [k_ for k_, v in SET_NAMES.items() if v != "{fine}"]).mean() * 100
cov_f = np.isin(sets[legit], [k_ for k_, v in SET_NAMES.items() if v != "{scam}"]).mean() * 100
print(f"  conformal coverage: scam {cov_s:.2f}% (target 90), fine {cov_f:.2f}% (target 99)")

# money and the RBI flat-rule baseline
rs_total = amt[y].sum()
print(f"  ₹ of scam money stopped: Maya hold {amt[y & hold].sum() / rs_total * 100:.1f}%, "
      f"hold-or-nudge {amt[y & stopped].sum() / rs_total * 100:.1f}%")
rbi = amt > 10_000
budget = int(hold[legit].sum())
thr_amt = np.sort(amt[legit])[::-1][budget - 1] if budget else np.inf
same = amt >= thr_amt
print("  per 1,000 honest payments slowed (hold) -> share of scam ₹ stopped:")
for nm, m in (("RBI flat rule: delay all > ₹10k", rbi), ("amount rule, same honest budget", same),
              ("Maya (hold only)", hold)):
    slowed = m[legit].mean() * 1000
    print(f"    {nm:<34} honest slowed {slowed:7.2f}/1000   scam ₹ stopped {amt[y & m].sum() / rs_total * 100:5.1f}%   "
          f"scams stopped {m[y].mean() * 100:5.1f}%")

# journeys: stopped by the 2nd scam payment?
j = df[y].copy()
j["act"] = act[df.index.get_indexer(j.index)]
j = j.sort_values("ts")
first = []
for _, g in j.groupby(["campaign_id", "sender_id"]):
    a = g["act"].to_numpy()
    idx = np.flatnonzero(a == "hold")
    first.append(idx[0] + 1 if len(idx) else None)
nj = len(first)
by2 = sum(1 for f in first if f is not None and f <= 2)
never = sum(1 for f in first if f is None)
print(f"  victim journeys: {nj}; held by 2nd scam payment {by2}/{nj} = {by2 / max(nj, 1) * 100:.1f}%; "
      f"never held {never}")

# named failure cases
miss = df[y & rel]
print(f"  released scams (named misses): {len(miss)}")
for _, r in miss.head(8).iterrows():
    print(f"    txn {int(r.txn_id)} {r.scam_type} stage {r.stage} ₹{r.amount:,.0f} p={p[df.index.get_loc(_)]:.4f} "
          f"d_R={r.d_R:.0f} z_t={r.z_t:.2f} zc_t={r.zc_t:.2f} n_t={r.n_t:.0f}")
fp = df[legit & hold]
if len(fp):
    print(f"  honest payments held (false positives), first 5 of {len(fp)}:")
    for _, r in fp.head(5).iterrows():
        print(f"    txn {int(r.txn_id)} ₹{r.amount:,.0f} p={p[df.index.get_loc(_)]:.4f} d_R={r.d_R:.0f} "
              f"z_t={r.z_t:.2f} zc_t={r.zc_t:.2f} n_t={r.n_t:.0f}")
