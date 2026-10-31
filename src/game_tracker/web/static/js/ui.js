// Generic UI building blocks: toasts, modals, empty/error/loading states.
import { esc } from "./format.js";
import { icon } from "./icons.js";

export function toast(message, kind = "success") {
  const root = document.getElementById("toasts");
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  const iconName = { success: "check", error: "alert", info: "info" }[kind] ?? "info";
  el.innerHTML = `${icon(iconName)}<div>${esc(message)}</div>`;
  root.append(el);
  setTimeout(() => el.remove(), kind === "error" ? 6000 : 3500);
}

/** Open a modal. `render(body, close)` fills the body; returns the close function. */
export function openModal({ title, render, footer = "" }) {
  const root = document.getElementById("modal-root");
  const previousFocus = document.activeElement;
  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <div class="modal" role="dialog" aria-modal="true" aria-label="${esc(title)}">
      <div class="modal-head"><h2>${esc(title)}</h2>
        <button class="icon-button" data-close aria-label="Close">${icon("x")}</button></div>
      <div class="modal-body"></div>
      ${footer ? `<div class="modal-foot">${footer}</div>` : ""}
    </div>`;
  const close = () => {
    backdrop.remove();
    document.removeEventListener("keydown", onKey);
    previousFocus?.focus?.();
  };
  const onKey = (event) => { if (event.key === "Escape") close(); };
  backdrop.addEventListener("click", (event) => {
    if (event.target === backdrop || event.target.closest("[data-close]")) close();
  });
  document.addEventListener("keydown", onKey);
  root.append(backdrop);
  render(backdrop.querySelector(".modal-body"), close, backdrop);
  backdrop.querySelector("input, button:not([data-close])")?.focus();
  return close;
}

export function confirmDialog(title, text, confirmLabel = "Confirm") {
  return new Promise((resolve) => {
    let answered = false;
    openModal({
      title,
      footer: `<button class="btn btn-ghost" data-close>Cancel</button>
               <button class="btn btn-danger" data-confirm>${esc(confirmLabel)}</button>`,
      render(body, closeModal, backdrop) {
        body.innerHTML = `<p class="text-2" style="margin:0">${esc(text)}</p>`;
        backdrop.querySelector("[data-confirm]").addEventListener("click", () => {
          answered = true;
          closeModal();
          resolve(true);
        });
        new MutationObserver((_m, observer) => {
          if (!backdrop.isConnected) { observer.disconnect(); if (!answered) resolve(false); }
        }).observe(document.getElementById("modal-root"), { childList: true });
      },
    });
  });
}

export function emptyState(iconName, title, text, actionHtml = "") {
  return `<div class="empty">${icon(iconName)}<h3>${esc(title)}</h3><p>${esc(text)}</p>${actionHtml}</div>`;
}

export function errorState(error, retryAction = "") {
  return `<div class="error-box">${icon("alert")}<div><strong>Could not load this page.</strong>
    <div class="text-2">${esc(error.message ?? error)}</div>
    ${retryAction ? `<button class="btn btn-sm" style="margin-top:10px" data-action="${retryAction}">Try again</button>` : ""}
  </div></div>`;
}

export function skeletonTiles(count = 6) {
  return `<div class="grid grid-3">${Array.from({ length: count }, () => `
    <div class="skeleton" style="height:230px"></div>`).join("")}</div>`;
}

export function skeletonBlock(height = 120) {
  return `<div class="skeleton" style="height:${height}px"></div>`;
}
