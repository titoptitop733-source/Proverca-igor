import { api } from "../api.js";
import { openTargetModal, removeGame } from "../actions.js";
import { sparkline } from "../charts.js";
import { adviceBadge, cover, gameTile, statusLabel, trendIcon } from "../components.js";
import { esc, money } from "../format.js";
import { icon } from "../icons.js";
import { prefs, savePref } from "../state.js";
import { emptyState, errorState } from "../ui.js";

const FILTERS = {
  all: { label: "All games", test: () => true },
  drops: { label: "Price drops", test: (g) => (g.price_change ?? 0) < 0 },
  lows: { label: "Historical lows", test: (g) => g.at_historical_low },
  sale: { label: "On sale", test: (g) => (g.discount_percent ?? 0) > 0 },
  reached: { label: "Target reached", test: (g) => g.target_status === "TARGET REACHED" },
};

const ADVICE_ORDER = { BUY_NOW: 0, GOOD_DEAL: 1, WAIT: 2, NO_DATA: 3 };
const SORTS = {
  title: { label: "Name", compare: (a, b) => a.title.localeCompare(b.title) },
  price: { label: "Lowest price", compare: (a, b) => (a.current_price ?? Infinity) - (b.current_price ?? Infinity) },
  discount: { label: "Biggest discount", compare: (a, b) => (b.discount_percent ?? 0) - (a.discount_percent ?? 0) },
  target: { label: "Closest to target", compare: (a, b) => targetDistance(a) - targetDistance(b) },
  advice: { label: "Best time to buy", compare: (a, b) => ADVICE_ORDER[a.advice.verdict] - ADVICE_ORDER[b.advice.verdict] },
};

function targetDistance(game) {
  if (game.target_price === null || game.current_price === null) return Infinity;
  return (game.current_price - game.target_price) / (game.target_price || 1);
}

function distanceText(game) {
  if (game.target_price === null || game.current_price === null) return `<span class="muted">—</span>`;
  const diff = game.current_price - game.target_price;
  return diff <= 0.009 ? `<span class="lime">Reached</span>` : `<span class="num">${money(diff)} away</span>`;
}

function row(game) {
  return `<tr class="clickable" data-action="open-game" data-id="${game.game_id}">
    <td><div class="game-cell"><div class="result-thumb">${cover(game.cover_url, game.thumb_url, game.title)}</div>
      <div><div class="name">${esc(game.title)}</div><div class="muted">${esc(game.store_name ?? "No offers")}</div></div></div></td>
    <td class="right num"><strong>${money(game.current_price)}</strong></td>
    <td class="right num hide-mobile ${game.discount_percent > 0 ? "strike" : "muted"}">${money(game.retail_price)}</td>
    <td class="right num">${game.discount_percent > 0 ? `<span class="lime">-${Math.round(game.discount_percent)}%</span>` : `<span class="muted">0%</span>`}</td>
    <td class="right num hide-mobile">${money(game.target_price)}</td>
    <td class="right hide-mobile">${distanceText(game)}</td>
    <td class="hide-mobile"><div style="display:flex;align-items:center;gap:6px">${sparkline(game.sparkline, 80, 24)}${trendIcon(game.price_change)}</div></td>
    <td>${statusLabel(game.target_status)}</td>
    <td class="hide-mobile">${adviceBadge(game.advice)}</td>
    <td class="right"><div style="display:inline-flex;gap:6px">
      <button class="icon-button" data-row-action="target" data-id="${game.game_id}" title="Set target" aria-label="Set target for ${esc(game.title)}">${icon("target")}</button>
      <button class="icon-button" data-row-action="remove" data-id="${game.game_id}" title="Remove" aria-label="Remove ${esc(game.title)}">${icon("trash")}</button>
    </div></td>
  </tr>`;
}

