// Light / dark / system theme. The choice is stored in localStorage (see state.js).
import { prefs, savePref } from "./state.js";

const media = window.matchMedia("(prefers-color-scheme: light)");

/** Theme that is actually shown: "light" or "dark". */
export function resolvedTheme() {
  if (prefs.theme === "light" || prefs.theme === "dark") return prefs.theme;
  return media.matches ? "light" : "dark";
}

export function applyTheme() {
  document.documentElement.dataset.theme = resolvedTheme();
  document.dispatchEvent(new Event("dropzone:theme"));  // charts redraw with new colours
}

export function setTheme(theme) {
  savePref("theme", theme);
  applyTheme();
}

/** Quick toggle in the top bar: switch to the opposite of what is shown now. */
export function toggleTheme() {
  setTheme(resolvedTheme() === "light" ? "dark" : "light");
}

media.addEventListener("change", () => { if (prefs.theme === "system") applyTheme(); });
