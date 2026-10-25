# Six-minute MAYA judge runbook

One architecture should appear in the pitch, README and `/demo/`: see [MAYA_PILOT_BLUEPRINT.md](MAYA_PILOT_BLUEPRINT.md#serving-and-safety-boundary). This is a rehearsal script; the team must time and practice it rather than claim rehearsals that have not occurred.

## Prepare

1. From the repo root, install `requirements-dev.txt`, build the V4 bundle using `scripts/bootstrap_v4.py` and `scripts/train_wallet_bundle.py`, then start `run_demo.py`.
2. Open `/app/` on the customer device, `/demo/` on the judge display and `/recipient/` on a separate recipient device. Pair each with its own code. For the contact path, first enable consent in the customer app, then pair `/contact/`.
3. If analyst review is part of the demonstration, provision a random 32+ character `MAYA_OPERATOR_KEY` and open `/operator/`. On Render it is generated; copy it from the service's Environment page. Never show the key. On the public Render site (docs/DEPLOY_RENDER.md), judges pair by scanning the QR on the customer's payment screen with their own phones. Keep a local run and a second browser ready as backup.
4. To show a hold ending within the time slot, use **Skip ahead 1 hour of practice time** on the held payment. Say clearly that this is the practice world's clock; a real hold lasts a real hour.
5. Have [RUBRIC_DELIVERY.md](RUBRIC_DELIVERY.md) and the frozen PaySim/load evidence open for questions.

## Timing and story

| Time | Demonstration |
|---|---|
| 0:00–0:35 | Frame the user problem from the limited NIT Warangal vendor conversations: connectivity, soundbox reliance, fake-payment claims and phishing SMS. State that the observations are qualitative, not prevalence data. |
| 0:35–1:20 | Show the customer and recipient as separate devices. Explain that the demo transfers sandbox ledger balance only; no bank or UPI rail is connected. |
| 1:20–2:10 | On `/demo/`, choose a synthetic recipient and enter a new amount/context. Send it to the paired phone. On the phone, edit or cancel it; then request a review. Point to the computed features, model/policy versions and reason source. |
| 2:10–3:05 | Use a hold case. Show that a trusted contact can respond only with advice, then show the operator queue for an eligible high-value held payment. Approve/reject the exact revision; verify that the timer and final state still come from the backend. |
| 3:05–3:45 | Confirm a released dummy transfer and show the recipient's ledger-backed balance/receipt. Emphasize that an image or “payment success” claim cannot create a ledger transfer. |
| 3:45–4:35 | Open the evidence/metrics view. Separate PaySim, authored scenarios and same-generator wallet results; call out the small 89-positive PaySim test and synthetic-data limits. The 3-seed wallet mean PR-AUC is 0.798, but seeds share one generator. The kit is 20/24: spaced-probe and slow-drip cases were released. Show the age-slice review flag and the incoming-refund scope label. |
| 4:35–5:15 | Show the privacy panel with the exact request JSON; explain that message parsing is local and the API accepts derived labels, not raw message text. Show consent/revocation and the retention settings. |
| 5:15–6:00 | Close with the shadow-pilot boundary: bank rules remain authoritative; MAYA must meet source-matched quality, privacy and load gates before any enforcement. Name public hosting, human usability review and real-bank validation as outstanding. |

If a flow fails, switch to the local backup and identify the failed integration plainly; do not present a screenshot as a live transaction.

## Questions judges may ask

- **Does this move real UPI money?** No. The recipient sees a transfer only after the sandbox server commits ledger entries.
- **Is the data real?** PaySim is public synthetic mobile-money data. The interactive model uses generated worlds. Neither is real UPI customer data.
- **Why XGBoost instead of a large deep model?** It gives a compact CPU scoring path and a simpler latency/explanation boundary for this prototype. Neural/graph experiments remain challengers until source-matched evaluation shows a reliable gain.
- **Can a user be blocked by one suspicious score?** The sandbox requires two independent evidence groups for a hold; a model set alone cannot hold. Recipient report and mule flags are one group.
- **Can MAYA stop every payment in any UPI app?** No. Only the bank/PSP that owns authorization can enforce an action. The companion can provide limited advice and must abstain when bank facts are unavailable.
- **Will it scale to India's UPI volume?** Not established. The local load result is a short single-host observation; production TPS needs target-hardware/PostgreSQL measurements and bank traffic tests.
- **Does the 1930 button submit a complaint?** No. MAYA creates a labeled evidence draft; no government/bank endpoint is connected.
- **How can it be evaded?** The current kit misses slow-drip and spaced-probe behavior. The 64-world zero-history probe produces non-blocking nudges for neutral first payments and consented refund-claim context; that is a safeguard behavior check, not an estimate of safety or harm rates in actual customers. Unreported recipients and misleading evidence remain risks. Show `docs/evidence/kit.json` and `cold-start.json`, then name the next validation rather than promise complete detection.

## Claims to avoid

Do not call the sandbox bank-ready, real-time UPI-integrated, nationally scalable, demographically fair, fully accurate, or capable of filing an official complaint. Do not use perfect same-generator wallet metrics as external accuracy.
