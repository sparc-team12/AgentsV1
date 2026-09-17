/* comp-web-client — no build step, no framework. Plain DOM against /api/v1. */

const $ = (sel) => document.querySelector(sel);
const el = (tag, attrs = {}, ...kids) => {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "html") node.innerHTML = v;
    else if (v !== null && v !== undefined) node.setAttribute(k, v);
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return node;
};

const state = { listing: null, selected: null };

async function api(path, options = {}) {
  const res = await fetch(`/api/v1${path}`, {
    headers: { "content-type": "application/json" },
    ...options,
  });
  if (res.status === 401) { showLogin(); throw new Error("unauthenticated"); }
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || res.statusText);
  return body;
}

/* ---------- auth ---------- */

function showLogin() { $("#login").hidden = false; $("#app").hidden = true; }
function showApp(user) {
  $("#login").hidden = true;
  $("#app").hidden = false;
  $("#who").textContent = `${user.name} (${user.persona})`;
}

$("#login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const err = $("#login-error");
  err.hidden = true;
  try {
    const { user } = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: $("#email").value, password: $("#password").value }),
    });
    showApp(user);
    await loadDashboard();
  } catch (e) {
    err.textContent = e.message;
    err.hidden = false;
  }
});

$("#logout").addEventListener("click", async () => {
  await api("/auth/logout", { method: "POST" });
  showLogin();
});

/* ---------- navigation ---------- */

document.querySelectorAll(".topbar .tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".topbar .tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    const view = tab.dataset.view;
    $("#view-dashboard").hidden = view !== "dashboard";
    $("#view-setup").hidden = view !== "setup";
    if (view === "setup") loadSetup();
  });
});

/* ---------- dashboard (REQ-023 to REQ-027, REQ-034) ---------- */

async function loadDashboard() {
  const listing = await api("/risks");
  renderListing(listing);
  renderSuggestions();
}

function renderListing(listing) {
  state.listing = listing;
  $("#exposure").textContent = listing.total_waste_exposure;
  $("#exposure-note").textContent =
    `Includes ${listing.suppressed_count} warning(s) hidden by the materiality threshold.`;
  $("#asof").textContent = listing.as_of;
  $("#horizon").textContent = `${listing.horizon_days}-day forward horizon`;
  if (document.activeElement !== $("#threshold")) {
    $("#threshold").value = (listing.materiality_threshold_paise / 100).toFixed(0);
  }

  const body = $("#risk-table tbody");
  body.replaceChildren();
  $("#risk-empty").hidden = listing.rows.length > 0;

  listing.rows.forEach((row) => {
    const tr = el("tr", { "data-id": row.ingredient_id },
      el("td", {}, row.ingredient_name),
      el("td", {}, el("span", { class: "type" }, row.risk_type)),
      // REQ-034: the band is a text label, colour is secondary
      el("td", {}, el("span", { class: `sev sev-${row.severity}` }, row.severity)),
      el("td", {}, row.order_by_date
        ? `${row.order_by_date}${row.days_until_order_by !== null ? ` (${row.days_until_order_by}d)` : ""}`
        : "—"),
      el("td", { class: "num" }, row.waste_cost || "—"),
    );
    tr.addEventListener("click", () => selectIngredient(row.ingredient_id));
    body.append(tr);
  });

  if (state.selected) highlightRow(state.selected);
}

function highlightRow(id) {
  document.querySelectorAll("#risk-table tbody tr").forEach((tr) => {
    tr.classList.toggle("selected", tr.dataset.id === id);
  });
}

$("#apply-threshold").addEventListener("click", async () => {
  const rupees = Number($("#threshold").value || 0);
  const listing = await api("/config/materiality-threshold", {
    method: "PUT",
    body: JSON.stringify({ materiality_threshold_paise: Math.round(rupees * 100) }),
  });
  renderListing(listing);
});

/* ---------- ingredient detail + purchase order ---------- */

