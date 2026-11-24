/* AI Engineering Factory - the shell.

   Renders any pillar from library/pillars.json: the nav, the discipline strip,
   the hero, the capability ring and the discipline grid. It knows nothing about
   what a discipline proves. Panels register themselves against a pillar and a
   discipline id, so adding the next pillar is a new panel file, not a new shell. */

window.Factory = (function () {
  const PANELS = {};
  const state = { pillars: [], pillar: null, discipline: null, connected: false };

  const api = (path, opts) =>
    fetch(path, Object.assign({ headers: { "Content-Type": "application/json" } }, opts));

  const esc = (s) => String(s == null ? "" : s)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const el = (id) => document.getElementById(id);

  const register = (pillarId, disciplineId, render) => {
    PANELS[pillarId + "/" + disciplineId] = render;
  };

  /* ---- the capability ring ------------------------------------------ */

  const QUADRANT = { builds: 0, runs: 1, secures: 2, improves: 3 };

  function donut(cx, cy, rInner, rOuter, a0, a1) {
    const pt = (r, a) => {
      const t = (a - 90) * Math.PI / 180;
      return [cx + r * Math.cos(t), cy + r * Math.sin(t)];
    };
    const [x1, y1] = pt(rOuter, a0), [x2, y2] = pt(rOuter, a1);
    const [x3, y3] = pt(rInner, a1), [x4, y4] = pt(rInner, a0);
    const large = a1 - a0 > 180 ? 1 : 0;
    return `M${x1} ${y1} A${rOuter} ${rOuter} 0 ${large} 1 ${x2} ${y2}`
      + ` L${x3} ${y3} A${rInner} ${rInner} 0 ${large} 0 ${x4} ${y4} Z`;
  }

  function ring(pillar) {
    const cx = 180, cy = 180;
    const seg = state.pillars.map((p) => {
      const q = QUADRANT[p.id];
      const a0 = -45 + q * 90, a1 = a0 + 90;
      const on = p.id === pillar.id;
      const mid = (a0 + a1) / 2 - 90;
      const lr = 142;
      const lx = cx + lr * Math.cos(mid * Math.PI / 180);
      const ly = cy + lr * Math.sin(mid * Math.PI / 180);
      return `<path class="quad" data-pillar="${p.id}"
          d="${donut(cx, cy, 118, 166, a0, a1)}"
          fill="${on ? "#a100ff" : "#241733"}"
          stroke="${on ? "#be82ff" : "#3a2b50"}" stroke-width="1"></path>
        <text x="${lx}" y="${ly}" text-anchor="middle" dominant-baseline="middle"
          font-size="12.5" letter-spacing="0.6"
          fill="${on ? "#ffffff" : "#a39bb0"}"
          style="pointer-events:none">${p.verb}</text>`;
    }).join("");

    return `<div class="ring"><svg viewBox="0 0 360 360" role="img"
        aria-label="four capability quadrants">
      <circle cx="${cx}" cy="${cy}" r="104" fill="none" stroke="#2e2040"></circle>
      <circle cx="${cx}" cy="${cy}" r="78" fill="#120c1c" stroke="#460073"></circle>
      ${seg}
      <text x="${cx}" y="${cy - 15}" text-anchor="middle" font-size="12"
        letter-spacing="1.6" fill="#be82ff">AI</text>
      <text x="${cx}" y="${cy + 2}" text-anchor="middle" font-size="12"
        letter-spacing="1.6" fill="#ffffff">ENGINEERING</text>
      <text x="${cx}" y="${cy + 19}" text-anchor="middle" font-size="12"
        letter-spacing="1.6" fill="#ffffff">FACTORY</text>
    </svg></div>`;
  }

  /* ---- chrome -------------------------------------------------------- */

  function renderNav() {
    el("pillar-nav").innerHTML = state.pillars.map((p) =>
      `<button class="pnav ${p.id === state.pillar.id ? "on" : ""}"
        data-pillar="${p.id}" ${p.status === "next" ? "disabled" : ""}
        title="${p.status === "next" ? "not built yet" : p.promise}">${p.title}</button>`
    ).join("");
    el("pillar-nav").querySelectorAll("[data-pillar]").forEach((b) =>
      b.addEventListener("click", () => go(b.dataset.pillar)));
  }

  function renderStrip() {
    const p = state.pillar;
    el("strip").innerHTML =
      `<div class="strip-label">${p.title}<span class="arrow">&rsaquo;</span></div>`
      + p.disciplines.map((d) =>
        `<button class="dchip ${d.id === state.discipline ? "on" : ""}"
          data-d="${d.id}"><span class="dn">${d.n}</span>${d.title}</button>`
      ).join("");
    el("strip").querySelectorAll("[data-d]").forEach((b) =>
      b.addEventListener("click", () => go(state.pillar.id, b.dataset.d)));
  }

  function renderHero() {
    const p = state.pillar;
    const nxt = state.pillars.find((x) => x.id === p.next);
    el("hero").innerHTML = `
      <div>
        <div class="eyebrow"><b>0${p.index}</b> / 04 &nbsp;&middot;&nbsp; Capability</div>
        <div class="hero-title">
          <div class="hero-mark">&gt;</div>
          <h1>${p.title}</h1>
        </div>
        <p class="promise">${esc(p.promise)}</p>
        <div class="hero-actions">
          <button class="btn primary" id="hero-explore">Explore capabilities &rarr;</button>
          ${nxt ? `<button class="btn" data-pillar="${nxt.id}"
            ${nxt.status === "next" ? "disabled" : ""}>Next: ${nxt.title} &rsaquo;</button>` : ""}
        </div>
      </div>
      ${ring(p)}`;

    el("hero-explore").addEventListener("click", () =>
      go(p.id, p.disciplines[0].id));
    el("hero").querySelectorAll("[data-pillar]").forEach((b) =>
      b.addEventListener("click", () => go(b.dataset.pillar)));
    el("hero").querySelectorAll(".quad").forEach((q) =>
      q.addEventListener("click", () => go(q.dataset.pillar)));
  }

  function renderGrid() {
    el("dgrid").innerHTML = state.pillar.disciplines.map((d) =>
      `<div class="dcard" data-d="${d.id}">
        <div class="n">${d.n}</div>
        <div><div class="t">${d.title}</div>
          ${d.mode ? `<div class="m">${d.mode}</div>` : ""}</div>
      </div>`).join("");
    el("dgrid").querySelectorAll("[data-d]").forEach((c) =>
      c.addEventListener("click", () => go(state.pillar.id, c.dataset.d)));
  }

  function renderFooter() {
    const p = state.pillar;
    const nxt = state.pillars.find((x) => x.id === p.next);
    el("foot-note").textContent = state.connected
      ? "Factory server connected. Anything marked live runs for real when you press it."
      : "Factory server not reachable - start scripts/serve_factory.py and open localhost:8765.";
    const b = el("foot-next");
    b.textContent = nxt ? "Next: " + nxt.title + "  ›" : "";
    b.style.display = nxt ? "" : "none";
    b.disabled = !nxt || nxt.status === "next";
    b.onclick = () => nxt && go(nxt.id);
  }

  /* ---- panel ---------------------------------------------------------- */

  function renderPanel() {
    const panel = el("dpanel");
    const open = !!state.discipline;
    el("hero").style.display = open ? "none" : "";
    el("dgrid-wrap").style.display = open ? "none" : "";
    if (!open) { panel.innerHTML = ""; return; }

    const d = state.pillar.disciplines.find((x) => x.id === state.discipline);
    panel.innerHTML = `
      <div class="dhead">
        <span class="dn2">${d.n} / ${String(state.pillar.disciplines.length).padStart(2, "0")}</span>
        <h2>${d.title}</h2>
        ${d.mode ? `<span class="chip acn">${d.mode}</span>` : ""}
        <button class="link" id="back-grid" style="margin-left:auto">all disciplines</button>
      </div>
      <p class="claim">${esc(d.claim || "")}</p>
      ${(d.evidence || []).length ? `<div class="evidence"><span class="k">In the repo</span>
        ${d.evidence.map((e) => `<span class="chip mono">${esc(e)}</span>`).join("")}</div>` : ""}
      <div id="dbody"></div>`;

    el("back-grid").addEventListener("click", () => go(state.pillar.id));

    const render = PANELS[state.pillar.id + "/" + d.id];
    if (render) {
      render(el("dbody"), { pillar: state.pillar, discipline: d, state });
    } else {
      el("dbody").innerHTML =
        `<div class="card"><h3>Not wired yet</h3>
         <p class="sub">This discipline has no panel in the console yet.</p></div>`;
    }
  }

  /* ---- routing --------------------------------------------------------- */

  function go(pillarId, disciplineId) {
    location.hash = "#/" + pillarId + (disciplineId ? "/" + disciplineId : "");
  }

  function route() {
    const parts = (location.hash || "").replace(/^#\/?/, "").split("/").filter(Boolean);
    const pillar = state.pillars.find((p) => p.id === parts[0]) || state.pillars[0];
    state.pillar = pillar;
    state.discipline = pillar.disciplines.some((d) => d.id === parts[1]) ? parts[1] : null;
    renderNav();
    renderStrip();
    renderHero();
    renderGrid();
    renderFooter();
    renderPanel();
    window.scrollTo({ top: 0 });
  }

  async function boot() {
    state.pillars = (await (await api("/api/pillars")).json()).pillars;
    try {
      const s = await (await api("/api/state")).json();
      state.connected = !!s.connected;
      state.serverState = s;
      el("brand-sub").textContent = "Accenture  |  reference build: " + s.product;
    } catch (e) {
      state.connected = false;
    }
    el("conn-dot").className = "dot" + (state.connected ? " live" : "");
    el("conn-text").textContent = state.connected ? "live" : "replay only";
    window.addEventListener("hashchange", route);
    route();
  }

  // Panels register from scripts loaded after this one. Booting before they
  // have all run let a slow script lose the race, and the first route showed
  // "Not wired yet". DOMContentLoaded fires only after every script has run.
  document.addEventListener("DOMContentLoaded", boot);
  return { api, esc, el, register, state, go };
})();
