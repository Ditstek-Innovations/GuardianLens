import type { CorrectableField } from '@/constants/events';

export interface FieldCorrection {
  readonly field: CorrectableField;
  readonly value: string;
}

/**
 * CS-T-08 — a decision carries a reason only when it is a rejection and a
 * correction only when it is a correction (RULE_BOOK D3). Illegal states are
 * unrepresentable. There is deliberately no reviewer identity here: it comes
 * from the session token only (BR-S-01, CS-B-05).
 */
export type Decision =
  | { readonly type: 'accept' }
  | { readonly type: 'reject'; readonly reason: string }
  | { readonly type: 'correct'; readonly correction: FieldCorrection };
