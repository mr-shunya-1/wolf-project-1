const BASE = "";

async function fetchJson(path, options = {}) {
  const resp = await fetch(BASE + path, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const err = new Error(body.gripe || "request failed");
    err.status = resp.status;
    throw err;
  }
  return body;
}

export const wire = {
  get: (path) => fetchJson(path),
  post: (path, payload) => fetchJson(path, { method: "POST", body: JSON.stringify(payload || {}) }),
  put: (path, payload) => fetchJson(path, { method: "PUT", body: JSON.stringify(payload || {}) }),
  del: (path) => fetchJson(path, { method: "DELETE" }),
};
