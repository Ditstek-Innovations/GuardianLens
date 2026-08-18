import { useState } from 'react';

import { Button, ErrorState, Skeleton } from '@/components/ui';

import type { ReactNode } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';

export interface ConfigSectionProps<T> {
  readonly title: string;
  /** One sentence on what the section governs — admin screens carry weight (CS-AD). */
  readonly description?: string | undefined;
  readonly query: UseQueryResult<T[]>;
  readonly emptyDetail: string;
  readonly children: (items: T[]) => ReactNode;
  readonly actions?: ReactNode;
  /** Label for the button that reveals the form, e.g. "Add camera". */
  readonly actionLabel?: string | undefined;
}

/**
 * Shared loading / error / empty scaffolding for the configuration lists
 * (CS-D-07), composed as one panel card per section: a header strip with the
 * item count and an "Add …" toggle, the form ON DEMAND (collapsed by
 * default — the data is the page, the form is an occasional act), and the
 * list.
 */
export const ConfigSection = <T,>({
  title,
  description,
  query,
  emptyDetail,
  children,
  actions,
  actionLabel,
}: ConfigSectionProps<T>) => {
  const [isFormOpen, setIsFormOpen] = useState(false);

  let body: ReactNode;
  if (query.isPending) {
    // CS-Y-13 — skeleton rows inside the section card.
    body = (
      <div aria-label="Loading" className="space-y-2 p-4">
        <p className="sr-only">Loading…</p>
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-2/3" />
      </div>
    );
  } else if (query.isError || query.data === undefined) {
    body = (
      <div className="p-4">
        <ErrorState title={`${title} could not be loaded.`} onRetry={() => void query.refetch()} />
      </div>
    );
  } else if (query.data.length === 0) {
    body = <p className="px-4 py-6 text-sm text-fg-muted">{emptyDetail}</p>;
  } else {
    body = children(query.data);
  }

  return (
    <section
      aria-label={title}
      className="overflow-hidden rounded-card border border-border bg-surface-1 shadow-ambient"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-fg">{title}</h2>
            {query.data !== undefined ? (
              <span className="rounded-full bg-surface-3 px-2 py-0.5 text-xs font-medium tabular-nums text-fg-muted">
                {query.data.length}
              </span>
            ) : null}
          </div>
          {description !== undefined ? (
            <p className="mt-0.5 text-sm text-fg-muted">{description}</p>
          ) : null}
        </div>
        {actions !== undefined ? (
          <Button
            variant="secondary"
            size="sm"
            aria-expanded={isFormOpen}
            onClick={() => setIsFormOpen((current) => !current)}
          >
            {isFormOpen ? 'Close' : (actionLabel ?? 'Add')}
          </Button>
        ) : null}
      </div>
      {actions !== undefined && isFormOpen ? (
        <div className="border-b border-border px-4 py-4">{actions}</div>
      ) : null}
      <div className="overflow-x-auto">{body}</div>
    </section>
  );
};
