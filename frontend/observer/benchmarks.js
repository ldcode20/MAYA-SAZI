const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const pct = (n) => (100 * n).toFixed(1) + "%";
(async () => {
  const r = await fetch("/v1/observe/benchmarks");
  if (!r.ok)
    throw Error("Pair this browser with the customer as a judge first.");
  const b = await r.json();
  let html = "";
  const p = b.reports.paysim;
  if (p) {
    html += `<section class="benchmark"><span class="pill">PUBLIC SYNTHETIC MOBILE-MONEY DATA</span><h2>PaySim · ${Number(p.actual_rows).toLocaleString()} rows</h2><p>Held-out test: ${p.splits.test.rows.toLocaleString()} transactions, ${p.splits.test.positives} fraud labels.</p><table class="feature-table"><thead><tr><th>Model</th><th>PR-AUC</th><th>Recall</th><th>Benign intervention</th></tr></thead><tbody>${Object.entries(
      p.candidates,
    )
      .map(
        ([n, m]) =>
          `<tr><td>${esc(n)}</td><td>${m.pr_auc.toFixed(3)}</td><td>${pct(m.recall)}</td><td>${pct(m.benign_intervention_rate)}</td></tr>`,
      )
      .join(
        "",
      )}</tbody></table><p class="muted">Chronological prefix; complete hours. No UPI coercion labels. MLP remains a challenger.</p></section>`;
  }
  const l = b.reports.load;
  if (l) {
    html += `<section class="benchmark"><h2>Complete review-service load</h2><p>${esc(l.workload)}</p><table class="feature-table"><thead><tr><th>Offered/s</th><th>Success/s</th><th>Success/core</th><th>p95</th><th>Errors</th></tr></thead><tbody>${l.runs.map((x) => `<tr><td>${x.offered_rps}</td><td>${x.achieved_success_rps.toFixed(1)}</td><td>${x.success_rps_per_logical_cpu === undefined ? "Not measured" : x.success_rps_per_logical_cpu.toFixed(1)}</td><td>${x.p95_ms.toFixed(1)} ms</td><td>${Object.values(x.errors).reduce((a, b) => a + b, 0)}</td></tr>`).join("")}</tbody></table><p class="muted">${l.seconds_per_level}s per level on one local machine. Overload rejections are included. Not national-UPI capacity.</p></section>`;
  }
  const v = b.reports.validation;
  if (v) {
    html += `<section class="benchmark"><h2>Authored event-level kit</h2><table class="feature-table"><thead><tr><th>Case</th><th>Count</th><th>Release</th><th>Warn</th><th>Hold</th></tr></thead><tbody>${Object.entries(
      v.groups,
    )
      .map(
        ([n, g]) =>
          `<tr><td>${esc(n)}</td><td>${g.n}</td><td>${g.release}</td><td>${g.nudge}</td><td>${g.hold}</td></tr>`,
      )
      .join(
        "",
      )}</tbody></table><p class="muted">Small authored scenarios; not an unbiased fraud accuracy estimate. A fresh recipient cannot be held without independent evidence.</p></section>`;
  }
  const kit = b.reports.kit;
  if (kit) {
    html += `<section class="benchmark"><h2>Live event-history spot-check · ${kit.summary.pass_count}/${kit.summary.total} invariants</h2><p>Run seed ${kit.run_seed} · ${esc(kit.provenance)}</p><table class="feature-table"><thead><tr><th>Case</th><th>Expected</th><th>Actual</th><th>Risk score</th><th>Result</th></tr></thead><tbody>${kit.cases.map((x) => `<tr><td>${esc(x.case)}</td><td>${esc(x.expected)}</td><td>${esc(x.actual)}</td><td>${Number(x.score).toFixed(4)}</td><td>${x.pass_invariant ? "Pass" : "Miss"}</td></tr>`).join("")}</tbody></table><p class="muted">Authored synthetic scenarios, not a population accuracy estimate. ${kit.limits.map(esc).join(" ")}</p></section>`;
  }
  const f = b.reports.fairness;
  if (f) {
    html += `<section class="benchmark"><h2>Synthetic cohort review</h2>${Object.entries(f.reports).map(([dimension, report]) => `<h3>${esc(dimension)} · ${esc(report.gate)}${report.scam_miss_rate_gap === null ? "" : ` · ${pct(report.scam_miss_rate_gap)} gap`}</h3><table class="feature-table"><thead><tr><th>Group</th><th>Scams</th><th>Missed</th><th>Miss rate</th><th>Honest intervention</th></tr></thead><tbody>${Object.entries(report.groups).map(([group, row]) => `<tr><td>${esc(group)}</td><td>${row.scam_count}</td><td>${row.scam_misses}</td><td>${row.scam_miss_rate === null ? "—" : pct(row.scam_miss_rate)}</td><td>${row.honest_intervention_rate === null ? "—" : pct(row.honest_intervention_rate)}</td></tr>`).join("")}</tbody></table>`).join("")}<p class="muted">Synthetic groups only; this is not demographic evidence or a fairness certification.</p></section>`;
  }
  const look = b.reports.lookalikes;
  if (look) {
    html += `<section class="benchmark"><h2>Honest lookalike controls · later-day test</h2><table class="feature-table"><thead><tr><th>Scenario</th><th>Support</th><th>Held</th><th>Warned</th><th>Intervention</th><th>Scope</th></tr></thead><tbody>${Object.entries(look.results).map(([name, row]) => `<tr><td>${esc(name)}</td><td>${row.support}</td><td>${row.held}</td><td>${row.nudged}</td><td>${row.any_intervention_rate === null ? "—" : pct(row.any_intervention_rate)}</td><td>${name === "genuine_refund_credit" ? "Incoming credit · stress only" : "Outgoing synthetic control"}</td></tr>`).join("")}</tbody></table><p class="muted">${esc(look.provenance)} The refund row is an incoming credit and is out of scope for outgoing pre-authorization; its intervention rate is a counterfactual feature stress check, not a live refund decision.</p></section>`;
  }
  const held = b.reports["heldout-types"];
  if (held) {
    html += `<section class="benchmark"><h2>Unseen scam-type retraining</h2><table class="feature-table"><thead><tr><th>Type omitted from training</th><th>Test transactions</th><th>Campaigns</th><th>Interrupted</th><th>Released</th></tr></thead><tbody>${held.results.map((x) => `<tr><td>${esc(x.held_out_type)}</td><td>${x.test_transactions}</td><td>${x.test_campaigns}</td><td>${pct(x.detected_before_release)}</td><td>${x.released_count}</td></tr>`).join("")}</tbody></table><p class="muted">Synthetic holdout under the documented split procedure.</p></section>`;
  }
  const seeds = b.reports["seed-sweep"];
  if (seeds) {
    html += `<section class="benchmark"><h2>Three-world seed range</h2><table class="feature-table"><thead><tr><th>Seed</th><th>Test rows</th><th>Scams</th><th>PR-AUC</th><th>AUROC</th><th>Recall @ 1% FPR</th></tr></thead><tbody>${seeds.seeds.map((x) => `<tr><td>${x.seed}</td><td>${x.test_rows ?? "—"}</td><td>${x.test_positive_count ?? "—"}</td><td>${Number(x.test_auprc).toFixed(3)}</td><td>${Number(x.test_auroc).toFixed(3)}</td><td>${pct(x.recall_at_1pct_fpr)}</td></tr>`).join("")}</tbody></table><p class="muted">${esc(seeds.interpretation)}</p></section>`;
  }
  const fast = b.reports["fast-path"];
  if (fast) {
    html += `<section class="benchmark"><h2>Candidate fast path · measurement only</h2><p>Eligible: ${pct(fast.eligible_share)} of the ${fast.transactions.toLocaleString()} test transactions. Scams that would bypass scoring: ${fast.eligible_scam_count}/${fast.total_scam_count} (${fast.share_of_scam_transactions_bypassed === null ? "—" : pct(fast.share_of_scam_transactions_bypassed)}).</p><p class="muted">Fast-path bypass remains disabled. ${fast.limitations.map(esc).join(" ")}</p></section>`;
  }
  const cold = b.reports["cold-start"];
  if (cold) {
    const probe = cold.zero_history_probe;
    const actions = (items) => Object.entries(items || {}).map(([action, count]) => `${esc(action)} ${count}`).join(" · ") || "—";
    html += `<section class="benchmark"><h2>Cold-start uncertainty</h2><table class="feature-table"><thead><tr><th>Account tenure</th><th>Honest rows</th><th>Uncertain</th><th>Nudge</th><th>Scam misses</th></tr></thead><tbody>${Object.entries(cold.buckets).map(([name,row]) => `<tr><td>${esc(name)}</td><td>${row.honest}</td><td>${row.honest_unsure_share === null ? "—" : pct(row.honest_unsure_share)}</td><td>${row.honest_nudge_share === null ? "—" : pct(row.honest_nudge_share)}</td><td>${row.scam_miss_count}</td></tr>`).join("")}</tbody></table>${probe?.status === "measured" ? `<h3>Live zero-history probe · ${probe.worlds} generated worlds</h3><p>No prior endpoint payments in ${probe.endpoint_history_events.zero_history_worlds}/${probe.worlds} worlds. Neutral: ${actions(probe.policy_actions.neutral)}. Consented refund-claim context: ${actions(probe.policy_actions.refund_claim)}.</p><p class="muted">${esc(probe.definition)} ${probe.limits.map(esc).join(" ")}</p>` : ""}<p class="muted">${cold.limits.map(esc).join(" ")}</p></section>`;
  }
  document.querySelector("#results").innerHTML =
    html || "<p>No recorded reports are available in this deployment.</p>";
})().catch((e) => {
  document.querySelector("#results").textContent = e.message;
});
