export const EVENT_STATUS = {
  UNVERIFIED: 'unverified',
  ACCEPTED: 'accepted',
  CORRECTED: 'corrected',
  REJECTED: 'rejected',
  EXPIRED: 'expired',
} as const;

export type EventStatus = (typeof EVENT_STATUS)[keyof typeof EVENT_STATUS];

// Keyboard bindings are a product requirement (TRD §7.4, NFR-ACC-01) — not a
// magic string.
export const DECISION_KEY = {
  ACCEPT: 'a',
  REJECT: 'r',
  CORRECT: 'c',
} as const;

export const QUEUE_NAV_KEY = {
  NEXT: ['j', 'arrowdown'],
  PREVIOUS: ['k', 'arrowup'],
} as const;

/** Fields a `correct` decision may amend (TRD §10.4 corrections payload). */
export const CORRECTABLE_FIELD = {
  ZONE: 'zone_id',
  RULE: 'rule_id',
} as const;

export type CorrectableField = (typeof CORRECTABLE_FIELD)[keyof typeof CORRECTABLE_FIELD];
