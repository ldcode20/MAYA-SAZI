# Rubric proof: delivered, partial and still gated

Updated 25 October 2026. This records what the repository can show today; it does not predict a score. A green software test proves a code path, not real-world fraud performance or a completed human rehearsal.

## Stage 1

| Judge criterion | Status | What is demonstrable | Proof and remaining gap |
|---|---|---|---|
| Working prototype | **Partial** | A judge can create a new amount/recipient/context on `/demo/`; the paired customer receives it, edits it, and submits a server-scored review. Confirmed transfers use the sandbox ledger and create a recipient-visible receipt. | `tests/test_product.py`; `docs/evidence/browser.json`. Local flow only; public host and venue rehearsal are pending. |
| Detection metrics | **Partial** | PaySim is separately reported: 250,349 held-out rows, 89 fraud labels, recall 0.854 and precision 0.028 at its validation-selected operating point. Three 5,000-user × 60-day generated worlds produced mean PR-AUC 0.798 (range 0.736–0.876), mean recall 0.843 at validation-selected 1%-FPR thresholds (range 0.808–0.884), and observed FPR 0.24%–0.78%. | `docs/evidence/paysim.json`, `wallet-model.json`, `seed-sweep.json`. PaySim is synthetic mobile money; all wallet seeds share one generator family. Neither is a real-UPI estimate or independent population sample. |
| Own engineering | **Partial** | Feature lineage, exact online feature recomputation, policy, ledger, and role-scoped APIs are inspectable. | `docs/FEATURE_CONTRACT.md`, `docs/V4_SPECIFICATION.md`, `src/online_features.py`, `src/simulator_service.py`. Add individual names and verified commit IDs to `CONTRIBUTION_LEDGER.md`; do not infer authorship from a shared GitHub account. |
| Alert and response | **Partial** | `/operator/` has a separate demo credential and revision-bound approve/reject; `/contact/` is opt-in, revocable and advice-only; the app shows the exact derived request body; evidence packets are drafts. World/check TTLs are configured and regression-tested. | `tests/test_product.py`; `/operator/audit`. No external 1930/bank submission, individual operator identity, or timed human review has been demonstrated. |
| Delivery against proposal | **Partial** | Research/deck promises and evidence boundaries are summarized below. | No feature is marked delivered solely because it appears in a plan or older branch. |

## Stage 2

| Judge criterion | Status | What is demonstrable | Proof and remaining gap |
|---|---|---|---|
| Problem and user | **Partial** | README records qualitative visits to around 10 vendors near NIT Warangal and the reported concerns: soundboxes, connectivity, fake-payment claims and phishing SMS. | `README.md`, `docs/field-research/`. This is a small qualitative sample, not a prevalence study. The demo does not yet replay a validated Ramesh day-6/8/10 journey. |
| Deployability and scale | **Partial** | Docker, PostgreSQL, Caddy/HTTPS and backup instructions are included. A prior local full-review run reached 25 successful requests/s with 37 ms p95; at 50 offered requests/s it returned 60 overload responses and p95 was 229 ms. | `docs/DEPLOY_V4.md`, `docs/evidence/load.json`. One Windows host, SQLite, a shared hot world and short load levels; **not** a per-core production capacity guarantee. No public domain/server is connected. |
| Communication and Q&A | **Partial** | A single architecture and launch/runbook is provided in `JUDGE_RUNBOOK.md`. | A six-minute script is a rehearsal guide, not evidence that the team has completed three timed rehearsals. |
| Live journey | **Partial** | Customer, judge, recipient and optional trusted-contact pages show a server-created simulation and ledger-backed final state. The judge can vary core payment inputs. | `tests/test_product.py`, `docs/evidence/browser.json`. No actual UPI integration or external money movement; judge controls are input-only. Human accessibility/usability sessions remain pending. |
| Adversarial robustness | **Partial** | The generated-event kit passed 20/24 authored invariants. Split-10 and warmed-recipient examples interrupted; both spaced-probe and both slow-drip examples were released. Leave-one-type-out tests interrupted 61/72 investment, 21/21 digital-arrest and 10/10 sextortion transactions, counting a nudge as interruption. | `docs/evidence/kit.json`, `heldout-types.json`. The held-out supports are only 72/21/10 transactions across 7/3/1 campaigns, from the same generator family; no independent red team or loss-prevention claim. |
| Responsible AI | **Partial** | Two-signal intervention, versioned reasons/events, consent/revocation and TTL safeguards are present. Synthetic fairness miss-rate gaps are 3.03 pp for age (review), 0.53 for language and 1.29 for phone type. A 64-world live-path zero-history probe produced a non-blocking nudge in every neutral and consented refund-claim case. | `docs/evidence/fairness.json`, `cold-start.json`, `tests/test_policy.py`, `tests/test_wallet.py`. Synthetic cohorts are not demographic evidence; the zero-history result is an authored advice-flow probe, not accuracy. The age slice needs investigation; do not claim fairness certification. |

