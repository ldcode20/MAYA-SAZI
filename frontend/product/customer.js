const $ = (s) => document.querySelector(s);
const esc = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let lang = localStorage.getItem("maya-v4-language") || "en",
  world = null,
  payment = null,
  review = null,
  receipt = null,
  camera = null,
  incomingScenario = null;
const words = {
  en: {
    home: "Home",
    activity: "Activity",
    settings: "Settings",
    title: "A little clarity\nbefore you pay.",
    scan: "Scan a QR",
    check: "Check a message",
    sandbox: "Try a payment",
    demo: "Practice money",
    practice: "Practise a payment",
    choose: "Pick a situation to practise with. The money here is pretend.",
    situation: "Situation",
    change: "Change situation",
    makePayment: "Make a payment",
    balance: "Practice balance",
    preset_everyday: "Everyday payments",
    preset_everyday_desc: "Family, rent and the corner shop. Nothing unusual in your history.",
    preset_investment: "After a “stock tips” group",
    preset_investment_desc: "A trader account paid you a small “profit”. Dozens of strangers also pay it, and it is linked to a reported account.",
    preset_probes: "After tiny test payments",
    preset_probes_desc: "The same trader, plus ₹1, ₹2 and ₹5 test payments sent to it minutes ago.",
    preset_refund: "A refund that asks you to pay",
    preset_refund_desc: "A stranger’s small credit and a message saying “approve to receive your refund”.",
    heldUntil: "Held until",
    practiceTime: "practice time",
    skip: "Skip ahead 1 hour of practice time",
    clockNote: "Practice time only. A real hold lasts a real hour.",
    holdOver: "The hold has ended",
    holdOverNote: "The hour has passed. Check the details once more before sending.",
    sendAnyway: "Send dummy payment anyway",
    analystWait: "This is over ₹1 lakh, so a bank analyst must approve this check before it can be sent.",
    checkAgain: "Check again",
    to: "To",
    when: "When",
    transfer: "Transfer ID",
    scanToConnect: (where) => `Scan this with the other device, or open ${where} there and type the code.`,
    expires: "The code works once and expires in 5 minutes.",
    start: "Start a fresh session",
    review: "Review payment",
    recipient: "Recipient",
    amount: "Amount",
    context: "Optional payment context",
    none: "No shared context",
    refund: "Message promises a refund",
    withdrawal: "Payment unlocks a withdrawal",
    rent: "Rent payment",
    merchant_refund: "Refund to a customer",
    pay: "Check payment",
    continue: "Send dummy payment",
    confirm: "I understand. Send dummy payment",
    cancel: "Cancel payment",
    edit: "Edit details",
    back: "Back",
    sent: "Dummy payment completed",
    checking: "Checking your payment",
    held: "Payment held",
    warning: "Check before you continue",
    ready: "Ready to continue",
    pair: "Connect judge device",
    pairRecipient: "Connect recipient device",
    pairContact: "Connect trusted contact",
    scenarioReady: "A judge sent a scenario. Review it before sending a dummy payment.",
    openScenario: "Review scenario",
    whatLeft: "Exact request body sent from this device",
    revoke: "Revoke device access",
    new: "New payment",
    help: "Create evidence draft",
    private: "This message stays on this device.",
    paste: "Message or UPI link",
    analyse: "Check intent",
    limited: "Limited information",
    retry: "Try again",
    delete: "Delete this session",
    consent: "Data & access",
    empty: "No completed payments yet.",
    camera: "Open camera",
    upload: "Upload QR image",
    cameraUnsupported:
      "QR reading is unavailable in this browser. Paste the UPI link instead.",
    copied: "Pairing code copied",
    checkTitle: "Understand this payment",
    invalid: "Use a valid upi://pay link with recipient and a positive amount.",
    noRaw: "Only derived intent is sent. Raw messages are not retained.",
    withdrawalRisk: "A payment cannot verify a promised investment withdrawal.",
    mismatch: "This sends money. The message describes incoming money.",
    limitedReason:
      "Bank history and verified recipient information are unavailable for this check.",
    error: "Unable to complete this action. No payment has been confirmed.",
    save: "Download draft",
    draft: "Evidence draft · Not submitted",
    status: "Status",
    refresh: "Refresh",
    restricted: "Payment checks do not prove the recipient is legitimate.",
  },
  hi: {
    home: "होम",
    activity: "गतिविधि",
    settings: "सेटिंग",
    title: "भुगतान से पहले\nस्पष्ट जानकारी।",
    scan: "QR स्कैन करें",
    check: "संदेश जाँचें",
    sandbox: "भुगतान आज़माएँ",
    demo: "अभ्यास के पैसे",
    practice: "भुगतान का अभ्यास करें",
    choose: "अभ्यास के लिए एक स्थिति चुनें। यहाँ के पैसे नकली हैं।",
    situation: "स्थिति",
    change: "स्थिति बदलें",
    makePayment: "भुगतान करें",
    balance: "अभ्यास का बैलेंस",
    preset_everyday: "रोज़ के भुगतान",
    preset_everyday_desc: "परिवार, किराया और पास की दुकान। आपके इतिहास में कुछ असामान्य नहीं।",
    preset_investment: "“स्टॉक टिप्स” ग्रुप के बाद",
    preset_investment_desc: "एक ट्रेडर खाते ने आपको थोड़ा “मुनाफ़ा” भेजा। कई अजनबी भी उसे पैसे भेजते हैं, और वह एक रिपोर्ट किए गए खाते से जुड़ा है।",
    preset_probes: "छोटे परीक्षण भुगतानों के बाद",
    preset_probes_desc: "वही ट्रेडर, और कुछ मिनट पहले उसे भेजे गए ₹1, ₹2 और ₹5 के परीक्षण भुगतान।",
    preset_refund: "रिफंड जिसके लिए भुगतान माँगा जाए",
    preset_refund_desc: "किसी अजनबी का छोटा क्रेडिट और संदेश: “रिफंड पाने के लिए मंज़ूरी दें”।",
    heldUntil: "तब तक रोका गया",
    practiceTime: "अभ्यास का समय",
    skip: "अभ्यास का समय 1 घंटा आगे करें",
    clockNote: "यह केवल अभ्यास का समय है। असली रोक पूरे एक घंटे की होती है।",
    holdOver: "रोक समाप्त हुई",
    holdOverNote: "एक घंटा बीत गया। भेजने से पहले विवरण एक बार फिर जाँचें।",
    sendAnyway: "फिर भी नकली भुगतान भेजें",
    analystWait: "यह ₹1 लाख से अधिक है, इसलिए भेजने से पहले बैंक विश्लेषक की मंज़ूरी चाहिए।",
    checkAgain: "फिर जाँचें",
    to: "किसे",
    when: "कब",
    transfer: "ट्रांसफ़र ID",
    scanToConnect: (where) => `दूसरे डिवाइस से इसे स्कैन करें, या वहाँ ${where} खोलकर कोड लिखें।`,
    expires: "कोड एक बार चलता है और 5 मिनट में समाप्त हो जाता है।",
    start: "नया सत्र शुरू करें",
    review: "भुगतान की जाँच",
    recipient: "प्राप्तकर्ता",
    amount: "राशि",
    context: "भुगतान का संदर्भ",
    none: "कोई संदर्भ नहीं",
    refund: "संदेश में रिफंड का वादा",
    withdrawal: "निकासी खोलने के लिए भुगतान",
    rent: "किराया",
    merchant_refund: "ग्राहक को रिफंड",
    pay: "भुगतान जाँचें",
    continue: "नकली भुगतान भेजें",
    confirm: "समझ गया। नकली भुगतान भेजें",
    cancel: "भुगतान रद्द करें",
    edit: "विवरण बदलें",
    back: "वापस",
    sent: "नकली भुगतान पूरा हुआ",
    checking: "भुगतान की जाँच जारी है",
    held: "भुगतान रोका गया",
    warning: "आगे बढ़ने से पहले जाँचें",
    ready: "आगे बढ़ सकते हैं",
    pair: "जज का डिवाइस जोड़ें",
    pairRecipient: "प्राप्तकर्ता का डिवाइस जोड़ें",
    pairContact: "भरोसेमंद संपर्क जोड़ें",
    scenarioReady: "जज ने एक उदाहरण भेजा है। नकली भुगतान से पहले इसकी जाँच करें।",
    openScenario: "उदाहरण जाँचें",
    whatLeft: "इस डिवाइस से भेजा गया अनुरोध",
    revoke: "डिवाइस की पहुँच हटाएँ",
    new: "नया भुगतान",
    help: "साक्ष्य का मसौदा बनाएँ",
    private: "यह संदेश इसी डिवाइस पर रहता है।",
    paste: "संदेश या UPI लिंक",
    analyse: "इरादा जाँचें",
    limited: "सीमित जानकारी",
    retry: "फिर कोशिश करें",
    delete: "यह सत्र हटाएँ",
    consent: "डेटा और पहुँच",
    empty: "अभी कोई भुगतान पूरा नहीं हुआ।",
    camera: "कैमरा खोलें",
    upload: "QR चित्र अपलोड करें",
    cameraUnsupported:
      "इस ब्राउज़र में QR पढ़ना उपलब्ध नहीं है। UPI लिंक पेस्ट करें।",
    copied: "कोड कॉपी हो गया",
    checkTitle: "इस भुगतान को समझें",
    invalid: "प्राप्तकर्ता और सही राशि वाला upi://pay लिंक डालें।",
    noRaw: "केवल निकाला गया इरादा भेजा जाता है। संदेश सहेजा नहीं जाता।",
    withdrawalRisk: "भुगतान से निवेश की निकासी की पुष्टि नहीं होती।",
    mismatch: "इससे पैसे भेजे जाएँगे। संदेश में पैसे मिलने की बात है।",
    limitedReason:
      "बैंक का इतिहास और प्राप्तकर्ता की सत्यापित जानकारी उपलब्ध नहीं है।",
    error: "यह काम पूरा नहीं हुआ। भुगतान की पुष्टि नहीं हुई है।",
    save: "मसौदा डाउनलोड करें",
    draft: "साक्ष्य का मसौदा · भेजा नहीं गया",
    status: "स्थिति",
    refresh: "ताज़ा करें",
    restricted: "जाँच से प्राप्तकर्ता के सही होने का प्रमाण नहीं मिलता।",
  },
};
const t = (k) => words[lang][k] || words.en[k] || k;
const money = (p) =>
  new Intl.NumberFormat(lang === "hi" ? "hi-IN" : "en-IN", {
    style: "currency",
    currency: "INR",
  }).format(p / 100);
