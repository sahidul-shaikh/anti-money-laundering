/* AI improves AI - one mistake, one fix, one proof.

   Three cards in plain order: what the agent got wrong, what was changed, and
   the same alert run again. The statistics that decide whether a change ships
   live underneath, deliberately after the story rather than instead of it. */

(function () {
  const F = window.Factory;
  if (!F) return;
  const { api, esc } = F;

  const CASES = [
    ["S90009", "salary-sized credits arriving every month"],
    ["S90011", "equal payments going out on a schedule"],
    ["S90013", "equal payments going out on a schedule"],
    ["S90001", "a large sale receipt that was banked and left alone"],
  ];

  const say = (host, text, tone) => {
    const el = host.querySelector(".status");
    if (el) { el.textContent = text; el.className = "status sm " + (tone || "quiet"); }
  };

  F.register("improves", "harness", async (host) => {
    const d = await (await api("/api/improve/recorded")).json();
    const byId = Object.fromEntries((d.decisions || []).map((x) => [x.proposal_id, x]));

    host.innerHTML = `
      <div class="card">
        <h3>Pick a case the agent got wrong</h3>
        <div class="bar">
          <select id="im-case">
            ${CASES.map(([id, what]) =>
              `<option value="${id}">${id} - ${esc(what)}</option>`).join("")}
          </select>
          <button class="btn primary" id="im-go">show me</button>
        </div>
        <div class="status sm quiet"></div>
      </div>
      <div id="im-out"></div>
      <div class="card">
        <h3>One case is a story, not a decision</h3>
        <p class="sub">Run the same configuration twice with nothing changed and six of
        the seventy alerts answer differently. So a change ships on a paired test across
        the whole corpus, not on a case that went well.</p>
        <table><thead><tr><th>Change</th><th>Fixed</th><th>Broke</th>
          <th>Verdict</th></tr></thead><tbody>
          ${(d.evaluations || []).map((e) => {
            const dec = byId[e.proposal.proposal_id] || { outcome: "" };
            const tone = dec.outcome === "approved" ? "good"
              : dec.outcome === "refused" ? "crit" : "warn";
            const words = { approved: "shipped", refused: "rejected",
              insufficient_evidence: "not proven yet" };
            return `<tr><td>${esc(e.proposal.change)}</td>
              <td class="num good">${e.improved}</td>
              <td class="num ${e.regressed > e.improved ? "crit" : ""}">${e.regressed}</td>
              <td><span class="chip ${tone}">${
                esc(words[dec.outcome] || dec.outcome)}</span></td></tr>`;
          }).join("")}
        </tbody></table>
      </div>`;

    host.querySelector("#im-go").addEventListener("click", async () => {
      const out = host.querySelector("#im-out");
      out.innerHTML = "";
      say(host, "running the same alert before and after the change...", "warn");

      const r = await (await api("/api/improve/case", {
        method: "POST",
        body: JSON.stringify({ alert_id: host.querySelector("#im-case").value }),
      })).json();
      if (r.error) { say(host, r.error, "crit"); return; }

      const [before, after] = r.arms;
      const PLAIN = {
        escalate_to_case: "escalate this to an investigator",
        close_no_further_action: "close it, nothing to see",
        insufficient_information: "the record cannot settle it",
      };
      const plain = (x) => PLAIN[x] || x;

      out.innerHTML = `
        <div class="card" style="border-color:var(--crit)">
          <h3>1. The mistake <span class="chip crit">WRONG</span></h3>
          <p class="sub">Alert ${esc(r.alert_id)}, ${esc(r.party)}. The right answer is
          <b>${esc(plain(r.label))}</b>.</p>
          <p>The agent said: <b class="crit">${esc(plain(before.disposition))}</b>,
          at confidence ${before.confidence}.</p>
          <p class="sub" style="margin-top:8px">${esc(before.narrative)}</p>
        </div>
        <div class="card" style="border-color:var(--acn-purple)">
          <h3>2. The fix</h3>
          <p class="sub">The same mistake showed up on a group of alerts, all with the
          same shape. One instruction was added to the agent:</p>
          <p style="margin-top:8px"><b>Before calling a large amount suspicious, look for
          the explanation in the transactions you were already given.</b> Is the source of
          the money visible? Did it move on, or did it stay? Are the payments regular and
          matched by receipts? If the record explains it, close it and say what explained it.</p>
        </div>
        <div class="card" style="border-color:${
            after.correct ? "var(--good)" : "var(--crit)"}">
          <h3>3. The same alert, again
            <span class="chip ${after.correct ? "good" : "crit"}">${
              after.correct ? "RIGHT" : "STILL WRONG"}</span></h3>
          <p>The agent said: <b class="${after.correct ? "good" : "crit"}">${
            esc(plain(after.disposition))}</b>, at confidence ${after.confidence}.</p>
          <p class="sub" style="margin-top:8px">${esc(after.narrative)}</p>
        </div>`;

      say(host, r.flipped
        ? "wrong, then right - and nothing about the alert changed"
        : "this one did not flip on this run", r.flipped ? "good" : "warn");
    });
  });

  /* ---- Failure mining: how the mistake was found -------------------- */

  F.register("improves", "failure-mining", async (host) => {
    const d = await (await api("/api/improve/recorded")).json();
    const PLAIN = {
      "over_escalation:large_receipt_retained":
        "A large payment arrived and stayed in the account. The agent called it suspicious without checking whether it moved on.",
      "over_escalation:regular_equal_credits":
        "Equal credits arriving on a schedule - the shape of a salary. The agent read the rhythm as a burst of activity.",
      "over_escalation:regular_equal_debits":
        "Equal payments going out on a schedule - the shape of a trading relationship. The agent read it as structuring.",
      "missed_escalation:unremarkable":
        "Activity that looks ordinary but should have been escalated. No common cause found yet.",
    };

    host.innerHTML = `
      <div class="card">
        <h3>The same mistake, made repeatedly</h3>
        <p class="sub">Failures are grouped by what the alert looks like - never by the
        answer, which would be circular. A group under three examples is not reported:
        two mistakes are not a pattern.</p>
        ${(d.clusters || []).map((c) => `<div class="verdict" style="margin-top:12px">
          <div class="vrow"><span class="k">${c.count} alerts</span>
            <span class="big">${esc(PLAIN[c.signature] || c.signature)}</span></div>
          <div class="vrow"><span class="k">Points at</span>
            <span>${c.proposal
              ? esc("a change to the agent's instructions")
              : '<span class="warn">nothing yet - this one needs an analyst</span>'}</span></div>
        </div>`).join("")}
      </div>`;
  });
})();
