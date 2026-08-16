import { Link } from 'react-router-dom';

import { StatusChip } from '@/components/StatusChip';
import { ErrorState, Skeleton } from '@/components/ui';
import { EVENT_STATUS } from '@/constants/events';
import { ROUTES } from '@/constants/routes';
import { formatTimestamp } from '@/lib/format/formatTimestamp';

import { useDecidedEvents } from '../api/useDecidedEvents';

import type { QueueEventItem } from '@/lib/api/types';
import type { ReportParams } from '../types';

const EventList = ({ items, emptyText }: { items: QueueEventItem[]; emptyText: string }) => {
  if (items.length === 0) {
    return <p className="px-4 py-3 text-sm text-fg-muted">{emptyText}</p>;
  }
  return (
    <ul className="divide-y divide-border">
      {items.map((item) => (
        <li key={item.id}>
          {/* Each row opens the full record: reviewer, timestamp, reason. */}
          <Link
            to={ROUTES.queueEvent(item.id)}
            className="flex items-center justify-between gap-4 px-4 py-2.5 transition-colors duration-120 hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
          >
            <div className="min-w-0">
              <p className="truncate text-sm text-fg">{item.rule.human_readable}</p>
              <p className="truncate text-xs tabular-nums text-fg-muted">
                {item.camera.name} · {formatTimestamp(item.occurred_at, item.site_timezone)}
              </p>
            </div>
            <StatusChip status={item.status} />
          </Link>
        </li>
      ))}
    </ul>
  );
};

/**
 * The analytics drill-down: every decision of the period, listed and
 * clickable through to its full record. BR-R-03 / BR-007 — accepted and
 * rejected are equally visible; nothing here is editable (BR-V-01).
 */
export const DecisionDrilldown = ({ params }: { params: ReportParams }) => {
  const accepted = useDecidedEvents(params, EVENT_STATUS.ACCEPTED);
  const corrected = useDecidedEvents(params, EVENT_STATUS.CORRECTED);
  const rejected = useDecidedEvents(params, EVENT_STATUS.REJECTED);

  if (accepted.isPending || corrected.isPending || rejected.isPending) {
    return (
      <div aria-label="Loading decisions" className="grid gap-4 xl:grid-cols-2">
        <Skeleton className="h-40 rounded-card" />
        <Skeleton className="h-40 rounded-card" />
      </div>
    );
  }
  if (accepted.isError || corrected.isError || rejected.isError) {
    return (
      <ErrorState
        title="The period's decisions could not be loaded."
        onRetry={() => {
          void accepted.refetch();
          void corrected.refetch();
          void rejected.refetch();
        }}
      />
    );
  }

  const passed = [...(accepted.data?.items ?? []), ...(corrected.data?.items ?? [])];
  const failed = rejected.data?.items ?? [];

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <section
        aria-label="Verified records of the period"
        className="rounded-card border border-border bg-surface-1 shadow-ambient"
      >
        <h3 className="border-b border-border px-4 py-3 text-sm font-semibold text-fg">
          Passed review — verified records ({passed.length})
        </h3>
        <EventList items={passed} emptyText="No candidate was accepted in this period." />
      </section>
      <section
        aria-label="Rejected candidates of the period"
        className="rounded-card border border-border bg-surface-1 shadow-ambient"
      >
        <h3 className="border-b border-border px-4 py-3 text-sm font-semibold text-fg">
          Did not pass — rejected ({failed.length})
        </h3>
        <EventList items={failed} emptyText="No candidate was rejected in this period." />
      </section>
    </div>
  );
};
