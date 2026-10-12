// Global client state and user preferences persisted in localStorage.
const PREFS_KEY = "dropzone.prefs.v1";

const defaults = { currency: "EUR", wishlistView: "list", lastSeenActivity: null };

function loadPrefs() {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(PREFS_KEY) ?? "{}") };
  } catch {
    return { ...defaults }; // storage blocked or corrupted - fall back to defaults
  }
}

export const prefs = loadPrefs();

export function savePref(key, value) {
  prefs[key] = value;
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {
    /* storage unavailable (private mode) - preference lives for this session only */
  }
}

export const state = {
  meta: null,          // /api/meta: rates, sources
  stores: [],          // /api/stores
  tracked: new Set(),  // ids of tracked games
  dashboard: null,     // last /api/dashboard
};

/** Currency actually used: the preferred one if its rate is known, otherwise USD. */
export function activeCurrency() {
  const rates = state.meta?.rates ?? { USD: 1 };
  return rates[prefs.currency] ? prefs.currency : "USD";
}
