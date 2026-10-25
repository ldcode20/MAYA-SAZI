const $ = (s) => document.querySelector(s),
  esc = (s) =>
    String(s ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
const money = (p) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(
    p / 100,
  );
let data = null,
  selected = null,
  stream = null,
  stages = [],
  busy = false,
  refreshTimer = null;
// Until this device has paired (or found an existing grant), a refused
// /v1/observe just means "not connected yet", not an error to show.
let paired = false;
let followLatest = true,
  activePayment = null,
  activeEvaluation = null;
async function api(url, body) {
  const r = await fetch(url, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(10000),
  });
  const d = await r.json();
  if (!r.ok) throw new Error(d.detail || "Unable to connect");
  return d;
}
function fail(e) {
  $("#error").hidden = false;
  $("#error").textContent = e.message;
}
async function pairWith(code) {
  await api("/v1/observe/pair", { code });
  paired = true;
  sessionStorage.removeItem("maya-v4-event-cursor");
  stages = [];
  selected = null;
  await connect();
}
$("#pair-form").onsubmit = async (e) => {
  e.preventDefault();
  try {
    await pairWith($("#code").value.trim());
  } catch (e) {
    fail(e);
  }
};
async function refresh() {
  if (busy) return;
  busy = true;
  try {
    data = await api("/v1/observe");
    paired = true;
    $("#pairing").hidden = true;
    $("#dashboard").hidden = false;
    $("#error").hidden = true;
    if (data.role === "recipient") {
      renderRecipient();
      return;
    }
    if (data.role === "contact") {
      renderContact();
      return;
    }
    const editor = $("#scenario-editor");
    if (editor) {
      editor.hidden = false;
      const select = $("#scenario-recipient");
      if (select && !select.options.length) {
        select.innerHTML = data.accounts.filter((a) => a.id > 0).map((a) =>
          `<option value="${a.id}">${esc(a.name)} · #${a.id}</option>`).join("");
      }
    }
    selected =
      (followLatest
        ? data.reviews[0]
        : data.reviews.find((r) => r.id === selected?.id)) ||
      data.reviews[0] ||
      null;
    render();
  } catch (e) {
    stream?.close();
    if (!paired) {
      $("#connection").textContent = "Not connected";
      return;
    }
    $("#connection").textContent = "Access unavailable";
    fail(e);
  } finally {
    busy = false;
  }
}
async function connect() {
  while (busy) await new Promise((r) => setTimeout(r, 20));
  await refresh();
  if (!data) return;
  if (data.role === "judge") {
    stream?.close();
    const cursor = sessionStorage.getItem("maya-v4-event-cursor") || "0";
    stream = new EventSource(
      "/v1/observe/events?after=" + encodeURIComponent(cursor),
    );
    stream.onopen = () => {
      $("#connection").textContent = "Live";
    };
    stream.onmessage = (e) => {
      const event = JSON.parse(e.data);
      if (event.stage === "world_changed") {
        // The customer started a new practice world; follow it from scratch.
        stages = [];
        selected = null;
        followLatest = true;
        activePayment = activeEvaluation = null;
        const select = $("#scenario-recipient");
        if (select) select.replaceChildren();
        clearTimeout(refreshTimer);
        refreshTimer = setTimeout(refresh, 80);
        return;
      }
      sessionStorage.setItem("maya-v4-event-cursor", e.lastEventId);
      stages.push(event);
      if (stages.length > 300) stages.shift();
      if (event.stage === "intent_validated") {
        followLatest = true;
        activePayment = event.payment_id;
        activeEvaluation = null;
      }
      if (followLatest && event.evaluation_id) {
        activePayment = event.payment_id;
        activeEvaluation = event.evaluation_id;
      }
      renderStages();
      if (
        [
          "review_saved",
          "settled",
          "cancelled",
          "intent_validated",
          "review_failed",
        ].includes(event.stage)
      ) {
        clearTimeout(refreshTimer);
        refreshTimer = setTimeout(refresh, 80);
      }
    };
    stream.onerror = () => {
      $("#connection").textContent = "Reconnecting…";
    };
  } else {
    $("#connection").textContent = data.role === "contact" ? "Connected as trusted contact" : "Connected as recipient";
    refreshTimer = setInterval(refresh, 2000);
  }
}
$("#scenario-form").onsubmit = async (event) => {
  event.preventDefault();
  const amount = Number($("#scenario-amount").value);
  if (!Number.isFinite(amount) || amount <= 0) return fail(new Error("Enter a positive amount."));
  try {
    const result = await api("/v1/observe/scenario", {
      recipient: Number($("#scenario-recipient").value),
      amount_paise: Math.round(amount * 100),
      context: $("#scenario-context").value,
    });
    $("#scenario-status").textContent = `Scenario ${result.payment_id.slice(0, 8)} sent. The customer must review it on their device.`;
    followLatest = true;
  } catch (e) {
    fail(e);
  }
};
const labels = {
  intent_validated: "Input and validation",
  history_loaded: "Available evidence",
  features_computed: "Feature computation",
  model_scored: "Model inference",
  uncertainty_computed: "Uncertainty",
  policy_evaluated: "Policy",
  review_saved: "Durable review",
  settled: "Confirmed transfer",
  review_failed: "Review failed",
};
function renderStages() {
  if (data?.role !== "judge") return;
  const current = followLatest
    ? activeEvaluation || selected?.id
    : selected?.id;
  const payment = followLatest
    ? activePayment || selected?.payment_id
    : selected?.payment_id;
  const applicable = stages.filter((e) =>
    e.evaluation_id ? e.evaluation_id === current : e.payment_id === payment,
  );
  const defaults = [
    "intent_validated",
    "history_loaded",
    "features_computed",
    "model_scored",
    "uncertainty_computed",
    "policy_evaluated",
    "review_saved",
  ];
  $("#stages").innerHTML = defaults
    .map((k) => {
      const ev = applicable.findLast((e) => e.stage === k);
      const key = {
        history_loaded: "history_loaded",
        features_computed: "features_computed",
        model_scored: "model_scored",
        uncertainty_computed: "uncertainty_computed",
        policy_evaluated: "policy_evaluated",
      }[k];
      const historical = selected?.id === current;
      const measured =
        ev?.duration_ms ?? (historical ? selected?.timings_ms[key] : undefined);
      const done =
        !!ev || (historical && !!selected && k !== "intent_validated");
      return `<div class="stage ${done ? "done" : ""}"><span>${esc(labels[k])}</span><span class="number">${measured !== undefined ? esc(measured.toFixed(2)) + " ms" : done ? "Committed" : "Waiting"}</span></div>`;
    })
    .join("");
  const terminal = applicable.findLast(
    (e) => e.stage === "review_failed" || e.stage === "settled",
  );
  if (terminal)
    $("#stages").insertAdjacentHTML(
      "beforeend",
      `<div class="stage ${terminal.stage === "review_failed" ? "failed" : "done"}"><strong>${esc(labels[terminal.stage])}</strong><span>${esc(terminal.status || "Committed")}</span></div>`,
    );
}
function render() {
  if (!selected) {
    $("#summary").innerHTML = "<h2>A customer can now create a payment.</h2>";
    $("#evidence").textContent = "No review yet.";
    renderStages();
    return;
  }
  $("#headline").textContent = "One payment. Every decision visible.";
  const r = selected,
    a = r.decision.action;
  const transfer = data.transfers.find((t) => t.review_id === r.id);
  const name = data.accounts?.find((x) => x.id === r.recipient)?.name || `Recipient ${r.recipient}`;
  const word =
    ({ release: "Released", nudge: "Warned", hold: "Held" }[a] || a) +
    (transfer && a !== "release" ? ", then sent" : "");
  $("#summary").className = `card ${a}`;
  // The transfer ID is the one the customer's receipt and the recipient show;
  // the review ID identifies this check. Both are listed so they can be matched.
  $("#summary").innerHTML =
    `<span class="pill ${a}">${esc(word)}</span><p class="amount">${esc(money(r.amount_paise))}</p><p class="payee">${esc(name)}</p><p>${transfer ? "<strong>Sent. The ledger recorded this transfer.</strong>" : "Checked. No money has moved for this check."}</p><dl class="ids">${transfer ? `<dt>Transfer ID</dt><dd>${esc(transfer.id)}</dd>` : ""}<dt>Check ID</dt><dd>${esc(r.id)}</dd><dt>Revision</dt><dd>${esc(r.revision)}</dd></dl>`;
  $("#evidence").innerHTML =
    `<ul class="reasons">${r.decision.reasons.map((s) => `<li>${esc(s)}</li>`).join("")}</ul><p>Prediction set: <strong>${esc(r.model.uncertainty)}</strong></p><p>Model score: <strong>${Number(r.model.score).toFixed(4)}</strong></p><p class="muted">${esc(r.graph_convention)}</p><p>Groups: ${Object.entries(
      r.groups,
    )
      .map(([k, v]) => esc(k) + ": " + (v ? "present" : "absent"))
      .join(" · ")}</p>`;
  $("#history").innerHTML = data.reviews
    .map(
      (x) =>
        `<button class="quiet" data-review="${esc(x.id)}">${esc(money(x.amount_paise))}, ${esc(x.decision.action)} <span class="muted">${esc(x.id.slice(0, 6))}</span></button>`,
    )
    .join("");
  document.querySelectorAll("[data-review]").forEach(
    (b) =>
      (b.onclick = () => {
        followLatest = false;
        selected = data.reviews.find((x) => x.id === b.dataset.review);
        render();
      }),
  );
  $("#model").innerHTML = Object.entries(r.versions)
    .map(
      ([k, v]) =>
        `<p><strong>${esc(k)}</strong><br><small>${esc(v)}</small></p>`,
    )
    .join("");
  $("#features").innerHTML =
    `<table class="feature-table"><thead><tr><th>Feature</th><th>Value</th><th>SHAP, log-odds</th></tr></thead><tbody>${Object.entries(
      r.features,
    )
      .map(([k, v]) => {
        const c = r.model.contributions?.find((c) => c.feature === k);
        return `<tr><td>${esc(k)}</td><td>${v === null ? "Missing" : Number(v).toFixed(4)}</td><td>${c ? Number(c.value).toFixed(4) : "Unavailable"}</td></tr>`;
      })
      .join("")}</tbody></table>`;
  renderStages();
  renderGraph();
}
function renderRecipient() {
  const main = $("#dashboard");
  main.innerHTML = `<span class="pill sandbox">Practice money</span><h1>${esc(data.recipient)}</h1><p class="muted">Balance</p><p class="amount">${esc(money(data.balance_paise))}</p><h2>Money received</h2><p class="muted">Only payments the ledger has recorded appear here. A screenshot or a "payment successful" message cannot add one.</p>${data.transfers.length ? data.transfers.map((t) => `<section class="card"><span class="pill release">Received</span><h2>${esc(money(t.amount_paise))}</h2><dl class="ids"><dt>Transfer ID</dt><dd>${esc(t.id)}</dd></dl></section>`).join("") : "<p>Nothing received yet. This updates on its own.</p>"}`;
}
function renderContact() {
  $("#pairing").hidden = true;
  $("#dashboard").hidden = false;
  $("#scenario-editor").hidden = true;
  $("#headline").textContent = "Trusted-contact requests";
  $("#summary").innerHTML = `<span class="pill sandbox">Practice money</span><h2>Advice only</h2><p>Your answer is shown to the person paying. It cannot approve or release a payment.</p>`;
  $("#evidence").textContent = "Only a payment hold and masked payment details are shown here.";
  $("#stages").replaceChildren();
  $("#history").innerHTML = data.alerts.length ? data.alerts.map((a) =>
    `<section class="card"><p>${esc(a.message || "A payment needs a second opinion.")}</p><p class="number">${esc(a.payment_id || "")}</p>${a.response ? `<strong>Response recorded: ${esc(a.response)}</strong>` : `<div class="row"><button data-contact="support" data-payment="${esc(a.payment_id)}">Looks okay</button><button class="quiet" data-contact="concern" data-payment="${esc(a.payment_id)}">I’m concerned</button></div>`}</section>`).join("") : "<p>No request yet.</p>";
  $("#model").textContent = "Your response is advice only; the payer retains control.";
  $("#history").querySelectorAll("button[data-contact]").forEach((button) => {
    button.onclick = async () => {
      try {
        await api("/v1/observe/contact-response", {
          payment_id: button.dataset.payment,
          response: button.dataset.contact,
        });
        await refresh();
      } catch (e) { fail(e); }
    };
  });
}
function renderGraph() {
  const svg = $("#graph");
  svg.replaceChildren();
  const edges = selected.graph || [],
    nodes = [...new Set(edges.flatMap((e) => [e.source, e.target]))].slice(
      0,
      14,
    ),
    ns = "http://www.w3.org/2000/svg";
  const positions = new Map(
    nodes.map((n, i) => [
      n,
      {
        x: 300 + 220 * Math.cos((2 * Math.PI * i) / nodes.length),
        y: 110 + 80 * Math.sin((2 * Math.PI * i) / nodes.length),
      },
    ]),
  );
  for (const e of edges) {
    const a = positions.get(e.source),
      b = positions.get(e.target);
    if (!a || !b) continue;
    const line = document.createElementNS(ns, "line");
    for (const [k, v] of Object.entries({ x1: a.x, y1: a.y, x2: b.x, y2: b.y }))
      line.setAttribute(k, v);
    svg.append(line);
  }
  for (const [n, p] of positions) {
    const circle = document.createElementNS(ns, "circle");
    circle.setAttribute("cx", p.x);
    circle.setAttribute("cy", p.y);
    circle.setAttribute("r", "17");
    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", p.x);
    text.setAttribute("y", p.y + 4);
    text.textContent = String(n);
    svg.append(circle, text);
  }
}
$("#refresh").onclick = refresh;
$("#export").onclick = () => {
  if (!selected) return;
  const u = URL.createObjectURL(
    new Blob([JSON.stringify(selected, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = u;
  a.download = `maya-review-${selected.id}.json`;
  a.click();
  URL.revokeObjectURL(u);
};
window.addEventListener("pagehide", () => {
  stream?.close();
  clearInterval(refreshTimer);
});
const evidenceLink = document.createElement("a");
evidenceLink.href = "/demo/benchmarks.html";
evidenceLink.textContent = "Evidence";
document.querySelector(".header").append(evidenceLink);
// Opened from the customer's QR: exchange the one-time code for this device's
// own HttpOnly grant, then drop it from the address bar and history.
const qrCode = new URLSearchParams(location.search).get("code");
if (qrCode) {
  history.replaceState(null, "", location.pathname);
  pairWith(qrCode.trim()).catch(fail);
} else {
  connect().catch(() => {});
}
