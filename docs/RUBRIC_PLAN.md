# What it takes to reach 5 on every rubric criterion

Each item closes a gap between the measured evidence (`docs/RUBRIC_BENCHMARK.md`)
and the rubric's "5 =" description, with the proof a judge must see. Items marked
**[V4]** already exist on the team's `codex/v4-product` branch and are faster to
port than rebuild. No plan guarantees the jury's rating.

## Stage 1

### 1. Working prototype (25), now 4
1. Every judge-chosen input must reach the model: an event-history service that
   recomputes all 27 features from the payment plus the account's past (same
   formulas as `features.py`), replacing the fixed medians in `custom.js`.
2. Authoritative payment state [V4]: release creates a sandbox transfer with a
   server ID, cancel creates none; the phone shows that ID, never a frontend "sent".
3. A scenario editor on `/demo`: the judge sets history, payee, amount and soft
   signals and pushes it to a paired phone.
4. Host it publicly (Render or similar), rehearse on venue Wi-Fi, keep a local
   fallback.

Proof: an unseen amount and payee typed by a judge runs input, detection, alert,
action and status live.

### 2. Spot-check and measured accuracy (30), now 4
1. Held-out scam type (promised): retrain three times leaving one type out
   entirely; report detection on the unseen type.
2. Three seeds, report the range (promised): 42, 2026 and one more, later days only.
3. Honest lookalikes in the test set: festivals and weddings, legitimate new
   merchants, rent rises, real refunds, one-off family transfers; FPR per type.
4. Public data (promised, IBM AML) or PaySim [V4]: recall at 1% false alarms vs
   the 70% target.
5. A fixed printed kit (20-30 scams and honest controls) run live by one command,
   expected vs actual per case.
6. Fix or name the misses: a cold-start rule (thin history -> lighter nudge) or
   report it with numbers; decide whether d_R = 0 plus a "mule" verdict should hold.
7. Evidence tab fed from a frozen results JSON: confusion counts, FPR, intervals,
   per type, RBI baseline, named failures.

Proof: kit run live, about 95%+ right, FPR on unseen data, failures named.

### 3. Own engineering (15), now 5
1. Contribution ledger from git: built during the finale vs before, per member.
2. "Follow one payment through the code" page with file/line references.
3. Every member traces a transaction aloud in under 2 minutes.

### 4. Alert and response (15), now 3
1. Human review that runs [V4 operator API]: `/operator` with its own login, a
   hold queue, approve/reject bound to the exact revision, stale approvals fail,
   holds over Rs 1 lakh need an analyst.
2. Trusted contact for real: Priya as a second paired device gets the hold and
   can approve or decline; consent and revoke.
3. Safeguards visibly running: chat/voice signals computed in the browser with a
   "what left the phone" panel showing the request body; a no-retention test and
   TTL; an audit log of every hold with timeline, reasons and model version.
4. Report path: "report to 1930" produces a pre-filled draft, labelled a draft.

Proof: a hold reaches user, Priya and operator; the operator acts; the payment
ends in the right state; the panel shows only labels left the phone.

### 5. Delivery against Round 1 plan (15), now 3
1. Plan-vs-delivered table (slide and README), each promise Delivered / Partial /
   Cut with reason and evidence: chat-stage model (3 languages), voice
   anti-spoofing, typing flag, stage bar, analyst screen, capped soft fusion,
   cost-sensitive action choice, fairness slices, scam DNA / GNN
   (`gnn_challenger.py`), federated learning (`federated_sim.py`), held-out type
   and 3 seeds.
2. Most visible builds if time allows: fairness slices, stage bar with a small
   chat-stage classifier, the soft-score cap.

## Stage 2

### 1. Problem and user (20), now 5
Keep Ramesh and the NCRP figures; add the field visits as qualitative evidence
(no invented prevalence); replay his day 6 / 8 / 10 journey as the live demo.

### 2. Deployability and scale (15), now 3
1. One-page pilot blueprint: the bank's fraud team runs it in shadow mode; one
   call before UPI authorisation plus an app SDK; named feature sources; fail-open
   to existing bank rules within 150 ms; needs one bank, a month of shadow
   traffic, a data agreement and analyst hours.
2. Costs from measurements: ~320 MB per instance and 24 ms p95 (measured); add a
   load test for throughput per core; label estimates.
3. Measure the fast-path share (known payees, small amounts) and what it misses.
4. A public HTTPS host plus Docker/PostgreSQL [V4].

### 3. Communication and Q&A (10)
A timed 6-minute script rehearsed three times, one architecture diagram, a
prepared FAQ with honest "we don't know" answers, one launch command and URL.

### 4. Live user journey (25), now 3-4
1. Show the attack arriving: a simulated scam chat or call, then the payment request.
2. The whole path live: alert, user action, Priya or operator review, report
   draft, final ledger state.
3. The judge varies amount, payee, chat text and screen share and sees it change.
4. Merchant extension: a fake "payment success" screenshot never credits the
   merchant; only a committed transfer does.

### 5. Adversarial robustness (20), now 4-5
1. Live: `split_10` (unseen in training) with its measured drop, a fresh unreported
   mule, reworded text (text alone never holds).
2. Show one real miss live and the experiment that would fix it.
3. New attacks with measured drops: slow drip over weeks, warmed-up mules, spaced
   probing, abuse of the trusted-contact approval.
4. A "how to beat Maya" slide: cold start, low-and-slow, unreported mules, fixes,
   monthly retest.

### 6. Responsible AI and handling mistakes (10), now 3-4
1. Time an honest first-time payment flagged by mistake: nudge cleared in one tap;
   hold cleared by operator or Priya; auto-release at 60 min on a labelled demo clock.
2. The alert says why: SHAP reasons, each labelled model or rule.
3. Privacy running (see S1.4.3); consent toggles.
4. Fairness: miss-rate gap by age, language and phone against the 3-point gate.
5. "Pay anyway" after a hold needs deliberate confirmation and is logged.

## Order (points per hour)
1. Cuts table, FAQ, timed script, failure slide (about 4 h).
2. Held-out type, 3 seeds, honest lookalikes, kit script (about 1 day).
3. Operator page, Priya device, privacy panel, timed FP path (1-2 days; less via V4).
4. Event-history features and a real ledger (about 2 days).
5. Fairness slices, stage bar, soft cap (about 1 day).
6. Pilot blueprint with a load test and a live HTTPS host (about half a day).
