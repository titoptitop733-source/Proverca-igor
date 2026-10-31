import { api } from "../api.js";
import { openTargetModal, removeGame, saveTarget, trackGame } from "../actions.js";
import { renderPriceChart } from "../charts.js";
import { cover, discountBadge, statusLabel } from "../components.js";
import { currencySymbol, esc, fromUsd, localizePrices, money, percent, shortDate, timeAgo } from "../format.js";
import { icon } from "../icons.js";
import { emptyState, errorState, skeletonBlock } from "../ui.js";

const RANGES = [["1M", 30], ["3M", 91], ["6M", 182], ["1Y", 365], ["ALL", null]];
const DAY = 86400000;

function rangePoints(history, days) {
  if (!days || !history.length) return history;
  const end = new Date(history.at(-1).recorded_at).getTime();
  const inRange = history.filter((p) => new Date(p.recorded_at).getTime() >= end - days * DAY);
  // Keep the price that was valid when the range starts, so the line does not begin mid-air.
  const before = history.filter((p) => new Date(p.recorded_at).getTime() < end - days * DAY).at(-1);
  return before ? [{ ...before, recorded_at: new Date(end - days * DAY).toISOString() }, ...inRange] : inRange;
}

function summary(points, game) {
  const prices = points.map((p) => p.price);
  const avg = prices.reduce((a, b) => a + b, 0) / (prices.length || 1);
  const vsLow = game.all_time_low ? ((game.current_price - game.all_time_low) / game.all_time_low) * 100 : null;
  const cell = (label, value) => `<div><div class="fact-label">${label}</div><div class="fact-value num">${value}</div></div>`;
  return cell("Lowest in range", money(Math.min(...prices)))
    + cell("Highest in range", money(Math.max(...prices)))
    + cell("Average in range", money(avg))
    + cell("Now vs all-time low", vsLow === null ? "—" : vsLow <= 0.05 ? "At the low" : `+${percent(vsLow)}`);
}

function verdictCard(game) {
  return `<div class="verdict ${esc(game.advice.verdict)}">
    <div class="verdict-kicker">${icon("scale")}Buy or wait?</div>
    <div class="verdict-label">${esc(game.advice.label)}</div>
    <ul>${game.advice.reasons.map((r) => `<li>${localizePrices(esc(r))}</li>`).join("")}</ul>
    <div class="verdict-note">Based on recorded prices and the all-time low reported by CheapShark.
      It explains past prices and does not predict future sales.</div></div>`;
}

function pricePanel(game) {
  const stats = game.stats;
  const saving = game.retail_price && game.current_price !== null ? game.retail_price - game.current_price : 0;
  const fact = (label, value) => `<div><div class="fact-label">${label}</div><div class="fact-value num">${value}</div></div>`;
  return `<div class="panel price-panel"><div class="panel-body">
    <div class="fact-label">Best price now${game.store_name ? ` at ${esc(game.store_name)}` : ""}</div>
    <div class="price-row"><span class="price-big num ${game.discount_percent > 0 ? "lime" : ""}">${money(game.current_price)}</span>
      ${game.discount_percent > 0 ? `<span class="strike num">${money(game.retail_price)}</span>${discountBadge(game.discount_percent)}` : ""}</div>
    <div class="facts">
      ${fact("You save", saving > 0 ? money(saving) : "—")}
      ${fact("All-time low", money(game.all_time_low))}
      ${fact("Highest recorded", money(stats?.observed_max))}
      ${fact("Average recorded", money(stats?.average_price))}
      ${fact("On sale in", stats ? `${percent(stats.discount_share * 100)} of checks` : "—")}
      ${fact("Last checked", esc(timeAgo(game.last_updated)))}
    </div></div></div>`;
}

function targetPanel(game) {
  const value = game.target_price !== null ? fromUsd(game.target_price).toFixed(2) : "";
  return `<div class="panel"><div class="panel-head"><h2>Set your target</h2>${statusLabel(game.target_status)}</div>
    <div class="panel-body target-form">
      <div class="field"><label for="target-price">Alert me at or below</label>
        <div class="input-prefix"><span>${esc(currencySymbol())}</span>
          <input class="input num" id="target-price" inputmode="decimal" placeholder="19.99" value="${esc(value)}"></div></div>
      <label class="toggle"><input type="checkbox" id="target-on" ${game.target_price !== null ? "checked" : ""}>Price alert enabled</label>
      <button class="btn btn-primary" id="target-save">Save target</button>
      <p class="muted" style="margin:0;font-size:12px">You get an alert in DROPZONE when an update finds the price at or below your target.</p>
    </div></div>`;
}

function offersTable(game) {
  if (!game.offers.length) return emptyState("store", "No store offers recorded", "Update prices to load offers from stores.");
  return `<div class="table-wrap"><table>
    <thead><tr><th>Store</th><th class="right">Price</th><th class="right">Discount</th><th class="right hide-mobile">Regular price</th><th>Source</th></tr></thead>
    <tbody>${game.offers.map((o) => `<tr>
      <td><strong>${esc(o.store_name ?? `Store #${o.store_id}`)}</strong> ${o.is_best ? `<span class="badge badge-lime">Best price</span>` : ""}</td>
      <td class="right num"><strong>${money(o.price)}</strong></td>
      <td class="right num">${o.savings_percent > 0 ? `<span class="lime">-${Math.round(o.savings_percent)}%</span>` : `<span class="muted">0%</span>`}</td>
      <td class="right num hide-mobile">${money(o.retail_price)}</td>
      <td class="muted">CheapShark, ${esc(timeAgo(game.last_updated))}</td></tr>`).join("")}
    </tbody></table></div>`;
}

