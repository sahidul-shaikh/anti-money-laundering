/* AI runs AI - the Observability and FinOps panels. Both read the recorded
   baseline; no model is called, and the panels say so. Routing and
   Reliability, which call Bedrock live, live in panels.js. */

(function () {
  const F = window.Factory;
  if (!F) return;
  const { api, esc, register } = F;

  const num = (n) => Number(n || 0).toLocaleString();
  const pct = (n) => (Number(n || 0) * 100).toFixed(1) + "%";
  const kpi = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
  const card = (title, sub, body, id) =>
    `<div class="card"${id ? ` id="${id}"` : ""}><h3>${title}</h3>`
    + (sub ? `<p class="sub">${sub}</p>` : "") + body + "</div>";

  let CATALOGUE = null;
  let RECORDED = null;

  const alerts = async () => {
    if (!CATALOGUE) CATALOGUE = (await (await api("/api/alerts")).json()).alerts;
    return CATALOGUE;
  };
  const recorded = async () => {
    if (!RECORDED) RECORDED = await (await api("/api/runs/recorded")).json();
    return RECORDED;
  };

  /* ================================================================= 03 */

  const LAYERS = [
    ["SYSTEM", "Is the estate up, and how fast?"],
    ["MODEL", "What did it consume, and from which models?"],
    ["AGENT", "Did it show its working?"],
    ["TRANSACTION", "Did it get the right answer?"],
    ["VALUE", "Was it worth doing?"],
  ];

  register("runs", "observability", async (host) => {
    const rec = await recorded();
    const tiers = Object.keys(rec.runs || {});

    const layerTable = (layer) => {
      const keys = [...new Set(tiers.flatMap((t) =>
        Object.keys(rec.runs[t].telemetry[layer] || {})))]
        .filter((k) => typeof rec.runs[tiers[0]].telemetry[layer][k] !== "object");
      return `<table><thead><tr><th>${layer}</th>
        ${tiers.map((t) => `<th>${esc(t)}</th>`).join("")}</tr></thead><tbody>
        ${keys.map((k) => `<tr><td>${esc(k.replace(/_/g, " "))}</td>
          ${tiers.map((t) => {
            const v = rec.runs[t].telemetry[layer][k];
            return `<td class="num">${typeof v === "number"
              ? (v < 1 && v > 0 ? v.toFixed(4) : num(v)) : esc(String(v))}</td>`;
          }).join("")}</tr>`).join("")}
      </tbody></table>`;
    };

    const byScenario = rec.runs[tiers[tiers.length - 1]].telemetry.TRANSACTION.by_scenario || {};

    host.innerHTML =
      card("Five layers, recorded for every run",
        "Uptime tells you the pipe is open. It does not tell you whether the control is "
        + "working, and it is the control a regulator asks about.",
        LAYERS.map(([name, question]) =>
          `<h4 style="margin:18px 0 2px;font-size:12px;letter-spacing:1.2px;color:var(--acn-light)">
             ${name}</h4><p class="sub" style="margin:0 0 4px">${question}</p>
           ${layerTable(name)}`).join(""))
      + card("Accuracy by scenario, which an aggregate would hide",
        "The same agent, the same prompt, the same run - and a 40-point spread between "
        + "scenarios. This is the number that tells you where to work next.",
        `<table><thead><tr><th>Scenario</th><th>Alerts</th><th>Accuracy</th>
           <th style="width:40%"></th></tr></thead><tbody>
           ${Object.entries(byScenario).sort((a, b) => a[1].accuracy - b[1].accuracy)
             .map(([code, s]) => `<tr><td class="mono">${esc(code)}</td>
               <td class="num">${s.n}</td>
               <td class="num ${s.accuracy < 0.7 ? "crit" : s.accuracy < 0.9 ? "warn" : "good"}">
                 ${pct(s.accuracy)}</td>
               <td><div style="height:7px;border-radius:4px;background:${
                 s.accuracy < 0.7 ? "#ff5e5e" : s.accuracy < 0.9 ? "#ffb020" : "#3ddc97"
               };width:${(s.accuracy * 100).toFixed(0)}%"></div></td></tr>`).join("")}
         </tbody></table>`);
  });

  /* ================================================================= 04 */

  register("runs", "finops", async (host) => {
    const rec = await recorded();
    const tiers = Object.keys(rec.runs || {});
    const contract = rec.contract || {};

    host.innerHTML =
      card("Cost per correctly handled alert, not cost per token",
        "Token spend is a rounding error next to the human consequence of a wrong answer. "
        + "The number that governs is model spend plus the handling each disposition "
        + "implies: a review costs about &pound;17, a missed escalation about &pound;102.",
        `<table><thead><tr><th>Tier</th><th>Tokens in</th><th>Tokens out</th>
           <th>Model spend</th><th>$ / alert</th><th>&pound; per outcome</th>
           <th>vs &pound;${contract.baseline_gbp || 17} manual</th></tr></thead><tbody>
           ${tiers.map((t) => {
             const s = rec.runs[t].summary;
             const v = rec.runs[t].telemetry.VALUE;
             const delta = v.saving_per_alert_gbp;
             return `<tr><td><b>${esc(t)}</b></td>
               <td class="num">${num(s.tokens_in)}</td>
               <td class="num">${num(s.tokens_out)}</td>
               <td class="num">$${s.cost_usd.toFixed(4)}</td>
               <td class="num">$${(s.cost_usd / s.outcomes).toFixed(4)}</td>
               <td class="num">${s.cost_per_outcome_gbp.toFixed(2)}</td>
               <td class="num ${delta > 0 ? "good" : "crit"}">
                 ${delta > 0 ? "+" : ""}${delta.toFixed(2)}</td></tr>`;
           }).join("")}
         </tbody></table>
         <p class="sub" style="margin-top:12px">At launch the agent costs
         <b class="crit">more</b> than the analyst it is meant to relieve. That is measured,
         it is on the console, and closing it is what the Improve pillar is for.</p>`)
      + card("Where the money actually goes",
        "The model bill is not where the cost is. These clusters come from the token "
        + "ledger, and two of the four levers were refused on measurement.",
        (rec.spend_clusters || []).length ? `<table><thead><tr><th>Cluster</th>
           <th>Share of model spend</th><th>Lever</th><th>Verdict</th></tr></thead><tbody>
           ${rec.spend_clusters.map((c) => {
             const refused = c.verdict.startsWith("REFUSE");
             return `<tr>
               <td><b>${esc(c.name)}</b><div class="sub sm">${esc(c.basis)}</div></td>
               <td class="num">${c.share_of_spend ? pct(c.share_of_spend) : "-"}</td>
               <td class="sm">${esc(c.lever)}
                 <div class="quiet sm">saves ${esc(c.estimated_saving)}</div></td>
               <td class="sm">${refused
                 ? `<span class="chip crit">refused</span> ${esc(c.verdict.slice(8))}`
                 : esc(c.verdict)}</td></tr>`;
           }).join("")}
         </tbody></table>
         <p class="sub" style="margin-top:12px">Two of the four were refused on
         measurement. The third one matters here: <b>route everything to the cheap
         tier</b> was costed, measured, and refused because accuracy falls 14.3 points.
         The evidence-gated policy in discipline 01 is what that refusal forced -
         escalate only the answers that cannot be verified, and you get better accuracy
         than premium for 85% of its spend.</p>`
          : '<p class="sub">No spend analysis recorded.</p>')
      + card("The contract this is measured against",
        "Declared before the build, not after. No contract, no build.",
        `<div class="kpis">
           ${kpi("&pound;" + (contract.baseline_gbp || 17).toFixed(2), "manual baseline")}
           ${kpi("&pound;" + (contract.target_gbp || 12).toFixed(2), "target per alert")}
           ${kpi(pct(contract.target_recall || 0.9), "recall floor, binding")}
           ${kpi(pct(contract.target_accuracy || 0.85), "accuracy floor")}
           ${kpi(num(rec.system_tokens), "tokens of system prompt")}</div>
         <p class="sub" style="margin-top:14px">Every call carries those
         ${num(rec.system_tokens)} tokens. On ${rec.corpus ? rec.corpus.total : 70} alerts
         that is the single largest line in the model bill, which is why the first
         tokenomics lever anyone reaches for is the system prompt - and why it was
         measured rather than assumed.</p>`);
  });
})();
