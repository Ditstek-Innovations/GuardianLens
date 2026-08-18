import { createContext, useContext } from 'react';

/**
 * §12.2 — the toast channel carries operation outcomes only; validation and
 * credential errors stay inline (CS-FM-03, CS-AU-04). The provider (and its
 * single region/announcer) is mounted ONCE, by AppShell (CS-SH-07) — auth
 * screens render outside it and deliberately have no toast surface
 * (CS-MSG-04).
 */

/** success — polite, auto-dismisses · failure — assertive, persists ·
 *  notice — warn-styled but informational: polite, auto-dismisses. */
export type ToastTone = 'success' | 'failure' | 'notice';

export interface ToastInput {
  readonly tone: ToastTone;
  readonly message: string;
}

export interface ToastContextValue {
  readonly showToast: (toast: ToastInput) => void;
}

export const ToastContext = createContext<ToastContextValue | null>(null);

export const useToast = (): ToastContextValue => {
  const value = useContext(ToastContext);
  if (value === null) throw new Error('useToast must be used within ToastProvider');
  return value;
};
