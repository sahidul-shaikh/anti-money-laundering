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

  // Quadrant start angles, clockwise from the top, as in the wireframe:
  // builds top left, improves top right, secures bottom right, runs bottom left.
  const QUADRANT = { builds: 270, improves: 0, secures: 90, runs: 180 };

  /** Line icons on a 24-unit grid, drawn in the current colour. */
  const ICON = {
    builds: '<path d="M8 6l-6 6 6 6M16 6l6 6-6 6M14 4l-4 16"/>',
    improves: '<path d="M3 17l6-6 4 4 8-8M15 7h6v6"/>',
    runs: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    secures: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
  };
  const icon = (id, size, x, y) => `<svg ${x == null ? "" : `x="${x}" y="${y}"`}
    width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor"
    stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${ICON[id] || ""}</svg>`;

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

  const polar = (cx, cy, r, a) => {
    const t = (a - 90) * Math.PI / 180;
    return [cx + r * Math.cos(t), cy + r * Math.sin(t)];
  };

  /** The capability wheel: four quadrants with their icons, the verbs on an inner band. */
  function ring(pillar) {
    const cx = 200, cy = 200;
    const seg = state.pillars.map((p) => {
      const a0 = QUADRANT[p.id], mid = a0 + 45;
      const on = p.id === pillar.id;
      const [ix, iy] = polar(cx, cy, 146, mid);
      const [vx, vy] = polar(cx, cy, 82, mid);
      return `<g class="quad" data-pillar="${p.id}"
          style="color:${on ? "var(--on-accent)" : "var(--acn-core)"}">
          <path d="${donut(cx, cy, 108, 194, a0 + 1, a0 + 89)}"
            style="fill:${on ? "var(--acn-purple)" : "var(--lav)"};stroke:var(--page)" stroke-width="5"/>
          ${icon(p.id, 40, ix - 20, iy - 20)}
        </g>
        <text x="${vx}" y="${vy}" text-anchor="middle" dominant-baseline="middle"
          font-size="11.5" letter-spacing="0.3" style="pointer-events:none">${p.verb}</text>`;
    }).join("");

    return `<div class="ring"><svg viewBox="0 0 400 400" role="img"
        aria-label="four capability quadrants">
      <circle cx="${cx}" cy="${cy}" r="106" style="fill:var(--panel-2);stroke:var(--lav-strong)"/>
      ${seg}
      <circle cx="${cx}" cy="${cy}" r="54" style="fill:var(--page);stroke:var(--lav-strong)" stroke-width="2"/>
      <circle class="orbit" cx="${cx}" cy="${cy}" r="59" fill="none"
        style="stroke:var(--acn-light)" stroke-width="1.5" stroke-dasharray="3 7"/>
      <text x="${cx}" y="${cy - 14}" text-anchor="middle" font-size="12"
        letter-spacing="1.6" style="fill:var(--acn-purple)">AI</text>
      <text x="${cx}" y="${cy + 3}" text-anchor="middle" font-size="12"
        letter-spacing="1.4">ENGINEERING</text>
      <text x="${cx}" y="${cy + 20}" text-anchor="middle" font-size="12"
        letter-spacing="1.4">FACTORY</text>
    </svg></div>`;
  }

  /* ---- chrome -------------------------------------------------------- */

  function renderNav() {
    el("pillar-nav").innerHTML = state.pillars.map((p) =>
      `<button class="pnav ${p.id === state.pillar.id && !state.home ? "on" : ""}"
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

  /* ---- home: every pillar on one screen ------------------------------- */

  // Tile order follows the wireframe: builds, improves / secures, runs.
  const HOME_ORDER = ["builds", "improves", "secures", "runs"];

  function renderHome() {
    const tiles = HOME_ORDER.map((id) => state.pillars.find((p) => p.id === id)).filter(Boolean);
    el("home").innerHTML = `
      <div class="home-left">
        <div class="eyebrow">AI for enterprise AI &nbsp;&middot;&nbsp; AML investigation use case</div>
        <h1 class="home-title">AI-for-AI closes the gap between innovation and outcomes</h1>
        <p class="promise">Apply AI across the entire AI lifecycle to industrialize the build,
          run, security and continuous improvement of AI systems at scale.</p>
        <div class="hero-actions">
          <button class="btn primary" data-go="builds">Start with AI builds AI &rarr;</button>
          <button class="btn" data-go="builds/delivery">Watch the factory deliver &rsaquo;</button>
        </div>
        <div class="card home-feature">
          <div class="eyebrow">Featured use case &nbsp;&middot;&nbsp; FinCrime AML investigation</div>
          <p>One alert, one traceable chain: financial activity &rarr; investigation &rarr;
            evidence-backed decision &rarr; evaluated AI improvement &rarr; approved release.</p>
        </div>
      </div>
      <div class="home-grid">
        ${tiles.map((p, i) => `<button class="home-tile ${i === 0 ? "lead" : ""}"
            data-go="${p.id}" ${p.status === "next" ? "disabled" : ""}>
          <span class="ic">${icon(p.id, 30)}</span>
          <span class="t">${esc(p.title)}</span>
          <span class="d">${p.disciplines.map((d) => esc(d.title)).join(" &middot; ")}</span>
        </button>`).join("")}
        <div class="home-hub">AI<br>ENGINEERING<br>FACTORY</div>
      </div>`;
    el("home").querySelectorAll("[data-go]").forEach((b) =>
      b.addEventListener("click", () => { location.hash = "#/" + b.dataset.go; }));
  }

  function renderHero() {
    const p = state.pillar;
    const nxt = state.pillars.find((x) => x.id === p.next);
    el("hero").innerHTML = `
      <div>
        <div class="eyebrow"><b>0${p.index}</b> / 04 &nbsp;&middot;&nbsp; Capability</div>
        <div class="hero-title">
          <div class="hero-mark">${icon(p.id, 36)}</div>
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
    const found = state.pillars.find((p) => p.id === parts[0]);
    // No pillar in the address: the home screen, with every pillar on it.
    state.home = !found;
    document.body.classList.toggle("at-home", state.home);
    const pillar = found || state.pillars[0];
    state.pillar = pillar;
    state.discipline = pillar.disciplines.some((d) => d.id === parts[1]) ? parts[1] : null;
    renderNav();
    if (state.home) {
      renderHome();
      window.scrollTo({ top: 0 });
      return;
    }
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
    el("brand").addEventListener("click", () => { location.hash = "#/"; });
    route();
  }

  // Panels register from scripts loaded after this one. Booting before they
  // have all run let a slow script lose the race, and the first route showed
  // "Not wired yet". DOMContentLoaded fires only after every script has run.
  document.addEventListener("DOMContentLoaded", boot);
  return { api, esc, el, register, state, go, icon };
})();
