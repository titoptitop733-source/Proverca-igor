// Small dependency-free SVG charts: sparkline and interactive price history chart.
import { esc, fromUsd, money, moneyLocal, shortDate } from "./format.js";

/** Chart colours come from CSS variables, so charts follow the light/dark theme. */
function themeColors() {
  const css = getComputedStyle(document.documentElement);
  const read = (name) => css.getPropertyValue(name).trim();
  return {
    lime: read("--chart-line"), area: read("--chart-area"), blue: read("--blue-text"),
    coral: read("--negative-text"), grid: read("--border"), muted: read("--muted"),
    text: read("--text-2"), bg: read("--bg"),
  };
}

/** Mini trend line. Lime when the price went down, coral when it went up. */
export function sparkline(values, width = 96, height = 28) {
  const COLORS = themeColors();
  if (!values || values.length < 2) {
    return `<svg width="${width}" height="${height}" aria-hidden="true">
      <line x1="0" x2="${width}" y1="${height / 2}" y2="${height / 2}" stroke="${COLORS.grid}" stroke-dasharray="3 3"/></svg>`;
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = width / (values.length - 1);
  const y = (v) => height - 3 - ((v - min) / span) * (height - 6);
  // Step path: price stays constant until the next snapshot.
  let path = `M0 ${y(values[0]).toFixed(1)}`;
  values.slice(1).forEach((value, index) => {
    const x = ((index + 1) * step).toFixed(1);
    path += ` H${x} V${y(value).toFixed(1)}`;
  });
  const last = values.at(-1);
  const color = last < values[0] ? COLORS.lime : last > values[0] ? COLORS.coral : COLORS.muted;
  return `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" aria-hidden="true">
    <path d="${path}" fill="none" stroke="${color}" stroke-width="1.6" stroke-linejoin="round"/></svg>`;
}

function niceStep(range) {
  const rough = range / 4;
  const power = 10 ** Math.floor(Math.log10(rough || 1));
  const steps = [1, 2, 2.5, 5, 10].map((s) => s * power);
  return steps.find((s) => s >= rough) ?? rough;
}

/**
 * Render an interactive step chart of the best price over time into `container`.
 * `points` are API price points ({recorded_at, price, retail_price, store_name}).
 */
export function renderPriceChart(container, points, { target = null, low = null } = {}) {
  const tooltip = document.createElement("div");
  tooltip.className = "chart-tooltip";

  const draw = () => {
    const COLORS = themeColors();
    const width = Math.max(container.clientWidth - 16, 280);
    const height = Math.max(container.clientHeight - 16, 180);
    const pad = { top: 12, right: 16, bottom: 26, left: 52 };
    const innerW = width - pad.left - pad.right;
    const innerH = height - pad.top - pad.bottom;

    const times = points.map((p) => new Date(p.recorded_at).getTime());
    let t0 = Math.min(...times);
    let t1 = Math.max(...times);
    if (t0 === t1) { t0 -= 86400000; t1 += 86400000; }   // single snapshot: show +/- 1 day

    // Scale in the display currency, so axis labels are round numbers (e.g. EUR 10, 20, 30).
    const values = points.flatMap((p) => [p.price, p.retail_price])
      .concat([target, low].filter((v) => v !== null && v !== undefined)).map(fromUsd);
    const maxValue = Math.max(...values) * 1.12 || 1;
    const yStep = niceStep(maxValue);
    const yMax = Math.ceil(maxValue / yStep) * yStep;

    const x = (t) => pad.left + ((t - t0) / (t1 - t0)) * innerW;
    const yLocal = (v) => pad.top + innerH - (v / yMax) * innerH;
    const y = (usd) => yLocal(fromUsd(usd));

    let grid = "";
    for (let value = 0; value <= yMax + 1e-9; value += yStep) {
      grid += `<line x1="${pad.left}" x2="${width - pad.right}" y1="${yLocal(value)}" y2="${yLocal(value)}" stroke="${COLORS.grid}" stroke-width="1"/>
        <text x="${pad.left - 8}" y="${yLocal(value) + 4}" text-anchor="end" fill="${COLORS.muted}" font-size="11">${esc(moneyLocal(value).replace(/\.00$/, ""))}</text>`;
    }
    const ticks = 5;
    for (let i = 0; i <= ticks; i += 1) {
      const t = t0 + ((t1 - t0) * i) / ticks;
      const label = new Date(t).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
      grid += `<text x="${x(t)}" y="${height - 6}" text-anchor="middle" fill="${COLORS.muted}" font-size="11">${label}</text>`;
    }

    const stepPath = (accessor) => {
      let d = `M${x(times[0])} ${y(accessor(points[0]))}`;
      points.slice(1).forEach((p, i) => { d += ` H${x(times[i + 1])} V${y(accessor(p))}`; });
      return `${d} H${x(t1)}`;
    };
    const line = stepPath((p) => p.price);
    const area = `${line} V${yLocal(0)} H${x(times[0])} Z`;

    const refLine = (value, color, label) => value === null || value === undefined ? "" : `
      <line x1="${pad.left}" x2="${width - pad.right}" y1="${y(value)}" y2="${y(value)}" stroke="${color}" stroke-dasharray="5 5" stroke-width="1.2"/>
      <text x="${width - pad.right}" y="${y(value) - 6}" text-anchor="end" fill="${color}" font-size="11">${esc(label)}</text>`;

    container.innerHTML = `
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Price history chart">
        <defs><linearGradient id="area-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stop-color="${COLORS.area}" stop-opacity="0.18"/>
          <stop offset="1" stop-color="${COLORS.area}" stop-opacity="0"/></linearGradient></defs>
        ${grid}
        <path d="${stepPath((p) => p.retail_price)}" fill="none" stroke="${COLORS.muted}" stroke-dasharray="2 4" stroke-width="1.2"/>
        <path d="${area}" fill="url(#area-fill)"/>
        <path d="${line}" fill="none" stroke="${COLORS.lime}" stroke-width="2.2" stroke-linejoin="round"/>
        ${refLine(target, COLORS.blue, `Target ${money(target)}`)}
        ${refLine(low, COLORS.coral, `All-time low ${money(low)}`)}
        <line class="guide" y1="${pad.top}" y2="${pad.top + innerH}" stroke="${COLORS.text}" stroke-width="1" opacity="0"/>
        <circle class="dot" r="4.5" fill="${COLORS.lime}" stroke="${COLORS.bg}" stroke-width="2" opacity="0"/>
        <rect class="hit" x="${pad.left}" y="${pad.top}" width="${innerW}" height="${innerH}" fill="transparent"/>
      </svg>`;
    container.append(tooltip);

    const svg = container.querySelector("svg");
    const guide = svg.querySelector(".guide");
    const dot = svg.querySelector(".dot");
    const hit = svg.querySelector(".hit");
    const show = (event) => {
      const box = svg.getBoundingClientRect();
      const px = ((event.clientX - box.left) / box.width) * width;
      const t = t0 + ((px - pad.left) / innerW) * (t1 - t0);
      // Last snapshot at or before the cursor (step chart semantics).
      let index = 0;
      times.forEach((time, i) => { if (time <= t) index = i; });
      const point = points[index];
      guide.setAttribute("x1", px); guide.setAttribute("x2", px); guide.setAttribute("opacity", "0.35");
      dot.setAttribute("cx", px); dot.setAttribute("cy", y(point.price)); dot.setAttribute("opacity", "1");
      tooltip.innerHTML = `<strong class="num">${esc(money(point.price))}</strong>
        <span class="muted">${esc(shortDate(point.recorded_at))}<br>${esc(point.store_name ?? "Store")}</span>`;
      tooltip.style.left = `${(px / width) * box.width + 8}px`;
      tooltip.style.top = `${(y(point.price) / height) * box.height + 12}px`;
      tooltip.classList.add("visible");
    };
    const hide = () => {
      guide.setAttribute("opacity", "0"); dot.setAttribute("opacity", "0");
      tooltip.classList.remove("visible");
    };
    hit.addEventListener("pointermove", show);
    hit.addEventListener("pointerleave", hide);
  };

  draw();
  const observer = new ResizeObserver(() => draw());
  observer.observe(container);
  document.addEventListener("dropzone:theme", draw);
  return () => {
    observer.disconnect();
    document.removeEventListener("dropzone:theme", draw);
  };
}
