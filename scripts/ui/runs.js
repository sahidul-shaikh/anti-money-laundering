/* Discipline panels for AI runs AI.

   Routing and Reliability make real calls to Amazon Bedrock when you press
   them. Observability and FinOps read the recorded baseline - no model is
   called, and the panels say so. */

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

  const fleetTable = (fleet) => `
    <table><thead><tr><th>Tier</th><th>Model</th><th>Quality</th>
      <th>$/Mtok in</th><th>$/Mtok out</th><th>Serving</th></tr></thead><tbody>
      ${fleet.map((m) => `<tr>
        <td><b>${esc(m.tier)}</b></td>
        <td class="mono sm">${esc(m.model)}</td>
        <td class="num">${m.quality}</td>
        <td class="num">${m.price_in}</td>
        <td class="num">${m.price_out}</td>
        <td>${m.serving ? '<span class="chip good">serving</span>'
          : '<span class="chip crit">withdrawn</span>'}</td></tr>`).join("")}
    </tbody></table>`;

  const alertOptions = (list, onlyCandidates) => list
    .filter((a) => !onlyCandidates || a.candidate)
    .map((a) => `<option value="${a.alert_id}">${a.alert_id} &middot; ${esc(a.party)}`
      + ` &middot; ${a.scenario}${a.candidate ? " (cheap got this wrong)" : ""}</option>`)
    .join("");

  /* ================================================================= 01 */

  /* The live trace. Shared by Routing and Reliability. */
  function streamRoute(host, alertId, body, opts) {
    const trace = host.querySelector(opts.trace);
    const finalBox = host.querySelector(opts.final);
    const say = (t, tone) => {
      const el = host.querySelector(".status");
      el.textContent = t;
      el.className = "status sm " + (tone || "quiet");
    };
    trace.innerHTML = "";
    finalBox.innerHTML = "";
    finalBox.className = "verdict";
    say("calling Amazon Bedrock...", "warn");

    const step = (html) => {
      const div = document.createElement("div");
      div.className = "card";
      div.style.marginTop = "12px";
      div.innerHTML = html;
      trace.appendChild(div);
      return div;
    };

    api("/api/route/" + alertId, { method: "POST", body: JSON.stringify(body) })
      .then((started) => {
        if (!started.ok) { say("could not start - a run may be in flight", "crit"); return; }
        const source = new EventSource("/api/routestream/" + alertId);

        source.onmessage = (message) => {
          const e = JSON.parse(message.data);
          if (e.kind === "eof") { source.close(); return; }

          if (e.kind === "decision") {
            const d = e.data;
            step(`<h3>Routing decision</h3>
              <p class="sub">${esc(d.describe)}</p>
              <div class="bar"><span class="chip acn">policy: ${esc(d.policy)}</span>
                <span class="chip">quality floor ${d.quality_floor}</span>
                <span class="chip good">starting at ${esc(d.chain[0].tier)}</span></div>
              <table><thead><tr><th>Eligible, cheapest first</th><th>Quality</th>
                <th>$/Mtok</th></tr></thead><tbody>
                ${d.chain.map((m) => `<tr><td>${esc(m.tier)}
                  <span class="mono sm quiet">${esc(m.model)}</span></td>
                  <td class="num">${m.quality}</td>
                  <td class="num">${m.price_in} / ${m.price_out}</td></tr>`).join("")}
              </tbody></table>`);
            say(e.text, "quiet");
          } else if (e.kind === "prompt") {
            const d = e.data;
            const box = step(`<h3>What goes to the model</h3>
              <p class="sub">${esc(e.text)}. Nothing else reaches Bedrock.</p>
              <div class="bar"><button class="link" data-show="sys">show the system prompt</button>
                <button class="link" data-show="usr">show the alert as rendered</button></div>
              <pre class="feed tall" data-pane="sys"></pre>
              <pre class="feed tall" data-pane="usr"></pre>`);
            box.querySelectorAll("[data-show]").forEach((btn) =>
              btn.addEventListener("click", () => {
                const pane = box.querySelector(`[data-pane="${btn.dataset.show}"]`);
                pane.textContent = pane.textContent
                  ? "" : (btn.dataset.show === "sys" ? d.system : d.prompt);
              }));
          } else if (e.kind === "calling") {
            say(`calling the ${e.data.tier} tier...`, "warn");
          } else if (e.kind === "provider_error") {
            step(`<h3>Attempt ${e.data.n} &middot; ${esc(e.data.tier)}
                <span class="chip crit">provider error</span></h3>
              <p class="sub">The call did not reach a model. The router records the
              failed attempt and moves to the next eligible one.</p>
              <pre class="feed">${esc(e.data.error)}</pre>`);
            say(e.text, "crit");
          } else if (e.kind === "answer") {
            const d = e.data;
            step(`<h3>Attempt ${d.n} &middot; ${esc(d.tier)} answered</h3>
              <div class="kpis">${kpi(d.latency_ms + " ms", "latency")}
                ${kpi(num(d.tokens_in), "tokens in")}
                ${kpi(num(d.tokens_out), "tokens out")}
                ${kpi("$" + d.cost_usd.toFixed(6), "cost of this call")}</div>
              <p class="sub" style="margin-top:12px">Exactly what came back:</p>
              <pre class="feed">${esc(d.response)}</pre>`);
          } else if (e.kind === "unparseable") {
            step(`<h3>Unparseable <span class="chip crit">not a scorable answer</span></h3>
              <p class="sub">${esc(e.text)}</p>`);
          } else if (e.kind === "check") {
            const c = e.data.check;
            step(`<h3>Evidence check
                <span class="chip ${c.passed ? "good" : "crit"}">${c.passed ? "TRUSTED" : "NOT TRUSTED"}</span></h3>
              <p class="sub">Every cited reference is ticked off against this alert's own
              transaction list. Deterministic - no model is asked whether the answer was good.</p>
              <div class="bar">
                <span class="chip">${esc(e.data.disposition)}</span>
                <span class="chip">confidence ${e.data.confidence}</span>
                <span class="chip">cited ${c.cited}</span>
                <span class="chip ${c.invented ? "crit" : ""}">invented ${c.invented}</span>
                <span class="chip">groundedness ${c.groundedness}</span></div>
              <p class="${c.passed ? "good" : "crit"} sm">${esc(c.reason)}</p>
              ${c.references.length ? `<div class="bar">${c.references.map((r) =>
                `<span class="chip ${r.in_alert ? "good" : "crit"} mono">${
                  r.in_alert ? "&#10003;" : "&#10007;"} ${esc(r.ref)}</span>`).join("")}</div>`
                : '<p class="crit sm">No references at all - there is nothing to verify.</p>'}`);
            say(c.reason, c.passed ? "good" : "crit");
          } else if (e.kind === "escalate") {
            step(`<h3>Escalating <span class="chip acn">${esc(e.data.from)} &rarr; ${esc(e.data.to)}</span></h3>
              <p class="sub">${esc(e.data.reason)}. The policy does not accept an answer
              it cannot verify, so the alert goes to the stronger model.</p>`);
            say(e.text, "warn");
          } else if (e.kind === "error") {
            say("error: " + e.text, "crit");
          } else if (e.kind === "final") {
            const d = e.data;
            const ok = d.correct;
            finalBox.className = "verdict " + (ok ? "ok" : "bad");
            finalBox.innerHTML = `
              <div class="vrow"><span class="k">Final answer</span>
                <span class="big">${esc(d.final_disposition || "no answer")}</span>
                <span class="chip ${ok ? "good" : "crit"}">${ok ? "CORRECT" : "WRONG"}</span></div>
              <div class="vrow"><span class="k">Answered by</span>
                <span>${esc(d.final_tier || "-")}${d.escalated
                  ? " after escalation on the evidence check"
                  : d.attempts.some((a) => a.error)
                    ? " after falling through a provider failure"
                    : " first time"}</span></div>
              <div class="vrow"><span class="k">Calls</span>
                <span>${d.attempts.length} &middot; $${d.cost_usd.toFixed(6)}
                &middot; ${num(d.latency_ms)} ms end to end</span></div>
              <div class="vrow"><span class="k">Policy</span>
                <span class="sm">${esc(d.policy.describe)}</span></div>`;
            say(ok ? "the routed answer is correct" : "the routed answer is still wrong",
              ok ? "good" : "crit");
          }
        };
        source.onerror = () => source.close();
      });
  }

  /* ================================================================= 02 */

  register("runs", "reliability", async (host) => {
    const rec = await recorded();
    const sys = (tier) => ((rec.runs[tier] || {}).telemetry || {}).SYSTEM || {};

    host.innerHTML = `
      <div class="card">
        <h3>Send an alert with the cheap model unreachable</h3>
        <p class="sub">The cheap tier is pointed at a model name that does not exist, so
        Bedrock rejects the call outright. That is a stand-in, not a real outage - the
        failure that actually happened in the recorded run was throttling - but the
        router cannot tell the difference, which is the point.</p>
        <div class="bar">
          <select id="rl-sample"></select>
          <label class="switch"><input type="checkbox" id="rl-break" checked>
            <span>make the cheap model unreachable</span></label>
          <button class="btn primary" id="rl-go">send it</button>
        </div>
        <textarea id="rl-text" spellcheck="false" style="${window.FactoryChat.TEXTAREA};height:120px"
          placeholder="Paste an alert"></textarea>
        <div class="status sm quiet" style="margin-top:8px"></div>
        <div id="rl-trace"></div>
        <div class="verdict" id="rl-final"></div>
      </div>
      <div class="card">
        <h3>A failed call is not a wrong answer</h3>
        <table><thead><tr><th>Tier</th><th>Calls</th><th>Reached a model</th>
          <th>Slowest 5%</th></tr></thead><tbody>
          ${Object.keys(rec.runs || {}).map((t) => {
            const s = sys(t);
            return `<tr><td><b>${esc(t)}</b></td><td class="num">${s.calls}</td>
              <td class="num ${s.failed_calls ? "crit" : "good"}">${
                s.calls - s.failed_calls} of ${s.calls}</td>
              <td class="num">${Math.round((s.latency_p95_ms || 0) / 1000)}s</td></tr>`;
          }).join("")}
        </tbody></table>
        <p class="sub" style="margin-top:10px">Where no model answers, the alert is
        queued to a human and priced as a review - never as a missed report. The nine
        alerts that hit this in the recorded run are excluded from the accuracy figures,
        because a call that never arrived is not a bad answer.</p>
      </div>`;

    host.querySelector("#rl-sample").outerHTML =
      window.FactoryChat.sampleSelect("rl-sample");
    const box = host.querySelector("#rl-text");
    const sample = host.querySelector("#rl-sample");
    const fill = async () => {
      box.value = await window.FactoryChat.loadSample(api, sample.value);
    };
    sample.addEventListener("change", fill);
    await fill();

    host.querySelector("#rl-go").addEventListener("click", async () => {
      const alertId = (box.value.match(/ALERT\s+([A-Z]?\d{4,6})/i) || [])[1] || "11366";
      streamRoute(host, alertId, {
        quality_floor: 0,
        escalate_without_evidence: true,
        break_tier: host.querySelector("#rl-break").checked ? "cheap" : null,
      }, { trace: "#rl-trace", final: "#rl-final" });
    });
  });
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
