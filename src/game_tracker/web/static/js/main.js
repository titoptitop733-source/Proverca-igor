// DROPZONE entry point: app shell, routing, global search, notifications, background sync.
import { openAddModal, resultRow, trackGame } from "./actions.js";
import { api } from "./api.js";
import { activityItem } from "./components.js";
import { esc, money } from "./format.js";
import { icon } from "./icons.js";
import { activeCurrency, prefs, savePref, state } from "./state.js";
import { openModal, toast } from "./ui.js";
import { renderDiscover } from "./views/discover.js";
import { renderGame } from "./views/game.js";
import { renderOverview } from "./views/overview.js";
import { renderWishlist } from "./views/wishlist.js";

const view = document.getElementById("view");
let currentRoute = { name: "overview", param: null, params: new URLSearchParams() };
let disposeView = null;
let routeCounter = 0;

// ------------------------------------------------------------------ navigation

const MAIN_NAV = [
  ["overview", "Overview", "overview"],
  ["discover", "Discover", "discover"],
  ["wishlist", "My wishlist", "heart"],
];
const LIBRARY_NAV = [
  ["wishlist?filter=all", "All tracked games", "gamepad", "all"],
  ["wishlist?filter=drops", "Price drops", "down", "drops"],
  ["wishlist?filter=lows", "Historical lows", "award", "lows"],
  ["wishlist?filter=reached", "Target reached", "target", "reached"],
];

function renderNav() {
  const link = ([path, label, iconName]) =>
    `<a class="nav-link" href="#/${path}" data-path="${path}">${icon(iconName)}<span>${label}</span></a>`;
  document.getElementById("nav-main").innerHTML = MAIN_NAV.map(link).join("");
  document.getElementById("nav-library").innerHTML = `<div class="nav-title">Library</div>`
    + LIBRARY_NAV.map(([path, label, iconName, key]) =>
      `<a class="nav-link" href="#/${path}" data-path="${path}">${icon(iconName)}<span>${label}</span>
        <span class="count num" data-count="${key}"></span></a>`).join("");
  document.getElementById("mobile-nav").innerHTML = MAIN_NAV.map(([path, label, iconName]) =>
    `<a href="#/${path}" data-path="${path}">${icon(iconName)}${label === "My wishlist" ? "Wishlist" : label}</a>`).join("")
    + `<a href="#" data-action="open-add">${icon("plus")}Track</a>`;
  document.getElementById("refresh-button").innerHTML = icon("refresh");
  document.getElementById("search-wrap").insertAdjacentHTML("afterbegin", icon("search"));
  document.getElementById("notify-button").innerHTML = icon("bell");
  document.getElementById("settings-button").innerHTML = icon("settings");
}

function highlightNav() {
  const filter = currentRoute.params.get("filter");
  const key = currentRoute.name === "wishlist" && filter ? `wishlist?filter=${filter}` : currentRoute.name;
  document.querySelectorAll("[data-path]").forEach((el) => {
    el.classList.toggle("active", el.dataset.path === key
      || (currentRoute.name === "game" && el.dataset.path === "wishlist"));
  });
}

