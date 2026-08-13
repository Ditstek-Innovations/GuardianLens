import { REFRESH_TOKEN_STORAGE_KEY } from '@/constants/storage';

/**
 * TRD §12.2 — access token (15 min) + rotating refresh token (7 days).
 *
 * The access token is held IN MEMORY ONLY (CS-AU-07). The refresh credential
 * additionally persists to sessionStorage so the session survives a hard
 * reload of the tab; localStorage is banned for either token (CS-SEC-06).
 *
 * Threat model for the persisted refresh credential (CS-SEC-06 requires this
 * to be documented): sessionStorage is per-tab and dies when the tab closes,
 * so the credential never outlives the tab and is invisible to other tabs.
 * Script injected into the origin could read it — the same script could
 * equally capture tokens from memory or drive the authenticated client
 * directly, so persistence adds no new capability to that attacker; CSP is
 * the defence against injection (CS-SEC-09). Rotation with reuse detection
 * (TRD §12.2) revokes the whole family server-side if a stolen copy is ever
 * replayed. An httpOnly refresh cookie remains the stronger design once the
 * server can set and accept cookies for this SPA-only slice.
 */
export interface Tokens {
  readonly accessToken: string;
  readonly refreshToken: string;
}

let current: Tokens | null = null;
const listeners = new Set<() => void>();

/** Storage is an external boundary and may throw (private browsing) — the
 * session then simply lives in memory only (CS-G-13). */
const persistRefreshToken = (token: string | null): void => {
  try {
    if (token === null) window.sessionStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);
    else window.sessionStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
  } catch {
    // Storage unavailable — nothing persisted, nothing to clear.
  }
};

export const tokenStore = {
  get: (): Tokens | null => current,
  set: (tokens: Tokens | null): void => {
    current = tokens;
    persistRefreshToken(tokens?.refreshToken ?? null);
    listeners.forEach((listener) => listener());
  },
  clear: (): void => {
    tokenStore.set(null);
  },
  subscribe: (listener: () => void): (() => void) => {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  },
  /** The refresh credential left by a previous load of this tab, if any. */
  persistedRefreshToken: (): string | null => {
    try {
      return window.sessionStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
    } catch {
      return null;
    }
  },
};
