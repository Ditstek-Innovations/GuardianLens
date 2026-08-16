import { forwardRef, useId } from 'react';

import { cn } from '@/lib/utils/cn';

import type { InputHTMLAttributes } from 'react';

export interface CheckboxProps
  extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'className'> {
  readonly label: string;
  readonly hint?: string;
}

/**
 * §12.1 — a native checkbox (real keyboard/AT semantics for free), styled
 * with the design tokens via accent-color; the label is always clickable.
 */
export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, hint, ...props }, ref) => {
    const id = useId();
    const hintId = `${id}-hint`;
    return (
      <div className="flex items-start gap-2.5">
        <input
          ref={ref}
          id={id}
          type="checkbox"
          aria-describedby={hint !== undefined ? hintId : undefined}
          className={cn(
            'mt-0.5 h-4 w-4 shrink-0 cursor-pointer rounded border-border accent-brand-500',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2 focus-visible:ring-offset-bg',
          )}
          {...props}
        />
        <span className="min-w-0">
          <label htmlFor={id} className="cursor-pointer text-sm text-fg">
            {label}
          </label>
          {hint !== undefined ? (
            <p id={hintId} className="mt-0.5 text-xs text-fg-muted">
              {hint}
            </p>
          ) : null}
        </span>
      </div>
    );
  },
);
Checkbox.displayName = 'Checkbox';