## Proposal promises: disposition

| Proposal item | Status | Reason / evidence |
|---|---|---|
| XGBoost, conformal set and policy with explainable reasons | **Delivered in sandbox** | Source-specific model bundle, recorded model/policy versions and reason list; see `docs/V4_SPECIFICATION.md`. |
| Payment stage bar / multilingual chat-stage classifier | **Cut** | The app supports English/Hindi draft UI and limited local intent checks; it does not claim a trained three-language scam-stage classifier. |
| AASIST voice anti-spoofing | **Cut** | No licensed, validated voice model or representative consented audio set is present. |
| Typing-rhythm signal | **Cut** | No user-behavior telemetry is collected. |
| Soft-score fusion cap / cost-sensitive learned action | **Replaced** | The deployed sandbox uses a visible two-independent-group policy. It is easier to audit and does not claim a learned cost-optimization result. |
| Analyst review | **Delivered in sandbox; rehearsal pending** | Separate `/operator/` credential, queue, revision-bound decision and audit events. Approval cannot bypass the hold timer. |
| Trusted contact | **Delivered as advice-only sandbox flow** | Consent, revoke and separate `/contact/` view. A contact response never controls payment. |
| Fairness slices | **Measured; remediation/review needed** | Age gap is 3.03 pp and crosses the descriptive 3 pp review gate; language gap is 0.53 pp and phone gap is 1.29 pp. Sparse synthetic scam support and broad confidence intervals prevent a demographic conclusion. |
| Held-out scam-type and three-seed evidence | **Measured with severe scope limits** | Seed ranges and leave-one-type-out results are frozen in `seed-sweep.json` and `heldout-types.json`. Held-out scam samples are tiny; the three worlds share a generator. Results are reproducibility evidence, not external validity. |
| Lookalike controls | **Measured; one case is out of decision scope** | First-time-merchant intervention is 0.11% (n=51,250), wedding/festival 16.77% (n=984), and rent-increase 12.09% (n=182). Genuine-refund-credit is an incoming synthetic credit; its 46.24% intervention rate is a counterfactual feature stress check, not an outbound authorization false-positive rate. |
| Cold-start controls | **Measured; non-blocking safeguard added** | Later-day test data has no accounts in the first 30 tenure days. The separate 64-world zero-history live-path probe yields 64/64 advisory nudges in both the neutral and consented refund-claim variants. The nudge is not a hold and has no effect on the ledger. Validate with real onboarding users before enforcement use. |
| Candidate fast path | **Measured; remains disabled** | A known-payee/≤₹2,000 candidate covers 60.9% of this synthetic test but would bypass 6/103 scams (5.83%). This rejects the shortcut for now; it is not a proposed bypass. |
| Graph neural network / federated learning | **Research-only** | Existing research experiments do not run on the synchronous payment path and are not production validations. |
| Public data | **Delivered with scope limits** | PaySim source receipt and benchmark are frozen; it is synthetic mobile money, not real UPI. See `docs/evidence/paysim-source.json`. |
| Real UPI transaction execution | **Out of scope** | The app moves only sandbox ledger balances. No UPI credentials, bank rails, 1930 submission or external authorization are used. |

## Current reproducible checks

From the repository root, with the documented Python environment and generated model bundle:

```powershell
python -m pytest -q
python src/policy.py --self-test
python scripts/run_kit.py
```

The kit samples fresh event histories each run; pass `--seed N` to reproduce. The frozen run uses seed `42042` and records 4 misses: spaced probes and slow-drip journeys were released in both repeats. Those are current known limits, not hidden successes. Frozen source/model hashes accompany the evidence JSON. Reports are reproducible with `scripts/run_seed_sweep.py`, `run_heldout_types.py`, `lookalike_report.py`, `fairness_report.py`, `cold_start_report.py` and `fast_path_report.py`; regenerate from the documented full data/model pipeline before treating any numbers as current. The small cold-start test tenure bins are empty, so the wallet-model probe is reported separately and explicitly as a generated zero-history exercise.
