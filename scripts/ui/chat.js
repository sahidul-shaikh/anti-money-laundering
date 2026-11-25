/* Shared helpers for panels that work on a pasted alert, exposed as
   window.FactoryChat: sample alerts, a reveal link, the status line. The
   Routing panel itself lives in panels.js. */

(function () {
  const F = window.Factory;
  if (!F) return;
  const { api, esc } = F;

  const SAMPLES = [
    ["alert_11368.txt", "11368 - real alert, individual"],
    ["alert_11366.txt", "11366 - real alert, structured withdrawals"],
    ["alert_11391.txt", "11391 - real alert, business"],
    ["alert_S90001.txt", "S90001 - a large receipt, retained"],
  ];

  const TEXTAREA = "width:100%;background:var(--code-bg);color:var(--code-ink);"
    + "border:1px solid var(--line);border-radius:9px;padding:12px;"
    + "font-family:var(--mono);font-size:11.5px;resize:vertical";

  const say = (host, text, tone) => {
    const el = host.querySelector(".status");
    if (el) { el.textContent = text; el.className = "status sm " + (tone || "quiet"); }
  };

  /** A link that reveals a pane of text. */
  function reveal(host, label, text) {
    const id = "r" + Math.random().toString(36).slice(2, 9);
    setTimeout(() => {
      const btn = host.querySelector(`[data-rv="${id}"]`);
      const pane = host.querySelector("#" + id);
      if (!btn || !pane) return;
      pane.textContent = text;
      btn.addEventListener("click", () => {
        const open = pane.style.display !== "none";
        pane.style.display = open ? "none" : "block";
        btn.textContent = (open ? "" : "hide ") + label;
      });
    }, 0);
    return `<button class="link" data-rv="${id}">${esc(label)}</button>
      <pre class="feed" id="${id}" style="display:none;margin-top:8px"></pre>`;
  }

  const sampleSelect = (id) => `<select id="${id}">`
    + SAMPLES.map(([f, l]) => `<option value="${f}">${esc(l)}</option>`).join("")
    + "</select>";

  async function loadSample(api_, name) {
    const r = await (await api_("/api/demo/" + name)).json();
    return r.body || "";
  }

  window.FactoryChat = { reveal, sampleSelect, loadSample, TEXTAREA, say };
})();
