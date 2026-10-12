(() => {
  // Theme toggle (remembered per viewer).
  const toggle = document.getElementById("theme-toggle");
  if (toggle) toggle.addEventListener("click", () => {
    const root = document.documentElement;
    const dark = root.dataset.theme
      ? root.dataset.theme === "dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
    root.dataset.theme = dark ? "light" : "dark";
    try { localStorage.setItem("ssr-theme", root.dataset.theme); } catch (e) {}
  });

  // Tooltips on level cells.
  const tip = document.getElementById("tooltip");
  const show = (el, x, y) => {
    tip.replaceChildren();
    for (const [cls, key] of [["t-title", "tipTitle"], ["t-level", "tipLevel"], ["t-body", "tipBody"]]) {
      if (!el.dataset[key]) continue;
      const d = document.createElement("div");
      d.className = cls;
      d.textContent = el.dataset[key];
      tip.append(d);
    }
    tip.hidden = false;
    const r = tip.getBoundingClientRect();
    tip.style.left = Math.min(x + 14, innerWidth - r.width - 8) + "px";
    tip.style.top = (y + 14 + r.height > innerHeight ? y - r.height - 10 : y + 14) + "px";
  };
  document.addEventListener("mouseover", (e) => {
    const el = e.target.closest("[data-tip-title]");
    if (el) show(el, e.clientX, e.clientY);
  });
  document.addEventListener("mousemove", (e) => {
    const el = e.target.closest("[data-tip-title]");
    if (el && !tip.hidden) show(el, e.clientX, e.clientY);
  });
  document.addEventListener("mouseout", (e) => {
    if (e.target.closest("[data-tip-title]")) tip.hidden = true;
  });
  document.addEventListener("focusin", (e) => {
    const el = e.target.closest("[data-tip-title]");
    if (el) { const r = el.getBoundingClientRect(); show(el, r.right, r.bottom); }
  });
  document.addEventListener("focusout", () => { tip.hidden = true; });

  // Copy the action plan as Markdown.
  document.querySelectorAll("[data-copy]").forEach((b) => b.addEventListener("click", async () => {
    const text = document.getElementById(b.dataset.copy).value;
    try { await navigator.clipboard.writeText(text); b.textContent = "Copied"; }
    catch (e) { b.textContent = "Copy failed: use the download link"; }
  }));

  // Overview matrix: filters, view switch, sorting.
  const table = document.getElementById("matrix");
  if (!table) return;
  const body = table.tBodies[0];
  const dom = document.getElementById("f-domain");
  const role = document.getElementById("f-role");
  const view = document.getElementById("f-view");
  const prefs = (() => { try { return JSON.parse(localStorage.getItem("ssr-overview") || "{}"); } catch (e) { return {}; } })();
  if (prefs.view) view.value = prefs.view;
  const apply = () => {
    table.dataset.view = view.value;
    for (const tr of body.rows) {
      tr.hidden = (dom.value && tr.dataset.domain !== dom.value) || (role.value && tr.dataset.role !== role.value);
    }
    try { localStorage.setItem("ssr-overview", JSON.stringify({ view: view.value })); } catch (e) {}
  };
  [dom, role, view].forEach((s) => s.addEventListener("change", apply));
  apply();

  let sortKey = "overall", desc = true;
  table.querySelectorAll("th.sortable").forEach((th) => {
    th.addEventListener("click", (e) => {
      if (e.target.closest("a")) return;
      const k = th.dataset.sort;
      desc = k === sortKey ? !desc : k !== "name";
      sortKey = k;
      const val = (tr) => {
        if (k === "name") return tr.dataset.name;
        if (k === "overall") return +tr.dataset.overall;
        if (k.startsWith("cat-")) return +tr.dataset[k.replace(/-([a-z])/g, (_, c) => c.toUpperCase())];
        const td = tr.querySelector(`td[data-k="${k}"]`);
        return td ? +td.dataset.v : -1;
      };
      const rows = [...body.rows].sort((a, b) => {
        const x = val(a), y = val(b);
        return (x < y ? -1 : x > y ? 1 : 0) * (desc ? -1 : 1);
      });
      body.append(...rows);
      table.querySelectorAll("th.sortable").forEach((h) => h.removeAttribute("aria-sort"));
      th.setAttribute("aria-sort", desc ? "descending" : "ascending");
    });
  });
})();
