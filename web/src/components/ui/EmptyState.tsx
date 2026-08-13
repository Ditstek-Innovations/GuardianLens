import type { ReactNode } from 'react';

export interface EmptyStateProps {
  readonly title: string;
  readonly detail?: string | undefined;
  readonly icon?: ReactNode | undefined;
  readonly action?: ReactNode | undefined;
}

const InboxIcon = () => (
  <svg
    aria-hidden="true"
    focusable="false"
    width="28"
    height="28"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={1.5}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M22 12h-6l-2 3h-4l-2-3H2" />
    <path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11Z" />
  </svg>
);

/**
 * CS-Y-13 / CS-D-07 — empty is a designed state: icon, one-line explanation,
 * optional action. Never a blank region.
 */
export const EmptyState = ({ title, detail, icon, action }: EmptyStateProps) => (
  <div className="flex flex-col items-center rounded-card border border-border bg-surface-1 px-8 py-12 text-center shadow-ambient">
    <span className="text-fg-faint">{icon ?? <InboxIcon />}</span>
    <p className="mt-3 text-base font-medium text-fg">{title}</p>
    {detail !== undefined ? <p className="mt-1 max-w-sm text-sm text-fg-muted">{detail}</p> : null}
    {action !== undefined ? <div className="mt-4">{action}</div> : null}
  </div>
);
