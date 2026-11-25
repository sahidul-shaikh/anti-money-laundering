/* Discipline panels for AI builds AI.

   One renderer per discipline, registered against the shell. Each one shows
   the real thing: the requirements on disk, the exact prompt a stage is sent,
   the skills, the loop, the graph, the evaluators. Nothing here is illustrative. */

(function () {
  const F = window.Factory;
  if (!F) return;
  const { api, esc, register } = F;

  /* ---- shared helpers ------------------------------------------------ */

  const num = (n) => Number(n || 0).toLocaleString();

  const kpi = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;

  const card = (title, sub, body, id) =>
    `<div class="card"${id ? ` id="${id}"` : ""}><h3>${title}</h3>`
    + (sub ? `<p class="sub">${sub}</p>` : "") + body + "</div>";

  const say = (host, text, tone) => {
    const el = host.querySelector(".status");
    if (el) { el.textContent = text; el.className = "status sm " + (tone || "quiet"); }
  };

  const phases = () => (F.state.serverState || { phases: [] }).phases;

  async function refreshState() {
    F.state.serverState = await (await api("/api/state")).json();
    return F.state.serverState;
  }

  const stageOptions = (filter) => phases().filter(filter || (() => true)).map((p) =>
    `<option value="${p.phase_id}">${p.n}. ${p.name}</option>`).join("");

  /* ================================================================= 02 */

  const ANCHORS = [
    ["Standing preamble and approved brief", null],
    ["This stage's instruction", "YOUR STAGE:"],
    ["Skills attached to this stage", "HOW THIS DISCIPLINE IS DONE"],
    ["The requirements, in full", "THE REQUIREMENTS, IN FULL"],
    ["The contract, rules withheld", "THE INTEGRATION CONTRACT"],
    ["What earlier stages produced", "WHAT EARLIER STAGES PRODUCED"],
  ];

  function compose(prompt) {
    const found = ANCHORS
      .map(([label, token]) => ({ label, at: token ? prompt.indexOf(token) : 0 }))
      .filter((s) => s.at >= 0)
      .sort((a, b) => a.at - b.at);
    return found.map((s, i) => ({
      label: s.label,
      chars: (i + 1 < found.length ? found[i + 1].at : prompt.length) - s.at,
    }));
  }

  register("builds", "context", (host) => {
    host.innerHTML =
      card("Assemble the exact prompt a stage is sent",
        "This costs nothing and calls no model. It builds the same string the stage "
        + "would receive and shows you what it is made of.",
        `<div class="bar">
           <select id="ctx-stage"></select>
           <label class="switch"><input type="checkbox" id="ctx-withhold">
             <span>withhold the rule detail</span></label>
           <button class="btn primary" id="ctx-go">assemble</button>
         </div>
         <div class="status sm quiet"></div>
         <div id="ctx-mix"></div>
         <pre class="feed tall" id="ctx-prompt"></pre>`)
      + card("Send it",
        "The same string, now handed to Claude Code. The artifact on disk grows as "
        + "the tokens arrive - open it in VS Code first and watch it fill.",
        `<div class="bar">
           <span class="sub">model</span>
           <select id="ctx-model"><option value="sonnet">sonnet</option>
             <option value="haiku">haiku</option></select>
           <button class="btn primary" id="ctx-run">run this stage live</button>
         </div>
         <div class="status2 sm quiet"></div>
         <div class="sub mono sm" id="ctx-meta"></div>
         <pre class="feed" id="ctx-out"></pre>
         <div class="verdict" id="ctx-verdict"></div>`);

    host.querySelector("#ctx-stage").innerHTML = stageOptions();
    host.querySelector("#ctx-stage").value = "spec";

    const say2 = (text, tone) => {
      const el = host.querySelector(".status2");
      el.textContent = text;
      el.className = "status2 sm " + (tone || "quiet");
    };

    host.querySelector("#ctx-run").addEventListener("click", () => {
      const id = host.querySelector("#ctx-stage").value;
      const phase = phases().find((p) => p.phase_id === id);
      if (phase.kind === "code") {
        say2("the implementation stage runs from the Loops discipline, "
          + "where its attempts are shown", "warn");
        return;
      }
      runStage(host, id, host.querySelector("#ctx-model").value, say2);
    });

    host.querySelector("#ctx-go").addEventListener("click", async () => {
      const id = host.querySelector("#ctx-stage").value;
      const withhold = host.querySelector("#ctx-withhold").checked ? 1 : 0;
      const r = await (await api(`/api/prompt/${id}?withhold=${withhold}`)).json();
      const mix = compose(r.prompt);
      host.querySelector("#ctx-mix").innerHTML = `
        <table><thead><tr><th>Part of the context window</th><th>Characters</th>
          <th style="width:42%">Share</th></tr></thead><tbody>
          ${mix.map((m) => `<tr><td>${m.label}</td><td class="mono">${num(m.chars)}</td>
            <td><div style="height:7px;border-radius:4px;background:var(--acn-purple);
              width:${(100 * m.chars / r.chars).toFixed(1)}%"></div></td></tr>`).join("")}
        </tbody></table>`;
      host.querySelector("#ctx-prompt").textContent = r.prompt;
      say(host, `${r.name}: ${num(r.chars)} characters, `
        + (r.skills.length ? `with the ${r.skills.join(" and ")} skill inlined`
          : "no skill attached"), "good");
    });
  });

  /* Run one document stage and tee the stream into the panel. The artifact on
     disk is written by the server as the deltas arrive, so VS Code shows the
     same text filling in. */
  function runStage(host, phaseId, model, say2) {
    const phase = phases().find((p) => p.phase_id === phaseId);
    const out = host.querySelector("#ctx-out");
    const meta = host.querySelector("#ctx-meta");
    out.textContent = "";
    meta.textContent = "";
    host.querySelector("#ctx-verdict").innerHTML = "";
    host.querySelector("#ctx-verdict").className = "verdict";
    say2("starting Claude Code for " + phase.name + "...", "warn");

    api("/api/run/" + phaseId, {
      method: "POST",
      body: JSON.stringify({ focus: true, model, withhold_rules: false }),
    }).then((started) => {
      if (!started.ok) { say2("could not start - is a run already going?", "crit"); return; }
      const source = new EventSource("/api/stream/" + phaseId);
      let boot = null;
      source.onmessage = (message) => {
        const e = JSON.parse(message.data);
        if (e.kind === "eof") { source.close(); refreshState(); return; }
        if (e.kind === "starting") {
          meta.textContent = `${e.data.name} -> ${e.data.artifact.split(/[\\/]/).pop()}`
            + ` | model ${e.data.model} | prompt ${num(e.data.prompt_chars)} chars`
            + ` | required: ${(e.data.markers || []).join(", ")}`;
          say2("Claude Code is starting - 20 to 40 seconds of silence first", "warn");
        } else if (e.kind === "booting") {
          boot = e.data.boot_s;
          say2(`first token after ${boot}s; the file on disk is growing now`, "good");
        } else if (e.kind === "delta") {
          out.textContent += e.text;
          out.scrollTop = out.scrollHeight;
          const written = e.data && e.data.written;
          meta.textContent = (written ? `${num(written)} characters on disk`
            : `${num(out.textContent.length)} characters generated`)
            + ` | ${e.elapsed_s.toFixed(0)}s elapsed`;
        } else if (e.kind === "error") {
          say2("error: " + e.text, "crit");
        } else if (e.kind === "done") {
          const v = e.data.evaluation;
          const box = host.querySelector("#ctx-verdict");
          box.className = "verdict " + (v.passed ? "ok" : "bad");
          box.innerHTML = `
            <div class="vrow"><span class="k">Evaluator</span><span class="big">${esc(v.reason)}</span>
              <span class="chip ${v.passed ? "good" : "crit"}">${v.passed ? "PASS" : "BLOCKED"}</span></div>
            <div class="vrow"><span class="k">Generated</span><span>${num(e.data.chars)}
              characters in ${e.data.duration_s}s${boot ? `, ${boot}s of that startup` : ""}</span></div>
            <div class="vrow"><span class="k">Cost</span><span>$${e.data.cost_usd.toFixed(4)}</span></div>
            ${v.missing && v.missing.length ? `<div class="vrow"><span class="k">Missing</span>
              <span class="crit mono">${v.missing.map(esc).join(", ")}</span></div>` : ""}
            ${phase.gate ? `<div class="vrow"><span class="k">Gate</span>
              <span class="warn">this stage is gated - nothing downstream runs until a human approves</span></div>` : ""}`;
          say2(v.passed ? phase.name + " passed its evaluator"
            : phase.name + " was blocked by its evaluator", v.passed ? "good" : "crit");
        }
      };
      source.onerror = () => source.close();
    });
  }

  /* ================================================================= 03 */

  register("builds", "skills", async (host) => {
    const r = await (await api("/api/skills")).json();
    const total = r.skills.reduce((a, s) => a + s.chars, 0);
    const attached = r.skills.filter((s) => s.used_by.length).length;

    host.innerHTML =
      card("The skill library on disk",
        "A skill is how a discipline is done, written once. It carries what good looks "
        + "like and the specific mistakes already made, so the next build does not "
        + "repeat them. These files are the asset that outlives this product.",
        `<div class="kpis">${kpi(r.skills.length, "skill files")}
           ${kpi(num(total), "characters of procedure")}
           ${kpi(attached + " / " + r.skills.length, "attached to a stage")}</div>
         <p class="sub mono" style="margin-top:12px">${esc(r.root)}</p>
         <div class="split">
           <div class="list" id="sk-list"></div>
           <div id="sk-body"></div>
         </div>`);

    const list = host.querySelector("#sk-list");
    list.innerHTML = r.skills.map((s, i) =>
      `<div class="slot ${i === 0 ? "on" : ""}" data-i="${i}">
        <div>${esc(s.name)}</div>
        <div class="f">${num(s.chars)} chars &middot; ${s.used_by.length
          ? esc(s.used_by.join(", ")) : "not attached"}</div>
      </div>`).join("");

    const show = (i) => {
      const s = r.skills[i];
      host.querySelector("#sk-body").innerHTML = `
        <div class="bar" style="margin-top:0">
          <span class="chip mono">${esc(s.file)}</span>
          <span class="chip">${num(s.lines)} lines</span>
          ${s.used_by.map((u) => `<span class="chip acn">${esc(u)}</span>`).join("")}
        </div>
        ${s.headings.length ? `<div class="bar">${s.headings.map((h) =>
          `<span class="chip">${esc(h)}</span>`).join("")}</div>` : ""}
        <pre class="feed tall">${esc(s.body)}</pre>`;
      list.querySelectorAll(".slot").forEach((el) =>
        el.classList.toggle("on", Number(el.dataset.i) === i));
    };
    list.querySelectorAll(".slot").forEach((el) =>
      el.addEventListener("click", () => show(Number(el.dataset.i))));
    show(0);
  });

  /* ================================================================= 04 */

  const STEPS = [
    ["Goal", "the stage brief and the integration contract"],
    ["Act", "Claude Code writes the module and its tests"],
    ["Verify", "an acceptance suite the model never sees is run"],
    ["Iterate", "its own code and the pytest output become the next instruction"],
  ];

  register("builds", "loops", async (host) => {
    host.innerHTML =
      card("Goal, act, verify, iterate",
        "Three attempts, and then the gate says no. An agent that cannot satisfy a "
        + "fixed contract in three goes will not satisfy it in thirty.",
        `<div class="dgrid" style="grid-template-columns:repeat(4,1fr);max-width:100%">
           ${STEPS.map(([t, d], i) => `<div class="dcard" style="cursor:default">
             <div class="n">${i + 1}</div><div><div class="t">${t}</div>
             <div class="sub sm">${d}</div></div></div>`).join("")}
         </div>`)
      + card("Run the implementation stage for real",
        "Tick the handicap and the detail is held back: the signature and the output "
        + "keys go over, but not the boundary, window and direction semantics, and "
        + "not the output conventions the downstream system expects. The acceptance "
        + "suite knows them. The first attempt has to guess, so it is expected to "
        + "fail; the record below shows what actually happened.",
        `<div class="bar">
           <span class="sub">model</span>
           <select id="loop-model"><option value="haiku">haiku</option>
             <option value="sonnet">sonnet</option></select>
           <label class="switch"><input type="checkbox" id="loop-withhold" checked>
             <span>withhold the rule detail</span></label>
           <button class="btn primary" id="loop-plan">draft a plan for this run</button>
         </div>
         <div id="loop-plan-box"></div>
         <div class="status sm quiet"></div>
         <div id="loop-attempts"></div>
         <pre class="feed" id="loop-out"></pre>
         <div class="verdict" id="loop-verdict"></div>`)
      + card("The last loop recorded on this machine", "", `<div id="loop-last"></div>`);

    renderLast(host);

    host.querySelector("#loop-plan").addEventListener("click", () => draftPlan(host));
  });

  /* Nothing is built without a plan a person accepted. Step 1 drafts it;
     step 2, "accept plan", is what starts the build. */
  async function draftPlan(host) {
    const box = host.querySelector("#loop-plan-box");
    const button = host.querySelector("#loop-plan");
    const body = { model: host.querySelector("#loop-model").value,
                   withhold_rules: host.querySelector("#loop-withhold").checked };
    const r = await api("/api/plan", { method: "POST", body: JSON.stringify(body) });
    if (!r.ok) { say(host, (await r.json()).error, "crit"); return; }
    button.disabled = true;
    box.innerHTML = "";
    say(host, "Claude is drafting the plan for this run - nothing is built yet", "warn");
    for (;;) {
      await new Promise((ok) => setTimeout(ok, 2000));
      const p = await (await api("/api/plan")).json();
      if (p.step === "drafting") continue;
      button.disabled = false;
      if (p.step === "failed") { say(host, "drafting failed: " + p.error, "crit"); return; }
      box.innerHTML = `<div class="verdict" style="margin-top:12px">
        <div class="vrow"><span class="k">Plan for ${esc(p.task)}</span>
          <span class="sub">drafted by ${esc(p.model)} in ${p.duration_s}s &middot;
          $${Number(p.cost_usd).toFixed(4)}</span></div>
        <pre class="feed" style="max-height:none">${esc(p.text)}</pre>
        <button class="btn primary" id="loop-accept">accept plan - start the build</button>
        <span class="sub" style="margin-left:10px">your acceptance is recorded in the
          pull request this run delivers</span></div>`;
      say(host, "read the plan; nothing is built until a person accepts it", "warn");
      host.querySelector("#loop-accept").addEventListener("click", () => {
        box.innerHTML = "";
        runLoop(host, "/api/plan/accept", { focus: true });
      });
      return;
    }
  }

  async function renderLast(host) {
    const r = await (await api("/api/lastrun/development")).json();
    const box = host.querySelector("#loop-last");
    if (!r.found) {
      box.innerHTML = `<p class="sub">No loop has been run through this console yet. `
        + `Press the button above and this fills in from the run.</p>`;
      return;
    }
    const attempts = r.events.filter((e) => e.kind === "attempt");
    const tests = r.events.filter((e) => e.kind === "tests");
    const done = r.events.find((e) => e.kind === "done");
    box.innerHTML = `<div class="bar" style="margin-top:0">
        <span class="chip">${esc(r.finished_at)}</span>
        <span class="chip mono">model ${esc(r.model)}</span>
        <span class="chip ${r.rules_withheld ? "warn" : ""}">${r.rules_withheld
          ? "rule detail withheld" : "full requirements"}</span>
      </div>
      <table><thead><tr><th>Attempt</th><th>Acceptance suite</th><th>At</th></tr></thead>
      <tbody>${attempts.map((a, i) => `<tr>
        <td>${esc(a.text)}${a.data && a.data.has_feedback
          ? ' <span class="chip warn">carrying the failure back</span>' : ""}</td>
        <td class="${tests[i] && tests[i].data.ok ? "good" : "crit"}">
          ${tests[i] ? esc(tests[i].data.summary) : "-"}</td>
        <td class="mono quiet">${a.elapsed_s.toFixed(0)}s</td></tr>`).join("")}</tbody></table>
      ${done ? `<p class="sub" style="margin-top:10px">Finished in
        ${done.data.duration_s}s for $${done.data.cost_usd.toFixed(4)}.
        Evaluator: <span class="${done.data.evaluation.passed ? "good" : "crit"}">
        ${esc(done.data.evaluation.reason)}</span></p>` : ""}`;
  }

  /** Start the stage through `path` (accepting a plan starts it) and stream it. */
  function runLoop(host, path, body) {
    const out = host.querySelector("#loop-out");
    const attemptBox = host.querySelector("#loop-attempts");
    out.textContent = "";
    attemptBox.innerHTML = "";
    host.querySelector("#loop-verdict").innerHTML = "";
    host.querySelector("#loop-verdict").className = "verdict";

    const withheld = host.querySelector("#loop-withhold").checked;
    const rows = [];

    say(host, "starting Claude Code...", "warn");
    api(path, { method: "POST", body: JSON.stringify(body) }).then(async (started) => {
      if (!started.ok) { say(host, "could not start the stage", "crit"); return; }
      const deliverTo = (await started.json()).deliver_to;

      const source = new EventSource("/api/stream/development");
      source.onmessage = (message) => {
        const e = JSON.parse(message.data);
        if (e.kind === "eof") { source.close(); renderLast(host); return; }

        if (e.kind === "starting") {
          say(host, withheld
            ? "the rule detail is withheld - the first attempt has to guess"
            : "Claude Code is starting with the full requirements", "warn");
        } else if (e.kind === "delta") {
          out.textContent += e.text;
          out.scrollTop = out.scrollHeight;
        } else if (e.kind === "attempt") {
          rows.push({ label: e.text, feedback: !!(e.data && e.data.has_feedback), tests: null });
          paintAttempts(attemptBox, rows);
          say(host, e.text + (e.data.has_feedback
            ? " - the previous attempt failed its tests"
            : " - writing the module and its tests"), "warn");
        } else if (e.kind === "files") {
          out.textContent += `\n[wrote ${e.text}]\n`;
          say(host, "files written; running the acceptance suite", "warn");
        } else if (e.kind === "tests") {
          if (rows.length) rows[rows.length - 1].tests = e.data;
          paintAttempts(attemptBox, rows);
          out.textContent += `\n[acceptance suite: ${e.data.summary}]\n`;
          if (!e.data.ok) out.textContent += e.data.output.slice(-1400) + "\n";
          out.scrollTop = out.scrollHeight;
          say(host, "acceptance suite: " + e.data.summary, e.data.ok ? "good" : "crit");
        } else if (e.kind === "error") {
          say(host, "error: " + e.text, "crit");
        } else if (e.kind === "done") {
          const v = e.data.evaluation;
          host.querySelector("#loop-verdict").className =
            "verdict " + (v.passed ? "ok" : "bad");
          host.querySelector("#loop-verdict").innerHTML = `
            <div class="vrow"><span class="k">Verdict</span><span class="big">${esc(v.reason)}</span>
              <span class="chip ${v.passed ? "good" : "crit"}">${v.passed ? "PASS" : "BLOCKED"}</span></div>
            <div class="vrow"><span class="k">Attempts</span><span>${e.data.turns}</span></div>
            <div class="vrow"><span class="k">Took</span><span>${e.data.duration_s}s
              &middot; $${e.data.cost_usd.toFixed(4)}</span></div>
            <div class="vrow"><span class="k">Verified by</span>
              <span class="mono sm">checks/acceptance/test_detector_contract.py
              &mdash; which the model never sees</span></div>`;
          say(host, v.passed
            ? "the loop closed: the contract is satisfied"
              + (deliverTo ? ` - delivering to ${deliverTo} as a pull request, watch the rail` : "")
            : "the gate refused it - nothing is delivered", v.passed ? "good" : "crit");
        }
      };
      source.onerror = () => source.close();
    });
  }

  function paintAttempts(box, rows) {
    box.innerHTML = `<table><thead><tr><th>Attempt</th><th>Fed back in</th>
      <th>Acceptance suite</th></tr></thead><tbody>
      ${rows.map((r) => `<tr>
        <td>${esc(r.label)}</td>
        <td class="sub">${r.feedback ? "the previous pytest failure" : "nothing yet"}</td>
        <td class="${r.tests ? (r.tests.ok ? "good" : "crit") : "quiet"}">
          ${r.tests ? esc(r.tests.summary) : "running..."}</td></tr>`).join("")}
      </tbody></table>`;
  }

  /* ================================================================= 05 */

  const SHORT = {
    contract: "Value contract", spec: "Spec + threat model", architecture: "Architecture",
    agent_design: "Agent graph", context: "Context design", development: "Implementation",
    evaluation: "Evaluation design", code_review: "Code review",
    security_review: "Security review", model_risk: "Model risk",
    functional_test: "Functional test", deployment: "Deployment",
  };

  function drawGraph(nodes) {
    const byId = Object.fromEntries(nodes.map((n) => [n.phase_id, n]));
    const depthOf = {};
    const depth = (id) => {
      if (depthOf[id] !== undefined) return depthOf[id];
      const parents = byId[id].depends_on;
      depthOf[id] = parents.length ? 1 + Math.max(...parents.map(depth)) : 0;
      return depthOf[id];
    };
    nodes.forEach((n) => depth(n.phase_id));

    const columns = {};
    nodes.forEach((n) => {
      const d = depthOf[n.phase_id];
      (columns[d] = columns[d] || []).push(n.phase_id);
    });

    const W = 126, H = 48, GX = 38, GY = 20, PAD = 14;
    const lanes = Math.max(...Object.values(columns).map((c) => c.length));
    const width = PAD * 2 + Object.keys(columns).length * (W + GX);
    const height = PAD * 2 + lanes * (H + GY);

    const pos = {};
    Object.entries(columns).forEach(([d, ids]) => {
      const offset = (lanes - ids.length) / 2;
      ids.forEach((id, lane) => {
        pos[id] = { x: PAD + Number(d) * (W + GX), y: PAD + (lane + offset) * (H + GY) };
      });
    });

    const edges = [];
    nodes.forEach((n) => n.depends_on.forEach((p) => edges.push([p, n.phase_id])));
    const parents = Object.fromEntries(nodes.map((n) => [n.phase_id, n.depends_on.length]));
    const children = {};
    edges.forEach(([from]) => (children[from] = (children[from] || 0) + 1));

    const edge = ([from, to]) => {
      const a = pos[from], b = pos[to];
      const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x, y2 = b.y + H / 2;
      const mid = (x1 + x2) / 2;
      const join = parents[to] > 1;
      return `<path d="M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}" fill="none"
        style="stroke:${join ? "var(--acn-purple)" : "var(--grey)"}" stroke-width="${join ? 1.8 : 1.1}"
        marker-end="url(#ar)"/>`;
    };

    const box = (n) => {
      const p = pos[n.phase_id];
      const fork = (children[n.phase_id] || 0) > 1;
      const join = parents[n.phase_id] > 1;
      return `<g class="gnode" data-p="${n.phase_id}" style="cursor:pointer">
        <rect x="${p.x}" y="${p.y}" width="${W}" height="${H}" rx="8"
          style="fill:${n.kind === "code" ? "var(--panel-2)" : "var(--page)"};stroke:${
            n.gate ? "var(--acn-purple)" : join ? "var(--acn-core)" : "var(--line)"}"
          stroke-width="${n.gate ? 1.7 : 1}"/>
        <text x="${p.x + 10}" y="${p.y + 18}" style="fill:var(--muted)" font-size="10">${n.n}${
          n.gate ? " · GATE" : ""}${n.kind === "code" ? " · CODE" : ""}</text>
        <text x="${p.x + 10}" y="${p.y + 34}" style="fill:var(--ink)" font-size="11.5">${
          SHORT[n.phase_id] || n.phase_id}</text>
        ${fork ? `<circle cx="${p.x + W}" cy="${p.y + H / 2}" r="3.2" style="fill:var(--acn-light)"/>` : ""}
        ${join ? `<circle cx="${p.x}" cy="${p.y + H / 2}" r="3.2" style="fill:var(--acn-purple)"/>` : ""}
      </g>`;
    };

    return {
      svg: `<svg viewBox="0 0 ${width} ${height}" width="100%" height="${height}"
          style="max-width:${width}px">
        <defs><marker id="ar" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6"
          markerHeight="6" orient="auto"><path d="M0,0 L8,4 L0,8 z" style="fill:var(--grey)"/></marker></defs>
        ${edges.map(edge).join("")}${nodes.map(box).join("")}</svg>`,
      edges: edges.length,
      depth: Math.max(...Object.values(depthOf)) + 1,
      forks: Object.values(children).filter((c) => c > 1).length,
      joins: Object.values(parents).filter((c) => c > 1).length,
    };
  }

  register("builds", "graphs", async (host) => {
    const nodes = phases();
    const g = drawGraph(nodes);
    host.innerHTML =
      card("The dependency graph the orchestrator walks",
        "Each stage declares what it depends on. A stage whose upstream has not passed "
        + "does not start - the orchestrator raises rather than carrying on.",
        `<div class="kpis">${kpi(nodes.length, "stages")}${kpi(g.edges, "dependencies")}
           ${kpi(nodes.filter((n) => n.gate).length, "human gates")}
           ${kpi(g.depth, "stages on the longest path")}
           ${kpi(g.forks, "forks")}${kpi(g.joins, "joins")}</div>
         <div style="overflow:auto;margin-top:16px">${g.svg}</div>
         <p class="sub" style="margin-top:10px">
           <span style="color:var(--acn-light)">&#9679;</span> feeds more than one stage &nbsp;
           <span style="color:var(--acn-purple)">&#9679;</span> cannot start until several have passed &nbsp;
           <span style="color:var(--acn-purple)">GATE</span> stops for a human &nbsp;
           <span style="color:var(--accent)">CODE</span> produces Python, verified by running tests</p>
         <div id="g-detail"></div>`);

    host.querySelectorAll(".gnode").forEach((el) => el.addEventListener("click", () => {
      const n = nodes.find((x) => x.phase_id === el.dataset.p);
      const feeds = nodes.filter((x) => x.depends_on.includes(n.phase_id));
      host.querySelector("#g-detail").innerHTML = `<div class="verdict">
        <div class="vrow"><span class="k">Stage ${n.n}</span><span class="big">${esc(n.name)}</span>
          ${n.gate ? '<span class="chip acn">gated</span>' : ""}</div>
        <div class="vrow"><span class="k">Produces</span><span class="mono">${esc(n.produces)}
          ${n.artifact_chars ? "&middot; " + num(n.artifact_chars) + " bytes on disk" : ""}</span></div>
        <div class="vrow"><span class="k">Waits for</span><span>${n.depends_on.length
          ? n.depends_on.map((d) => esc(SHORT[d] || d)).join(", ") : "nothing - it is a root"}</span></div>
        <div class="vrow"><span class="k">Feeds</span><span>${feeds.length
          ? feeds.map((f) => esc(SHORT[f.phase_id] || f.phase_id)).join(", ") : "nothing downstream"}</span></div>
        ${n.verify_with.length ? `<div class="vrow"><span class="k">Verified by</span>
          <span class="mono sm">${n.verify_with.map(esc).join(", ")}</span></div>` : ""}
        ${n.markers.length ? `<div class="vrow"><span class="k">Must contain</span>
          <span class="mono sm">${n.markers.map(esc).join(", ")}</span></div>` : ""}</div>`;
    }));
  });
})();
