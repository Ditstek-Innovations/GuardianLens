/**
 * ADR-007 — after an outage, replayed events carry an old occurred_at and a
 * new received_at; the UI must make the delay visible or a reviewer will read
 * a stale candidate as current. A candidate received more than this long
 * after observation is flagged as delayed.
 */
export const DELAYED_EVENT_THRESHOLD_MS = 5 * 60_000;

/** How long the "already decided" notice is shown before auto-advancing (F-2/F-3). */
export const CONFLICT_ADVANCE_DELAY_MS = 4_000;

/** CS-MSG-03 — success toasts auto-dismiss after this; failures persist. */
export const TOAST_AUTO_DISMISS_MS = 5_000;
