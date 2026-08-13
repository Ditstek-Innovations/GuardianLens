import { forwardRef } from 'react';

import { cn } from '@/lib/utils/cn';

import type { ButtonHTMLAttributes } from 'react';

export type RowButtonProps = ButtonHTMLAttributes<HTMLButtonElement>;

/** Full-width list-row action target (queue rows). Domain-blind. */
export const RowButton = forwardRef<HTMLButtonElement, RowButtonProps>(
  ({ className, children, ...rest }, ref) => (
    <button
      ref={ref}
      type="button"
      className={cn(
        'block w-full border-l-2 border-transparent px-4 py-2.5 text-left',
        'hover:bg-surface-2 motion-safe:transition-colors motion-safe:duration-120 motion-safe:ease-out',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-400',
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  ),
);

RowButton.displayName = 'RowButton';
