// Client-side session handling. The password is NEVER stored or checked here —
// it is verified server-side by POST /api/auth/login, which returns a signed,
// time-limited token. This module only remembers that token to gate the UI.

const BASE_URL = import.meta.env.VITE_API_URL || '';
const TOKEN_KEY = 'kintix_auth_token';
const EMAIL_KEY = 'kintix_auth_email';
const EXPIRY_KEY = 'kintix_auth_expiry';

export async function login(email: string, password: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    let detail = 'Login failed. Please try again.';
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      // response had no JSON body
    }
    throw new Error(detail);
  }

  const data: { token: string; email: string; expires_at: number } = await res.json();
  try {
    localStorage.setItem(TOKEN_KEY, data.token);
    localStorage.setItem(EMAIL_KEY, data.email);
    localStorage.setItem(EXPIRY_KEY, String(data.expires_at));
  } catch {
    // localStorage unavailable (private mode) — session lasts this tab only
  }
}

export function logout(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_KEY);
    localStorage.removeItem(EXPIRY_KEY);
  } catch {
    // ignore
  }
}

export function isAuthenticated(): boolean {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) return false;
    const expiry = Number(localStorage.getItem(EXPIRY_KEY));
    if (expiry && Date.now() / 1000 > expiry) {
      logout();
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

export function getUserEmail(): string | null {
  try {
    return localStorage.getItem(EMAIL_KEY);
  } catch {
    return null;
  }
}
