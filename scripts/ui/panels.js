/* The panels a presenter drives step by step.

   Loaded last, so these definitions win over the pillar modules. Each one is
   built around a sequence a person can narrate: break it, then ask; send it
   cheap, then escalate; show the prompt, then send it; what went wrong, why,
   and what fixed it. */

(function () {
  const F = window.Factory;
  if (!F) return;
  const { api, esc } = F;
  const C = window.FactoryChat;

  const say = (host, text, tone) => {
    const el = host.querySelector(".status");
    if (el) { el.textContent = text; el.className = "status sm " + (tone || "quiet"); }
  };
  const chip = (text, tone) => `<span class="chip ${tone || ""}">${esc(text)}</span>`;

  /* ================================================== Builds / Evaluation */

  F.register("builds", "evaluation", async (host) => {
    const oracle = await (await api("/api/oracle")).json();
    const state = await (await api("/api/tamper")).json();

    host.innerHTML = `
      <div class="card">
        <h3>Break the generated code</h3>
        <p class="sub mono sm" id="ev-path"></p>
        <div class="bar">
          <button class="btn primary" id="ev-run">run the tests</button>
        </div>
        <div class="status sm quiet"></div>
      </div>
      <div class="card">
        <h3>The ${oracle.count} acceptance tests</h3>
        <p class="sub">Written before the build, never shown to the model.</p>
        <div id="ev-tests"></div>
      </div>
      <div class="card">
        <h3>Break a document instead</h3>
        <p class="sub">Rename the THREAT MODEL heading in the specification, by hand or
        by button, and ask the gate to re-read it.</p>
        <p class="sub mono sm" id="ev-docpath"></p>
        <div class="bar">
          <button class="btn" id="ev-docbreak"></button>
          <button class="btn primary" id="ev-docrun">re-read the document</button>
        </div>
        <div class="status2 sm quiet"></div>
        <div class="verdict" id="ev-docverdict"></div>
      </div>`;

    const say2 = (t, tone) => {
      const el = host.querySelector(".status2");
      el.textContent = t; el.className = "status2 sm " + (tone || "quiet");
    };

    const paintTests = (failed) => {
      const set = new Set(failed || []);
      host.querySelector("#ev-tests").innerHTML = `<table><tbody>
        ${oracle.tests.map((t, i) => {
          const name = (oracle.test_names || [])[i];
          const bad = set.has(name);
          return `<tr${bad ? ' style="background:rgba(255,94,94,.12)"' : ""}>
            <td class="num" style="width:34px">${String(i + 1).padStart(2, "0")}</td>
            <td class="${bad ? "crit" : ""}">${bad ? "<b>" : ""}${esc(t)}${bad ? "</b>" : ""}</td>
            <td style="width:92px">${bad ? chip("FAILED", "crit") : chip("pass", "good")}</td>
            </tr>`;
        }).join("")}</tbody></table>`;
    };
    paintTests([]);

    const paintButtons = (s) => {
      host.querySelector("#ev-path").textContent =
        `artifacts/builds/aml-alert-investigator/${s.code.file}`
        + `   -   change 9999.99 to 9000.0 on the upper_bound line`;
      host.querySelector("#ev-docpath").textContent =
        `artifacts/builds/aml-alert-investigator/${s.document.file}`
        + `   -   rename the heading containing THREAT MODEL`;
      host.querySelector("#ev-docbreak").textContent =
        s.document.broken ? "put the heading back" : "rename the heading for me";
      host.querySelector("#ev-docbreak").dataset.action =
        s.document.broken ? "restore" : "break";
    };
    paintButtons(state);

    const tamper = async (target, button) => {
      const r = await (await api("/api/tamper", {
        method: "POST",
        body: JSON.stringify({ target, action: button.dataset.action }),
      })).json();
      paintButtons(await (await api("/api/tamper")).json());
      return r;
    };

    host.querySelector("#ev-run").addEventListener("click", async () => {
      say(host, "running the acceptance suite...", "warn");
      const v = await (await api("/api/evaluate/development", { method: "POST" })).json();
      paintTests(v.failed_tests || []);
      say(host, v.reason + (v.passed ? "" : " - the failing tests are marked below"),
        v.passed ? "good" : "crit");
    });

    host.querySelector("#ev-docbreak").addEventListener("click", async (e) => {
      const r = await tamper("document", e.target);
      host.querySelector("#ev-docverdict").innerHTML = "";
      say2(r.changed
        ? `${r.action === "break" ? "renamed" : "restored"} the heading in ${r.file}.`
        : "nothing to change", "warn");
    });

    host.querySelector("#ev-docrun").addEventListener("click", async () => {
      say2("asking the gate...", "warn");
      const v = await (await api("/api/evaluate/spec", { method: "POST" })).json();
      const box = host.querySelector("#ev-docverdict");
      box.className = "verdict " + (v.passed ? "ok" : "bad");
      box.innerHTML = `<div class="vrow"><span class="k">The gate says</span>
          <span class="big">${esc(v.reason)}</span>
          ${chip(v.passed ? "ACCEPTED" : "REFUSED", v.passed ? "good" : "crit")}</div>`;
      say2(v.passed ? "accepted" : "refused", v.passed ? "good" : "crit");
    });
  });

  /* ======================================================= Runs / Routing */

  F.register("runs", "routing", async (host) => {
    host.innerHTML = `
      <div class="card">
        <h3>The alert</h3>
        <div class="bar">
          ${C.sampleSelect("rt-sample")}
          <button class="btn primary" id="rt-go">start</button>
        </div>
        <textarea id="rt-text" spellcheck="false" style="${C.TEXTAREA};height:120px"></textarea>
        <div class="status sm quiet" style="margin-top:8px"></div>
      </div>
      <div id="rt-steps"></div>`;

    const box = host.querySelector("#rt-text");
    const sample = host.querySelector("#rt-sample");
    const fill = async () => { box.value = await C.loadSample(api, sample.value); };
    sample.addEventListener("change", fill);
    await fill();

    host.querySelector("#rt-go").addEventListener("click", async () => {
      const steps = host.querySelector("#rt-steps");
      steps.innerHTML = "";
      const add = (html) => {
        const div = document.createElement("div");
        div.className = "card";
        div.innerHTML = html;
        steps.appendChild(div);
        div.scrollIntoView({ block: "nearest", behavior: "smooth" });
        return div;
      };

      say(host, "step 1 - trying the cheap model...", "warn");
      const r = await (await api("/api/chat/route", {
        method: "POST", body: JSON.stringify({ text: box.value }),
      })).json();
      if (r.error) { say(host, r.error, "crit"); return; }

      const a1 = r.attempts[0];
      const answer = (a) => `
        <div class="bar">
          ${chip("said " + (a.disposition || "nothing"))}
          ${chip(a.cited.length + " transactions cited")}
        </div>
        <p class="${a.trusted ? "good" : "crit"} sm">${esc(a.reason)}</p>
        ${a.narrative ? `<p class="sub" style="margin-top:8px">${esc(a.narrative)}</p>` : ""}
        ${C.reveal(host, "show the raw answer", a.response || a.error || "")}`;

      add(`<h3>Step 1 &middot; ask the cheap model
          ${chip(a1.trusted ? "GOOD ENOUGH" : "NOT GOOD ENOUGH", a1.trusted ? "good" : "crit")}</h3>
        <p class="sub">Every alert starts here. ${a1.rule
          ? `The rule it fired was read from the rulebook, page ${a1.rule.page}.` : ""}</p>
        ${C.reveal(host, "show what was sent", a1.prompt)}
        ${answer(a1)}`);

      await new Promise((done) => setTimeout(done, 900));

      if (!r.escalated) {
        say(host, "the cheap model showed its working, so nothing was escalated", "good");
      } else {
        add(`<h3>Step 2 &middot; escalate</h3>
          <p class="sub">The cheap answer could not be checked against the alert, so the
          policy sends the same alert to the stronger model. Nothing about the alert
          changed - only which model was asked.</p>`);
        await new Promise((done) => setTimeout(done, 700));
        const a2 = r.attempts[1];
        add(`<h3>Step 3 &middot; ask the premium model
            ${chip(a2.trusted ? "GOOD ENOUGH" : "STILL NOT", a2.trusted ? "good" : "crit")}</h3>
          ${answer(a2)}`);
        say(host, "escalated, and the second answer could be checked", "good");
      }

      const scored = r.correct !== null && r.correct !== undefined;
      add(`<h3>Outcome</h3>
        <div class="verdict ${scored && r.correct ? "ok" : "bad"}">
          <div class="vrow"><span class="k">Disposition</span>
            <span class="big">${esc(r.disposition || "none")}</span>
            ${scored ? chip(r.correct ? "CORRECT" : "WRONG", r.correct ? "good" : "crit") : ""}</div>
          <div class="vrow"><span class="k">Decided by</span>
            <span>${esc(r.final_tier)}${r.escalated ? ", after escalation" : ", first time"}</span></div>
        </div>`);
    });
  });

  /* =================================================== Runs / Reliability */

  F.register("runs", "reliability", async (host) => {
    const rec = await (await api("/api/runs/recorded")).json();
    const real = (rec.fleet || []).find((m) => m.tier === "cheap") || {};

    host.innerHTML = `
      <div class="card">
        <h3>Take the cheap model away</h3>
        <div class="bar" style="margin-top:14px">
          ${C.sampleSelect("rl-sample")}
          <button class="btn primary" id="rl-go">send it</button>
        </div>
        <textarea id="rl-text" spellcheck="false" style="${C.TEXTAREA};height:100px"></textarea>
        <div class="status sm quiet" style="margin-top:8px"></div>
        <div class="verdict" id="rl-final"></div>
      </div>
      <div id="rl-answer"></div>`;

    const box = host.querySelector("#rl-text");
    const sample = host.querySelector("#rl-sample");
    const fill = async () => { box.value = await C.loadSample(api, sample.value); };
    sample.addEventListener("change", fill);
    await fill();

    host.querySelector("#rl-go").addEventListener("click", async () => {
      host.querySelector("#rl-final").innerHTML = "";
      host.querySelector("#rl-answer").innerHTML = "";
      say(host, "sending...", "warn");
      const r = await (await api("/api/chat/route", {
        method: "POST",
        body: JSON.stringify({ text: box.value, break_tier: "cheap" }),
      })).json();
      if (r.error) { say(host, r.error, "crit"); return; }

      const answer = r.attempts[r.attempts.length - 1];
      const fin = host.querySelector("#rl-final");
      fin.className = "verdict " + (r.correct ? "ok" : "bad");
      const failed = r.attempts.filter((a) => a.error);
      fin.innerHTML = (failed.length ? `<div class="vrow">
            <span class="k">The cheap tier really calls</span>
            <span class="mono sm">${esc(real.model || "")}</span>
            ${chip("exists", "good")}</div>
          <div class="vrow"><span class="k">This run asked for</span>
            <span class="mono sm crit">meta.llama3-3-70b-instruct-v9:0</span>
            ${chip("no such model", "crit")}</div>` : "")
        + failed.map((a) => `<div class="vrow">
          <span class="k">Bedrock replied</span>
          <span class="mono sm crit">${esc((a.error || "").slice(0, 200))}</span>
          ${chip("CALL FAILED", "crit")}</div>`).join("")
        + `<div class="vrow"><span class="k">Still dispositioned</span>
            <span class="big">${esc(r.disposition || "no answer")}</span>
            ${r.correct !== null ? chip(r.correct ? "CORRECT" : "WRONG",
              r.correct ? "good" : "crit") : ""}</div>
           <div class="vrow"><span class="k">By</span>
            <span>${esc(r.final_tier || "-")} model</span></div>`;

      if (answer && !answer.error) {
        host.querySelector("#rl-answer").innerHTML = `<div class="card"
            style="border-color:var(--good)">
          <h3>What the ${esc(answer.tier)} model answered</h3>
          <div class="bar">${chip("said " + (answer.disposition || "nothing"))}
            ${chip(answer.cited.length + " transactions cited")}</div>
          <p class="sub">${esc(answer.narrative || "")}</p>
          ${C.reveal(host, "show the full answer", answer.response || "")}
        </div>`;
      }
      say(host, "the cheap call never reached a model; the router moved on and the "
        + "alert was still answered", "good");
    });
  });

  /* ================================================ Secures / Pen-testing */

  F.register("secures", "swarm", async (host) => {
    const d = await (await api("/api/secures/recorded")).json();

    host.innerHTML = `
      <div class="card">
        <h3>The attacker's line</h3>
        <p class="sub">This text goes into a payment reference - the one field in an
        alert written by an outsider rather than by the bank. Both prompts below carry
        it; the only difference is where it sits.</p>
        <div class="bar"><select id="pt-probe"></select>
          <button class="btn primary" id="pt-send">send both to the agent</button></div>
        <textarea id="pt-payload" spellcheck="false"
          style="width:100%;height:58px;background:#1a0606;color:#ffd9d9;
            border:1px solid var(--crit);border-radius:9px;padding:11px;
            font-family:var(--mono);font-size:11.5px;resize:vertical"></textarea>
        <div class="status sm quiet" style="margin-top:8px"></div>
      </div>
      <div class="pair">
        <div id="pt-off"></div>
        <div id="pt-on"></div>
      </div>`;

    const probe = host.querySelector("#pt-probe");
    probe.innerHTML = d.payloads.map((x) =>
      `<option value="${x.probe_id}">${x.probe_id} &middot; ${esc(x.name)}</option>`).join("");
    const payloadBox = host.querySelector("#pt-payload");
    const setPayload = () => {
      const x = d.payloads.find((y) => y.probe_id === probe.value);
      payloadBox.value = x ? x.text : "";
    };
    setPayload();

    /* The whole prompt, with the attacker's line picked out of it. */
    const marked = (prompt) => {
      const line = payloadBox.value.trim();
      const body = esc(prompt || "");
      if (!line) return body;
      return body.split(esc(line)).join(
        `<span style="background:#4a0d0d;color:#ffd9d9;padding:1px 2px">`
        + esc(line) + `</span>`);
    };

    const call = async (promptOnly) => (await (await api("/api/chat/attack", {
      method: "POST",
      body: JSON.stringify({
        text: await C.loadSample(api, "alert_11366.txt"),
        payload: payloadBox.value, tier: "cheap",
        probe_id: probe.value, prompt_only: promptOnly,
      }),
    })).json());

    const build = async () => {
      say(host, "assembling both prompts - nothing has been sent", "warn");
      const r = await call(true);
      ["off", "on"].forEach((state) => {
        const e = r[state] || {};
        host.querySelector("#pt-" + state).innerHTML = `<div class="card">
          <h3>${state === "off" ? "Unprotected" : "Protected"}</h3>
          <p class="sub">${state === "off"
            ? "The attacker's line sits among the bank's own rows, in the same voice."
            : "Every payment reference goes inside the untrusted wrapper, always."}</p>
          <pre class="feed" style="max-height:330px;overflow:auto">${
            marked(e.prompt)}</pre>
        </div>`;
      });
      say(host, "both prompts assembled. Press send when you are ready.", "quiet");
    };

    const send = async () => {
      say(host, "sending both to the model...", "warn");
      const r = await call(false);
      let worked = false;
      ["off", "on"].forEach((state) => {
        const e = r[state] || {};
        const bad = (e.note || "").startsWith("EXPLOITED");
        worked = worked || bad;
        host.querySelector("#pt-" + state).insertAdjacentHTML("beforeend",
          `<div class="card" style="border-color:${bad ? "var(--crit)" : "var(--good)"}">
            <h3>What the agent answered
              ${chip(bad ? "THE ATTACK WORKED" : "THE ATTACK FAILED",
                bad ? "crit" : "good")}</h3>
            <div class="bar">
              ${chip("agent said " + (e.disposition || "nothing"))}
              ${chip("correct answer " + (e.expected || ""))}
            </div>
            <p class="sub">${esc(e.narrative || "")}</p>
            ${C.reveal(host, "show the whole answer", e.response || "")}
          </div>`);
      });
      say(host, worked
        ? "unprotected, the attack closed an alert that should have been escalated; "
          + "protected, the same line was reported rather than obeyed"
        : "neither framing was exploited on this run", worked ? "crit" : "good");
    };

    probe.addEventListener("change", async () => { setPayload(); await build(); });
    payloadBox.addEventListener("change", build);
    host.querySelector("#pt-send").addEventListener("click", send);
    await build();
  });

  /* ================================================== Improves / Harness */

  /* Three alerts the agent escalated that should have closed. Each line is
     checked against the alert itself: what it is, what the agent said, and
     what in the record already explained it. */
  const WHY = {
    S90009: [
      "A military salary, read as layering",
      "It offered the four credits that paid for the cheque as evidence against "
        + "the party - in its own words, \"suggesting potential layering or "
        + "structuring of funds\".",
      "They are a salary. Four credits of $3,960 on the 26th of each month, "
        + "against a declared income of $68,900, from a serving soldier. The "
        + "explanation for the payment was in the same list as the payment.",
    ],
    S90013: [
      "A shop paying its suppliers, read as structuring",
      "It saw four equal payments of $8,750 on a fortnightly rhythm and reached "
        + "for structuring.",
      "Each one is matched by a trade receipt of $12,000 to $15,000 a day or two "
        + "earlier, from a hardware retailer with $740,000 of declared turnover. "
        + "That is a trading rhythm, not concealment.",
    ],
    S90001: [
      "A settlement cheque, banked and left alone",
      "It treated the size of the receipt as suspicion in itself.",
      "Layering means money moving on. $45,500 arrived by cheque and stayed - "
        + "the only payments after it are four routine ones of about $1,000.",
    ],
  };

  F.register("improves", "tokenomics", async (host) => {
    host.innerHTML = `
      <div class="card">
        <h3>One block of instructions, seventy times</h3>
        <p class="sub">The agent carries the same standing instructions into every
        alert. Bedrock bills a repeated prefix at a tenth of the rate if the model
        supports prompt caching, so the question is whether ours do. This asks each
        of them twice, with a cache point in the request.</p>
        <div class="bar">
          <button class="btn primary" id="tk-go">run the cache probe</button>
        </div>
        <div class="status sm quiet"></div>
        <div id="tk-out"></div>
      </div>`;

    host.querySelector("#tk-go").addEventListener("click", async () => {
      say(host, "sending the same prefix to every model, twice...", "warn");
      const r = await (await api("/api/improve/cache", { method: "POST" })).json();
      if (r.error) { say(host, r.error, "crit"); return; }
      const n = (v) => Number(v || 0).toLocaleString();

      const rows = r.models.map((m) => {
        const first = m.calls[0] || {};
        const second = m.calls[1] || {};
        const outcome = first.ok
          ? `wrote ${n(first.written)} tokens, then read ${n(second.read)} back`
          : `<span class="mono sm crit">${esc(first.error || "")}</span>`;
        return `<tr>
          <td class="mono sm">${esc(m.model)}</td>
          <td>${chip(m.serving ? m.tier : "not in service", m.serving ? "" : "quiet")}</td>
          <td>${outcome}</td>
          <td>${chip(m.caches ? "CACHES" : "REFUSES", m.caches ? "good" : "crit")}</td>
        </tr>`;
      }).join("");

      const works = r.models.filter((m) => m.caches);
      host.querySelector("#tk-out").innerHTML = `
        <table style="margin-top:12px"><thead><tr><th>Model</th><th>Tier</th>
          <th>What Bedrock did</th><th></th></tr></thead><tbody>${rows}</tbody></table>
        <div class="kpis" style="margin-top:14px">
          <div class="kpi"><div class="v">${n(r.prefix_tokens)}</div>
            <div class="l">tokens of standing instruction, measured</div></div>
          <div class="kpi"><div class="v">${n(r.tokens_now)}</div>
            <div class="l">billed in full across ${r.alerts} alerts</div></div>
          <div class="kpi"><div class="v">${n(r.tokens_cached)}</div>
            <div class="l">what the same prefix would bill cached</div></div>
          <div class="kpi"><div class="v">${(100 - r.cache_read_rate * 100).toFixed(0)}%</div>
            <div class="l">off the fixed prefix, where it is available</div></div>
        </div>
        <p class="sub" style="margin-top:12px">The lever is real and it works:
        ${esc(works.map((m) => m.model).join(", ") || "no model here")} wrote the
        prefix once and read it back on the second call. It is not available to us.
        Both serving models refuse the request outright, and the one that caches is
        the one the quality gate rejected - so this is a procurement decision, not an
        engineering one.</p>
        <p class="sub">Priced on ${esc(r.priced_on)}, the fixed prefix across
        ${r.alerts} alerts costs $${r.usd_now.toFixed(4)}, and $${r.usd_cached.toFixed(4)}
        cached. Worth having, and worth saying out loud that it is pennies: the money
        in this process is the GBP 17.00 of human review per alert, not the tokens.</p>`;
      say(host, works.length
        ? `${works.length} of ${r.models.length} models cache; neither serving model does`
        : "no model in this fleet caches", "good");
    });
  });

  F.register("improves", "harness", async (host) => {
    const d = await (await api("/api/improve/recorded")).json();
    const byId = Object.fromEntries((d.decisions || []).map((x) => [x.proposal_id, x]));

    host.innerHTML = `
      <div class="card">
        <h3>Pick an alert the agent got wrong</h3>
        <div class="bar">
          <select id="hz-case">
            ${Object.keys(WHY).map((id) =>
              `<option value="${id}">${id} - ${esc(WHY[id][0])}</option>`).join("")}
          </select>
          <button class="btn primary" id="hz-go">walk through it</button>
        </div>
        <div class="status sm quiet"></div>
      </div>
      <div id="hz-steps"></div>
      <div class="card">
        <h3>And then the part that decides</h3>
        <p class="sub">One case is a story. A change only ships if it helps across all
        seventy alerts, because running the same configuration twice already moves six
        of them.</p>
        <table><thead><tr><th>Change</th><th>Fixed</th><th>Broke</th><th>Verdict</th>
          </tr></thead><tbody>
          ${(d.evaluations || []).map((e) => {
            const dec = byId[e.proposal.proposal_id] || { outcome: "" };
            const tone = dec.outcome === "approved" ? "good"
              : dec.outcome === "refused" ? "crit" : "warn";
            const words = { approved: "shipped", refused: "rejected",
              insufficient_evidence: "not proven yet" };
            return `<tr><td>${esc(e.proposal.change)}</td>
              <td class="num good">${e.improved}</td>
              <td class="num ${e.regressed > e.improved ? "crit" : ""}">${e.regressed}</td>
              <td>${chip(words[dec.outcome] || dec.outcome, tone)}</td></tr>`;
          }).join("")}
        </tbody></table>
      </div>`;

    host.querySelector("#hz-go").addEventListener("click", async () => {
      const id = host.querySelector("#hz-case").value;
      const steps = host.querySelector("#hz-steps");
      steps.innerHTML = "";
      const add = (html) => {
        const div = document.createElement("div");
        div.className = "card";
        div.innerHTML = html;
        steps.appendChild(div);
        div.scrollIntoView({ block: "nearest", behavior: "smooth" });
      };

      say(host, "running the alert as it is configured today...", "warn");
      const r = await (await api("/api/improve/case", {
        method: "POST", body: JSON.stringify({ alert_id: id }),
      })).json();
      if (r.error) { say(host, r.error, "crit"); return; }
      const [before, after] = r.arms;
      const PLAIN = {
        escalate_to_case: "escalate to an investigator",
        close_no_further_action: "close it, nothing to see",
        insufficient_information: "cannot tell from this record",
      };
      const plain = (x) => PLAIN[x] || x;
      const why = WHY[id] || ["", "", ""];

      const money = (v) => "$" + Number(v || 0).toLocaleString(
        undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      const txns = r.transactions || [];
      const inbound = txns.filter((t) => /credit|in/i.test(t.direction));
      const total = inbound.reduce((a, t) => a + t.amount, 0);

      add(`<h3>Step 1 &middot; what the agent was looking at</h3>
        <p class="sub">Alert ${esc(r.alert_id)} &middot; ${esc(r.party)} &middot;
          ${esc(r.occupation || "occupation not stated")} &middot;
          declared income ${money(r.annual_income)}</p>
        <div class="bar">
          ${chip(txns.length + " transactions")}
          ${chip(inbound.length + " of them money coming in")}
          ${chip(money(total) + " in total")}
        </div>
        <table style="margin-top:10px"><thead><tr><th>Date</th><th>Reference</th>
          <th>Amount</th><th>Direction</th><th>Medium</th></tr></thead><tbody>
          ${txns.slice(0, 8).map((t) => `<tr>
            <td class="mono sm">${esc(t.date)}</td>
            <td class="mono sm">${esc(t.ref)}</td>
            <td class="num">${money(t.amount)}</td>
            <td class="sm">${esc(t.direction)}</td>
            <td class="sm">${esc(t.medium)}</td></tr>`).join("")}
        </tbody></table>
        ${txns.length > 8 ? `<p class="sub sm">and ${txns.length - 8} more</p>` : ""}
        ${C.reveal(host, "show the whole prompt the agent was sent", r.prompt || "")}`);

      await new Promise((done) => setTimeout(done, 700));
      add(`<h3>Step 2 &middot; what it decided ${chip(
          before.correct ? "RIGHT THIS TIME" : "WRONG",
          before.correct ? "good" : "crit")}</h3>
        <p>The right answer was <b>${esc(plain(r.label))}</b>.
        The agent said <b class="${before.correct ? "good" : "crit"}">${
          esc(plain(before.disposition))}</b>.</p>
        ${before.correct ? `<p class="sub">It got this one right without the fix.
          That is the run-to-run variance the table at the bottom exists for, and
          it is exactly why one case never decides anything.</p>` : ""}
        <p class="sub" style="margin-top:8px">${esc(before.narrative)}</p>`);

      await new Promise((done) => setTimeout(done, 700));
      add(`<h3>Step 3 &middot; why it got it wrong</h3>
        <p>${esc(why[1])}</p>
        <p class="sub" style="margin-top:8px">${esc(why[2])}</p>`);

      await new Promise((done) => setTimeout(done, 700));
      add(`<h3>Step 4 &middot; the fix</h3>
        <p class="sub">The same mistake appeared on a group of alerts with the same
        shape. Nothing about the alert changes and the base instructions are not
        rewritten - this is appended to them, exactly as printed:</p>
        <pre class="feed">${esc(r.added_rule || "")}</pre>
        ${C.reveal(host, "show the standing instructions with it applied",
          after.system || "")}`);

      await new Promise((done) => setTimeout(done, 700));
      say(host, "running the same alert again with the fix applied...", "warn");
      add(`<h3>Step 5 &middot; the same alert, again
          ${chip(after.correct ? "RIGHT" : "STILL WRONG", after.correct ? "good" : "crit")}</h3>
        <p>The agent said <b class="${after.correct ? "good" : "crit"}">${
          esc(plain(after.disposition))}</b>.</p>
        <p class="sub" style="margin-top:8px">${esc(after.narrative)}</p>`);

      say(host, r.flipped
        ? "wrong, then right - and nothing about the alert changed"
        : before.correct
          ? "it got this one right before the change too - run-to-run variance"
          : "this one did not flip on this run", r.flipped ? "good" : "warn");
    });
  });
})();