async function selectIngredient(id) {
  state.selected = id;
  highlightRow(id);
  const detail = await api(`/risks/${id}`);
  const ing = detail.ingredient;
  const panel = $("#detail");
  panel.replaceChildren();

  panel.append(el("h2", {}, ing.name));
  panel.append(el("dl", {},
    el("dt", {}, "On hand"), el("dd", {}, `${ing.quantity_on_hand ?? "—"} ${ing.unit}`),
    el("dt", {}, "Unit cost"), el("dd", {}, ing.unit_cost),
    el("dt", {}, "Supplier"), el("dd", {}, ing.supplier_name ?? "— not mapped —"),
    el("dt", {}, "Lead time"), el("dd", {}, ing.lead_time_days !== null ? `${ing.lead_time_days} days` : "—"),
    el("dt", {}, "Safety margin"), el("dd", {}, ing.safety_margin_days !== null ? `${ing.safety_margin_days} days` : "— not configured —"),
    ing.use_by_date ? el("dt", {}, "Use by") : null,
    ing.use_by_date ? el("dd", {}, ing.use_by_date) : null,
  ));

  if (detail.stockout) {
    const s = detail.stockout;
    const section = el("div", { class: "section" },
      el("h2", {}, "Stockout risk ", el("span", { class: `sev sev-${s.severity}` }, s.severity)),
      el("dl", {},
        el("dt", {}, "Runs out"), el("dd", {}, s.projected_stockout_date),
        el("dt", {}, "Order by"), el("dd", {}, s.order_by_date ?? "— not computed —"),
        el("dt", {}, "Order qty"), el("dd", {}, s.suggested_order_quantity ? `${s.suggested_order_quantity} ${ing.unit}` : "—"),
      ),
      s.data_gap ? el("p", { class: "gap" }, s.data_gap) : null,
      traceBlock(s.trace),
      el("button", { class: "ghost" }, "Draft purchase order"),
    );
    section.querySelector("button").addEventListener("click", () => draftPO(id, section));
    panel.append(section);
  }

  if (detail.spoilage) {
    const s = detail.spoilage;
    panel.append(el("div", { class: "section" },
      el("h2", {}, "Spoilage risk ", el("span", { class: `sev sev-${s.severity}` }, s.severity)),
      el("dl", {},
        el("dt", {}, "Use by"), el("dd", {}, s.use_by_date),
        el("dt", {}, "Used by then"), el("dd", {}, `${s.projected_consumption_by_use_by} ${ing.unit}`),
        el("dt", {}, "Unconsumed"), el("dd", {}, `${s.unconsumed_quantity} ${ing.unit}`),
        el("dt", {}, "Waste cost"), el("dd", {}, s.waste_cost),
      ),
      s.suppressed ? el("p", { class: "muted" }, "Below the materiality threshold — hidden from the list, still counted in total exposure.") : null,
      traceBlock(s.trace),
    ));
  }

  panel.append(el("div", { class: "section" },
    el("h2", {}, "Demand"),
    el("dl", {}, el("dt", {}, "Projected"), el("dd", {}, `${detail.demand.total} ${ing.unit}`)),
    el("table", {}, el("tbody", {},
      detail.demand.contributions.slice(0, 6).map((c) =>
        el("tr", {}, el("td", {}, c.dish_name), el("td", { class: "num" }, `${c.share_pct}%`))),
    )),
    traceBlock(detail.demand.trace),
  ));

  const ask = el("button", { class: "ghost" }, "Ask why this is flagged");
  ask.addEventListener("click", () => {
    $("#chat-input").value = `why is ${ing.name} flagged?`;
    $("#chat-form").requestSubmit();
  });
  panel.append(el("div", { class: "section" }, ask));
}

function traceBlock(trace) {
  if (!trace || !trace.length) return null;
  return el("details", { class: "trace" },
    el("summary", {}, "How this was calculated"),
    el("table", {}, el("tbody", {},
      trace.map((t) => el("tr", {},
        el("td", {}, t.label),
        el("td", {}, t.value),
        el("td", { class: "src" }, t.source))),
    )));
}

async function draftPO(id, container) {
  const po = await api(`/purchase-orders/draft?ingredient_id=${encodeURIComponent(id)}`, { method: "POST" });
  container.querySelector("pre.po")?.remove();
  container.querySelector(".po-note")?.remove();
  const box = el("pre", { class: "po", contenteditable: "true" }, po.body_text);
  container.append(box, el("p", { class: "muted po-note" }, po.note));
}

/* ---------- chat agent (REQ-013 to REQ-020, REQ-036) ---------- */

function renderSuggestions() {
  const box = $("#suggestions");
  box.replaceChildren();
  const first = state.listing?.rows?.[0];
  const prompts = [
    first ? `why is ${first.ingredient_name} flagged?` : "why is Prawns flagged?",
    "what if we add a 50-cover banquet of Chicken Dum Biryani next Saturday?",
    "what if we add 30 covers of Butter Chicken this weekend?",
  ];
  prompts.forEach((p) => {
    const b = el("button", { type: "button" }, p);
    b.addEventListener("click", () => { $("#chat-input").value = p; $("#chat-form").requestSubmit(); });
    box.append(b);
  });
}

