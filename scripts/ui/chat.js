/* AI runs AI - Routing.

   Paste an alert and the real policy runs: cheapest serving model first, its
   answer checked against the alert's own transaction list, and only an answer
   that cannot show its working is sent up to the stronger model. There is no
   model picker, because picking by hand is the thing this replaces. */

(function () {
  const F = window.Factory;
  if (!F) return;
  const { api, esc } = F;

  const SAMPLES = [
    ["alert_11368.txt", "11368 - real alert, individual"],
    ["alert_11366.txt", "11366 - real alert, structured withdrawals"],
    ["alert_11391.txt", "11391 - real alert, business"],
    ["alert_S90001.txt", "S90001 - a large receipt, retained"],
  ];

  const TEXTAREA = "width:100%;background:#080510;color:#cfc6da;"
    + "border:1px solid var(--line);border-radius:9px;padding:12px;"
    + "font-family:var(--mono);font-size:11.5px;resize:vertical";

  const say = (host, text, tone) => {
    const el = host.querySelector(".status");
    if (el) { el.textContent = text; el.className = "status sm " + (tone || "quiet"); }
  };

  /** A link that reveals a pane of text. */
  function reveal(host, label, text) {
    const id = "r" + Math.random().toString(36).slice(2, 9);
    setTimeout(() => {
      const btn = host.querySelector(`[data-rv="${id}"]`);
      const pane = host.querySelector("#" + id);
      if (!btn || !pane) return;
      pane.textContent = text;
      btn.addEventListener("click", () => {
        const open = pane.style.display !== "none";
        pane.style.display = open ? "none" : "block";
        btn.textContent = (open ? "" : "hide ") + label;
      });
    }, 0);
    return `<button class="link" data-rv="${id}">${esc(label)}</button>
      <pre class="feed" id="${id}" style="display:none;margin-top:8px"></pre>`;
  }

  const sampleSelect = (id) => `<select id="${id}">`
    + SAMPLES.map(([f, l]) => `<option value="${f}">${esc(l)}</option>`).join("")
    + "</select>";

  async function loadSample(api_, name) {
    const r = await (await api_("/api/demo/" + name)).json();
    return r.body || "";
  }

  /* ------------------------------------------------------------------ */

  F.register("runs", "routing", async (host) => {
    host.innerHTML = `
      <div class="card">
        <h3>Give the agent an alert</h3>
        <div class="bar">
          ${sampleSelect("ro-sample")}
          <button class="btn primary" id="ro-go">send it</button>
        </div>
        <textarea id="ro-text" spellcheck="false" style="${TEXTAREA};height:150px"
          placeholder="Paste an alert"></textarea>
        <div class="status sm quiet" style="margin-top:8px"></div>
      </div>
      <div id="ro-out"></div>`;

    const box = host.querySelector("#ro-text");
    const sample = host.querySelector("#ro-sample");
    const fill = async () => { box.value = await loadSample(api, sample.value); };
    sample.addEventListener("change", fill);
    await fill();

    host.querySelector("#ro-go").addEventListener("click", async () => {
      const out = host.querySelector("#ro-out");
      out.innerHTML = "";
      say(host, "trying the cheapest model first...", "warn");

      const r = await (await api("/api/chat/route", {
        method: "POST", body: JSON.stringify({ text: box.value }),
      })).json();
      if (r.error) { say(host, r.error, "crit"); return; }

      const head = `<div class="card">
        <h3>What the policy did</h3>
        <div class="bar">
          ${r.chain.map((t, i) => `<span class="chip ${
            i < r.attempts.length ? "acn" : ""}">${i + 1}. ${esc(t)}</span>`).join("")}
          ${r.rule ? `<span class="chip">rule ${esc(r.rule.rule_id)} &middot; page ${
            r.rule.page}</span>` : ""}
        </div>
        ${reveal(host, "show the system prompt", r.attempts[0].system)}
        ${reveal(host, "show what was sent", r.attempts[0].prompt)}
      </div>`;

      const attempt = (a) => `<div class="card" style="border-color:${
          a.trusted ? "var(--good)" : "var(--crit)"}">
        <h3>${esc(a.tier)} model
          <span class="chip ${a.trusted ? "good" : "crit"}">${
            a.trusted ? "TRUSTED" : "NOT TRUSTED"}</span></h3>
        <div class="bar">
          <span class="chip">said ${esc(a.disposition || "no answer")}</span>
          <span class="chip">${a.cited.length} citations</span>
        </div>
        <p class="${a.trusted ? "good" : "crit"} sm">${esc(a.reason)}</p>
        ${a.verified.length ? `<div class="bar">${a.verified.map((v) =>
          `<span class="chip ${v.in_alert ? "good" : "crit"} mono">${
            v.in_alert ? "&#10003;" : "&#10007;"} ${esc(v.ref)}</span>`)
          .slice(0, 14).join("")}</div>` : ""}
        ${a.narrative ? `<p class="sub" style="margin-top:8px">${esc(a.narrative)}</p>` : ""}
        ${reveal(host, "show the raw answer", a.response || a.error || "")}
      </div>`;

      const escalation = r.escalated ? `<div class="card"
          style="border-color:var(--acn-purple)">
        <h3>Escalating <span class="chip acn">${esc(r.chain[0])} &rarr; ${
          esc(r.chain[1])}</span></h3>
        <p class="sub">The policy does not accept an answer it cannot verify, so the
        alert goes to the stronger model. Nothing about the alert changed.</p>
      </div>` : "";

      const scored = r.correct !== null && r.correct !== undefined;
      const final = `<div class="verdict ${scored && r.correct ? "ok" : "bad"}">
        <div class="vrow"><span class="k">Final answer</span>
          <span class="big">${esc(r.disposition || "none")}</span>
          ${scored ? `<span class="chip ${r.correct ? "good" : "crit"}">${
            r.correct ? "CORRECT" : "WRONG"}</span>` : ""}</div>
        <div class="vrow"><span class="k">Answered by</span>
          <span>${esc(r.final_tier)}${r.escalated ? ", after escalation" : " first time"}</span></div>
        ${scored ? `<div class="vrow"><span class="k">Correct answer</span>
          <span class="mono">${esc(r.expected)}</span>
          <span class="quiet sm">held by the harness, never in the prompt</span></div>` : ""}
      </div>`;

      // Built once: reveal() binds on a timer, so rewriting innerHTML after it
      // has been called would leave those links pointing at removed panes.
      out.innerHTML = head + attempt(r.attempts[0]) + escalation
        + (r.escalated ? attempt(r.attempts[1]) : "") + final;

      say(host, r.escalated
        ? "the cheap model could not show its working, so the policy escalated"
        : "the cheap model answered with evidence, so nothing was escalated",
        scored && r.correct ? "good" : "warn");
    });
  });

  window.FactoryChat = { reveal, sampleSelect, loadSample, TEXTAREA, say };
})();
