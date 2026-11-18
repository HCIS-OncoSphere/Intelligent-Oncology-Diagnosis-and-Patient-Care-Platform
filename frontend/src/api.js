let access = localStorage.getItem("access");

export async function api(path, { method = "GET", body } = {}) {
  const res = await fetch("/api" + path, {
    method,
    headers: { "Content-Type": "application/json", ...(access ? { Authorization: `Bearer ${access}` } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new Error(JSON.stringify(data) || res.statusText);
  return data;
}

export async function login(username, password) {
  const t = await api("/auth/login/", { method: "POST", body: { username, password } });
  access = t.access;
  localStorage.setItem("access", access);
  return api("/auth/me/");
}

export function logout() { access = null; localStorage.removeItem("access"); }
