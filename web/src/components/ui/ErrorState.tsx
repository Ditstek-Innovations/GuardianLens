import { Button } from '@/components/ui/Button';

export interface ErrorStateProps {
  readonly title: string;
  readonly detail?: string | undefined;
  readonly onRetry?: (() => void) | undefined;
}

const AlertTriangleIcon = () => (
  <svg
    aria-hidden="true"
    focusable="false"
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
    <path d="M12 9v4" />
    <path d="M12 17h.01" />
  </svg>
);

/**
 * CS-Y-13 / CS-D-08 — error is a designed state: icon, a human-readable
 * message and a recovery action; never silent, never colour alone.
 */
export const ErrorState = ({ title, detail, onRetry }: ErrorStateProps) => (
  <div role="alert" className="flex gap-3 rounded-card border border-danger bg-danger-subtle p-5">
    <span className="mt-0.5 shrink-0 text-danger">
      <AlertTriangleIcon />
    </span>
    <div>
      <p className="font-medium text-danger">{title}</p>
      {detail !== undefined ? <p className="mt-1 text-sm text-danger">{detail}</p> : null}
      {onRetry !== undefined ? (
        <Button variant="secondary" size="sm" className="mt-3" onClick={onRetry}>
          Retry
        </Button>
      ) : null}
    </div>
  </div>
);
