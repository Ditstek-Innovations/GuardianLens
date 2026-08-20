import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { PageHeading } from '@/components/layout/PageHeading';
import { Button, Chip, EmptyState, ErrorState, Kbd, Skeleton } from '@/components/ui';
import { QUEUE_NAV_KEY } from '@/constants/events';
import { ROUTES } from '@/constants/routes';
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut';
import { usePageTitle } from '@/hooks/usePageTitle';

import { flattenQueueItems, useQueueQuery } from '../api/useQueueQuery';
import { useIncidentsQuery } from '../api/useIncidentsQuery';
import { IncidentRow } from './IncidentRow';
import { QueueList } from './QueueList';
import { WhyNotReviewPanel } from './WhyNotReviewPanel';

import type { ReactNode } from 'react';
import type { IncidentGroup } from '@/lib/api/types';

type QueueView = 'incidents' | 'all';

/*
 * The review queue deliberately has NO bulk affordances: no checkboxes, no
 * select-all, no multi-select and no bulk decision control — BR-V-02, FR-047,
 * DP-3, CS-B-01. One candidate, one decision, one act. Incident grouping
 * collapses the VIEW only: opening a group walks its members one by one.
 */
export const QueuePage = () => {
  usePageTitle('Review queue');
  const navigate = useNavigate();
  const [view, setView] = useState<QueueView>('incidents');
  const query = useQueueQuery();
  const incidentsQuery = useIncidentsQuery();
  const [selectedIndex, setSelectedIndex] = useState(0);
  const rowRefs = useRef(new Map<string, HTMLButtonElement>());

  const items = query.data === undefined ? [] : flattenQueueItems(query.data.pages);
  const incidents = incidentsQuery.data?.incidents ?? [];
  const isIncidentView = view === 'incidents';
  const itemCount = isIncidentView ? incidents.length : items.length;
  const selected = itemCount === 0 ? 0 : Math.min(selectedIndex, itemCount - 1);
  const selectedId = isIncidentView
    ? incidents[selected]?.incident_key
    : items[selected]?.id;
  const queueDepth = isIncidentView
    ? incidentsQuery.data?.queue_depth
    : query.data?.pages[0]?.queue_depth;
  const whyNotReview = isIncidentView
    ? (incidentsQuery.data?.why_not_review ?? [])
    : (query.data?.pages[0]?.why_not_review ?? []);

  // Opening an incident starts one-by-one review of its members: the detail
  // page advances through these ids, each decided individually (BR-V-02).
  const openIncident = (incident: IncidentGroup): void => {
    const first = incident.event_ids[0];
    if (first === undefined) return;
    navigate(ROUTES.queueEvent(first), {
      state: { incidentEventIds: incident.event_ids },
    });
  };

  const rowKeyAt = (index: number): string | undefined =>
    isIncidentView ? incidents[index]?.incident_key : items[index]?.id;

  const focusRow = (index: number): void => {
    const key = rowKeyAt(index);
    if (key !== undefined) rowRefs.current.get(key)?.focus();
  };

  const handleSelectNext = (): void => {
    const next = itemCount === 0 ? 0 : Math.min(selected + 1, itemCount - 1);
    setSelectedIndex(next);
    focusRow(next);
  };

  const handleSelectPrevious = (): void => {
    const previous = Math.max(selected - 1, 0);
    setSelectedIndex(previous);
    focusRow(previous);
  };

  const handleOpenSelected = (): void => {
    // A focused row handles Enter natively; this covers Enter pressed
    // anywhere else on the page.
    const active = document.activeElement;
    if (active instanceof HTMLElement && active.dataset.queueRow === 'true') return;
    if (isIncidentView) {
      const incident = incidents[selected];
      if (incident !== undefined) openIncident(incident);
      return;
    }
    const item = items[selected];
    if (item !== undefined) navigate(ROUTES.queueEvent(item.id));
  };

  const handleOpen = (eventId: string): void => {
    navigate(ROUTES.queueEvent(eventId));
  };

  const handleLoadMore = (): void => {
    void query.fetchNextPage();
  };

  const registerRow = (eventId: string, element: HTMLButtonElement | null): void => {
    if (element === null) rowRefs.current.delete(eventId);
    else rowRefs.current.set(eventId, element);
  };

  // NFR-ACC-01 — the queue is operable without a mouse: J/K or arrows move
  // the selection (focus follows), Enter opens.
  useKeyboardShortcut(QUEUE_NAV_KEY.NEXT, handleSelectNext);
  useKeyboardShortcut(QUEUE_NAV_KEY.PREVIOUS, handleSelectPrevious);
  useKeyboardShortcut('enter', handleOpenSelected);

  const activeQuery = isIncidentView ? incidentsQuery : query;

  let content: ReactNode;
  if (activeQuery.isPending) {
    // CS-Y-13 — loading is a designed state: skeleton rows in the list
    // frame, no layout shift on resolve. The text carries the signal for
    // assistive tech; the shimmer is decorative (CS-A-12).
    content = (
      <div
        aria-label="Loading queue"
        className="divide-y divide-border rounded-card border border-border bg-surface-1 shadow-ambient"
      >
        <p className="sr-only">Loading queue…</p>
        {[0, 1, 2, 3, 4].map((row) => (
          <div key={row} className="flex items-center justify-between gap-4 px-4 py-2.5">
            <div className="min-w-0 flex-1 space-y-1.5">
              <Skeleton className="h-4 w-2/5" />
              <Skeleton className="h-3.5 w-3/5" />
              <Skeleton className="h-3 w-1/4" />
            </div>
            <Skeleton className="h-6 w-24 rounded-full" />
          </div>
        ))}
      </div>
    );
  } else if (activeQuery.isError) {
    content = (
      <ErrorState
        title="The queue could not be loaded."
        onRetry={() => void activeQuery.refetch()}
      />
    );
  } else if (itemCount === 0) {
    // CS-Y-13 — empty is designed; depth stays visible above (CS-B-08).
    content = (
      <EmptyState
        title="Queue clear — nothing awaits review"
        detail="No unverified candidates are waiting. The panel above lists each camera and why its last frames did not enter Review."
      />
    );
  } else if (isIncidentView) {
    content = (
      <>
        {incidentsQuery.data?.capped === true ? (
          // A truncated grouping is surfaced as partial, never silent.
          <Chip variant="warn">
            Large queue — grouping covers the oldest {''}
            candidates only; decide some to see the rest.
          </Chip>
        ) : null}
        <ul
          aria-label="Incidents awaiting review"
          className="divide-y divide-border rounded-card border border-border bg-surface-1 shadow-ambient"
        >
          {incidents.map((incident) => (
            <IncidentRow
              key={incident.incident_key}
              incident={incident}
              isSelected={incident.incident_key === selectedId}
              onSelect={openIncident}
              registerRow={registerRow}
            />
          ))}
        </ul>
      </>
    );
  } else {
    content = (
      <>
        <QueueList
          items={items}
          selectedId={selectedId}
          onSelect={handleOpen}
          registerRow={registerRow}
        />
        {query.hasNextPage ? (
          <div className="flex justify-center">
            {/* Cursor-based "load more" — never page numbers (TRD §10.1). */}
            <Button
              variant="secondary"
              isLoading={query.isFetchingNextPage}
              onClick={handleLoadMore}
            >
              Load more
            </Button>
          </div>
        ) : null}
      </>
    );
  }

  return (
    <section aria-label="Review queue" className="space-y-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1.5">
          <PageHeading>Review queue</PageHeading>
          {/* CS-A-11 — the shortcuts have a visible affordance. */}
          <p className="flex flex-wrap items-center gap-1.5 text-sm text-fg-muted">
            <Kbd>J</Kbd>
            <Kbd>K</Kbd>
            <span>navigate</span>
            <span aria-hidden="true" className="text-fg-faint">
              ·
            </span>
            <Kbd>Enter</Kbd>
            <span>open</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* View toggle — grouping is presentation; both views show the
              same candidates and the same one-by-one decisions. */}
          <div className="flex gap-1">
            <Button
              size="sm"
              variant={isIncidentView ? 'primary' : 'ghost'}
              aria-pressed={isIncidentView}
              onClick={() => setView('incidents')}
            >
              Incidents
            </Button>
            <Button
              size="sm"
              variant={isIncidentView ? 'ghost' : 'primary'}
              aria-pressed={!isIncidentView}
              onClick={() => setView('all')}
            >
              All candidates
            </Button>
          </div>
          {/* DP-4 / CS-B-08 — queue depth is always visible, including at zero. */}
          <Chip variant="brand" className="tabular-nums">
            Queue depth: {queueDepth ?? '…'}
          </Chip>
        </div>
      </header>
      <WhyNotReviewPanel rows={whyNotReview} />
      {content}
    </section>
  );
};
