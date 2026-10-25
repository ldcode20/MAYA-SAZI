# Rebuild the frozen rubric evidence

The JSON under `docs/evidence/` is a snapshot of the runs reviewed on 25 October 2026. Each report includes source and/or model SHA-256 fingerprints. Generated transaction data and model artifacts stay out of Git; regenerate them locally before reproducing these reports.

Run the following from the repository root with the locked development dependencies installed. The 5,000-user/120-day generator and feature pass are intentionally smaller than the project's full defaults while preserving the documented chronological train/validation/calibration/test split.

## Full synthetic source and batch model

```powershell
python src/journey_generator.py --seed 42 --users 5000 --days 120 --out-dir tmp/rubric-full/data
python src/features.py --txns tmp/rubric-full/data/transactions.csv --edges tmp/rubric-full/data/graph_edges.csv --labels tmp/rubric-full/data/labels.csv --out tmp/rubric-full/data/features.csv --days 120
python src/train_xgb.py --features tmp/rubric-full/data/features.csv --model-out tmp/rubric-full/xgb_model.json --meta-out tmp/rubric-full/model_meta.json --seed 42
python src/conformal.py --features tmp/rubric-full/data/features.csv --model tmp/rubric-full/xgb_model.json --out tmp/rubric-full/conformal.json
```

Rebuild the split-specific reports from those exact local files:

```powershell
python scripts/run_heldout_types.py --features tmp/rubric-full/data/features.csv --transactions tmp/rubric-full/data/transactions.csv --out docs/evidence/heldout-types.json
python scripts/fairness_report.py --features tmp/rubric-full/data/features.csv --transactions tmp/rubric-full/data/transactions.csv --model tmp/rubric-full/xgb_model.json --conformal tmp/rubric-full/conformal.json --out docs/evidence/fairness.json
python scripts/lookalike_report.py --features tmp/rubric-full/data/features.csv --transactions tmp/rubric-full/data/transactions.csv --model tmp/rubric-full/xgb_model.json --conformal tmp/rubric-full/conformal.json --out docs/evidence/lookalikes.json
python scripts/fast_path_report.py --transactions tmp/rubric-full/data/transactions.csv --out docs/evidence/fast-path.json
python scripts/cold_start_report.py --features tmp/rubric-full/data/features.csv --transactions tmp/rubric-full/data/transactions.csv --model tmp/rubric-full/xgb_model.json --conformal tmp/rubric-full/conformal.json --out docs/evidence/cold-start.json
```

The cold-start command also runs 64 deterministic, generated zero-history probes through the separate `models/wallet/` bundle. Set `--probe-worlds` and `--probe-seed` to reproduce or change that advice-flow exercise. It is not a labeled new-customer accuracy study.

## Three-seed stability and the event-level kit

```powershell
python scripts/run_seed_sweep.py --users 5000 --days 60 --seeds 42 2026 2027 --out docs/evidence/seed-sweep.json
python scripts/bootstrap_v4.py
python scripts/train_wallet_bundle.py
python scripts/run_kit.py --seed 42042 --out docs/evidence/kit.json
```

The seed sweep rebuilds each world, feature table and model. The event kit resamples generated histories while retaining its authored scenario assertions; a nudge is counted as an interruption for an attack case, not as proof that money was saved.

## Reading and limits

- PaySim is public **synthetic mobile-money** data, not real UPI activity.
- The 5,000-user reports share one generator and labeling system. The three seed runs measure simulator-to-simulator variability, not independent populations.
- Held-out scam-type support is small (72 investment, 21 digital-arrest and 10 sextortion test transactions). A warning counts as an interruption in these reports.
- `genuine_refund_credit` is an incoming credit. Its feature stress result is out of scope for an outgoing pre-authorization false-positive rate.
- Synthetic age, language and phone metadata are not demographic evidence. The age slice currently crosses a descriptive review threshold; that is an open investigation.
- The candidate fast path is measurement-only and disabled because it would bypass known synthetic scam examples.
- A report hash identifies the exact input file used. It does not make an unavailable local dataset or model artifact part of the repository.
