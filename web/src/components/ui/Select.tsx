import { forwardRef } from 'react';

import { FIELD_CLASS } from '@/components/ui/Input';
import { cn } from '@/lib/utils/cn';

import type { SelectHTMLAttributes } from 'react';

export type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

/**
 * Native select with the §12.1 field treatment. The OS-drawn arrow is
 * replaced by an inline chevron (no icon font, no external asset) so the
 * control reads identically on both themes; the select itself stays native
 * for keyboard and screen-reader behaviour.
 */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, ...rest }, ref) => (
    <span className="relative block">
      <select
        ref={ref}
        className={cn(FIELD_CLASS, 'appearance-none pr-9', className)}
        {...rest}
      >
        {children}
      </select>
      <svg
        aria-hidden="true"
        focusable="false"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-fg-muted"
      >
        <path d="m6 9.5 6 6 6-6" />
      </svg>
    </span>
  ),
);

Select.displayName = 'Select';
