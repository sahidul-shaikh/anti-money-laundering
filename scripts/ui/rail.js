/* The delivery rail: the current task's chain, on every page.

   Stations come from /api/delivery, which reads git, GitHub and the run
   records when asked. Nothing advances on a timer: the only thing the clock
   does here is count elapsed time since a real timestamp. Polls every 5 s
   while a station is running or waiting for a human, every 30 s otherwise. */

(function () {
  const F = window.Factory;
  if (!F) return;
  const { api, esc } = F;

  const elapsed = (since) => {
    if (!since) return "";
    const s = Math.max(0, Math.floor((Date.now() - Date.parse(since)) / 1000));
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), r = s % 60;
    return h ? `${h}h ${m}m` : `${m}:${String(r).padStart(2, "0")}`;
  };

  /** One station as HTML; shared by the rail and the Delivery panel. */
  const stationHtml = (s) => {
    const live = s.state === "running" || s.state === "waiting";
    const detail = esc(s.detail || "");
    return `<div class="st st-${s.state}">
      <span class="st-ic"></span>
      <div class="st-body">
        <div class="st-label">${esc(s.label)}${live && s.since
          ? ` <span class="st-time" data-since="${esc(s.since)}">${elapsed(s.since)}</span>` : ""}</div>
        ${detail ? `<div class="st-detail">${s.link
          ? `<a href="${esc(s.link)}" target="_blank" rel="noopener">${detail}</a>` : detail}</div>` : ""}
      </div></div>`;
  };

  const chainHtml = (chain) => chain.map(stationHtml).join("");

  let snapshot = null;
  let timer = null;
  let chosen = "";
  try { chosen = localStorage.getItem("rail-task") || ""; } catch (e) { /* storage blocked */ }

  function paint() {
    const rail = document.getElementById("rail");
    if (!rail || !snapshot) return;
    const task = snapshot.tasks.find((t) => t.id === snapshot.focus);
    const pick = rail.querySelector("#rail-pick");
    pick.innerHTML = snapshot.tasks.map((t) =>
      `<option value="${esc(t.id)}" ${t.id === snapshot.focus ? "selected" : ""}>${esc(t.id)}</option>`).join("");
    rail.querySelector(".rail-body").innerHTML = task ? `
      <a class="rail-task" href="#/builds/delivery">${esc(task.id)}
        <span>${esc(task.title)}</span></a>
      <div class="rail-chain">${chainHtml(task.chain)}</div>`
      : `<p class="sub">No tasks yet.</p>`;
  }

  /** Follow a task: the rail shows its chain, and a live run is shown against it. */
  function setFocus(id) {
    chosen = id || "";
    try { localStorage.setItem("rail-task", chosen); } catch (e) { /* storage blocked */ }
    refresh();
  }

  async function refresh() {
    try {
      const q = chosen ? `?focus=${encodeURIComponent(chosen)}` : "";
      snapshot = await (await api("/api/delivery" + q)).json();
      paint();
      document.dispatchEvent(new CustomEvent("delivery", { detail: snapshot }));
    } catch (e) {
      const body = document.querySelector("#rail .rail-body");
      if (body) body.innerHTML = `<p class="sub">Delivery state unavailable: ${esc(String(e))}</p>`;
    }
    const task = snapshot && snapshot.tasks.find((t) => t.id === snapshot.focus);
    const busy = task && task.chain.some((s) => s.state === "running" || s.state === "waiting");
    clearTimeout(timer);
    timer = setTimeout(refresh, busy ? 5000 : 30000);
  }

  function mount() {
    const rail = document.createElement("aside");
    rail.id = "rail";
    rail.innerHTML = `<div class="rail-head"><span>Delivery</span>
      <select id="rail-pick" title="the task this rail follows"></select>
      <button class="link" id="rail-toggle" title="hide or show the delivery rail">hide</button></div>
      <div class="rail-body"><p class="sub">reading git and GitHub...</p></div>`;
    document.body.appendChild(rail);
    let closed = false;
    try { closed = localStorage.getItem("rail-closed") === "1"; } catch (e) { /* storage blocked */ }
    const apply = () => {
      document.body.classList.toggle("rail-closed", closed);
      document.getElementById("rail-toggle").textContent = closed ? "show" : "hide";
    };
    document.getElementById("rail-pick").addEventListener("change", (e) => setFocus(e.target.value));
    document.getElementById("rail-toggle").addEventListener("click", () => {
      closed = !closed;
      try { localStorage.setItem("rail-closed", closed ? "1" : "0"); } catch (e) { /* storage blocked */ }
      apply();
    });
    apply();
    setInterval(() => document.querySelectorAll(".st-time[data-since]").forEach((el) => {
      el.textContent = elapsed(el.dataset.since);
    }), 1000);
    refresh();
  }

  window.FactoryRail = { chainHtml, refresh, setFocus, current: () => snapshot };
  mount();
})();
