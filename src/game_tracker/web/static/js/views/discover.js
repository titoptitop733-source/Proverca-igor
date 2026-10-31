import { api } from "../api.js";
import { dealTile } from "../components.js";
import { currencySymbol, esc } from "../format.js";
import { parsePriceInput } from "../actions.js";
import { state } from "../state.js";
import { emptyState, errorState, skeletonTiles, toast } from "../ui.js";

const SORTS = [
  ["Deal Rating", "Best rated deals"],
  ["Savings", "Biggest discount"],
  ["Price", "Lowest price"],
  ["Recent", "Recently reduced"],
  ["Metacritic", "Metacritic score"],
];
const MIN_DISCOUNTS = [0, 25, 50, 75, 90];
const PAGE_SIZE = 30;

export async function renderDiscover(view, active = () => true) {
  const filters = { sort: "Deal Rating", store: "", maxPrice: "", minDiscount: 0, title: "" };
  let page = 0;
  let deals = [];
  let exhausted = false;
  let requestId = 0;

  const stores = state.stores.filter((s) => s.is_active);
  view.innerHTML = `
    <div class="page-head"><div><div class="eyebrow">Discover</div><h1>Deals right now</h1>
      <p class="subtitle">Live discounts from PC stores tracked by CheapShark. Track any game to follow its price.</p></div></div>
    <div class="toolbar">
      <div class="field grow"><label for="dc-title">Title</label>
        <input class="input" id="dc-title" type="search" placeholder="Any game"></div>
      <div class="field"><label for="dc-store">Store</label>
        <select class="select" id="dc-store"><option value="">All stores</option>
          ${stores.map((s) => `<option value="${s.store_id}">${esc(s.name)}</option>`).join("")}</select></div>
      <div class="field" style="width:130px"><label for="dc-max">Max price</label>
        <div class="input-prefix"><span>${esc(currencySymbol())}</span>
          <input class="input" id="dc-max" inputmode="decimal" placeholder="Any"></div></div>
      <div class="field"><label for="dc-discount">Min discount</label>
        <select class="select" id="dc-discount">${MIN_DISCOUNTS.map((d) =>
          `<option value="${d}">${d ? `${d}% or more` : "Any"}</option>`).join("")}</select></div>
      <div class="field"><label for="dc-sort">Sort by</label>
        <select class="select" id="dc-sort">${SORTS.map(([value, label]) =>
          `<option value="${value}">${label}</option>`).join("")}</select></div>
    </div>
    <div class="result-count" id="dc-count"></div>
    <div id="dc-results">${skeletonTiles(9)}</div>
    <div style="display:flex;justify-content:center;margin-top:20px">
      <button class="btn" id="dc-more" hidden>Load more deals</button></div>`;

  const results = view.querySelector("#dc-results");
  const count = view.querySelector("#dc-count");
  const more = view.querySelector("#dc-more");

  const visible = () => deals.filter((d) => d.savings_percent >= filters.minDiscount);

  const draw = () => {
    const items = visible();
    count.textContent = `${items.length} deal${items.length === 1 ? "" : "s"} shown`;
    results.innerHTML = items.length ? `<div class="grid grid-3">${items.map(dealTile).join("")}</div>`
      : emptyState("tag", "No deals match these filters", "Raise the maximum price, lower the minimum discount or choose another store.");
    more.hidden = exhausted;
  };

  const load = async (reset) => {
    let maxUsd = null;
    try {
      maxUsd = parsePriceInput(filters.maxPrice);
    } catch (error) {
      toast(error.message, "error");
      return;
    }
    if (reset) { page = 0; deals = []; exhausted = false; results.innerHTML = skeletonTiles(9); }
    const id = ++requestId;
    more.disabled = true;
    try {
      const batch = await api.deals({
        sort: filters.sort, store: filters.store || null, max_price: maxUsd,
        title: filters.title.trim() || null, page, page_size: PAGE_SIZE,
      });
      if (id !== requestId || !active()) return;
      // The same game can be on sale in several stores - keep its cheapest offer only.
      const known = new Set(deals.map((d) => d.game_id));
      deals = deals.concat(batch.filter((d) => !known.has(d.game_id) && known.add(d.game_id)));
      exhausted = batch.length < PAGE_SIZE;
      page += 1;
      draw();
    } catch (error) {
      if (id === requestId && active()) results.innerHTML = errorState(error, "reload");
    } finally {
      more.disabled = false;
    }
  };

  let timer;
  const debounced = () => { clearTimeout(timer); timer = setTimeout(() => load(true), 400); };
  view.querySelector("#dc-title").addEventListener("input", (e) => { filters.title = e.target.value; debounced(); });
  view.querySelector("#dc-max").addEventListener("input", (e) => { filters.maxPrice = e.target.value; debounced(); });
  view.querySelector("#dc-store").addEventListener("change", (e) => { filters.store = e.target.value; load(true); });
  view.querySelector("#dc-sort").addEventListener("change", (e) => { filters.sort = e.target.value; load(true); });
  view.querySelector("#dc-discount").addEventListener("change", (e) => { filters.minDiscount = Number(e.target.value); draw(); });
  more.addEventListener("click", () => load(false));

  // When a game gets tracked from this page, flip its button without reloading the feed.
  view.addEventListener("dropzone:tracked", () => {
    deals = deals.map((d) => ({ ...d, tracked: state.tracked.has(d.game_id) }));
    draw();
  });
  await load(true);
}
