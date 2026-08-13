import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { PageHeading } from '@/components/layout/PageHeading';
import { Button, Chip, EmptyState, ErrorState, Kbd, Skeleton } from '@/components/ui';
import { QUEUE_NAV_KEY } from '@/constants/events';
import { ROUTES } from '@/constants/routes';
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut';
import { usePageTitle } from '@/hooks/usePageTitle';

import { flattenQueueItems, useQueueQuery } from '../api/useQueueQuery';
import { QueueList } from './QueueList';

import type { ReactNode } from 'react';

/*
 * The review queue deliberately has NO bulk affordances: no checkboxes, no
 * select-all, no multi-select and no bulk decision control — BR-V-02, FR-047,
 * DP-3, CS-B-01. One candidate, one decision, one act.
 */
export const QueuePage = () => {
  usePageTitle('Review queue');
  const navigate = useNavigate();
  const query = useQueueQuery();
  const [selectedIndex, setSelectedIndex] = useState(0);
  const rowRefs = useRef(new Map<string, HTMLButtonElement>());

  const items = query.data === undefined ? [] : flattenQueueItems(query.data.pages);
  const itemCount = items.length;
  const selected = itemCount === 0 ? 0 : Math.min(selectedIndex, itemCount - 1);
  const selectedId = items[selected]?.id;
  const queueDepth = query.data?.pages[0]?.queue_depth;

  const focusRow = (index: number): void => {
    const item = items[index];
    if (item !== undefined) rowRefs.current.get(item.id)?.focus();
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

  let content: ReactNode;
  if (query.isPending) {
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
  } else if (query.isError) {
    content = (
      <ErrorState
        title="The queue could not be loaded."
        onRetry={() => void query.refetch()}
      />
    );
  } else if (itemCount === 0) {
    // CS-Y-13 — empty is designed; depth stays visible above (CS-B-08).
    content = (
      <EmptyState
        title="Queue clear — nothing awaits review"
        detail="No unverified candidates are waiting. New candidates appear here as cameras report them."
      />
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
        {/* DP-4 / CS-B-08 — queue depth is always visible, including at zero. */}
        <Chip variant="brand" className="tabular-nums">
          Queue depth: {queueDepth ?? '…'}
        </Chip>
      </header>
      {content}
    </section>
  );
};
