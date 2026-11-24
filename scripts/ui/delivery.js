/* AI builds AI - the Delivery panel: every task's chain, with its evidence.

   Read from /api/delivery (git, GitHub, run records). The one action here is
   delivering a passing run as a pull request; approving and merging happen on
   GitHub, by a human, and there is deliberately no button for either. */

(function () {
  const F = window.Factory;
  const R = window.FactoryRail;
  if (!F || !R) return;
  const { api, esc } = F;

  const kpi = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;

  const taskCard = (t) => {
    const commits = t.prs.flatMap((p) => p.commits.filter((c) => c.trailers.Task === t.id));
    const prs = t.prs.map((p) => `<a href="${esc(p.url)}" target="_blank" rel="noopener"
        class="chip ${p.state === "MERGED" ? "good" : p.state === "OPEN" ? "acn" : ""}">#${p.number}
        ${esc(p.state.toLowerCase())} &middot; ${esc(p.author)}</a>`).join(" ");
    const rows = commits.map((c) => `<tr><td class="mono sm">${esc(c.oid.slice(0, 7))}</td>
        <td>${esc(c.author)}</td><td class="sm">${esc(c.headline)}</td>
        <td class="mono sm">${Object.entries(c.trailers).filter(([k]) => k !== "Task")
          .map(([k, v]) => `${esc(k)}: ${esc(v)}`).join("<br>")}</td></tr>`).join("");
    return `<div class="card">
      <h3>${esc(t.id)} &middot; ${esc(t.title)}</h3>
      <p class="sub">Intent by ${esc(t.intent_author)}. ${prs || "No pull request yet."}</p>
      <div class="chain-h">${R.chainHtml(t.chain)}</div>
      ${rows ? `<details style="margin-top:10px"><summary class="sub">commits and their provenance
        (${commits.length})</summary><table class="sm" style="margin-top:8px"><thead><tr>
        <th>Commit</th><th>Author</th><th>Message</th><th>Trailers</th></tr></thead>
        <tbody>${rows}</tbody></table></details>` : ""}
    </div>`;
  };

  function paint(host, s) {
    const all = s.tasks.flatMap((t) => t.prs);
    const merged = s.tasks.flatMap((t) => t.chain.filter((c) => c.label === "Merged"));
    // No default: delivering under the wrong task would put a false record in git.
    // Only tasks whose intent says "Delivery: factory" accept the loop's output.
    const select = `<option value="">choose the task this run belongs to</option>`
      + s.tasks.filter((t) => t.intent_status === "accepted" && t.deliverable)
        .map((t) => `<option value="${esc(t.id)}">${esc(t.id)} - ${esc(t.title)}</option>`).join("");
    host.querySelector("#dv-kpis").innerHTML =
      kpi(s.tasks.length, "tasks")
      + kpi(all.filter((p) => p.author === "aml-factory-bot").length, "PRs opened by the bot")
      + kpi(merged.filter((c) => c.state === "done").length, "merged with an approval")
      + kpi(merged.filter((c) => c.state === "override").length, "merged by owner override");
    const picker = host.querySelector("#dv-task");
    if (!picker.dataset.touched) picker.innerHTML = select;
    host.querySelector("#dv-tasks").innerHTML = [...s.tasks].reverse().map(taskCard).join("")
      + (s.unmatched.length ? `<div class="card"><h3>Pull requests with no task</h3>
          <p class="sub">Set up before the task flow existed: ${s.unmatched.map((u) =>
            `<a href="${esc(u.url)}" target="_blank" rel="noopener">#${u.number}</a> ${esc(u.title)}`)
            .join("; ")}</p></div>` : "");
  }

  F.register("builds", "delivery", async (host) => {
    host.innerHTML = `
      <div class="kpis" id="dv-kpis"></div>
      <div class="card"><h3>Deliver a passing run</h3>
        <p class="sub">Takes the latest passing build-loop run, commits its files with
          their provenance, and opens a pull request as aml-factory-bot. The bot cannot
          approve or merge it: that needs a human on GitHub and both required checks.</p>
        <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:10px">
          <select id="dv-task"></select>
          <button class="btn" id="dv-go">deliver latest passing run</button>
          <span class="status sm quiet" id="dv-status"></span></div></div>
      <div id="dv-tasks"><p class="sub">reading git and GitHub...</p></div>`;

    host.querySelector("#dv-go").disabled = true;
    host.querySelector("#dv-task").addEventListener("change", (e) => {
      e.target.dataset.touched = "1";
      host.querySelector("#dv-go").disabled = !e.target.value;
      if (e.target.value) R.setFocus(e.target.value);
    });
    host.querySelector("#dv-go").addEventListener("click", async () => {
      const status = host.querySelector("#dv-status");
      const button = host.querySelector("#dv-go");
      button.disabled = true;
      status.className = "status sm quiet";
      status.textContent = "committing, scanning for real data, pushing, opening the PR...";
      const r = await api("/api/deliver", { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: host.querySelector("#dv-task").value }) });
      const d = await r.json();
      button.disabled = false;
      status.className = "status sm " + (r.ok ? "good" : "crit");
      status.innerHTML = r.ok
        ? `opened <a href="${esc(d.pr_url)}" target="_blank" rel="noopener">${esc(d.pr_url)}</a>`
        : `refused: ${esc(d.error)}`;
      R.refresh();
    });

    const listen = (e) => {
      if (!document.body.contains(host)) { document.removeEventListener("delivery", listen); return; }
      paint(host, e.detail);
    };
    document.addEventListener("delivery", listen);
    const now = R.current();
    if (now) paint(host, now); else R.refresh();
  });
})();
