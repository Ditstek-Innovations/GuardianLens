import { REFRESH_TOKEN_STORAGE_KEY } from '@/constants/storage';

/**
 * TRD §12.2 — access token (15 min) + rotating refresh token (7 days).
 *
 * The access token is held IN MEMORY ONLY, always (CS-AU-07). The refresh
 * credential persists so the session survives a reload — WHERE it persists
 * is the user's explicit choice at sign-in (CS-AU-19):
 *
 *   - default: sessionStorage — dies with the tab, invisible to other tabs;
 *   - "Keep me signed in": localStorage — survives browser restarts on this
 *     device, bounded server-side by the 7-day refresh TTL.
 *
 * Threat model (CS-SEC-06 requires this documented): script injected into
 * the origin could read either store — the same script could equally capture
 * tokens from memory or drive the authenticated client directly, so
 * persistence adds no new capability to that attacker; CSP is the defence
 * against injection (CS-SEC-09). What localStorage DOES change: the
 * credential outlives the tab and is readable from any tab of this origin —
 * which is exactly the behaviour the user opts into, on what they judge to
 * be their own device. Rotation with reuse detection (TRD §12.2) revokes the
 * whole family server-side if a stolen copy is ever replayed, and sign-out
 * clears both stores. An httpOnly refresh cookie remains the stronger design
 * once the server can set and accept cookies for this SPA-only slice.
 */
export interface Tokens {
  readonly accessToken: string;
  readonly refreshToken: string;
}

let current: Tokens | null = null;
/** Where the refresh credential lives. Chosen at sign-in; rediscovered from
 * whichever store holds a credential after a reload; kept across rotations. */
let rememberDevice = false;
const listeners = new Set<() => void>();

/** Storage is an external boundary and may throw (private browsing) — the
 * session then simply lives in memory only (CS-G-13). */
const tryStorage = (kind: 'local' | 'session'): Storage | null => {
  try {
    return kind === 'local' ? window.localStorage : window.sessionStorage;
  } catch {
    return null;
  }
};

const persistRefreshToken = (token: string | null): void => {
  const local = tryStorage('local');
  const session = tryStorage('session');
  try {
    // Exactly one store may hold a credential; the other is always cleared
    // so a mode change (or sign-out) never leaves a stale copy behind.
    if (token === null) {
      local?.removeItem(REFRESH_TOKEN_STORAGE_KEY);
      session?.removeItem(REFRESH_TOKEN_STORAGE_KEY);
      return;
    }
    (rememberDevice ? local : session)?.setItem(REFRESH_TOKEN_STORAGE_KEY, token);
    (rememberDevice ? session : local)?.removeItem(REFRESH_TOKEN_STORAGE_KEY);
  } catch {
    // Storage unavailable or full — nothing persisted; memory still works.
  }
};

export const tokenStore = {
  get: (): Tokens | null => current,
  /** `remember` is meaningful at sign-in; omitted (rotation, restore) keeps
   * the mode already in force. */
  set: (tokens: Tokens | null, options?: { remember?: boolean }): void => {
    if (options?.remember !== undefined) rememberDevice = options.remember;
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
  /** The refresh credential left by a previous load, if any. Checking
   * localStorage first also restores the remember-mode it implies, so
   * later rotations keep writing to the store the user chose. */
  persistedRefreshToken: (): string | null => {
    const local = tryStorage('local');
    const session = tryStorage('session');
    try {
      const remembered = local?.getItem(REFRESH_TOKEN_STORAGE_KEY) ?? null;
      if (remembered !== null) {
        rememberDevice = true;
        return remembered;
      }
      const tabScoped = session?.getItem(REFRESH_TOKEN_STORAGE_KEY) ?? null;
      if (tabScoped !== null) rememberDevice = false;
      return tabScoped;
    } catch {
      return null;
    }
  },
};