function parseHash() {
  const [path, queryString = ""] = location.hash.replace(/^#\/?/, "").split("?");
  const [name, param] = path.split("/");
  return { name: name || "overview", param: param ?? null, params: new URLSearchParams(queryString) };
}

async function route() {
  currentRoute = parseHash();
  // Views check `active()` after every await, so a slow response from a page the user
  // already left never overwrites the page that is shown now.
  const token = ++routeCounter;
  const active = () => token === routeCounter;
  disposeView?.();
  disposeView = null;
  highlightNav();
  window.scrollTo({ top: 0 });
  const { name, param, params } = currentRoute;
  if (name === "discover") await renderDiscover(view, active);
  else if (name === "wishlist") await renderWishlist(view, params, active);
  else if (name === "game" && /^\d+$/.test(param ?? "")) {
    const dispose = await renderGame(view, Number(param), active);
    if (active()) disposeView = dispose ?? null;
    else dispose?.();
  } else await renderOverview(view, active);
}

// ------------------------------------------------------------------ sidebar, notifications

async function refreshSidebar() {
  try {
    const [dashboard, wishlist] = await Promise.all([api.dashboard(), api.wishlist()]);
    state.dashboard = dashboard;
    state.tracked = new Set(wishlist.map((g) => g.game_id));
    const counts = {
      all: wishlist.length,
      drops: wishlist.filter((g) => (g.price_change ?? 0) < 0).length,
      lows: wishlist.filter((g) => g.at_historical_low).length,
      reached: wishlist.filter((g) => g.target_status === "TARGET REACHED").length,
    };
    Object.entries(counts).forEach(([key, value]) => {
      const el = document.querySelector(`[data-count="${key}"]`);
      if (el) el.textContent = value || "";
    });
    const box = document.getElementById("savings-box");
    box.hidden = false;
    box.innerHTML = `<div class="label">Potential savings</div>
      <div class="value num">${money(dashboard.potential_savings)}</div>
      <div class="hint">Across ${dashboard.tracked_games} tracked game${dashboard.tracked_games === 1 ? "" : "s"}</div>`;
    const newest = dashboard.activity[0]?.at;
    const unseen = newest && (!prefs.lastSeenActivity || newest > prefs.lastSeenActivity);
    document.getElementById("notify-button").innerHTML = icon("bell") + (unseen ? `<i class="badge-dot"></i>` : "");
  } catch {
    /* sidebar is optional; the page itself shows connection errors */
  }
}

function setSync(status, text) {
  document.getElementById("sync-status").innerHTML = `<i class="sync-dot ${status}"></i><span>${esc(text)}</span>`;
}

async function syncPrices(force = false) {
  setSync("busy", "Checking prices…");
  try {
    const report = await api.update(force);
    const failed = Object.keys(report.failed).length;
    setSync(failed ? "error" : "ok",
      failed ? `${failed} game(s) failed to update` : `Prices checked ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`);
    report.alerts.forEach((alert) => toast(`${alert.title} reached your target: ${money(alert.price)}`, "success"));
    if (force && !report.updated && !failed) toast("Your wishlist is empty, nothing to update", "info");
    else if (force) toast(`Updated ${report.updated} game(s)`);
    if (report.updated) { await refreshSidebar(); if (currentRoute.name !== "discover") route(); }
  } catch (error) {
    setSync("error", "Price check failed");
    if (force) toast(error.message, "error");
  }
}

function toggleNotifications() {
  const root = document.getElementById("drawer-root");
  if (root.firstChild) { root.innerHTML = ""; return; }
  const events = state.dashboard?.activity ?? [];
  root.innerHTML = `<div class="drawer" role="dialog" aria-label="Price activity">
    <div class="panel-head"><h2>Price activity</h2>
      <button class="icon-button" data-close-drawer aria-label="Close">${icon("x")}</button></div>
    ${events.length ? `<ul class="activity">${events.map(activityItem).join("")}</ul>`
      : `<div class="panel-body muted">No price changes yet. You will see drops, new lows and reached targets here.</div>`}
  </div>`;
  if (events[0]) savePref("lastSeenActivity", events[0].at);
  refreshSidebar();
}

function openSettings() {
  const meta = state.meta;
  openModal({
    title: "Settings",
    render(body) {
      const rates = Object.entries(meta?.rates ?? { USD: 1 });
      body.innerHTML = `
        <div class="field"><label for="settings-currency">Display currency</label>
          <select class="select" id="settings-currency">${rates.map(([code]) =>
            `<option value="${code}" ${code === activeCurrency() ? "selected" : ""}>${code}</option>`).join("")}</select></div>
        <p class="muted" style="font-size:13px">Stores report prices in USD. ${meta?.rates_date
          ? `Converted with ECB reference rates from ${esc(meta.rates_date)}.` : "Exchange rates are unavailable, prices are shown in USD."}</p>
        <div class="facts" style="margin-top:8px">
          <div><div class="fact-label">Price checks</div><div class="fact-value">Every ${esc(meta?.snapshot_interval_hours ?? 6)} h</div></div>
          <div><div class="fact-label">Version</div><div class="fact-value">${esc(meta?.version ?? "—")}</div></div>
          <div><div class="fact-label">Prices</div><div class="fact-value">${esc(meta?.price_source ?? "CheapShark")}</div></div>
          <div><div class="fact-label">Exchange rates</div><div class="fact-value">${esc(meta?.rates_source ?? "Frankfurter")}</div></div>
        </div>
        <div style="display:flex;gap:8px;margin-top:18px;flex-wrap:wrap">
          <button class="btn" id="settings-force">${icon("refresh")}Check all prices now</button>
          <a class="btn btn-ghost" href="/docs" target="_blank" rel="noopener">${icon("external")}API documentation</a></div>`;
      body.querySelector("#settings-currency").addEventListener("change", (e) => setCurrency(e.target.value));
      body.querySelector("#settings-force").addEventListener("click", () => syncPrices(true));
    },
  });
}

function setCurrency(code) {
  savePref("currency", code);
  fillCurrencySelect();
  refreshSidebar();
  route();
}

function fillCurrencySelect() {
  const select = document.getElementById("currency-select");
  const codes = Object.keys(state.meta?.rates ?? { USD: 1 });
  select.innerHTML = codes.map((c) => `<option value="${c}" ${c === activeCurrency() ? "selected" : ""}>${c}</option>`).join("");
}

// ------------------------------------------------------------------ global search

function setupSearch() {
  const input = document.getElementById("global-search");
  const box = document.getElementById("search-results");
  let timer;
  let requestId = 0;

  const close = () => { box.hidden = true; };
  const run = async () => {
    const q = input.value.trim();
    if (q.length < 2) { close(); return; }
    const id = ++requestId;
    box.hidden = false;
    box.innerHTML = `<div class="skeleton" style="height:120px"></div>`;
    try {
      const items = await api.search(q, 8);
      if (id !== requestId) return;
      box.innerHTML = items.length ? items.map(resultRow).join("")
        : `<div class="panel-body muted">No games found for “${esc(q)}”.</div>`;
    } catch (error) {
      if (id === requestId) box.innerHTML = `<div class="panel-body negative">${esc(error.message)}</div>`;
    }
  };

  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(run, 300); });
  input.addEventListener("keydown", (e) => { if (e.key === "Escape") { input.value = ""; close(); input.blur(); } });
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); input.focus(); input.select(); }
  });
  document.addEventListener("click", (e) => { if (!e.target.closest("#search-wrap")) close(); });
  box.addEventListener("click", async (e) => {
    const add = e.target.closest("[data-add]");
    if (add) {
      add.disabled = true;
      const game = await trackGame(add.dataset.add);
      if (game) { close(); input.value = ""; location.hash = `#/game/${game.game_id}`; }
      else add.disabled = false;
    } else if (e.target.closest("a")) {
      close();
      input.value = "";
    }
  });
}

