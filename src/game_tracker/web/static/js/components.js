// Reusable HTML fragments. Every dynamic value goes through esc().
import { sparkline } from "./charts.js";
import { esc, localizePrices, money, percent, timeAgo } from "./format.js";
import { icon } from "./icons.js";

/** Cover artwork with fallback: Steam header -> CheapShark thumbnail -> title placeholder. */
export function cover(url, fallback, title) {
  if (!url && !fallback) return `<div class="cover-fallback">${esc(title)}</div>`;
  return `<img src="${esc(url ?? fallback)}" data-fallback="${esc(fallback ?? "")}"
    data-title="${esc(title)}" alt="" loading="lazy" referrerpolicy="no-referrer">`;
}

export function discountBadge(value) {
  return value > 0 ? `<span class="badge badge-discount num">-${Math.round(value)}%</span>` : "";
}

const ADVICE_CLASS = { BUY_NOW: "badge-lime", GOOD_DEAL: "badge-blue", WAIT: "badge-warning",
  NO_DATA: "badge-neutral" };

export function adviceBadge(advice) {
  return `<span class="badge ${ADVICE_CLASS[advice.verdict] ?? "badge-neutral"}">${esc(advice.label)}</span>`;
}

const STATUS_CLASS = { "TARGET REACHED": "status-reached", "ALMOST THERE": "status-almost",
  "WAITING FOR DROP": "status-waiting", "NO TARGET": "status-none" };

export function statusLabel(status) {
  return `<span class="status ${STATUS_CLASS[status] ?? "status-none"}">${esc(status)}</span>`;
}

export function trendIcon(change) {
  if (!change) return "";
  return change < 0
    ? `<span class="lime" title="Price dropped">${icon("down")}</span>`
    : `<span class="negative" title="Price increased">${icon("up")}</span>`;
}

/** Tile for a tracked game (summary from /api/wishlist). */
export function gameTile(game) {
  const flag = game.target_status === "TARGET REACHED"
    ? `<span class="badge badge-lime tile-flag">${icon("target")}Target</span>`
    : game.at_historical_low && game.discount_percent > 0
      ? `<span class="badge badge-blue tile-flag">${icon("award")}Lowest</span>` : "";
  return `
    <article class="tile" data-action="open-game" data-id="${game.game_id}" tabindex="0">
      <div class="tile-art">${cover(game.cover_url, game.thumb_url, game.title)}
        ${discountBadge(game.discount_percent)}${flag}</div>
      <div class="tile-body">
        <h3 class="tile-title" title="${esc(game.title)}">${esc(game.title)}</h3>
        <div class="tile-meta"><span>${esc(game.store_name ?? "No offers yet")}</span>${adviceBadge(game.advice)}</div>
        <div class="tile-prices">
          <div>
            <div class="tile-price num">${money(game.current_price)}</div>
            ${game.discount_percent > 0 ? `<div class="tile-retail strike num">${money(game.retail_price)}</div>`
              : `<div class="tile-retail muted num">Low ${money(game.all_time_low)}</div>`}
          </div>
          ${sparkline(game.sparkline)}
        </div>
      </div>
    </article>`;
}

/** Tile for a deal from the CheapShark deals feed (Discover page). */
export function dealTile(deal) {
  const rating = deal.metacritic_score ? `Metacritic ${deal.metacritic_score}`
    : deal.steam_rating_text ? esc(deal.steam_rating_text) : "No rating";
  const action = deal.tracked
    ? `<button class="btn btn-sm" data-action="open-game" data-id="${deal.game_id}">${icon("check")}Tracked</button>`
    : `<button class="btn btn-sm btn-primary" data-action="track" data-id="${deal.game_id}">${icon("plus")}Track</button>`;
  return `
    <article class="tile" ${deal.tracked ? `data-action="open-game" data-id="${deal.game_id}"` : ""}>
      <div class="tile-art">${cover(deal.cover_url, deal.thumb_url, deal.title)}${discountBadge(deal.savings_percent)}</div>
      <div class="tile-body">
        <h3 class="tile-title" title="${esc(deal.title)}">${esc(deal.title)}</h3>
        <div class="tile-meta"><span>${esc(deal.store_name ?? "Store")}</span><span>${rating}</span></div>
        <div class="tile-prices">
          <div>
            <div class="tile-price num">${money(deal.sale_price)}</div>
            <div class="tile-retail strike num">${money(deal.normal_price)}</div>
          </div>
          ${action}
        </div>
      </div>
    </article>`;
}

const ACTIVITY_ICON = { drop: "down", rise: "up", low: "award", target: "target" };

export function activityItem(event) {
  return `
    <li data-action="open-game" data-id="${event.game_id}">
      <div class="activity-icon ${esc(event.kind)}">${icon(ACTIVITY_ICON[event.kind] ?? "info")}</div>
      <div>
        <div class="activity-title">${esc(event.title)}</div>
        <div class="activity-text">${localizePrices(esc(event.message))}</div>
        <div class="activity-time">${esc(timeAgo(event.at))}</div>
      </div>
    </li>`;
}

export function priceOrDash(value) {
  return `<span class="num">${money(value)}</span>`;
}

export { percent };
