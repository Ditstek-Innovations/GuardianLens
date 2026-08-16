import { Link, useSearchParams } from 'react-router-dom';

import { PageHeading } from '@/components/layout/PageHeading';
import { StatusChip } from '@/components/StatusChip';
import { Button, EmptyState, ErrorState, FormField, Select, Skeleton } from '@/components/ui';
import { EVENT_STATUS } from '@/constants/events';
import { ROUTES } from '@/constants/routes';
import { usePageTitle } from '@/hooks/usePageTitle';
import { formatConfidence } from '@/lib/format/formatConfidence';
import { formatTimestamp } from '@/lib/format/formatTimestamp';

import { useHistoryQuery } from '../api/useHistoryQuery';
import { EvidenceThumb } from './EvidenceThumb';

import type { ChangeEvent, ReactNode } from 'react';
import type { EventStatus } from '@/constants/events';

const STATUS_OPTIONS: readonly { readonly value: EventStatus; readonly label: string }[] = [
  { value: EVENT_STATUS.ACCEPTED, label: 'Accepted' },
  { value: EVENT_STATUS.CORRECTED, label: 'Corrected' },
  { value: EVENT_STATUS.REJECTED, label: 'Rejected' },
  { value: EVENT_STATUS.UNVERIFIED, label: 'Unverified' },
  { value: EVENT_STATUS.EXPIRED, label: 'Expired' },
];

// CS-G-13 — URL params are untrusted external input.
const parseStatus = (value: string | null): EventStatus =>
  STATUS_OPTIONS.find((option) => option.value === value)?.value ?? EVENT_STATUS.ACCEPTED;

/**
 * SCR-4 Event History — every capture the edge reported, with its frame,
 * the moment it happened, the analysing model and its disposition. One
 * status at a time, stated plainly (a filtered list is never mistaken for
 * the whole record — the CS-AD-09 discipline). Rows link to the same
 * detail screen the queue uses.
 */
export const HistoryPage = () => {
  usePageTitle('Event history');
  const [searchParams, setSearchParams] = useSearchParams();
  const status = parseStatus(searchParams.get('status'));
  const historyQuery = useHistoryQuery(status);

  const handleStatusChange = (event: ChangeEvent<HTMLSelectElement>): void => {
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.set('status', event.target.value);
        return next;
      },
      { replace: true },
    );
  };

  const items = historyQuery.data?.pages.flatMap((page) => page.items) ?? [];
  const total = historyQuery.data?.pages[0]?.queue_depth;
  const statusLabel =
    STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;

  let content: ReactNode;
  if (historyQuery.isPending) {
    content = (
      <div aria-label="Loading history" className="space-y-2">
        <p className="sr-only">Loading history…</p>
        <Skeleton className="h-16 w-full rounded-card" />
        <Skeleton className="h-16 w-full rounded-card" />
        <Skeleton className="h-16 w-2/3 rounded-card" />
      </div>
    );
  } else if (historyQuery.isError) {
    content = (
      <ErrorState
        title="Event history could not be loaded."
        onRetry={() => void historyQuery.refetch()}
      />
    );
  } else if (items.length === 0) {
    content = (
      <EmptyState
        title={`No ${statusLabel.toLowerCase()} captures`}
        detail="Captures appear here as rules fire and reviewers decide them. Change the disposition filter to see other records."
      />
    );
  } else {
    content = (
      <div className="overflow-x-auto rounded-card border border-border bg-surface-1 shadow-ambient">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-border text-xs font-medium uppercase tracking-wide text-fg-muted">
              <th scope="col" className="h-10 px-4">Capture</th>
              <th scope="col" className="h-10 px-4">When</th>
              <th scope="col" className="h-10 px-4">Camera · Zone</th>
              <th scope="col" className="h-10 px-4">Rule</th>
              <th scope="col" className="h-10 px-4">Confidence</th>
              <th scope="col" className="h-10 px-4">Analysed by</th>
              <th scope="col" className="h-10 px-4">Disposition</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {items.map((item) => (
              <tr key={item.id} className="transition-colors duration-120 hover:bg-surface-2">
                <td className="px-4 py-2">
                  <Link
                    to={ROUTES.queueEvent(item.id)}
                    aria-label={`Open capture of ${formatTimestamp(item.occurred_at)}`}
                    className="inline-block rounded-control focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 focus-visible:ring-offset-2"
                  >
                    <EvidenceThumb evidenceUrl={item.evidence_url} eventId={item.id} />
                  </Link>
                </td>
                <td className="whitespace-nowrap px-4 py-2 tabular-nums text-fg">
                  {formatTimestamp(item.occurred_at)}
                </td>
                <td className="px-4 py-2 text-fg-muted">
                  {item.camera.name} · {item.zone.name}
                </td>
                <td className="max-w-xs truncate px-4 py-2 text-fg" title={item.rule.human_readable}>
                  <Link
                    to={ROUTES.queueEvent(item.id)}
                    className="rounded-control text-fg hover:text-brand-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
                  >
                    {item.rule.human_readable}
                  </Link>
                </td>
                <td className="px-4 py-2 tabular-nums text-fg-muted">
                  {formatConfidence(item.confidence)}
                </td>
                <td className="px-4 py-2 font-mono text-xs text-fg-muted">
                  {item.model_version ?? '—'}
                </td>
                <td className="px-4 py-2">
                  <StatusChip status={item.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <section aria-label="Event history" className="space-y-4">
      <div>
        <PageHeading>Event history</PageHeading>
        <p className="mt-1 text-sm text-fg-muted">
          Every capture the edge reported, with the frame, the analysing model and what a reviewer
          decided. Oldest first.
        </p>
      </div>
      {/* Filter stated beside its result — a filtered log is never mistaken
          for the whole log (CS-AD-09); the selection is URL-backed (CS-RT-03). */}
      <div className="flex flex-wrap items-end gap-3 rounded-card border border-border bg-surface-1 p-4 shadow-ambient">
        <FormField label="Disposition" className="w-44">
          <Select value={status} onChange={handleStatusChange}>
            {STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </FormField>
        <p className="ml-auto pb-2.5 text-sm tabular-nums text-fg-muted">
          {total !== undefined ? `${total} ${statusLabel.toLowerCase()} capture(s) in total` : ''}
        </p>
      </div>
      {content}
      {historyQuery.hasNextPage ? (
        <div className="flex justify-center">
          <Button
            variant="secondary"
            onClick={() => void historyQuery.fetchNextPage()}
            isLoading={historyQuery.isFetchingNextPage}
          >
            Load more
          </Button>
        </div>
      ) : items.length > 0 ? (
        // CS-PG-13 — end-of-list is a rendered state, not silence.
        <p className="text-center text-sm text-fg-muted">End of {statusLabel.toLowerCase()} history.</p>
      ) : null}
    </section>
  );
};