const button = (id, label, cls = "full") =>
  `<button id="${id}" class="${cls}" type="button">${esc(t(label))}</button>`;
function announce(s) {
  $("#announcement").textContent = s;
}
function show(html) {
  stopCamera();
  $("#main").innerHTML = html;
  $("#main").focus({ preventScroll: true });
  document.documentElement.lang = lang;
}
function error(e) {
  announce(e.message);
  const box = document.createElement("p");
  box.className = "error";
  box.setAttribute("role", "alert");
  box.textContent = e.message || t("error");
  $("#main").prepend(box);
}
async function api(path, body, method) {
  const r = await fetch(path, {
    method: method || (body === undefined ? "GET" : "POST"),
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": crypto.randomUUID(),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal: AbortSignal.timeout(20000),
  });
  const data = await r.json();
  if (!r.ok) {
    const e = new Error(data.detail || t("error"));
    e.status = r.status;
    throw e;
  }
  return data;
}
const base = () => `/v1/sandbox/worlds/${world.id}`;
async function reloadWorld() {
  if (world) world = await api(base());
}
// Practice situations map to the server's world presets. Presets change the
// generated history only; every decision still comes from the live review.
const PRESETS = ["everyday", "investment", "probes", "refund"];
function choices() {
  return `<p class="muted">${esc(t("choose"))}</p><div class="choices">${PRESETS.map(
    (p) =>
      `<button type="button" class="choice" data-preset="${p}"><strong>${esc(t("preset_" + p))}</strong><span>${esc(t("preset_" + p + "_desc"))}</span></button>`,
  ).join("")}</div>`;
}
async function startWorld(preset) {
  const previous = world?.id;
  world = await api("/v1/sandbox/worlds", { preset });
  payment = null;
  review = null;
  incomingScenario = null;
  localStorage.setItem("maya-v4-world", world.id);
  // Paired judge and recipient screens follow the customer to the new world.
  if (previous)
    await api(base() + "/observers/carry", { previous }).catch(() => {});
}
function home(choosing = false) {
  const practice =
    world && !choosing
      ? `<div class="card soft"><div class="situation"><p class="eyebrow">${esc(t("situation"))}</p><button id="change" class="link" type="button">${esc(t("change"))}</button></div><h3>${esc(t("preset_" + (world.preset || "everyday")))}</h3><p class="muted">${esc(t("balance"))}</p><p class="balance">${esc(money(world.accounts[0].balance_paise))}</p>${button("sandbox", "makePayment")}</div>`
      : choices();
  show(
    `<section class="hero"><h1>${esc(t("title")).replace("\n", "<br>")}</h1></section><div id="judge-scenario-callout"></div><div class="tiles"><button id="scan" class="tile"><span class="icon" aria-hidden="true">▦</span>${esc(t("scan"))}</button><button id="check" class="tile"><span class="icon" aria-hidden="true">↗</span>${esc(t("check"))}</button></div><section class="section"><div class="row"><h2>${esc(t("practice"))}</h2><span class="pill sandbox">${esc(t("demo"))}</span></div>${practice}</section>`,
  );
  renderIncomingScenario();
  $("#scan").onclick = () => companion(true);
  $("#check").onclick = () => companion(false);
  if ($("#sandbox")) $("#sandbox").onclick = edit;
  if ($("#change")) $("#change").onclick = () => home(true);
  document.querySelectorAll("[data-preset]").forEach((b) => {
    b.onclick = async () => {
      b.disabled = true;
      try {
        await startWorld(b.dataset.preset);
        edit();
      } catch (e) {
        b.disabled = false;
        error(e);
      }
    };
  });
}
function renderIncomingScenario() {
  const box = $("#judge-scenario-callout");
  if (!box) return;
  if (!incomingScenario) { box.replaceChildren(); return; }
  const recipient = world?.accounts.find((a) => a.id === incomingScenario.recipient);
  box.innerHTML = `<section class="card"><p>${esc(t("scenarioReady"))}</p><p><strong>${esc(money(incomingScenario.amount_paise))}</strong> · ${esc(recipient?.name || "Synthetic recipient")}</p><button id="open-judge-scenario">${esc(t("openScenario"))}</button></section>`;
  $("#open-judge-scenario").onclick = () => { payment = incomingScenario; edit(); };
}
async function pollJudgeScenario() {
  if (!world) return;
  try {
    const result = await api(base() + "/judge-scenarios");
    const next = result.scenarios.at(-1) || null;
    const changed = next?.id !== incomingScenario?.id;
    incomingScenario = next;
    if (changed) renderIncomingScenario();
  } catch (_) {
    // Deleted or expired sessions are surfaced during the next customer action.
  }
}
function edit() {
  receipt = null;
  show(
    `<button id="back" class="quiet">← ${esc(t("back"))}</button><section class="section"><span class="pill sandbox">${esc(t("demo"))}</span><h1>${esc(t("review"))}</h1><form id="payment-form"><label for="recipient">${esc(t("recipient"))}</label><select id="recipient">${world.accounts
      .filter((a) => a.id > 0 && (a.id <= 11 || a.id === payment?.recipient))
      .map(
        (a) =>
          `<option value="${a.id}" ${a.id === (payment?.recipient ?? world.default_recipient) ? "selected" : ""}>${esc(a.name)} · ${esc(a.vpa)}</option>`,
      )
      .join(
        "",
      )}</select><label for="amount">${esc(t("amount"))} · INR</label><input id="amount" class="money" type="text" inputmode="decimal" value="${((payment?.amount_paise ?? world.default_amount_paise) / 100).toFixed(2)}" required autocomplete="off"><label for="context">${esc(t("context"))}</label><select id="context">${["none", "refund", "withdrawal", "rent", "merchant_refund"].map((k) => `<option value="${k}" ${k === (payment?.context || "none") ? "selected" : ""}>${esc(t(k))}</option>`).join("")}</select><div class="section"><button class="full" type="submit">${esc(t("pay"))}</button></div></form><div class="row">${button("pair", "pair", "quiet")}${button("recipient-pair", "pairRecipient", "quiet")}${button("contact-pair", "pairContact", "quiet")}</div></section>`,
  );
  $("#back").onclick = home;
  $("#pair").onclick = () => pair("judge");
  $("#recipient-pair").onclick = () => pair("recipient");
  $("#contact-pair").onclick = () => pair("contact");
  $("#payment-form").onsubmit = async (e) => {
    e.preventDefault();
    const value = $("#amount").value.trim();
    if (!/^\d{1,7}(\.\d{1,2})?$/.test(value) || Number(value) <= 0)
      return error(new Error(t("invalid")));
    const body = {
      recipient: Number($("#recipient").value),
      amount_paise: Math.round(Number(value) * 100),
      context: $("#context").value,
    };
    const old = payment;
    show(
      `<div class="empty"><div class="spinner"></div><h2>${esc(t("checking"))}</h2></div>`,
    );
    try {
      payment = await api(
        base() +
          "/intents" +
          (old && old.state === "pending" ? "/" + old.id : ""),
        body,
        old && old.state === "pending" ? "PUT" : "POST",
      );
      review = await api(base() + `/intents/${payment.id}/review`, {});
      await showOutcome();
    } catch (e) {
      payment = old;
      edit();
      error(e);
    }
  };
}
// The hold lives on the server's payment record; read it rather than infer it.
async function showOutcome() {
  await reloadWorld();
  outcome();
}
const clockTime = (seconds) =>
  new Date(seconds * 1000).toLocaleTimeString(lang === "hi" ? "hi-IN" : "en-IN", {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "Asia/Kolkata",
  });
