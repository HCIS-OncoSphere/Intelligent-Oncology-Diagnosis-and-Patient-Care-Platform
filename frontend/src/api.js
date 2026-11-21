// ---------------------------------------------------------------------------
// Token helpers
// ---------------------------------------------------------------------------

/** Always read the latest access token from storage (survives page refresh). */
function getAccess() {
  return localStorage.getItem("access");
}

function getRefresh() {
  return localStorage.getItem("refresh");
}

function storeTokens({ access, refresh }) {
  if (access)  localStorage.setItem("access",  access);
  if (refresh) localStorage.setItem("refresh", refresh);
}

function clearTokens() {
  localStorage.removeItem("access");
  localStorage.removeItem("refresh");
}

// ---------------------------------------------------------------------------
// Core fetch wrapper with automatic token refresh on 401
// ---------------------------------------------------------------------------

/**
 * Make an API call.  On a 401 response the function automatically attempts
 * one token refresh and retries the original request.  If the refresh also
 * fails (e.g. refresh token is expired) it clears stored tokens and re-throws.
 *
 * @param {string} path   - API path, e.g. "/auth/me/"
 * @param {object} opts   - { method, body, _isRetry }
 * @returns {Promise<any>}
 * @throws {{ status: number, data: any }} structured error object
 */
export async function api(path, { method = "GET", body, _isRetry = false } = {}) {
  const access = getAccess();
  // FormData (file uploads) is sent as-is so the browser sets the multipart boundary itself.
  const isForm = typeof FormData !== "undefined" && body instanceof FormData;
  const res = await fetch("/api" + path, {
    method,
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(access ? { Authorization: `Bearer ${access}` } : {}),
    },
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });

  const data = res.status === 204 ? null : await res.json().catch(() => null);

  if (res.status === 401 && !_isRetry) {
    // Attempt a silent token refresh
    const refreshed = await _tryRefresh();
    if (refreshed) {
      return api(path, { method, body, _isRetry: true });
    }
    // Refresh failed — clear tokens so the UI can redirect to login
    clearTokens();
  }

  if (!res.ok) {
    // Throw a structured error so callers get both the HTTP status and body
    throw { status: res.status, data };
  }

  return data;
}

/**
 * Attempt to refresh the access token using the stored refresh token.
 * @returns {Promise<boolean>} true if the refresh succeeded
 */
async function _tryRefresh() {
  const refresh = getRefresh();
  if (!refresh) return false;
  try {
    const res = await fetch("/api/auth/refresh/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
    if (!res.ok) return false;
    const tokens = await res.json();
    storeTokens(tokens);           // may include a rotated refresh token
    return true;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Auth helpers
// ---------------------------------------------------------------------------

export async function login(username, password) {
  const tokens = await api("/auth/login/", { method: "POST", body: { username, password } });
  // Persist both access and refresh tokens so refresh survives page reload
  storeTokens(tokens);
  return api("/auth/me/");
}

/** Patient self-registration. Throws { status, data } with per-field errors on 400. */
export function register(fields) {
  clearTokens(); // a stale token must not be sent with a public sign-up
  return api("/auth/register/", { method: "POST", body: fields });
}

export function logout() {
  clearTokens();
}
