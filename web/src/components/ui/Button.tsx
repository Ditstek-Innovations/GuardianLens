import { forwardRef } from 'react';

import { cn } from '@/lib/utils/cn';
import { Spinner } from '@/components/ui/Spinner';

import type { ButtonHTMLAttributes, ReactNode } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ok' | 'ghost';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  readonly variant?: ButtonVariant;
  readonly size?: ButtonSize;
  readonly isLoading?: boolean;
  readonly children: ReactNode;
}

// CS-U-04 / CS-Y-05 — variants resolve through a closed lookup record.
// Primary: brand-500 fill with the deep-cyan fill ink (white fails CS-A-08 on
// cyan — see tokens.css) and the §12.1 glow; hover brightens to 400.
// ok / danger: solid status fills for the decision path, white ink ≥4.5:1.
const VARIANT_CLASS: Record<ButtonVariant, string> = {
  primary: 'bg-brand-500 font-semibold text-brand-fill-ink shadow-glow hover:bg-brand-400',
  secondary: 'border border-border bg-surface-3 text-fg hover:border-border-strong hover:bg-surface-2',
  danger: 'bg-danger-solid text-white hover:bg-danger-solid-hover',
  ok: 'bg-ok-solid text-white hover:bg-ok-solid-hover',
  ghost: 'text-fg-muted hover:bg-surface-2 hover:text-fg',
};

const SIZE_CLASS: Record<ButtonSize, string> = {
  sm: 'h-9 px-3 text-sm',
  md: 'h-11 px-4 text-sm',
  lg: 'h-12 px-6 text-base',
};

const BASE_CLASS =
  'inline-flex select-none items-center justify-center gap-2 rounded-control font-medium ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 ' +
  'disabled:pointer-events-none disabled:opacity-50 ' +
  // CS-Y-12 — 120ms ease-out feedback, active press, all motion-safe gated.
  'motion-safe:transition motion-safe:duration-120 motion-safe:ease-out motion-safe:active:scale-98';

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    { variant = 'primary', size = 'md', isLoading = false, disabled, className, children, ...rest },
    ref,
  ) => (
    <button
      ref={ref}
      type="button"
      // `disabled || isLoading` is deliberate: `??` would leave the button live
      // mid-request when a caller passes disabled={false} — a double-submit
      // path on the decision endpoint.
      disabled={disabled || isLoading}
      aria-busy={isLoading}
      className={cn(BASE_CLASS, VARIANT_CLASS[variant], SIZE_CLASS[size], className)}
      {...rest}
    >
      {isLoading ? <Spinner /> : null}
      {children}
    </button>
  ),
);

Button.displayName = 'Button';
