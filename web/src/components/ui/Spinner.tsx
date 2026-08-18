import { cn } from '@/lib/utils/cn';

export interface SpinnerProps {
  readonly className?: string | undefined;
}

/** Decorative motion only — loading states always carry text too (CS-D-07, CS-A-12). */
export const Spinner = ({ className }: SpinnerProps) => (
  <span
    aria-hidden="true"
    className={cn(
      'inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent motion-reduce:animate-none',
      className,
    )}
  />
);
