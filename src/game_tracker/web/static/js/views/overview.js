import { api } from "../api.js";
import { activityItem, cover, discountBadge, gameTile } from "../components.js";
import { esc, money } from "../format.js";
import { icon } from "../icons.js";
import { state } from "../state.js";
import { emptyState, errorState, skeletonBlock, skeletonTiles } from "../ui.js";

function statsStrip(d) {
  const stat = (iconName, label, value, hint, accent = false) => `
    <div class="stat${accent ? " accent" : ""}">
      <div class="stat-label">${icon(iconName)}${esc(label)}</div>
      <div class="stat-value num">${value}</div>
      <div class="stat-hint">${esc(hint)}</div>
    </div>`;
  return `<div class="stats-strip">
    ${stat("gamepad", "Tracked games", d.tracked_games, "Games in your watchlist")}
    ${stat("coins", "Potential savings", money(d.potential_savings), "Sum of current discounts", d.potential_savings > 0)}
    ${stat("down", "Price drops", d.price_drops, "Cheaper since the last update")}
    ${stat("award", "Historical lows", d.historical_lows, "At their lowest known price")}
  </div>`;
}

function featured(game) {
  if (!game) {
    return emptyState("tag", "No discounts on your games right now",
      "When a tracked game goes on sale it will be highlighted here. Discover shows deals on other games.",
      `<a class="btn" href="#/discover">${icon("discover")}Browse deals</a>`);
  }
  const saving = game.retail_price - game.current_price;
  return `
    <article class="featured">
      <div class="featured-art">${cover(game.cover_url, game.thumb_url, game.title)}</div>
      <div class="featured-body">
        <div class="featured-kicker">${icon("down")}Biggest discount in your wishlist</div>
        <h2 class="featured-title">${esc(game.title)}</h2>
        <div class="price-row">
          <span class="price-big num lime">${money(game.current_price)}</span>
          <span class="strike num">${money(game.retail_price)}</span>
          ${discountBadge(game.discount_percent)}
        </div>
        <div class="featured-facts">
          <div>You save<strong class="num">${money(saving)}</strong></div>
          <div>All-time low<strong class="num">${money(game.all_time_low)}</strong></div>
          <div>Best store<strong>${esc(game.store_name ?? "—")}</strong></div>
        </div>
        <div><button class="btn btn-primary" data-action="open-game" data-id="${game.game_id}">View deal</button></div>
      </div>
    </article>`;
}

export async function renderOverview(view, active = () => true) {
  const today = new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long" });
  view.innerHTML = `
    <div class="page-head">
      <div>
        <div class="eyebrow">Player dashboard</div>
        <h1>Your gaming radar</h1>
        <p class="subtitle">Track prices. Catch the drop. Play for less.</p>
      </div>
      <div class="head-meta"><span class="hide-mobile">${esc(today)}</span>
        <button class="btn btn-primary" data-action="open-add">${icon("plus")}Track a game</button></div>
    </div>
    <div id="ov-stats">${skeletonBlock(96)}</div>
    <section class="section"><div class="section-head"><h2>Price drop detected</h2></div>
      <div id="ov-featured">${skeletonBlock(260)}</div></section>
    <div class="layout-split section">
      <section><div class="section-head"><h2>Your tracked games</h2>
        <a class="link" href="#/wishlist">Open wishlist</a></div><div id="ov-grid">${skeletonTiles()}</div></section>
      <aside class="panel"><div class="panel-head"><h2>Price activity</h2>
        <button class="btn btn-sm btn-ghost" id="ov-all-activity" hidden>View all</button></div>
        <div id="ov-activity">${skeletonBlock(220)}</div></aside>
    </div>`;

  let dashboard;
  let wishlist;
  try {
    [dashboard, wishlist] = await Promise.all([api.dashboard(), api.wishlist()]);
  } catch (error) {
    if (!active()) return;
    view.querySelector("#ov-stats").innerHTML = errorState(error, "reload");
    ["#ov-featured", "#ov-grid", "#ov-activity"].forEach((id) => { view.querySelector(id).innerHTML = ""; });
    return;
  }
  if (!active()) return;
  state.dashboard = dashboard;

  view.querySelector("#ov-stats").innerHTML = statsStrip(dashboard);
  view.querySelector("#ov-featured").innerHTML = featured(dashboard.featured);

  const top = [...wishlist]
    .sort((a, b) => (b.discount_percent ?? 0) - (a.discount_percent ?? 0) || a.title.localeCompare(b.title))
    .slice(0, 6);
  view.querySelector("#ov-grid").innerHTML = top.length
    ? `<div class="grid grid-3">${top.map(gameTile).join("")}</div>`
    : emptyState("gamepad", "Your wishlist is empty",
      "Search for a game you want and DROPZONE will watch its price in every store.",
      `<button class="btn btn-primary" data-action="open-add">${icon("plus")}Track your first game</button>`);

  const allButton = view.querySelector("#ov-all-activity");
  allButton.hidden = dashboard.activity.length <= 6;
  allButton.addEventListener("click", (event) => {
    event.stopPropagation();
    document.getElementById("notify-button").click();
  });
  view.querySelector("#ov-activity").innerHTML = dashboard.activity.length
    ? `<ul class="activity">${dashboard.activity.slice(0, 6).map(activityItem).join("")}</ul>`
    : `<div class="panel-body muted">No price changes yet. Prices are checked every
       ${esc(state.meta?.snapshot_interval_hours ?? 6)} hours while DROPZONE is running.</div>`;
}