function outcome() {
  const action = review.decision.action;
  const label =
    action === "hold" ? "held" : action === "nudge" ? "warning" : "ready";
  const reasons = review.decision.reasons.slice(0, 2);
  const localReason = (s) =>
    lang === "hi"
      ? s.includes("message says")
        ? t("mismatch")
        : s.includes("withdrawal")
          ? t("withdrawalRisk")
          : s.includes("reported")
            ? "पिछले दिन का भुगतान मार्ग रिपोर्ट किए खाते से जुड़ा है।"
            : s.includes("history")
              ? "यह भुगतान उपलब्ध इतिहास से अलग है।"
              : s.includes("uncertain")
                ? "मॉडल निश्चित नहीं है। आगे बढ़ने से पहले प्राप्तकर्ता और राशि जाँचें।"
                : s
      : s;
  const record = world?.intents?.find((i) => i.id === payment.id);
  const held =
    !!record && record.state === "pending" && record.hold_revision === record.revision;
  const holdOver = held && world.now >= record.hold_until;
  const analystNeeded =
    held &&
    record.analyst_required &&
    !(record.analyst_approved && record.analyst_review === review.id);
  const tone = held ? "hold" : action;
  const verdict = held ? (holdOver ? "holdOver" : "held") : label;
  const mark = tone === "release" ? "✓" : tone === "hold" ? "‖" : "!";
  let timer = "";
  if (held && !holdOver)
    timer = `<div class="hold-timer"><p><strong>${esc(t("heldUntil"))} ${esc(clockTime(record.hold_until))}</strong> <span class="muted">(${esc(t("practiceTime"))})</span></p><p class="muted">${esc(t("clockNote"))}</p></div>`;
  else if (holdOver)
    timer = `<div class="hold-timer"><p>${esc(analystNeeded ? t("analystWait") : t("holdOverNote"))}</p></div>`;
  let actions;
  if (!held)
    actions = button("send", action === "nudge" ? "confirm" : "continue");
  else if (!holdOver)
    actions = button("skip", "skip", "quiet") + button("draft", "help", "quiet");
  else if (analystNeeded)
    actions = button("again", "checkAgain") + button("draft", "help", "quiet");
  else actions = button("send", "sendAnyway");
  show(
    `<span class="pill sandbox">${esc(t("demo"))}</span><article class="slip ${tone}" aria-labelledby="verdict"><div class="slip-band" aria-hidden="true"></div><div class="slip-body"><h1 id="verdict" class="verdict"><span class="mark" aria-hidden="true">${mark}</span>${esc(t(verdict))}</h1><p class="amount">${esc(money(payment.amount_paise))}</p><p class="payee">${esc(world.accounts.find((a) => a.id === payment.recipient)?.name)}</p>${reasons.length ? `<ul class="reasons">${reasons.map((s) => `<li>${esc(localReason(s))}</li>`).join("")}</ul>` : ""}${timer}</div></article><div class="stack">${actions}${button("edit", "edit", "quiet")}${button("cancel", "cancel", "danger")}</div>`,
  );
  announce(t(verdict));
  if ($("#skip"))
    $("#skip").onclick = async () => {
      $("#skip").disabled = true;
      try {
        await api(base() + "/clock", { seconds: 3600 });
        // Moving the clock changes the evidence window, so the old check is stale.
        review = await api(base() + `/intents/${payment.id}/review`, {});
        await showOutcome();
      } catch (e) {
        $("#skip").disabled = false;
        error(e);
      }
    };
  if ($("#again"))
    $("#again").onclick = async () => {
      try {
        await showOutcome();
      } catch (e) {
        error(e);
      }
    };
  if ($("#send"))
    $("#send").onclick = async () => {
      const b = $("#send");
      b.disabled = true;
      try {
        receipt = await api(base() + `/intents/${payment.id}/execute`, {
          review_id: review.id,
          confirmed: action === "nudge" || held,
          authorization: "DEMO",
        });
        payment = null;
        await reloadWorld();
        showReceipt();
      } catch (e) {
        b.disabled = false;
        error(e);
      }
    };
  if ($("#draft")) $("#draft").onclick = draft;
  $("#edit").onclick = edit;
  $("#cancel").onclick = async () => {
    try {
      await api(base() + `/intents/${payment.id}/cancel`, {});
      payment = null;
      home();
    } catch (e) {
      error(e);
    }
  };
}
function showReceipt() {
  const to = world.accounts.find((a) => a.id === receipt.recipient);
  show(
    `<span class="pill sandbox">${esc(t("demo"))}</span><article class="slip release" aria-labelledby="verdict"><div class="slip-band" aria-hidden="true"></div><div class="slip-body"><h1 id="verdict" class="verdict"><span class="mark" aria-hidden="true">✓</span>${esc(t("sent"))}</h1><p class="amount">${esc(money(receipt.amount_paise))}</p><p class="payee">${esc(to?.name)}</p><dl><dt>${esc(t("to"))}</dt><dd>${esc(to?.vpa)}</dd><dt>${esc(t("when"))}</dt><dd>${esc(clockTime(receipt.timestamp))} (${esc(t("practiceTime"))})</dd><dt>${esc(t("status"))}</dt><dd>${esc(receipt.state)}</dd><dt>${esc(t("transfer"))}</dt><dd class="number">${esc(receipt.id)}</dd></dl></div></article>${button("new", "new")}`,
  );
  announce(t("sent"));
  $("#new").onclick = edit;
}
async function pair(role) {
  try {
    if (role === "contact") {
      const accepted = window.confirm(lang === "hi"
        ? "भरोसेमंद संपर्क को भुगतान-रोक की सूचना भेजें? वे केवल सलाह दे सकते हैं, भुगतान मंजूर नहीं कर सकते।"
        : "Let a trusted contact see payment-hold alerts? They can advise you, but cannot approve or release a payment.");
      if (!accepted) return;
      await api(base() + "/contact-consent", { enabled: true });
    }
    const grant = await api(base() + "/pair", {
      role,
      account: Number($("#recipient")?.value || world.default_recipient),
    });
    // The QR opens the viewer page on the other device with the one-time code;
    // that page exchanges it for its own HttpOnly grant and strips it from the URL.
    const link = `${location.origin}${grant.url}?code=${encodeURIComponent(grant.code)}`;
    $("#pair-qr").innerHTML = qrSvg(link);
    $("#pair-qr").hidden = !$("#pair-qr").innerHTML;
    $("#pair-code").textContent = grant.code;
    $("#pair-help").textContent = `${words[lang].scanToConnect(location.host + grant.url)} ${t("expires")}`;
    $("#pair-dialog").showModal();
    $("#copy-code").onclick = () =>
      navigator.clipboard
        .writeText(grant.code)
        .then(() => announce(t("copied")))
        .catch(error);
  } catch (e) {
    error(e);
  }
}
$("#close-dialog").onclick = () => $("#pair-dialog").close();
// qrcode.js (MIT, vendored in /static) is a classic script that sets window.qrcode.
function qrSvg(text) {
  if (typeof window.qrcode !== "function") return "";
  const qr = window.qrcode(0, "M");
  qr.addData(text);
  qr.make();
  return qr.createSvgTag({ cellSize: 4, margin: 0, scalable: true });
}
async function draft() {
  try {
    const d = await api(base() + "/cases", { review_id: review.id });
    const blob = new Blob([JSON.stringify(d, null, 2)], {
      type: "application/json",
    });
    const u = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = u;
    a.download = `maya-case-${d.id}.json`;
    a.click();
    URL.revokeObjectURL(u);
    announce(t("draft"));
  } catch (e) {
    error(e);
  }
}
async function activity() {
  try {
    await reloadWorld();
    show(
      `<h1>${esc(t("activity"))}</h1>${world?.transfers.length ? world.transfers.map((r) => `<div class="activity-item row"><div><p>${esc(world.accounts.find((a) => a.id === r.recipient)?.name)}</p><small>${esc(r.state)} · ${esc(r.id.slice(0, 8))}</small></div><strong>${esc(money(r.amount_paise))}</strong></div>`).join("") : `<p class="empty">${esc(t("empty"))}</p>`}${button("refresh", "refresh", "quiet")}`,
    );
    $("#refresh").onclick = activity;
  } catch (e) {
    error(e);
  }
}
function settings() {
  show(
    `<h1>${esc(t("settings"))}</h1><div class="card"><h2>${esc(t("consent"))}</h2><p>${esc(t("noRaw"))}</p><p class="muted">${esc(t("restricted"))}</p></div><div class="stack">${button("revoke", "revoke", "quiet")}${button("delete", "delete", "danger")}${button("fresh", "start", "quiet")}</div>`,
  );
  $("#revoke").onclick = async () => {
    try {
      if (world) {
        await api(base() + "/contact-consent", { enabled: false });
        await api(base() + "/revoke", {});
      }
      announce(t("revoke"));
    } catch (e) {
      error(e);
    }
  };
  $("#delete").onclick = async () => {
    try {
      if (world) await api(base(), undefined, "DELETE");
      world = null;
      payment = null;
      localStorage.removeItem("maya-v4-world");
      home();
    } catch (e) {
      error(e);
    }
  };
  $("#fresh").onclick = () => {
    document
      .querySelectorAll("[data-nav]")
      .forEach((x) =>
        x.dataset.nav === "home"
          ? x.setAttribute("aria-current", "page")
          : x.removeAttribute("aria-current"),
      );
    home(true);
  };
}
function stopCamera() {
  camera?.getTracks().forEach((t) => t.stop());
  camera = null;
}
function parseUPI(s) {
  const u = new URL(s);
  if (
    u.protocol !== "upi:" ||
    u.hostname !== "pay" ||
    (u.pathname && u.pathname !== "/")
  )
    throw new Error(t("invalid"));
  for (const k of ["pa", "am", "pn", "cu"])
    if (u.searchParams.getAll(k).length > 1) throw new Error(t("invalid"));
  const pa = u.searchParams.get("pa") || "",
    am = u.searchParams.get("am") || "";
  if (
    !/^[\w.\-]{1,128}@[\w.\-]{1,64}$/.test(pa) ||
    !/^\d{1,7}(\.\d{1,2})?$/.test(am) ||
    Number(am) <= 0 ||
    !["INR", null].includes(u.searchParams.get("cu"))
  )
    throw new Error(t("invalid"));
  return { recipient: pa, amount: Math.round(Number(am) * 100) };
}
// Reads a pasted message in this browser only and returns three labels; the text
// itself is never sent. It is a small, deliberately narrow rule set (English,
// some Hindi): anything it does not recognise stays "unknown", and the check
// then says it has limited information rather than guessing.
const RECEIVE_AFTER_ACTION =
  /\b(approve|accept|authori[sz]e|confirm|enter (your )?(upi )?pin|scan)\b.{0,60}\b(to|for|and) (receive|get|claim|collect)\b/;
