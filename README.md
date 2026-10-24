# Maya — real-time UPI scam intervention

Maya will score each UPI payment for scam risk and decide whether to **release**,
**nudge** (warn the payer), or **hold** it. Everything runs on synthetic data.

This is the starting point of the project: the environment setup and the
**synthetic data generator**, the first stage of the pipeline.

`src/journey_generator.py` simulates users, everyday payments, and 5-stage scam
journeys (investment, digital arrest, sextortion), with the stolen money layered
`victim -> entry mule -> mid mule -> aggregator -> exit`. It is deterministic
(`--seed`, default 42) and splits the data by contiguous day blocks
(train/val/test = 60/20/20), keeping every scam campaign inside one split so later
models can't leak across splits.

## Setup (Windows)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

`requirements-gnn.txt` adds `torch` / `torch-geometric`, which only a later graph
model stage needs.

## Generate the data

```powershell
# Small smoke dataset (600 users / 30 days, < 1 s) -> data/smoke/
.venv\Scripts\python src/journey_generator.py --smoke

# Full dataset (20k users / 120 days, ~30 s, ~430 MB) -> data/
.venv\Scripts\python src/journey_generator.py
```

Flags: `--out-dir`, `--seed`, `--users N`, `--days N`.

Outputs:

| File | Contents |
|---|---|
| `transactions.csv` | one row per payment, with `split`, `is_scam`, scam stage |
| `graph_edges.csv` | aggregated sender → receiver edges |
| `labels.csv` | one row per account: role, mule/victim flags, (slow, partial) fraud reports |

A run is healthy when its printed summary shows `campaign_split_violations == 0`
and `ref_integrity == True`. `data/` is generated and gitignored.

## Roadmap

1. Synthetic data generator ← *this commit*
2. Past-only journey features
3. XGBoost risk model, conformal prediction sets, SHAP reasons
4. Two-Signal action policy (release / nudge / hold)
5. Streamlit demo UI
