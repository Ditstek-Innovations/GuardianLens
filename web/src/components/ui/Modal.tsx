import { useEffect, useRef } from 'react';

import type { ReactNode } from 'react';

export interface ModalProps {
  readonly title: string;
  readonly onClose: () => void;
  readonly children: ReactNode;
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

/** CS-A-05 — traps focus, closes on Escape, restores focus to the trigger. */
export const Modal = ({ title, onClose, children }: ModalProps) => {
  const dialogRef = useRef<HTMLDivElement>(null);

  // Synchronising with the DOM focus system — a legitimate effect (CS-S-03).
  useEffect(() => {
    const previouslyFocused =
      document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    if (dialog === null) return undefined;

    const focusables = dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    (focusables[0] ?? dialog).focus();

    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== 'Tab') return;
      const items = dialog.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
      const first = items[0];
      const last = items[items.length - 1];
      if (first === undefined || last === undefined) return;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [onClose]);

  return (
    // §12.1 — modal radius 16, overlay token, hairline border + modal
    // elevation; 240ms entrance gated behind motion-safe (CS-Y-12).
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-overlay p-4 motion-safe:animate-fade-in">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className="w-full max-w-lg rounded-modal border border-border bg-surface-1 p-6 shadow-modal motion-safe:animate-modal-in"
      >
        <h2 className="mb-4 text-lg font-semibold text-fg">{title}</h2>
        {children}
      </div>
    </div>
  );
};
