import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { StatusChip } from '@/components/StatusChip';
import { Button, ErrorState, Skeleton } from '@/components/ui';
import { EVENT_STATUS } from '@/constants/events';
import { ROUTES } from '@/constants/routes';
import { formatTimestamp } from '@/lib/format/formatTimestamp';

import { useDecidedEvents } from '../api/useDecidedEvents';

import type { QueueEventItem } from '@/lib/api/types';
import type { ReportParams } from '../types';

const VISIBLE_PAGE_SIZE = 10;

const EventList = ({
  items,
  total,
  emptyText,
  hasMore,
  isLoadingMore,
  onLoadMore,
}: {
  items: QueueEventItem[];
  total: number;
  emptyText: string;
  hasMore: boolean;
  isLoadingMore: boolean;
  onLoadMore: () => Promise<void>;
}) => {
  const [page, setPage] = useState(0);
  const totalPages = Math.max(1, Math.ceil(total / VISIBLE_PAGE_SIZE));

  useEffect(() => {
    setPage((current) => Math.min(current, totalPages - 1));
  }, [totalPages]);

  if (items.length === 0) {
    return <p className="px-4 py-3 text-sm text-fg-muted">{emptyText}</p>;
  }
  const start = page * VISIBLE_PAGE_SIZE;
  const visibleItems = items.slice(start, start + VISIBLE_PAGE_SIZE);

  const handleNext = async (): Promise<void> => {
    const nextPage = page + 1;
    if (nextPage >= totalPages) return;
    if ((nextPage + 1) * VISIBLE_PAGE_SIZE > items.length && hasMore) {
      await onLoadMore();
    }
    setPage(nextPage);
  };

  return (
    <>
      <ul className="divide-y divide-border">
        {visibleItems.map((item) => (
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
      <div className="flex items-center justify-between gap-3 border-t border-border px-4 py-3">
        <p className="text-xs tabular-nums text-fg-muted">
          Page {page + 1} of {totalPages} · {total} records
        </p>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            disabled={page === 0}
            onClick={() => setPage((current) => Math.max(0, current - 1))}
          >
            Previous
          </Button>
          <Button
            variant="secondary"
            size="sm"
            disabled={page + 1 >= totalPages}
            isLoading={isLoadingMore}
            onClick={() => void handleNext()}
          >
            Next
          </Button>
        </div>
      </div>
    </>
  );
};

const flattenPages = (pages: { items: QueueEventItem[] }[] | undefined): QueueEventItem[] =>
  pages?.flatMap((page) => page.items) ?? [];

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

  const passed = [
    ...flattenPages(accepted.data?.pages),
    ...flattenPages(corrected.data?.pages),
  ];
  const failed = flattenPages(rejected.data?.pages);
  const totalPassed =
    (accepted.data?.pages[0]?.queue_depth ?? 0) +
    (corrected.data?.pages[0]?.queue_depth ?? 0);
  const totalFailed = rejected.data?.pages[0]?.queue_depth ?? 0;

  const loadMorePassed = async (): Promise<void> => {
    await Promise.all([
      accepted.hasNextPage ? accepted.fetchNextPage() : Promise.resolve(),
      corrected.hasNextPage ? corrected.fetchNextPage() : Promise.resolve(),
    ]);
  };

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <section
        aria-label="Verified records of the period"
        className="rounded-card border border-border bg-surface-1 shadow-ambient"
      >
        <h3 className="border-b border-border px-4 py-3 text-sm font-semibold text-fg">
          Passed review — verified records ({totalPassed})
        </h3>
        <EventList
          items={passed}
          total={totalPassed}
          emptyText="No candidate was accepted in this period."
          hasMore={accepted.hasNextPage || corrected.hasNextPage}
          isLoadingMore={accepted.isFetchingNextPage || corrected.isFetchingNextPage}
          onLoadMore={loadMorePassed}
        />
      </section>
      <section
        aria-label="Rejected candidates of the period"
        className="rounded-card border border-border bg-surface-1 shadow-ambient"
      >
        <h3 className="border-b border-border px-4 py-3 text-sm font-semibold text-fg">
          Did not pass — rejected ({totalFailed})
        </h3>
        <EventList
          items={failed}
          total={totalFailed}
          emptyText="No candidate was rejected in this period."
          hasMore={rejected.hasNextPage}
          isLoadingMore={rejected.isFetchingNextPage}
          onLoadMore={async () => {
            await rejected.fetchNextPage();
          }}
        />
      </section>
    </div>
  );
};
