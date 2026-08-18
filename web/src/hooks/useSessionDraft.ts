import { useCallback, useState } from 'react';

import { DECISION_DRAFT_KEY_PREFIX } from '@/constants/storage';

export interface SessionDraft {
  readonly draft: string;
  readonly setDraft: (value: string) => void;
  readonly clearDraft: () => void;
}

/**
 * TRD §7.3 — a draft decision survives a token refresh mid-decision (F-4).
 * sessionStorage only (CS-FM-08): the draft concerns a candidate event and
 * must not outlive the session. Storage is an external boundary and may throw
 * (private browsing) — the draft then simply stays in memory (CS-G-13).
 */
export const useSessionDraft = (eventId: string): SessionDraft => {
  const key = `${DECISION_DRAFT_KEY_PREFIX}${eventId}`;
  const [draft, setDraftState] = useState<string>(() => {
    try {
      return window.sessionStorage.getItem(key) ?? '';
    } catch {
      return '';
    }
  });

  const setDraft = useCallback(
    (value: string) => {
      setDraftState(value);
      try {
        window.sessionStorage.setItem(key, value);
      } catch {
        // Storage unavailable — draft stays in memory only.
      }
    },
    [key],
  );

  const clearDraft = useCallback(() => {
    setDraftState('');
    try {
      window.sessionStorage.removeItem(key);
    } catch {
      // Storage unavailable — nothing to clear.
    }
  }, [key]);

  return { draft, setDraft, clearDraft };
};
