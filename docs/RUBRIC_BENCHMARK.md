# Rubric benchmark (25 Oct 2026)

Measured on this code with the trained bundle in `models/` (XGBoost, 27 features,
`best_iteration` 187, Mondrian conformal). All data is synthetic, from our own
generator (`src/journey_generator.py`): these numbers prove the pipeline, not
real-UPI accuracy.

Reproduce (repo root, data and models built as in the README):

```
python -m pytest -q                                   # 110 passed
python src/policy.py --self-test                      # 22/22
python src/policy.py --eval                           # action rates, test split
python src/attack_sim.py --json-out models/attack_results.json
python scripts/rubric_bench.py data/features.csv data/transactions.csv test "seed 42 test"
MAYA_RATE_LIMIT=0 python scripts/rubric_kit.py        # spot-check kit + latency

# a world the model never saw: new seed, new features, same frozen model
python src/journey_generator.py --seed 2026 --out-dir data/seed2026
python src/features.py --txns data/seed2026/transactions.csv --edges data/seed2026/graph_edges.csv \
    --labels data/seed2026/labels.csv --out data/seed2026/features.csv
python scripts/rubric_bench.py data/seed2026/features.csv data/seed2026/transactions.csv test "seed 2026"
```

## Results

| Benchmark | Result |
|---|---|
| Tests | 110 passed; policy self-test 22/22 |
| Held-out test split (later days; 706,239 payments, 546 scams) | 100% of scams intercepted, 0 released (95% CI 99.3-100%); 89.6% held, 10.4% nudged. Honest payments: 0.196% held, 0.297% nudged. Hold precision 26% |
| Never-seen world, seed 2026, same later-day window (706,360 payments, 663 scams) | 100% intercepted, 85.4% held (CI 82.5-87.9%); 0.193% honest held, 0.317% nudged |
| By scam type (seed 2026) | digital arrest 97.7% held, sextortion 89.6%, investment 80.7% |
| vs RBI flat rule (delay all > Rs 10k) | RBI rule: 8.0 honest payments slowed per 1,000, 77% of scams stopped. Maya: 1.9 per 1,000, 85% held |
| Amount-only rule with Maya's honest budget | 64% of scams stopped vs Maya's 85% |
| Victim journeys held by their 2nd scam payment | 80-86% |
| Adaptive attacks (`attack_sim.py`) | worst drop 3.5 pts (`split_10`, held out of adversarial training); rewording cuts a text-only detector by 87.9 pts, Maya by 0 |
| Conformal coverage on test | scam 100% (target 90), fine 100% (target 99) |
| Latency through the HTTP API (in-process) | p50 20 ms, p95 24 ms (target 150 ms); model alone ~0.5 us/payment in batch |
| Spot-check kit (20 judge-style inputs) | 19/20 as expected |

## Named failure cases

1. **Cold start.** Scoring a whole new world, the share of honest payments put in
   the unsure set is 82% in its first 10 days, 45% by day 30, 6.7% by day 60 and
   0.5% after day 90. Thin-history users get many nudges (never holds without two
   signal groups). Over all days of seed 2026: 17.6% of honest payments nudged.
2. **A directly reported payee alone is released.** A payee one hop from a
   reported account with nothing else unusual gets `{fine}` and is released, even
   with a MuleHunter "mule" verdict (the mule signal only counts when the set is
   not `{fine}`).
3. **Amount on the built-in scenarios does not move the model.** Amount enters
   only through history features, which are fixed for those scenarios; the
   "Your own payment" lab recomputes them.
4. **One investment scam released** in the full seed-2026 world: Rs 819, stage 2,
   p = 0.0006, d_R = 2.

## Estimated rubric position (not a prediction of the jury)

| Criterion | Weight | Estimate | Main gap |
|---|---:|:---:|---|
| S1 Working prototype | 25 | 4 | receipt and provider checks mocked; built-in scenarios ignore amount |
| S1 Spot-check and accuracy | 30 | 4 (risk 3) | own generator only; no held-out scam type or 3-seed range yet |
| S1 Own engineering | 15 | 5 | every member must be able to walk through it |
| S1 Alert and response | 15 | 3 | analyst and trusted-contact paths described, not running |
| S1 Delivery vs Round 1 | 15 | 3 (4 with a cuts table) | chat stage, voice, typing, stage bar, analyst screen, fairness slices not built |
| S2 Problem and user | 20 | 5 | keep Ramesh grounded in NCRP data |
| S2 Deployability and scale | 15 | 3 | no cost model, operator or live host |
| S2 Communication and Q&A | 10 | 4? | rehearsal |
| S2 Live user journey | 25 | 3-4 | no review/report step or authoritative settlement |
| S2 Adversarial robustness | 20 | 4-5 | add the missing attack families and show a miss live |
| S2 Responsible AI | 10 | 3-4 | mistaken-hold recovery not shown or timed |

See `docs/RUBRIC_PLAN.md` for the changes that close each gap.
