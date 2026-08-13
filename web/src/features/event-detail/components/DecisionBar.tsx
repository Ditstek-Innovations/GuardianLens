import { useCallback } from 'react';

import { Button, Kbd } from '@/components/ui';
import { DECISION_KEY } from '@/constants/events';
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut';

export type DecisionIntent = 'accept' | 'reject' | 'correct';

export interface DecisionBarProps {
  readonly disabled: boolean;
  readonly isSubmitting: boolean;
  readonly onIntent: (intent: DecisionIntent) => void;
}

/**
 * NFR-ACC-01 / TRD §7.4 — keyboard-operable A / R / C on real <button>s with
 * aria-keyshortcuts. `disabled` is not cosmetic: the actions stay disabled
 * until the evidence frame has rendered (CS-P-05, ADR-013, F-6) — a decision
 * recorded against a frame the reviewer has not seen is a BR-004 failure.
 */
export const DecisionBar = ({ disabled, isSubmitting, onIntent }: DecisionBarProps) => {
  const isInactive = disabled || isSubmitting;

  const handleAccept = useCallback(() => {
    onIntent('accept');
  }, [onIntent]);
  const handleReject = useCallback(() => {
    onIntent('reject');
  }, [onIntent]);
  const handleCorrect = useCallback(() => {
    onIntent('correct');
  }, [onIntent]);

  useKeyboardShortcut(DECISION_KEY.ACCEPT, handleAccept, { enabled: !isInactive });
  useKeyboardShortcut(DECISION_KEY.REJECT, handleReject, { enabled: !isInactive });
  useKeyboardShortcut(DECISION_KEY.CORRECT, handleCorrect, { enabled: !isInactive });

  return (
    // §12.1 — the decision bar is a prominent, bottom-anchored card: the
    // three actions with their visible key hints (CS-A-11), ok / danger /
    // secondary styled per status semantics.
    <div
      role="group"
      aria-label="Decision actions"
      className="sticky bottom-4 z-30 flex flex-wrap items-center gap-3 rounded-card border border-border bg-surface-1 p-4 shadow-modal"
    >
      <Button variant="ok" onClick={handleAccept} disabled={isInactive} aria-keyshortcuts="a">
        Accept
        <Kbd className="border-ok-solid-hover bg-ok-solid-hover text-white">A</Kbd>
      </Button>
      <Button variant="danger" onClick={handleReject} disabled={isInactive} aria-keyshortcuts="r">
        Reject
        <Kbd className="border-danger-solid-hover bg-danger-solid-hover text-white">R</Kbd>
      </Button>
      <Button
        variant="secondary"
        onClick={handleCorrect}
        disabled={isInactive}
        aria-keyshortcuts="c"
      >
        Correct
        <Kbd>C</Kbd>
      </Button>
      {disabled ? (
        <span className="text-sm text-fg-muted">
          Decisions enable once the evidence frame has loaded.
        </span>
      ) : null}
    </div>
  );
};
