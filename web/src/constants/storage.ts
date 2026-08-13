/**
 * TRD §7.3 / CS-FM-08 — a draft decision persists to sessionStorage so it
 * survives a token refresh mid-decision, and never to localStorage: it
 * concerns a candidate event and must not outlive the session.
 */
export const DECISION_DRAFT_KEY_PREFIX = 'gl.decision-draft.';

/**
 * CS-SEC-06 / CS-AU-07 — the refresh credential persists to sessionStorage
 * (never localStorage) so a signed-in session survives a hard reload of the
 * tab. See lib/api/tokenStore.ts for the documented threat model.
 */
export const REFRESH_TOKEN_STORAGE_KEY = 'gl.refresh-token';

/**
 * Theme preference (CS-Y-09 — dark default, `light` class variant). Lives in
 * localStorage deliberately: it is a device preference, not session state,
 * and must survive sign-out. Mirrored by the inline pre-hydration snippet in
 * index.html — keep the literal there in sync.
 */
export const THEME_STORAGE_KEY = 'gl.theme';
