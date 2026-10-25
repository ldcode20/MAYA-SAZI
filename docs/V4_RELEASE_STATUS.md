# V4 implementation and release status

Original V4 snapshot: 24 October 2026, based on merged PR8 / `5872f87`, developed on `codex/v4-product`. The rubric-audit additions below are in the current `codex/rubric-evidence` branch, based on commit `959666d` in `ldcode20/MAYA-SAZI`.

## Rubric-audit additions (25 October 2026)

Implemented in the current branch; full branch verification is recorded in the running log after it completes.

| Audit gap | Current implementation | Proof status |
|---|---|---|
| Judge-controlled live variation | `/demo/` accepts a judge-selected amount, synthetic recipient and context; the server creates an intent that appears in the paired customer app. The customer still owns edit/review/cancel; judge cannot execute. | Regression test added; local browser rehearsal/public host pending. |
| Trusted-contact response | Consent required before pairing; separate contact view; support/concern response is advisory; consent revokes existing contact access. | Regression test added; independent human usability not run. |
| Analyst review | `/operator/` queue for eligible held payments above INR 1 lakh; approve/reject binds payment, review and revision; stale actions fail and audit events preserve model/policy versions. Approval cannot bypass the timer. | Regression test added; shared credential is demo-only, not per-person production identity. |
| Retention and request minimization | Runtime defaults: 7 days for sandbox worlds/events and 24 hours for derived checks. Companion API accepts only categorical intent fields; raw message text is processed in the browser. | TTL, revocation and strict request schema tests added; backups need their own deletion schedule. |
| Honest metrics | Generated kit, three-seed sweep, held-out scam type, lookalike, fairness, cold-start and measurement-only fast-path reports are frozen with model/data hashes. Cohort tags remain outside model features. | Kit is 20/24; both spaced-probe and both slow-drip cases were released. The age fairness gap crosses the descriptive review gate. A 64-world no-history probe shows non-blocking nudges for neutral and refund-claim variants; it is a behavior probe, not accuracy. Reports and caveats are itemized in `RUBRIC_DELIVERY.md`. |
| Judge / pilot communication | Added rubric proof matrix, pilot blueprint, six-minute runbook and asset/contribution ledger. | Rehearsal, public hosting, and per-member attribution confirmation remain team actions. |

Policy detail: a direct recipient report and a mule verdict are both recipient-group evidence. They nudge alone and do not create a hold without an independent signal group. This avoids treating correlated signals as two separate reasons.

## Implemented

|V4 requirement|Delivered|Evidence|
|Model/wallet integration|Exact batch computation of all 27 features, both endpoints, time availability, prior-day graph; two-threshold calibration and selected-tree explanation reconstruction|Random-world independent oracle and ledger regression tests|
|Customer product|Mobile home/review/result/activity/settings, editable recipient/amount, server-owned dummy execution, cancel and evidence draft, English/Hindi draft UI|Three-context browser screenshots and test report|
|Judge separation|Pairing codes, scoped HttpOnly grant, read-only cross-device snapshots and resumable ordered events|Denied mutation/cross-session tests; actual browser recipient and judge sessions|
|Companion privacy|QR/link parsing and explicit camera fallback; raw messages processed locally; only derived intent is sent; no fabricated behavioral score|Network canary and request/storage rejection tests|
|Data/evaluation|Downloaded public PaySim with checksums, separate adapter, whole-hour held-out splits; logistic/XGBoost/MLP comparison|Frozen public benchmark and leakage tests|
|Source matching|Separate interactive-world model; root batch model retained; no automatic sandbox model use on bank traffic|Disjoint world-seed train/val/calibration/test report; baseline failures retained|
|Robustness|Event-level split and fresh-recipient scenarios recompute histories; no desired verdict enters inference|Authored validation kit, explicitly separate from real fraud accuracy|
|Trust and recovery|Signed records and sanitized projection signatures, role separation, draft-only cases, operator label maturity/corrections|Tamper/access/privacy/retention tests; no official reporting claim|
|Deployment package|Non-root Docker image, PostgreSQL adapter/migrations, Caddy HTTPS, readiness/liveness, bounded admission, exact proxy trust|Compose validation and PostgreSQL CI jobs; local browser/service checks|
|Recovery|Artifact checkpoints, existing safe Git recovery, consistent SQLite backup tool, PostgreSQL backup/restore instructions|Preserved original artifacts and release instructions|

## Important limits

- Public release is **not live yet**. A Render Blueprint (`render.yaml`, docs/DEPLOY_RENDER.md) is ready, but someone must connect the repository at render.com before a public URL exists. Until then, the user has no server, cloud account or registered hostname connected. Docker is not installed on this workstation. GitHub Actions verified the Docker image build/startup and the PostgreSQL two-instance integration at commit `191de3d`; the actual target-host and public TLS rehearsal remain pending.
- Local SQLite full-path load results are short experiments on one machine, not production throughput or a guarantee for PostgreSQL replicas. See the frozen load report for saturation and rejected requests.
- The root batch smoke model missed its benign-class calibration target and generalized poorly to wallet worlds. Its failure report is retained. A separate generator-specific sandbox model improves those local journeys; this does not establish real-world generalization. Synthetic class mix and generator structure make its held-out task easy.
- PaySim is synthetic mobile-money data, not real UPI, and this run uses a disclosed chronological prefix. Opening balances are assumed pre-decision inputs for this benchmark. Partner availability still needs verification.
- A companion cannot observe private bank history, verify a QR display name, intercept every UPI app or enforce an external payment hold. It returns a limitation when those facts are absent. Actual money movement stays outside this release.
- Hindi copy needs native review. Keyboard/reduced-motion/mobile checks do not establish complete WCAG certification. Five independent human usability sessions remain unperformed.
- Android/iOS native extensions, full mandate lifecycle, validated production graph/sequence models, global multi-replica quotas and a production feature store remain gated follow-up work under V4. No fake implementations were added to claim them complete.
- Partner integration needs an authorized source-specific validation bundle and institution-owned authentication/status. HMAC signing is server authentication, not independent public-key attestation or a regulator audit.

## Source and metric separation

`docs/evidence/paysim.json`: external public synthetic benchmark.

`docs/evidence/wallet-model.json`: disjoint-seed interactive generator model; same generator family across splits.

`docs/evidence/validation-baseline.json` and `validation.json`: small authored event-level kit, before/after source routing. These are scenarios, not unbiased fraud prevalence estimates.

`docs/evidence/load.json`: client-observed complete-review latency/errors on the stated local workload. No scoring microbenchmark is presented as payment-system capacity.

`docs/evidence/browser.json`: automated browser integration checks, not a human comprehension study.

Verification at `191de3d`: [all CI jobs passed](https://github.com/aldenantonythalachira/maya-fraud-detection/actions/runs/40115861372). Final local baseline before subsequent small safeguards: 137 tests passed, one PostgreSQL test skipped locally, 24 subtests; policy self-test 22/22. PR9 remains a draft to expose hosting and human-review gates.

Raw data, trained artifacts, private session keys and live databases remain ignored by Git. Rebuild and verify bundles for each release. Preserve pre-event asset disclosure and finale commit history; this implementation does not change when prior work was created.
