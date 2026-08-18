import { cn } from '@/lib/utils/cn';

export interface SkeletonProps {
  readonly className?: string | undefined;
}

/**
 * CS-Y-13 / CS-D-07 — loading is a designed state. The shimmer runs only
 * under `prefers-reduced-motion: no-preference` (CS-A-12); without it the
 * block is a static surface-3 placeholder. Purely decorative: containers
 * that use it must still carry a text loading signal for assistive tech.
 */
export const Skeleton = ({ className }: SkeletonProps) => (
  <div
    aria-hidden="true"
    className={cn(
      'rounded-control bg-surface-3 motion-safe:animate-shimmer motion-safe:bg-shimmer',
      className,
    )}
  />
);
