import { cn } from '@/lib/utils/cn';

import type { ReactNode } from 'react';

export type ChipVariant = 'neutral' | 'ok' | 'warn' | 'danger' | 'brand';

export interface ChipProps {
  readonly variant?: ChipVariant;
  readonly icon?: ReactNode;
  readonly children: ReactNode;
  readonly className?: string | undefined;
}

// §12.1 — chips are full-radius, -subtle tinted grounds with the strong
// status ink on top. Status hues never appear without their text.
const VARIANT_CLASS: Record<ChipVariant, string> = {
  neutral: 'bg-surface-3 text-fg-muted',
  ok: 'bg-ok-subtle text-ok',
  warn: 'bg-warn-subtle text-warn',
  danger: 'bg-danger-subtle text-danger',
  brand: 'bg-brand-subtle text-brand-ink',
};

/**
 * NFR-ACC-02 / CS-A-02 — a chip always carries text (and usually an icon);
 * colour is never the sole signal.
 */
export const Chip = ({ variant = 'neutral', icon, children, className }: ChipProps) => (
  <span
    className={cn(
      'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-xs font-medium',
      VARIANT_CLASS[variant],
      className,
    )}
  >
    {icon}
    {children}
  </span>
);
