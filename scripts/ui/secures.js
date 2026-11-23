/* Discipline panels for AI secures AI.

   Runtime defense and Swarm make real calls to Amazon Bedrock. Threat modelling
   reads the factory's own artifact and the skill file behind it. */

(function () {
  const F = window.Factory;
  if (!F) return;
  const { api, esc, register } = F;

  const num = (n) => Number(n || 0).toLocaleString();
  const kpi = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
  const card = (title, sub, body, id) =>
    `<div class="card"${id ? ` id="${id}"` : ""}><h3>${title}</h3>`
    + (sub ? `<p class="sub">${sub}</p>` : "") + body + "</div>";

  let SEC = null;
  const secures = async () => {
    if (!SEC) SEC = await (await api("/api/secures/recorded")).json();
    return SEC;
  };
  let CAT = null;
  const alerts = async () => {
    if (!CAT) CAT = (await (await api("/api/alerts")).json()).alerts;
    return CAT;
  };

  const status = (host, text, tone) => {
    const el = host.querySelector(".status");
    if (el) { el.textContent = text; el.className = "status sm " + (tone || "quiet"); }
  };

  /* ================================================================= 01 */

  register("secures", "threat-modelling", async (host) => {
    const d = await secures();
    const tm = d.threat_model || {};
    const skill = d.skill || {};

    host.innerHTML =
      card("The threat model the factory was required to produce",
        "This is not a document written after the fact. Stage 2 declares THREAT MODEL as "
        + "a required section and the evaluator blocks the stage without it - which you "
        + "can prove in the Builds pillar by renaming the heading and pressing re-evaluate.",
        `<div class="kpis">${kpi(tm.threat_ids ? tm.threat_ids.length : 0, "threats identified")}
           ${kpi(num((tm.section || "").length), "characters in the section")}
           ${kpi(d.payloads.length + d.controls.length + d.declared.length, "probes derived from it")}</div>
         <div class="bar" style="margin-top:14px">
           ${(tm.threat_ids || []).map((t) => `<span class="chip acn mono">${esc(t)}</span>`).join("")}
         </div>
         <p class="sub mono sm">${esc(tm.source || "")}</p>
         <pre class="feed tall">${esc(tm.section || "no threat model section found")}</pre>`)
      + card("The skill it was written from",
        "The threat library is a file on disk, not knowledge in someone's head. The next "
        + "product the factory builds inherits it instead of rediscovering it.",
        `<p class="sub mono sm">${esc(skill.file || "")} &middot; ${num((skill.body || "").length)} characters</p>
         <pre class="feed tall">${esc(skill.body || "")}</pre>`);
  });

  /* ================================================================= 02 */

  const matrix = (sweep) => {
    if (!sweep) return '<p class="sub">No recorded sweep.</p>';
    const keys = Object.keys(sweep.by_tier_and_guardrail || {});
    const ids = [...new Set(keys.flatMap((k) =>
      sweep.by_tier_and_guardrail[k].map((f) => f.probe_id)))];
    return `<table><thead><tr><th>Probe</th>
      ${keys.map((k) => `<th>${esc(k.replace(":", " / envelope "))}</th>`).join("")}
      </tr></thead><tbody>
      ${ids.map((id) => `<tr>
        <td class="mono">${esc(id)}</td>
        ${keys.map((k) => {
          const f = sweep.by_tier_and_guardrail[k].find((x) => x.probe_id === id);
          if (!f) return "<td>-</td>";
          const cls = f.confirmed ? "crit" : f.outcome === "exploited" ? "warn" : "good";
          const label = f.confirmed ? "exploited"
            : f.outcome === "exploited" ? "not reproduced" : "defended";
          return `<td><span class="chip ${cls}">${label}</span></td>`;
        }).join("")}
      </tr>`).join("")}
      </tbody></table>
      <p class="sub" style="margin-top:10px">Target: alert ${esc(sweep.target.alert_id)},
      ${esc(sweep.target.party)}, which must escalate. ${sweep.calls} calls,
      $${sweep.cost_usd.toFixed(4)}. An amber cell is a probe that looked exploited
      and then failed to reproduce - it was discarded, not published.</p>`;
  };

  /* The paired trace. Also used by the sweep. */
  function streamProbe(host, alertId, body, opts) {
    const trace = host.querySelector(opts.trace);
    const finalBox = host.querySelector(opts.final);
    trace.innerHTML = "";
    finalBox.innerHTML = "";
    finalBox.className = "verdict";
    status(host, "calling Amazon Bedrock...", "warn");

    const step = (html) => {
      const div = document.createElement("div");
      div.className = "card";
      div.style.marginTop = "12px";
      div.innerHTML = html;
      trace.appendChild(div);
      return div;
    };

    api("/api/probe/" + alertId, { method: "POST", body: JSON.stringify(body) })
      .then((started) => {
        if (!started.ok) { status(host, "could not start - a probe may be in flight", "crit"); return; }
        const source = new EventSource("/api/probestream/" + alertId);

        source.onmessage = (message) => {
          const e = JSON.parse(message.data);
          if (e.kind === "eof") { source.close(); return; }
          const d = e.data;

          if (e.kind === "target") {
            step(`<h3>Target</h3>
              <div class="verdict" style="margin-top:6px">
                <div class="vrow"><span class="k">Alert</span>
                  <span class="big">${esc(d.alert_id)} &middot; ${esc(d.party)}</span></div>
                <div class="vrow"><span class="k">Correct answer</span>
                  <span class="mono">${esc(d.label)}</span></div>
                <div class="vrow"><span class="k">Payload lands in</span>
                  <span class="mono">reference text of transaction ${esc(d.carrier_ref)}</span></div>
                <div class="vrow"><span class="k">Attacker typed</span>
                  <span class="mono sm crit">${esc(d.attacker_text)}</span></div>
              </div>`);
          } else if (e.kind === "framing") {
            const box = step(`<h3>Envelope ${d.state.toUpperCase()}
                <span class="chip ${d.guardrail ? "good" : "crit"}">${
                  d.guardrail ? esc(d.control) : "no control"}</span></h3>
              <p class="sub">${esc(e.text)}</p>
              <pre class="feed">${esc(d.block)}</pre>`);
            box.scrollIntoView({ block: "nearest" });
          } else if (e.kind === "calling") {
            status(host, e.text, "warn");
          } else if (e.kind === "answer") {
            step(`<h3>What came back &middot; envelope ${esc(d.state)}</h3>
              <div class="kpis">${kpi(d.latency_ms + " ms", "latency")}
                ${kpi(num(d.tokens_out), "tokens out")}
                ${kpi("$" + d.cost_usd.toFixed(6), "cost")}</div>
              <pre class="feed" style="margin-top:12px">${esc(d.response)}</pre>`);
          } else if (e.kind === "verifying") {
            step(`<h3>Verifying <span class="chip warn">re-running</span></h3>
              <p class="sub">${esc(e.text)}</p>`);
            status(host, e.text, "warn");
          } else if (e.kind === "judged") {
            step(`<h3>Verdict &middot; envelope ${esc(d.state)}
                <span class="chip ${d.exploited ? "crit" : "good"}">${
                  d.exploited ? "EXPLOITED" : "DEFENDED"}</span></h3>
              <p class="sub">Judged by a deterministic rule, not by a model.</p>
              <div class="bar">
                <span class="chip">said ${esc(d.disposition)}</span>
                <span class="chip">correct answer ${esc(d.expected)}</span>
                ${d.reproduced === null ? ""
                  : `<span class="chip ${d.reproduced ? "crit" : "warn"}">${
                      d.reproduced ? "reproduced on re-run" : "did NOT reproduce - discarded"}</span>`}
              </div>
              <p class="${d.exploited ? "crit" : "good"} sm">${esc(d.observation)}</p>`);
            status(host, e.text, d.exploited ? "crit" : "good");
          } else if (e.kind === "final") {
            const off = d.off || {}, on = d.on || {};
            finalBox.className = "verdict " + (d.proved ? "ok" : "bad");
            finalBox.innerHTML = `
              <div class="vrow"><span class="k">Envelope off</span>
                <span class="big ${off.confirmed ? "crit" : "good"}">${
                  off.confirmed ? "EXPLOITED" : "held"}</span>
                <span class="quiet sm">${esc(off.observation || "")}</span></div>
              <div class="vrow"><span class="k">Envelope on</span>
                <span class="big ${on.confirmed ? "crit" : "good"}">${
                  on.confirmed ? "EXPLOITED" : "held"}</span>
                <span class="quiet sm">${esc(on.observation || "")}</span></div>
              <div class="vrow"><span class="k">Difference</span>
                <span>${d.proved
                  ? "the control is what stopped it - nothing else changed"
                  : "this payload did not separate the two framings on this run"}</span></div>
              <div class="vrow"><span class="k">Cost</span>
                <span>$${d.cost_usd.toFixed(6)} for the pair</span></div>`;
            status(host, d.proved
              ? "same payload, same model - only the framing differed"
              : "no separation on this run; see the recorded sweep below",
              d.proved ? "good" : "warn");
          } else if (e.kind === "sweep_start") {
            step(`<h3>Sweep &middot; ${esc(d.tier)} tier, envelope ${d.guardrail ? "on" : "off"}</h3>
              <p class="sub">${esc(e.text)}. Each finding is judged deterministically and
              anything that looks exploited is fired again before it is believed.</p>
              <div id="sw-rows"></div>`);
          } else if (e.kind === "probe") {
            status(host, "firing " + e.text, "warn");
          } else if (e.kind === "finding") {
            const rows = trace.querySelector("#sw-rows");
            const cls = d.confirmed ? "crit" : d.outcome === "exploited" ? "warn" : "good";
            const label = d.confirmed ? "EXPLOITED"
              : d.outcome === "exploited" ? "not reproduced" : "defended";
            rows.insertAdjacentHTML("beforeend", `<div class="row"
              style="grid-template-columns:70px 1fr 150px">
              <div class="mono num">${esc(d.probe_id)}</div>
              <div><div class="ink">${esc(d.name)}</div>
                <div class="sub sm">${esc(d.observation)}</div></div>
              <div><span class="chip ${cls}">${label}</span></div></div>`);
          } else if (e.kind === "controls") {
            step(`<h3>Controls that need no model</h3>
              <p class="sub">${esc(e.text)}. These either hold or they do not -
              there is nothing probabilistic about them.</p>
              ${d.controls.map((c) => `<div class="row"
                style="grid-template-columns:70px 1fr 110px">
                <div class="mono num">${esc(c.probe_id)}</div>
                <div>${esc(c.name)}<div class="sub sm">${esc(c.observation)}</div></div>
                <div><span class="chip ${c.outcome === "defended" ? "good" : "crit"}">
                  ${esc(c.outcome)}</span></div></div>`).join("")}`);
          } else if (e.kind === "declared") {
            step(`<h3>Declared, not executed</h3>
              <p class="sub">${esc(e.text)}.</p>
              ${d.declared.map((p) => `<div class="verdict" style="margin-top:10px">
                <div class="vrow"><span class="k">${esc(p.probe_id)}</span>
                  <span class="big">${esc(p.name)}</span>
                  <span class="chip warn">declared</span></div>
                <div class="vrow"><span class="k">Surface</span><span>${esc(p.surface)}</span></div>
                <div class="vrow"><span class="k">Threat</span><span class="sm">${esc(p.threat)}</span></div>
                <div class="vrow"><span class="k">Control</span><span class="sm">${esc(p.control)}</span></div>
              </div>`).join("")}`);
          } else if (e.kind === "sweep_done") {
            status(host, "sweep finished", "good");
          } else if (e.kind === "error") {
            status(host, "error: " + e.text, "crit");
          }
        };
        source.onerror = () => source.close();
      });
  }

  /* ================================================================= 03 */

})();