export async function renderGame(view, gameId, active = () => true) {
  view.innerHTML = `<a class="back-link" href="#/wishlist">${icon("back")}Back to wishlist</a>${skeletonBlock(220)}`;
  let game;
  try {
    game = await api.game(gameId);
  } catch (error) {
    if (!active()) return;
    view.innerHTML = `<a class="back-link" href="#/wishlist">${icon("back")}Back to wishlist</a>` + (error.status === 404
      ? emptyState("heart", "This game is not tracked yet",
        "Track it to start recording its price history and get buying advice.",
        `<button class="btn btn-primary" id="track-missing">${icon("plus")}Track this game</button>`)
      : errorState(error, "reload"));
    view.querySelector("#track-missing")?.addEventListener("click", async () => {
      if (await trackGame(gameId)) renderGame(view, gameId, active);
    });
    return;
  }
  if (!active()) return;

  view.innerHTML = `
    <a class="back-link" href="#/wishlist">${icon("back")}Back to wishlist</a>
    <section class="detail-hero">
      <div class="detail-art">${cover(game.cover_url, game.thumb_url, game.title)}</div>
      <div>
        <h1 class="detail-title">${esc(game.title)}</h1>
        <div class="detail-tags">
          <span class="badge badge-neutral">PC</span>
          <span class="badge badge-neutral">${game.offers.length} store${game.offers.length === 1 ? "" : "s"}</span>
          <span class="badge badge-neutral">Tracked since ${esc(shortDate(game.added_at))}</span>
          ${game.at_historical_low && game.discount_percent > 0 ? `<span class="badge badge-blue">${icon("award")}Historical low</span>` : ""}
        </div>
        <div class="detail-actions">
          ${game.steam_app_id ? `<a class="btn" href="https://store.steampowered.com/app/${Number(game.steam_app_id)}" target="_blank" rel="noopener noreferrer">${icon("external")}Steam page</a>` : ""}
          <button class="btn" id="edit-target">${icon("target")}Edit target</button>
          <button class="btn btn-danger" id="remove-game">${icon("trash")}Stop tracking</button>
        </div>
      </div>
    </section>
    <div class="detail-grid">
      <div style="display:flex;flex-direction:column;gap:20px;min-width:0">
        <section class="panel chart-panel">
          <div class="panel-head"><div><h2>Price history</h2>
            <div class="data-note">${icon("info")}${game.history.length} checks recorded by DROPZONE from CheapShark</div></div>
            <div class="segmented" id="ranges" role="group" aria-label="Chart range">${RANGES.map(([label]) =>
              `<button data-range="${label}" class="${label === "ALL" ? "active" : ""}">${label}</button>`).join("")}</div></div>
          <div class="chart-box" id="chart"></div>
          <div class="chart-summary" id="chart-summary"></div>
        </section>
        <section><div class="section-head"><h2>Store comparison</h2>
          <span class="muted" style="font-size:13px">Latest check, prices in ${esc(currencySymbol())}</span></div>${offersTable(game)}</section>
      </div>
      <div class="detail-side">${pricePanel(game)}${verdictCard(game)}${targetPanel(game)}</div>
    </div>`;

  const chartBox = view.querySelector("#chart");
  let disposeChart = null;
  const showRange = (label) => {
    const days = RANGES.find(([l]) => l === label)[1];
    const points = rangePoints(game.history, days);
    view.querySelectorAll("[data-range]").forEach((b) => b.classList.toggle("active", b.dataset.range === label));
    disposeChart?.();
    if (!points.length) {
      chartBox.innerHTML = emptyState("clock", "No prices recorded yet", "Update prices to record the first check.");
      view.querySelector("#chart-summary").innerHTML = "";
      return;
    }
    disposeChart = renderPriceChart(chartBox, points, { target: game.target_price, low: game.all_time_low });
    view.querySelector("#chart-summary").innerHTML = summary(points, game);
  };
  view.querySelector("#ranges").addEventListener("click", (e) => {
    const button = e.target.closest("[data-range]");
    if (button) showRange(button.dataset.range);
  });
  showRange("ALL");

  view.querySelector("#edit-target").addEventListener("click", () => openTargetModal(game));
  view.querySelector("#remove-game").addEventListener("click", async () => {
    if (await removeGame(game.game_id, game.title)) location.hash = "#/wishlist";
  });
  // Typing a price means the user wants an alert - switch the toggle on automatically.
  view.querySelector("#target-price").addEventListener("input", (event) => {
    if (event.target.value.trim()) view.querySelector("#target-on").checked = true;
  });
  view.querySelector("#target-save").addEventListener("click", async () => {
    const enabled = view.querySelector("#target-on").checked;
    await saveTarget(game.game_id, enabled ? view.querySelector("#target-price").value : "");
  });
  return () => disposeChart?.();
}
