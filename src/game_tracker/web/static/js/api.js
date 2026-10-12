// Thin wrapper around the DROPZONE REST API (see /docs for the OpenAPI description).

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

function errorMessage(data, status) {
  if (typeof data?.detail === "string") return data.detail;
  if (Array.isArray(data?.detail)) return data.detail.map((item) => item.msg).join("; ");
  return `Request failed with status ${status}`;
}

async function request(method, path, body) {
  let response;
  try {
    response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError("Cannot reach the DROPZONE server. Check that it is still running.", 0);
  }
  if (response.status === 204) return null;
  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) throw new ApiError(errorMessage(data, response.status), response.status);
  return data;
}

function query(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined || value === "") continue;
    if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
    else search.append(key, value);
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}

export const api = {
  meta: () => request("GET", "/api/meta"),
  dashboard: () => request("GET", "/api/dashboard"),
  wishlist: () => request("GET", "/api/wishlist"),
  game: (id) => request("GET", `/api/games/${encodeURIComponent(id)}`),
  add: (gameId, targetPrice = null) =>
    request("POST", "/api/wishlist", { game_id: gameId, target_price: targetPrice }),
  remove: (id) => request("DELETE", `/api/wishlist/${encodeURIComponent(id)}`),
  setTarget: (id, targetPrice) =>
    request("PUT", `/api/wishlist/${encodeURIComponent(id)}/target`, { target_price: targetPrice }),
  update: (force = false) => request("POST", "/api/update", { force }),
  search: (q, limit = 12) => request("GET", `/api/search${query({ q, limit })}`),
  deals: (params) => request("GET", `/api/deals${query(params)}`),
  stores: () => request("GET", "/api/stores"),
};
