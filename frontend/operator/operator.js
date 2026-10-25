const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const money = (paise) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(paise / 100);
let operatorKey = "";
async function request(path) {
  const response = await fetch(path, { headers: { "X-Operator-Key": operatorKey }, cache: "no-store" });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "Operator access failed");
  return body;
}
async function decide(c, decision) {
  const response = await fetch("/v1/operator/decision", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Operator-Key": operatorKey },
    body: JSON.stringify({ payment_id: c.payment_id, review_id: c.review_id, revision: c.revision, decision }),
  });
  const body = await response.json();
  if (!response.ok) throw new Error(body.detail || "This payment changed. Refresh the queue.");
  return body;
}
async function load() {
  try {
    const [queue, audit] = await Promise.all([request("/v1/operator/queue"), request("/v1/operator/audit")]);
    $("#message").hidden = true;
    $("#cases").innerHTML = queue.cases.length ? queue.cases.map((c, index) =>
      `<article class="card"><span class="pill hold">Held, revision ${c.revision}</span><h2>${esc(money(c.amount_paise))}</h2><p>Recipient ${esc(c.recipient)}, payment ${esc(c.payment_id.slice(0, 8))}</p><ul class="reasons">${c.reasons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul><p class="muted">Model ${esc(c.model_version.slice(0, 12))}, policy ${esc(c.policy_version)}</p><div class="row"><button data-decision="approve" data-index="${index}">Approve review</button><button class="quiet" data-decision="reject" data-index="${index}">Reject and cancel</button></div></article>`).join("") : "<p>No current analyst holds.</p>";
    document.querySelectorAll("[data-decision]").forEach((button) => button.onclick = async () => {
      const c = queue.cases[Number(button.dataset.index)];
      try { await decide(c, button.dataset.decision); await load(); }
      catch (e) { showError(e); await load(); }
    });
    $("#audit").innerHTML = audit.events.length ? audit.events.map((e) =>
      `<article class="activity-item"><strong>${esc(e.stage)}</strong><p>${esc(e.action || e.response || e.status || "Recorded")}</p><small>${esc(e.recorded_at || "")} · ${esc(e.payment_id || "")}${e.model_version ? ` · model ${esc(e.model_version)}` : ""}</small>${e.reasons?.length ? `<ul>${e.reasons.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>` : ""}</article>`).join("") : "<p>No decision events recorded.</p>";
  } catch (e) { showError(e); }
}
function showError(e) { $("#message").hidden = false; $("#message").textContent = e.message; }
$("#login-form").onsubmit = async (event) => {
  event.preventDefault();
  operatorKey = $("#operator-key").value;
  try {
    await request("/v1/operator/queue");
    $("#login").hidden = true;
    $("#queue-view").hidden = false;
    await load();
  } catch (e) { operatorKey = ""; showError(e); }
};
$("#refresh").onclick = load;
window.addEventListener("pagehide", () => { operatorKey = ""; });