export async function renderWishlist(view, params, active = () => true) {
  const ui = { query: "", sort: "advice", filter: FILTERS[params.get("filter")] ? params.get("filter") : "all" };
  view.innerHTML = `
    <div class="page-head"><div><div class="eyebrow">Library</div><h1>My wishlist</h1>
      <p class="subtitle">Every tracked game with its best price, target and buying advice.</p></div>
      <button class="btn btn-primary" data-action="open-add">${icon("plus")}Track a game</button></div>
    <div id="wl-body"><div class="skeleton" style="height:320px"></div></div>`;

  let games;
  try {
    games = await api.wishlist();
  } catch (error) {
    if (active()) view.querySelector("#wl-body").innerHTML = errorState(error, "reload");
    return;
  }
  if (!active()) return;
  const body = view.querySelector("#wl-body");
  if (!games.length) {
    body.innerHTML = emptyState("heart", "Nothing tracked yet",
      "Add games you want to buy. DROPZONE records their prices and tells you when it is a good time to buy.",
      `<button class="btn btn-primary" data-action="open-add">${icon("plus")}Track your first game</button>`);
    return;
  }

  body.innerHTML = `
    <div class="toolbar">
      <div class="field grow"><label for="wl-search">Search wishlist</label>
        <input class="input" id="wl-search" type="search" placeholder="Filter by title"></div>
      <div class="field"><label for="wl-sort">Sort by</label>
        <select class="select" id="wl-sort">${Object.entries(SORTS).map(([key, s]) =>
          `<option value="${key}" ${key === ui.sort ? "selected" : ""}>${s.label}</option>`).join("")}</select></div>
      <div class="segmented" role="group" aria-label="Layout">
        <button data-layout="list" aria-label="List view">${icon("list")}</button>
        <button data-layout="grid" aria-label="Grid view">${icon("grid")}</button></div>
    </div>
    <div class="chips" id="wl-chips"></div>
    <div class="result-count" id="wl-count"></div>
    <div id="wl-list"></div>`;

  const draw = () => {
    const filtered = games
      .filter(FILTERS[ui.filter].test)
      .filter((g) => g.title.toLowerCase().includes(ui.query.toLowerCase()))
      .sort((a, b) => SORTS[ui.sort].compare(a, b) || a.title.localeCompare(b.title));

    body.querySelector("#wl-chips").innerHTML = Object.entries(FILTERS).map(([key, f]) =>
      `<button class="chip ${key === ui.filter ? "active" : ""}" data-filter="${key}">${f.label}
        <span class="muted">${games.filter(f.test).length}</span></button>`).join("");
    body.querySelectorAll("[data-layout]").forEach((b) => b.classList.toggle("active", b.dataset.layout === prefs.wishlistView));
    body.querySelector("#wl-count").textContent = `${filtered.length} of ${games.length} games`;

    const list = body.querySelector("#wl-list");
    if (!filtered.length) {
      list.innerHTML = emptyState("search", "No games match", "Try another filter or clear the search.");
    } else if (prefs.wishlistView === "grid") {
      list.innerHTML = `<div class="grid grid-3">${filtered.map(gameTile).join("")}</div>`;
    } else {
      list.innerHTML = `<div class="table-wrap"><table>
        <thead><tr><th>Game</th><th class="right">Price</th><th class="right hide-mobile">Original</th>
          <th class="right">Discount</th><th class="right hide-mobile">Target</th><th class="right hide-mobile">To target</th>
          <th class="hide-mobile">Trend</th><th>Status</th><th class="hide-mobile">Advice</th><th class="right"><span class="visually-hidden">Actions</span></th></tr></thead>
        <tbody>${filtered.map(row).join("")}</tbody></table></div>`;
    }
  };

  body.querySelector("#wl-search").addEventListener("input", (e) => { ui.query = e.target.value; draw(); });
  body.querySelector("#wl-sort").addEventListener("change", (e) => { ui.sort = e.target.value; draw(); });
  body.addEventListener("click", async (event) => {
    const chip = event.target.closest("[data-filter]");
    const layout = event.target.closest("[data-layout]");
    const action = event.target.closest("[data-row-action]");
    if (chip) { ui.filter = chip.dataset.filter; draw(); }
    if (layout) { savePref("wishlistView", layout.dataset.layout); draw(); }
    if (action) {
      event.stopPropagation();  // do not open the game detail
      const game = games.find((g) => g.game_id === Number(action.dataset.id));
      if (action.dataset.rowAction === "target") openTargetModal(game);
      if (action.dataset.rowAction === "remove") await removeGame(game.game_id, game.title);
    }
  });
  draw();
}