// ------------------------------------------------------------------ global events

function setupEvents() {
  document.addEventListener("click", async (event) => {
    if (event.target.closest("[data-close-drawer]")) { document.getElementById("drawer-root").innerHTML = ""; return; }
    const target = event.target.closest("[data-action]");
    if (!target) {
      if (!event.target.closest(".drawer, #notify-button")) document.getElementById("drawer-root").innerHTML = "";
      return;
    }
    const { action, id } = target.dataset;
    if (action === "open-game") {
      document.getElementById("drawer-root").innerHTML = "";
      location.hash = `#/game/${id}`;
    } else if (action === "open-add") {
      event.preventDefault();
      openAddModal();
    } else if (action === "track") {
      event.stopPropagation();
      target.disabled = true;
      if (await trackGame(id)) view.dispatchEvent(new Event("dropzone:tracked"));
      else target.disabled = false;
    } else if (action === "reload") {
      route();
    }
  });
  document.addEventListener("keydown", (event) => {
    const tile = event.target.closest?.("[data-action='open-game']");
    if (tile && event.key === "Enter") location.hash = `#/game/${tile.dataset.id}`;
  });
  // Broken artwork: try the CheapShark thumbnail, then show the title instead.
  document.addEventListener("error", (event) => {
    const img = event.target;
    if (!(img instanceof HTMLImageElement)) return;
    if (img.dataset.fallback && img.src !== img.dataset.fallback) {
      img.src = img.dataset.fallback;
      img.dataset.fallback = "";
    } else {
      const placeholder = document.createElement("div");
      placeholder.className = "cover-fallback";
      placeholder.textContent = img.dataset.title || "";
      img.replaceWith(placeholder);
    }
  }, true);

  document.addEventListener("dropzone:changed", (event) => {
    refreshSidebar();
    if (currentRoute.name === "discover") view.dispatchEvent(new Event("dropzone:tracked"));
    else if (!(currentRoute.name === "game" && event.detail.removed)) route();
  });
  document.getElementById("refresh-button").addEventListener("click", () => syncPrices(true));
  document.getElementById("notify-button").addEventListener("click", (e) => { e.stopPropagation(); toggleNotifications(); });
  document.getElementById("settings-button").addEventListener("click", openSettings);
  document.getElementById("currency-select").addEventListener("change", (e) => setCurrency(e.target.value));
  window.addEventListener("hashchange", route);
}

// ------------------------------------------------------------------ start

async function start() {
  renderNav();
  setupEvents();
  setupSearch();
  const [meta, stores] = await Promise.allSettled([api.meta(), api.stores()]);
  state.meta = meta.status === "fulfilled" ? meta.value : { rates: { USD: 1 } };
  state.stores = stores.status === "fulfilled" ? stores.value : [];
  if (meta.status === "rejected") toast("Server is not responding. Start it with: game-tracker web", "error");
  fillCurrencySelect();
  await refreshSidebar();
  await route();
  syncPrices(false);  // respects the snapshot interval, so it is cheap to run on every start
}

start();
