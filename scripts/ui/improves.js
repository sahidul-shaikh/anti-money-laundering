/* Discipline panels for AI improves AI.

   Harness runs a real before/after on Bedrock. Tokenomics measures the system
   prefix with two real calls. Failure mining and Value engineering read the
   recorded evaluation. */

(function () {
  const F = window.Factory;
  if (!F) return;
  const { api, esc, register } = F;

  const num = (n) => Number(n || 0).toLocaleString();
  const pct = (n) => (Number(n || 0) * 100).toFixed(1) + "%";
  const sgn = (n, d = 2) => (n > 0 ? "+" : "") + Number(n).toFixed(d);
  const kpi = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
  const card = (title, sub, body, id) =>
    `<div class="card"${id ? ` id="${id}"` : ""}><h3>${title}</h3>`
    + (sub ? `<p class="sub">${sub}</p>` : "") + body + "</div>";

  let IMP = null;
  const improve = async () => {
    if (!IMP) IMP = await (await api("/api/improve/recorded")).json();
    return IMP;
  };

  const status = (host, text, tone) => {
    const el = host.querySelector(".status");
    if (el) { el.textContent = text; el.className = "status sm " + (tone || "quiet"); }
  };

  const OUTCOME = {
    approved: "good", refused: "crit", insufficient_evidence: "warn",
  };

  const decisionRow = (dec) => `<span class="chip ${OUTCOME[dec.outcome] || ""}">${
    esc(dec.outcome.replace(/_/g, " "))}</span>`;

  /* ================================================================= 01 */

  /* ================================================================= 02 */

  /* ================================================================= 03 */

  register("improves", "tokenomics", async (host) => {
    host.innerHTML = `
      <div class="card">
        <h3>The instructions every call carries</h3>
        <p class="sub">The agent is sent the same block of instructions on every alert.
        It used to spell out the detection thresholds for all six scenarios, whether or
        not the alert was about them. They now come from the rulebook instead, one rule
        at a time.</p>
        <div class="bar"><button class="btn primary" id="tk-go">measure it</button></div>
        <div class="status sm quiet"></div>
        <div id="tk-out"></div>
      </div>`;

    host.querySelector("#tk-go").addEventListener("click", async () => {
      status(host, "asking the model to count it...", "warn");
      const r = await (await api("/api/improve/tokens", { method: "POST" })).json();
      if (r.error) { status(host, r.error, "crit"); return; }
      host.querySelector("#tk-out").innerHTML = `
        <div class="kpis">
          ${kpi(num(r.tokens_before), "words of instruction, before")}
          ${kpi(num(r.tokens_now), "after")}
          ${kpi(num(Math.abs(r.saved_over_corpus)), "saved across 70 alerts")}
        </div>
        <p class="sub" style="margin-top:12px">Counted by the model itself, not estimated.</p>`;
      status(host, "measured", "good");
    });
  });
  /* ================================================================= 04 */

  register("improves", "value-engineering", async (host) => {
    const d = await improve();
    const c = d.contract || {};
    const r = d.realisation || {};

    const met = (ok) => ok
      ? '<span class="chip good">met</span>' : '<span class="chip crit">not met</span>';

    host.innerHTML =
      card("The contract, declared before the build",
        "No contract, no build. The factory's first stage cannot pass without one, and "
        + "every number on this page is measured against it.",
        `<div class="kpis">
           ${kpi("GBP " + (c.baseline_gbp || 0).toFixed(2), "manual baseline")}
           ${kpi("GBP " + (c.target_gbp || 0).toFixed(2), "target per alert")}
           ${kpi(pct(c.target_recall), "recall floor, binding")}
           ${kpi(pct(c.target_accuracy), "accuracy floor")}</div>
         <p class="sub mono sm" style="margin-top:12px">approver: ${esc(c.approver || "")}</p>`)
      + card("How far off, in standard errors",
        "Sigma is computed from the measurement's own standard error, so it is arithmetic "
        + "rather than an adjective. A gap inside one sigma is not progress and is not a "
        + "regression - it is a number you cannot act on yet.",
        `<table><thead><tr><th>Metric</th><th>Observed</th><th>Target</th>
           <th>Std error</th><th>Sigma</th><th>Band</th><th>Action</th></tr></thead><tbody>
           ${(d.detections || []).map((x) => `<tr>
             <td>${esc(x.metric)}</td>
             <td class="num">${typeof x.observed === "number" ? x.observed.toFixed(4) : "-"}</td>
             <td class="num">${typeof x.target === "number" ? x.target.toFixed(4) : "-"}</td>
             <td class="num">${x.stderr.toFixed(4)}</td>
             <td class="num ${x.sigma >= 2 ? "crit" : x.sigma >= 1 ? "warn" : ""}">${
               x.sigma.toFixed(2)}</td>
             <td class="num">${x.band}</td>
             <td class="sm">${esc(x.action)}</td></tr>`).join("")}
         </tbody></table>
         ${(d.detections || []).filter((x) => x.note).map((x) =>
           `<p class="sub" style="margin-top:8px"><b>${esc(x.metric)}</b> &mdash; ${esc(x.note)}</p>`).join("")}`)
      + card("Where the approved change actually landed",
        "One proposal cleared the gate. This is what it bought, and what it did not.",
        `<table><thead><tr><th>Target</th><th>Achieved</th><th></th></tr></thead><tbody>
           <tr><td>Cost per outcome &le; GBP ${(r.cost_target_gbp || 0).toFixed(2)}</td>
             <td class="num">GBP ${(r.cost_per_outcome_gbp || 0).toFixed(2)}</td>
             <td>${met(r.cost_target_met)}</td></tr>
           <tr><td>Recall &ge; ${pct(r.recall_target)}</td>
             <td class="num">${pct(r.recall)}</td>
             <td>${met(r.recall_target_met)}</td></tr>
           <tr><td>Accuracy &ge; ${pct(r.accuracy_target)}</td>
             <td class="num">${pct(r.accuracy)}</td>
             <td>${met(r.accuracy_target_met)}</td></tr>
         </tbody></table>
         <div class="kpis" style="margin-top:16px">
           ${kpi(pct(r.cost_gap_closed), "of the cost gap closed")}
           ${kpi((d.approved_changes || []).length, "changes approved")}
           ${kpi((d.decisions || []).filter((x) => !x.approved).length, "held back")}</div>
         <p class="sub" style="margin-top:14px">The contract is <b class="crit">not met</b>.
         That is the honest end of this pillar: one cycle closed ${pct(r.cost_gap_closed)}
         of the cost gap, the recall floor is still short, and the console says so rather
         than finding a number that looks better.</p>`);
  });
})();