$("#chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = $("#chat-input").value.trim();
  if (!question) return;
  const turn = el("div", { class: "turn" }, el("p", { class: "q" }, question), el("p", { class: "a" }, "…"));
  $("#chat-log").prepend(turn);
  $("#chat-input").value = "";

  try {
    const res = await api("/chat", {
      method: "POST",
      body: JSON.stringify({ question, ingredient_id: state.selected }),
    });
    turn.classList.toggle("unrecognised", res.intent === "unrecognised");
    turn.querySelector(".a").textContent = res.answer;
    if (res.figures?.length) {
      turn.append(el("div", { class: "figures" },
        res.figures.map((f) => el("span", { class: "chip" }, `${f.label}: ${f.value}`))));
    }
    // REQ-018/019/020: the scenario-adjusted view, clearly marked as transient
    if (res.intent === "what_if" && res.listing) {
      renderListing(res.listing);
      turn.append(el("p", { class: "muted" },
        "Dashboard above now shows the scenario-adjusted view. Reload to return to real data — scenarios are never saved."));
    }
  } catch (err) {
    turn.querySelector(".a").textContent = err.message;
  }
});

/* ---------- data setup (REQ-037 to REQ-041) ---------- */

async function loadSetup() {
  const status = await api("/setup/status");
  const grid = $("#setup-status");
  grid.replaceChildren();
  status.categories.forEach((c) => {
    grid.append(el("div", { class: `setup-card ${c.loaded ? "loaded" : "unloaded"}` },
      el("div", {}, el("strong", {}, c.title)),
      el("div", { class: "muted" }, c.loaded ? `Loaded — ${c.record_count} ${c.record_label}` : "Not loaded"),
      c.gap_count ? el("div", { class: "gap" }, `${c.gap_count} gap(s) flagged`) : null,
    ));
  });
  loadSetupTab("menu");
}

document.querySelectorAll("[data-setup]").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll("[data-setup]").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    loadSetupTab(tab.dataset.setup);
  });
});

async function loadSetupTab(key) {
  const body = $("#setup-body");
  body.replaceChildren(el("p", { class: "muted" }, "Loading…"));
  const data = await api(`/setup/${key}`);
  body.replaceChildren(el("div", { class: "scroll" }, buildSetupTable(key, data)));
}

function buildSetupTable(key, data) {
  const head = (...cols) => el("thead", {}, el("tr", {}, cols.map((c) => el("th", {}, c))));

  if (key === "menu") {
    return el("table", {}, head("Dish", "Ingredient", "Qty / serving", "Unit"),
      el("tbody", {}, data.dishes.flatMap((d) =>
        d.recipe.map((r, i) => el("tr", {},
          el("td", {}, i === 0 ? d.name : ""),
          el("td", {}, r.ingredient_name),
          el("td", { class: "num" }, r.quantity_per_serving),
          el("td", {}, r.unit),
        )))));
  }
  if (key === "ingredients") {
    return el("table", {}, head("Ingredient", "Unit", "Unit cost", "Perishable", "Shelf life", "Supplier", "Lead time", "Safety margin"),
      el("tbody", {}, data.ingredients.map((i) => el("tr", {},
        el("td", {}, i.name),
        el("td", {}, i.unit),
        el("td", { class: "num" }, i.unit_cost),
        el("td", {}, i.perishable ? "yes" : "no"),
        el("td", { class: "num" }, i.shelf_life_days ?? "—"),
        el("td", {}, i.supplier_name ?? el("span", { class: "gap" }, "not mapped")),
        el("td", { class: "num" }, i.lead_time_days ?? "—"),
        el("td", { class: "num" }, i.safety_margin_days ?? el("span", { class: "gap" }, "missing")),
      ))));
  }
  if (key === "stock") {
    return el("div", {},
      el("p", { class: "muted" }, `${data.note} Snapshot loaded ${data.snapshot_loaded_at ?? "—"}.`),
      el("table", {}, head("Ingredient", "Quantity", "Unit", "Use by"),
        el("tbody", {}, data.stock.map((s) => el("tr", {},
          el("td", {}, s.ingredient_name),
          el("td", { class: "num" }, s.quantity),
          el("td", {}, s.unit),
          el("td", {}, s.use_by_date ?? (s.gap ? el("span", { class: "gap" }, s.gap) : "—")),
        )))));
  }
  return el("table", {}, head("Dish", "Days of history", "From", "To", "Total units"),
    el("tbody", {}, data.dishes.map((d) => el("tr", {},
      el("td", {}, d.name),
      el("td", { class: "num" }, d.gap ? el("span", { class: "gap" }, d.days) : d.days),
      el("td", {}, d.first_date ?? "—"),
      el("td", {}, d.last_date ?? "—"),
      el("td", { class: "num" }, d.total_units),
    ))));
}

/* ---------- boot ---------- */

(async () => {
  try {
    const { user } = await api("/auth/me");
    showApp(user);
    await loadDashboard();
  } catch {
    showLogin();
  }
})();
