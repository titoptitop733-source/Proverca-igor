// User actions shared by several views. After a change a "dropzone:changed" event is fired
// so the current page and the sidebar can refresh themselves.
import { api } from "./api.js";
import { cover } from "./components.js";
import { currencySymbol, esc, fromUsd, money, toUsd } from "./format.js";
import { icon } from "./icons.js";
import { state } from "./state.js";
import { confirmDialog, openModal, toast } from "./ui.js";

export function notifyChanged(detail = {}) {
  document.dispatchEvent(new CustomEvent("dropzone:changed", { detail }));
}

export async function trackGame(gameId, targetPrice = null) {
  try {
    const game = await api.add(Number(gameId), targetPrice);
    state.tracked.add(game.game_id);
    toast(`Tracking ${game.title}`);
    notifyChanged({ added: game.game_id });
    return game;
  } catch (error) {
    if (error.status === 409) {
      toast("This game is already in your wishlist", "info");
      state.tracked.add(Number(gameId));
    } else {
      toast(error.message, "error");
    }
    return null;
  }
}

export async function removeGame(gameId, title) {
  const confirmed = await confirmDialog(
    "Stop tracking?", `${title} and its recorded price history will be removed.`, "Remove game");
  if (!confirmed) return false;
  try {
    await api.remove(gameId);
    state.tracked.delete(Number(gameId));
    toast(`Removed ${title}`);
    notifyChanged({ removed: Number(gameId) });
    return true;
  } catch (error) {
    toast(error.message, "error");
    return false;
  }
}

/** Parse a price typed by the user ("12,50", "12.5", "") into USD, or throw. */
export function parsePriceInput(raw) {
  const text = String(raw ?? "").trim().replace(",", ".");
  if (!text) return null;
  const value = Number(text);
  if (!Number.isFinite(value) || value < 0) throw new Error("Enter a price of 0 or more");
  if (value > 5000) throw new Error("That target looks too high - enter a price below 5000");
  return toUsd(value);
}

export async function saveTarget(gameId, rawValue) {
  let usd;
  try {
    usd = parsePriceInput(rawValue);
  } catch (error) {
    toast(error.message, "error");
    return null;
  }
  try {
    const game = await api.setTarget(gameId, usd);
    toast(usd === null ? "Target removed" : `Target saved: ${money(usd)}`);
    notifyChanged({ updated: gameId });
    return game;
  } catch (error) {
    toast(error.message, "error");
    return null;
  }
}

export function openTargetModal(game) {
  openModal({
    title: `Target for ${game.title}`,
    footer: `<button class="btn btn-ghost" data-close>Cancel</button>
             <button class="btn btn-primary" data-save>Save target</button>`,
    render(body, close, backdrop) {
      const current = game.target_price !== null ? fromUsd(game.target_price).toFixed(2) : "";
      body.innerHTML = `
        <div class="field"><label for="target-input">Notify me when the price drops to</label>
          <div class="input-prefix"><span>${esc(currencySymbol())}</span>
            <input class="input" id="target-input" inputmode="decimal" value="${esc(current)}" placeholder="19.99"></div></div>
        <p class="muted" style="margin:10px 0 0">Current best price ${money(game.current_price)},
          all-time low ${money(game.all_time_low)}. Leave empty to remove the target.</p>`;
      const input = body.querySelector("#target-input");
      const save = async () => { if (await saveTarget(game.game_id, input.value)) close(); };
      backdrop.querySelector("[data-save]").addEventListener("click", save);
      input.addEventListener("keydown", (event) => { if (event.key === "Enter") save(); });
      setTimeout(() => input.focus(), 0);
    },
  });
}

/** "Track a game" modal: search CheapShark and add results to the wishlist. */
export function openAddModal(initialQuery = "") {
  openModal({
    title: "Track a game",
    render(body) {
      body.innerHTML = `
        <div class="search-wrap" style="max-width:none">
          ${icon("search")}
          <input class="search-input" id="add-search" type="search" autocomplete="off"
                 placeholder="Type a game title, e.g. Hades" value="${esc(initialQuery)}">
        </div>
        <div id="add-results" style="margin-top:12px"></div>`;
      const input = body.querySelector("#add-search");
      const results = body.querySelector("#add-results");
      let timer;
      let requestId = 0;

      const run = async () => {
        const q = input.value.trim();
        if (q.length < 2) {
          results.innerHTML = `<p class="muted">Type at least 2 characters. Prices come live from CheapShark.</p>`;
          return;
        }
        const id = ++requestId;
        results.innerHTML = `<div class="skeleton" style="height:180px"></div>`;
        try {
          const items = await api.search(q, 15);
          if (id !== requestId) return;  // a newer search is running
          results.innerHTML = items.length ? items.map(resultRow).join("")
            : `<p class="muted">No games found for “${esc(q)}”. Check the spelling or try a shorter title.</p>`;
        } catch (error) {
          if (id === requestId) results.innerHTML = `<div class="error-box">${icon("alert")}<div>${esc(error.message)}</div></div>`;
        }
      };
      input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(run, 350); });
      results.addEventListener("click", async (event) => {
        const button = event.target.closest("[data-add]");
        if (!button) return;
        button.disabled = true;
        button.innerHTML = "Adding…";
        const game = await trackGame(button.dataset.add);
        button.outerHTML = game || state.tracked.has(Number(button.dataset.add))
          ? `<a class="btn btn-sm" href="#/game/${Number(button.dataset.add)}">${icon("check")}Tracked</a>`
          : `<button class="btn btn-sm btn-primary" data-add="${Number(button.dataset.add)}">Track</button>`;
      });
      run();
    },
  });
}

export function resultRow(item) {
  const tracked = item.tracked || state.tracked.has(item.game_id);
  return `<div class="result-row">
    <div class="result-thumb">${cover(item.cover_url, item.thumb_url, item.title)}</div>
    <div class="result-info"><div class="result-title">${esc(item.title)}</div>
      <div class="muted num">From ${money(item.cheapest_price)}</div></div>
    ${tracked ? `<a class="btn btn-sm" href="#/game/${item.game_id}">${icon("check")}Tracked</a>`
      : `<button class="btn btn-sm btn-primary" data-add="${item.game_id}">${icon("plus")}Track</button>`}
  </div>`;
}