const ACTION_AFTER_RECEIVE =
  /\b(receive|get|claim|collect)\b.{0,40}\b(refund|cashback|prize|reward|money|amount|payment)\b.{0,60}\b(approve|accept|enter (your )?(upi )?pin|scan)\b/;
const WITHDRAW_FUNDS =
  /\b(withdraw(al)?|unlock|release|redeem)\b.{0,50}\b(profits?|funds?|investment|earnings|returns|amount|money|balance)\b/;
const FEE_BEFORE_WITHDRAW =
  /\b(fee|tax|gst|charges?|commission|deposit)\b.{0,50}\b(withdraw(al)?|unlock|release|profits?|earnings|returns)\b/;
const WITHDRAW_BEFORE_FEE =
  /\b(profits?|earnings|returns|withdraw(al)?)\b.{0,50}\b(fee|tax|gst|charges?|commission)\b/;
const HI_RECEIVE = /(पाने|प्राप्त करने|लेने) के लिए/;
const HI_WITHDRAW = /(निकासी|मुनाफ़े|मुनाफे|प्रॉफिट).{0,30}(शुल्क|फीस|टैक्स|भुगतान)/;
function deriveIntent(text) {
  const s = text.toLowerCase().replace(/\s+/g, " ");
  const incoming =
    RECEIVE_AFTER_ACTION.test(s) || ACTION_AFTER_RECEIVE.test(s) || HI_RECEIVE.test(text);
  const withdrawal =
    WITHDRAW_FUNDS.test(s) ||
    FEE_BEFORE_WITHDRAW.test(s) ||
    WITHDRAW_BEFORE_FEE.test(s) ||
    HI_WITHDRAW.test(text);
  const refund = /\brefund\b|रिफंड/.test(s);
  return {
    direction: incoming ? "incoming" : "unknown",
    purpose: withdrawal ? "withdrawal" : incoming && refund ? "refund" : "unknown",
    operation: "transfer",
  };
}
function companion(scan) {
  show(
    `<button id="back" class="quiet">← ${esc(t("back"))}</button><section class="section"><h1>${esc(t("checkTitle"))}</h1><label for="message">${esc(t("paste"))}</label><textarea id="message" maxlength="2000"></textarea><p class="muted">${esc(t("private"))}</p><div class="stack">${button("analyse", "analyse")}${scan ? button("camera", "camera", "quiet") + `<label for="image">${esc(t("upload"))}</label><input type="file" id="image" accept="image/*"><video id="camera-view" muted playsinline hidden></video>` : ""}</div><details class="section"><summary>${esc(t("whatLeft"))}</summary><pre id="outbound-payload">Nothing sent.</pre></details><div id="check-result" class="section" aria-live="polite"></div></section>`,
  );
  $("#back").onclick = home;
  $("#analyse").onclick = async () => {
    const raw = $("#message").value.trim();
    if (!raw) return;
    let parsed = null;
    if (raw.toLowerCase().startsWith("upi:")) {
      try {
        parsed = parseUPI(raw);
      } catch (e) {
        return error(e);
      }
    }
    const body = deriveIntent(raw);
    try {
      $("#outbound-payload").textContent = JSON.stringify(body, null, 2);
      const r = await api("/v1/checks", body);
      const reason =
        r.action === "nudge"
          ? body.direction === "incoming"
            ? t("mismatch")
            : t("withdrawalRisk")
          : t("limitedReason");
      $("#check-result").innerHTML =
        `<div class="card"><span class="pill">${esc(t("limited"))}</span>${parsed ? `<h2>${esc(money(parsed.amount))}</h2><p>${esc(parsed.recipient)}</p>` : ""}<p>${esc(reason)}</p><small>${esc(t("restricted"))}</small></div>`;
      await api("/v1/checks/" + r.id, undefined, "DELETE");
    } catch (e) {
      error(e);
    }
  };
  if (scan) {
    $("#image").onchange = async (e) => {
      try {
        if (!("BarcodeDetector" in window))
          throw new Error(t("cameraUnsupported"));
        const bitmap = await createImageBitmap(e.target.files[0]);
        let codes;
        try {
          codes = await new BarcodeDetector({ formats: ["qr_code"] }).detect(
            bitmap,
          );
        } finally {
          bitmap.close();
        }
        if (!codes.length) throw new Error(t("invalid"));
        $("#message").value = codes[0].rawValue;
        $("#analyse").click();
      } catch (e) {
        error(e);
      }
    };
    $("#camera").onclick = async () => {
      try {
        if (!("BarcodeDetector" in window))
          throw new Error(t("cameraUnsupported"));
        camera = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        const v = $("#camera-view");
        v.srcObject = camera;
        v.hidden = false;
        await v.play();
        const detector = new BarcodeDetector({ formats: ["qr_code"] });
        const tick = async () => {
          if (!camera || !$("#camera-view")) return;
          try {
            const codes = await detector.detect(v);
            if (codes.length) {
              $("#message").value = codes[0].rawValue;
              stopCamera();
              v.hidden = true;
              $("#analyse").click();
              return;
            }
          } catch (e) {
            stopCamera();
            return error(e);
          }
          requestAnimationFrame(tick);
        };
        tick();
      } catch (e) {
        stopCamera();
        error(e);
      }
    };
  }
}
document.querySelectorAll("[data-nav]").forEach(
  (b) =>
    (b.onclick = () => {
      document
        .querySelectorAll("[data-nav]")
        .forEach((x) => x.removeAttribute("aria-current"));
      b.setAttribute("aria-current", "page");
      ({ home, activity, settings })[b.dataset.nav]();
    }),
);
$("#language").onclick = () => {
  lang = lang === "en" ? "hi" : "en";
  localStorage.setItem("maya-v4-language", lang);
  $("#language").textContent = lang === "en" ? "हिंदी" : "English";
  document
    .querySelectorAll("[data-nav]")
    .forEach((b) => (b.textContent = t(b.dataset.nav)));
  home();
};
window.addEventListener("pagehide", stopCamera);
if ("serviceWorker" in navigator)
  navigator.serviceWorker.register("/app/sw.js").catch(() => {});
(async () => {
  const wid = localStorage.getItem("maya-v4-world");
  if (wid) {
    try {
      world = await api("/v1/sandbox/worlds/" + wid);
    } catch (e) {
      if (e.status === 404 || e.status === 409)
        localStorage.removeItem("maya-v4-world");
    }
  }
  home();
  await pollJudgeScenario();
  window.setInterval(pollJudgeScenario, 2500);
})();
