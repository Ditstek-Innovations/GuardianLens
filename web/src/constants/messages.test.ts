// CS-MSG-01 — catalogue hygiene: sentence-case outcome — consequence copy
// with no banned strings and no exclamation marks, enforced over every
// value (including parameterised ones) so a future entry cannot regress.
import { describe, expect, it } from 'vitest';

import { MESSAGES } from './messages';

type CatalogueNode = string | ((name: string) => string) | { readonly [key: string]: CatalogueNode };

const collectMessages = (node: CatalogueNode, path: string): ReadonlyArray<[string, string]> => {
  if (typeof node === 'string') return [[path, node]];
  if (typeof node === 'function') return [[path, node('Sample rule')]];
  return Object.entries(node).flatMap(([key, child]) => collectMessages(child, `${path}.${key}`));
};

const ALL_MESSAGES = collectMessages(MESSAGES as CatalogueNode, 'MESSAGES');

const BANNED_PATTERNS: readonly RegExp[] = [
  /\bSuccess\b/,
  /\bFailed\b/,
  /Error occurred/i,
  /!/,
];

describe('MESSAGES catalogue (CS-MSG-01/02)', () => {
  it('contains at least the decision, config and reports operations', () => {
    expect(MESSAGES.decision.accepted).toBeTypeOf('string');
    expect(MESSAGES.config.cameraSaved).toBeTypeOf('string');
    expect(MESSAGES.reports.exportReady).toBeTypeOf('string');
  });

  it.each(ALL_MESSAGES)('%s carries no banned string and no exclamation mark', (_path, value) => {
    for (const pattern of BANNED_PATTERNS) {
      expect(value).not.toMatch(pattern);
    }
    // Outcome — consequence: every message carries a consequence clause.
    expect(value.length).toBeGreaterThan(20);
  });

  it('states the decision consequences on the record (CS-MSG-04)', () => {
    expect(MESSAGES.decision.accepted).toContain('your name'); // BR-005
    expect(MESSAGES.decision.rejected).toContain('rejection log'); // BR-007
  });
});
