import { cn } from '@/lib/utils/cn';

import type { ReactNode } from 'react';

export interface KbdProps {
  readonly children: ReactNode;
  readonly className?: string | undefined;
}

/**
 * CS-A-11 — every keyboard shortcut has a visible affordance. A keycap:
 * surface-3 ground, hairline border with a stronger bottom edge, radius 6,
 * tabular figures so hint rows align.
 */
export const Kbd = ({ children, className }: KbdProps) => (
  <kbd
    className={cn(
      'inline-flex h-5 min-w-5 items-center justify-center rounded-sm border border-border border-b-border-strong bg-surface-3 px-1 font-sans text-xs font-medium tabular-nums text-fg-muted',
      className,
    )}
  >
    {children}
  </kbd>
);
