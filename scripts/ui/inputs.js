/* Panels a presenter types or presses into: the requirement itself, one
   improvement case, and the price of the fixed instruction prefix.

   Registered after the pillar modules, so these definitions win. */

(function () {
  const F = window.Factory;
  if (!F) return;
  const { api, esc } = F;

  const num = (n) => Number(n || 0).toLocaleString();
  const kpi = (v, l) => `<div class="kpi"><div class="v">${v}</div><div class="l">${l}</div></div>`;
  const TEXTAREA = "width:100%;background:var(--code-bg);color:var(--code-ink);"
    + "border:1px solid var(--line);border-radius:9px;padding:12px;"
    + "font-family:var(--mono);font-size:11.5px;resize:vertical";

  const say = (host, text, tone) => {
    const el = host.querySelector(".status");
    if (el) { el.textContent = text; el.className = "status sm " + (tone || "quiet"); }
  };

  /* ---- Builds / Specs ------------------------------------------------ */

  F.register("builds", "specs", async (host) => {
    const state = await (await api("/api/state")).json();
    let brief = state.brief;

    host.innerHTML = `
      <div class="card">
        <h3>The requirement</h3>
        <p class="sub">One human writes this. Paste it, save it, then have stage 0 read it.</p>
        <div class="bar">
          <button class="btn primary" id="pr-extract">stage 0: read it</button>
          <button class="btn" id="pr-approve">approve it</button>
          <button class="btn" id="pr-save">save my edits</button>
        </div>
        <textarea id="pr-text" spellcheck="false" style="${TEXTAREA};height:230px"
          placeholder="Paste the product requirement here"></textarea>
        <div class="status sm quiet" style="margin-top:8px"></div>
      </div>
      <div class="card"><h3>What stage 0 extracted</h3>
        <div id="pr-brief"><p class="sub">Nothing yet. Press <b>stage 0: read it</b>.</p></div></div>`;

    const box = host.querySelector("#pr-text");
    // The requirement on disk is the starting point, so it is already in the box.
    box.value = ((await (await api("/api/prd")).json()).body) || "";

    const paint = () => {
      if (!brief) return;
      const list = (items, label) => items && items.length
        ? `<div class="vrow"><span class="k">${label}</span><span>`
          + items.map(esc).join("<br>") + "</span></div>" : "";
      host.querySelector("#pr-brief").innerHTML = `<div class="verdict">
        <div class="vrow"><span class="k">Product</span>
          <span class="big">${esc(brief.product)}</span></div>
        <div class="vrow"><span class="k">Domain</span><span>${esc(brief.domain)}</span></div>
        <div class="vrow"><span class="k">Raised by</span><span>${esc(brief.author)}</span></div>
        <div class="vrow"><span class="k">Statement</span><span>${esc(brief.statement)}</span></div>
        ${list(brief.constraints, "Constraints")}</div>`;
    };
    // Deliberately not painted on load: the card should fill because stage 0
    // ran, not because a brief happens to be on disk from a previous session.

    host.querySelector("#pr-save").addEventListener("click", async () => {
      const r = await (await api("/api/prd/save", {
        method: "POST", body: JSON.stringify({ body: box.value }),
      })).json();
      say(host, r.saved
        ? `saved ${num(r.chars)} characters to ${r.path}; the previous one is in ${r.backup}`
        : "not saved: " + (r.error || ""), r.saved ? "good" : "crit");
    });

    host.querySelector("#pr-extract").addEventListener("click", async () => {
      say(host, "stage 0 is reading the requirement...", "warn");
      const r = await (await api("/api/extract", { method: "POST" })).json();
      if (r.error) { say(host, "extraction failed: " + r.error.slice(0, 140), "crit"); return; }
      brief = r.brief;
      paint();
      say(host, "extracted - nothing is locked in until you approve it", "good");
    });

    host.querySelector("#pr-approve").addEventListener("click", async () => {
      if (!brief) { say(host, "read the requirement first", "crit"); return; }
      const r = await (await api("/api/brief", {
        method: "POST", body: JSON.stringify(brief),
      })).json();
      say(host, r.saved ? "approved. Every stage now derives from this." : "save failed",
        r.saved ? "good" : "crit");
    });
  });

})();
