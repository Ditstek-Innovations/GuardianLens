import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { ChipIcon } from '@/components/ui/ChipIcon';
import { TOAST_AUTO_DISMISS_MS } from '@/constants/time';
import { ToastContext } from '@/hooks/useToast';
import { cn } from '@/lib/utils/cn';

import type { KeyboardEvent, ReactNode } from 'react';
import type { ChipGlyph } from '@/components/ui/ChipIcon';
import type { ToastInput, ToastTone } from '@/hooks/useToast';

/**
 * CS-MSG-03 / CS-SH-07 — THE toast surface. One region, mounted once by the
 * shell through ToastProvider; each toast is its own announcer (role=status
 * for success/notice, role=alert for failure) so outcomes are announced
 * exactly once — no second aria-live region exists for outcomes.
 *
 * Success and notice auto-dismiss after 5 s, pausing while hovered or while
 * focus is inside; failure persists until dismissed. Every toast has a
 * visible close button and dismisses on Escape when focused. Max 3 stacked;
 * the oldest collapses.
 */

const MAX_STACKED_TOASTS = 3;

interface ToastItem extends ToastInput {
  readonly id: number;
}

interface TonePresentation {
  readonly glyph: ChipGlyph;
  readonly iconClass: string;
  readonly role: 'status' | 'alert';
  readonly autoDismisses: boolean;
}

// CS-Y-05 — tone resolves through a closed lookup record. Icon + text,
// never colour alone (CS-A-02).
const TONE_PRESENTATION: Record<ToastTone, TonePresentation> = {
  success: { glyph: 'check', iconClass: 'text-ok', role: 'status', autoDismisses: true },
  failure: { glyph: 'cross', iconClass: 'text-danger', role: 'alert', autoDismisses: false },
  notice: { glyph: 'alert', iconClass: 'text-warn', role: 'status', autoDismisses: true },
};

const ToastCard = ({
  toast,
  onDismiss,
}: {
  readonly toast: ToastItem;
  readonly onDismiss: (id: number) => void;
}) => {
  const presentation = TONE_PRESENTATION[toast.tone];
  const [isPaused, setIsPaused] = useState(false);

  // Auto-dismiss timer — suspended while hovered or focused (CS-MSG-03).
  useEffect(() => {
    if (!presentation.autoDismisses || isPaused) return undefined;
    const timer = window.setTimeout(() => {
      onDismiss(toast.id);
    }, TOAST_AUTO_DISMISS_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, [presentation.autoDismisses, isPaused, onDismiss, toast.id]);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onDismiss(toast.id);
    }
  };

  return (
    <div
      role={presentation.role}
      onKeyDown={handleKeyDown}
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
      onFocus={() => setIsPaused(true)}
      onBlur={() => setIsPaused(false)}
      className="pointer-events-auto flex items-start gap-3 rounded-card border border-border bg-surface-1 p-4 shadow-ambient motion-safe:animate-toast-in"
    >
      <span aria-hidden="true" className={cn('mt-0.5 shrink-0', presentation.iconClass)}>
        <ChipIcon glyph={presentation.glyph} />
      </span>
      <p className="min-w-0 flex-1 text-sm text-fg">{toast.message}</p>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        aria-label="Dismiss notification"
        className="shrink-0 rounded-sm p-0.5 text-fg-muted hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
      >
        <ChipIcon glyph="cross" />
      </button>
    </div>
  );
};

export interface ToastProviderProps {
  readonly children: ReactNode;
}

export const ToastProvider = ({ children }: ToastProviderProps) => {
  const [toasts, setToasts] = useState<readonly ToastItem[]>([]);
  const nextIdRef = useRef(0);

  const showToast = useCallback((input: ToastInput): void => {
    setToasts((current) => {
      const next = [...current, { ...input, id: nextIdRef.current++ }];
      // Max 3 stacked — the oldest collapses (CS-MSG-03).
      return next.length > MAX_STACKED_TOASTS ? next.slice(next.length - MAX_STACKED_TOASTS) : next;
    });
  }, []);

  const dismissToast = useCallback((id: number): void => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const value = useMemo(() => ({ showToast }), [showToast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* CS-SH-07 — the single outcome region, below the sticky header. */}
      <div
        aria-label="Notifications"
        className="pointer-events-none fixed right-4 top-16 z-50 flex w-80 max-w-full flex-col gap-2"
      >
        {toasts.map((toast) => (
          <ToastCard key={toast.id} toast={toast} onDismiss={dismissToast} />
        ))}
      </div>
    </ToastContext.Provider>
  );
};
