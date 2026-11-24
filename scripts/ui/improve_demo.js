/* AI improves AI - the Failure mining panel: how the mistake was found. The
   Harness panel (one mistake, one fix, one proof) lives in panels.js. */

(function () {
  const F = window.Factory;
  if (!F) return;
  const { api, esc } = F;

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
