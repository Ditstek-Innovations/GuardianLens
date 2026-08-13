/**
 * FRONTEND_CODING_STANDARDS §12.2 — THE outcome-message catalogue
 * (CS-MSG-02). Every user-facing operation outcome lives here, typed by
 * operation; a component that inlines an outcome string is duplicating this
 * file.
 *
 * Voice (CS-MSG-01): sentence case, outcome — consequence, no jargon, no
 * exclamation marks. "Success" / "Failed" / "Error occurred" are banned
 * strings — messages.test.ts enforces this over every value below.
 * Failures state the next step and never expose status codes or internal
 * error text (CS-MSG-05).
 */
export const MESSAGES = {
  decision: {
    /** BR-005 — an accept is attribution: the record carries the reviewer. */
    accepted: 'Recorded as a verified event — it now carries your name.',
    /** BR-007 — rejections are retained and visible, never discarded. */
    rejected: 'Recorded as rejected — it stays visible in the rejection log.',
    corrected: 'Correction recorded — the original model output is retained alongside it.',
    /** 409 — first decision wins (BR-V-04); the queue invalidates on settle. */
    conflict: 'Another reviewer decided this first — the queue has refreshed.',
    failed: 'The decision was not recorded. Check the connection and try again — nothing was saved.',
  },
  config: {
    ruleActivated: (ruleName: string): string =>
      `Rule active — “${ruleName}” is now monitored. Activation is recorded under your name.`,
    ruleDeactivated: (ruleName: string): string =>
      `Rule inactive — “${ruleName}” is no longer monitored. The change is recorded under your name.`,
    ruleChangeFailed:
      'The rule change was not applied. Check the connection and try again — monitoring is unchanged.',
    /** BR-S-03 / CS-AD-06 — the credential is write-only, stated plainly. */
    cameraSaved: 'Camera saved — the stream credential is stored and never shown again.',
    cameraSaveFailed:
      'The camera was not saved. Check the connection and try again — nothing was stored.',
    zoneSaved: 'Zone saved — its rules apply from the next edge sync.',
  },
  reports: {
    /** BR-R-02 — provenance rides along in the exported file. */
    exportReady: 'Export ready — the file includes the period and your name as generator.',
    exportFailed: 'The export did not complete. Check the connection and try again.',
  },
} as const;
