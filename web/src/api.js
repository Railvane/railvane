async function request(method, path, body) {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail
      : Array.isArray(data.detail) ? data.detail.map(d => d.msg).join("; ") : res.statusText;
    throw new Error(detail || `${res.status}`);
  }
  return data;
}

export const getJson = path => request("GET", path);
export const postJson = (path, body) => request("POST", path, body ?? {});
export const putJson = (path, body) => request("PUT", path, body);
export const qs = params => new URLSearchParams(params).toString();
