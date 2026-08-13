import { forwardRef } from 'react';

import { cn } from '@/lib/utils/cn';

import type { InputHTMLAttributes } from 'react';

export type InputProps = InputHTMLAttributes<HTMLInputElement>;

// §12.1 density — forms are comfortable: 44px controls. Fields sit on
// surface-2 with a hairline border; error state rides aria-invalid, which
// FormField sets (CS-FM-03) — no bespoke error styling per screen.
export const FIELD_CLASS =
  'h-11 w-full rounded-control border border-border bg-surface-2 px-3 text-base text-fg ' +
  'placeholder:text-fg-faint hover:border-border-strong ' +
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 ' +
  'aria-invalid:border-danger aria-invalid:focus-visible:ring-danger ' +
  'disabled:opacity-50 motion-safe:transition-colors motion-safe:duration-120 motion-safe:ease-out';

export const Input = forwardRef<HTMLInputElement, InputProps>(({ className, ...rest }, ref) => (
  <input ref={ref} className={cn(FIELD_CLASS, className)} {...rest} />
));

Input.displayName = 'Input';
