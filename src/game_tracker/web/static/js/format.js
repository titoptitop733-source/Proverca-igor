import { activeCurrency, state } from "./state.js";

const ESCAPES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

/** Escape text before inserting it into HTML (game titles come from an external API). */
export function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ESCAPES[char]);
}

function rate() {
  return state.meta?.rates?.[activeCurrency()] ?? 1;
}

/** Format a USD amount in the selected currency. */
export function money(usd) {
  if (usd === null || usd === undefined || Number.isNaN(usd)) return "—";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: activeCurrency() })
    .format(usd * rate());
}

/** Convert an amount typed in the selected currency back to USD (API currency). */
export function toUsd(amount) {
  return Math.round((amount / rate()) * 100) / 100;
}

export function fromUsd(usd) {
  return Math.round(usd * rate() * 100) / 100;
}

export function currencySymbol() {
  return { USD: "$", EUR: "€", GBP: "£" }[activeCurrency()] ?? activeCurrency();
}

export function percent(value, digits = 0) {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(digits)}%`;
}

export function shortDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}

export function timeAgo(iso) {
  if (!iso) return "never";
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)} d ago`;
  return shortDate(iso);
}

/** Currency of an amount already converted to the display currency. */
export function moneyLocal(amount) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: activeCurrency() }).format(amount);
}

/**
 * Explanations from the server mention USD amounts ("$14.99"). Show them in the selected
 * currency so the whole page is consistent. Input must already be HTML-escaped.
 */
export function localizePrices(escapedText) {
  return escapedText.replace(/\$(\d+(?:\.\d+)?)/g, (_match, amount) => money(Number(amount)));
}
