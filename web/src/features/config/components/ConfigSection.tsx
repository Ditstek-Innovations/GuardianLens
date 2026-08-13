import { ErrorState, Skeleton } from '@/components/ui';

import type { ReactNode } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';

export interface ConfigSectionProps<T> {
  readonly title: string;
  readonly query: UseQueryResult<T[]>;
  readonly emptyDetail: string;
  readonly children: (items: T[]) => ReactNode;
  readonly actions?: ReactNode;
}

/** Shared loading / error / empty scaffolding for the configuration lists (CS-D-07). */
export const ConfigSection = <T,>({
  title,
  query,
  emptyDetail,
  children,
  actions,
}: ConfigSectionProps<T>) => {
  let body: ReactNode;
  if (query.isPending) {
    // CS-Y-13 — skeleton rows inside the section card.
    body = (
      <div aria-label="Loading" className="space-y-2 p-4">
        <p className="sr-only">Loading…</p>
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-8 w-2/3" />
      </div>
    );
  } else if (query.isError || query.data === undefined) {
    body = (
      <ErrorState
        title={`${title} could not be loaded.`}
        onRetry={() => void query.refetch()}
      />
    );
  } else if (query.data.length === 0) {
    body = <p className="p-4 text-sm text-fg-muted">{emptyDetail}</p>;
  } else {
    body = children(query.data);
  }

  return (
    <section aria-label={title} className="space-y-3">
      <h2 className="text-lg font-semibold text-fg">{title}</h2>
      {actions}
      <div className="overflow-x-auto rounded-card border border-border bg-surface-1 shadow-ambient">{body}</div>
    </section>
  );
};
