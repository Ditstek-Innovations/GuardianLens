import { PageHeading } from '@/components/layout/PageHeading';
import { Button, Chip, EmptyState, ErrorState, Skeleton } from '@/components/ui';
import { ROLE } from '@/constants/roles';
import { useQueueQuery } from '@/features/review-queue';
import { useAuth } from '@/hooks/useAuth';
import { usePageTitle } from '@/hooks/usePageTitle';
import { useToast } from '@/hooks/useToast';
import { formatTimestamp } from '@/lib/format/formatTimestamp';

import { LiveFrame } from './LiveFrame';
import { usePtzMove } from '../api/usePtzMove';

import type { WhyNotReview } from '@/lib/api/types';
import type { PtzDirection } from '../api/usePtzMove';

const ClassList = ({ label, values }: { label: string; values: string[] }) => (
  <div>
    <p className="text-xs font-medium uppercase tracking-wide text-fg-faint">{label}</p>
    <p className="mt-1 text-sm text-fg-muted">{values.length > 0 ? values.join(', ') : 'None'}</p>
  </div>
);

const PtzControls = ({ row }: { row: WhyNotReview }) => {
  const move = usePtzMove(row.camera_id);
  const { showToast } = useToast();
  const moveCamera = (direction: PtzDirection): void => {
    move.mutate(direction, {
      onSuccess: () => showToast({ tone: 'success', message: `Camera moved ${direction}.` }),
      onError: () =>
        showToast({
          tone: 'failure',
          message: 'Camera could not be moved. Check ONVIF access and edge connectivity.',
        }),
    });
  };
  const isOnline = row.stream === 'online';
  return (
    <div className="border-b border-border bg-surface-2 p-3">
      <div
        className="mx-auto grid w-fit grid-cols-3 gap-2"
        aria-label={`${row.camera_name} movement controls`}
      >
        <span />
        <Button variant="secondary" size="sm" aria-label={`Move ${row.camera_name} up`} onClick={() => moveCamera('up')} disabled={!isOnline || move.isPending}>↑</Button>
        <span />
        <Button variant="secondary" size="sm" aria-label={`Move ${row.camera_name} left`} onClick={() => moveCamera('left')} disabled={!isOnline || move.isPending}>←</Button>
        <span className="flex items-center justify-center text-xs text-fg-faint">PTZ</span>
        <Button variant="secondary" size="sm" aria-label={`Move ${row.camera_name} right`} onClick={() => moveCamera('right')} disabled={!isOnline || move.isPending}>→</Button>
        <span />
        <Button variant="secondary" size="sm" aria-label={`Move ${row.camera_name} down`} onClick={() => moveCamera('down')} disabled={!isOnline || move.isPending}>↓</Button>
        <span />
      </div>
      <p className="mt-2 text-center text-xs text-fg-muted">Each click makes one short, safe movement.</p>
    </div>
  );
};

const CameraCard = ({ row, canControl }: { row: WhyNotReview; canControl: boolean }) => {
  const isOnline = row.stream === 'online';
  return (
    <article className="overflow-hidden rounded-card border border-border bg-surface-1 shadow-ambient">
      <div className="p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="font-semibold text-fg">{row.camera_name}</h2>
            <p className="mt-0.5 text-xs tabular-nums text-fg-muted">
              Detection checked{' '}
              {row.observed_at !== undefined && row.observed_at !== null
                ? formatTimestamp(row.observed_at)
                : '—'}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Chip variant={isOnline ? 'ok' : 'danger'}>
              {isOnline ? 'Camera online' : 'Camera offline'}
            </Chip>
            <Chip variant={row.matched ? 'ok' : 'neutral'}>
              {row.matched ? 'Detection matched' : 'Scanning'}
            </Chip>
          </div>
        </div>
      </div>
      <div className="border-y border-border bg-black">
        <LiveFrame cameraId={row.camera_id} cameraName={row.camera_name} />
      </div>
      {canControl ? <PtzControls row={row} /> : null}
      <div className="grid gap-4 p-4 sm:grid-cols-2">
        <ClassList label="Model last saw" values={row.last_seen_classes} />
        <ClassList label="Watching for" values={row.watched_classes} />
        {row.why_not_review.length > 0 ? (
          <div className="sm:col-span-2">
            <p className="text-xs font-medium uppercase tracking-wide text-fg-faint">
              Why no new review record
            </p>
            <p className="mt-1 text-sm text-fg-muted">{row.why_not_review[0]}</p>
          </div>
        ) : null}
      </div>
    </article>
  );
};

export const LiveFeedingPage = () => {
  usePageTitle('Live feeding');
  const { principal } = useAuth();
  const canControl = principal?.roles.includes(ROLE.SITE_ADMIN) ?? false;
  const queue = useQueueQuery();
  const firstPage = queue.data?.pages[0];
  const rows = firstPage?.why_not_review ?? [];
  const queueDepth = firstPage?.queue_depth;

  return (
    <section aria-label="Live feeding" className="space-y-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <PageHeading>Live feeding</PageHeading>
          <p className="mt-1 text-sm text-fg-muted">
            Secure near-live previews from the edge agent, refreshed every second. RTSP credentials
            never reach the browser.
          </p>
        </div>
        <Chip variant="brand" className="tabular-nums">
          Queue depth: {queueDepth ?? '…'}
        </Chip>
      </header>

      {queue.isPending ? (
        <div aria-label="Loading live cameras" className="grid gap-4 xl:grid-cols-2">
          <Skeleton className="aspect-video rounded-card" />
          <Skeleton className="aspect-video rounded-card" />
        </div>
      ) : queue.isError ? (
        <ErrorState
          title="Live camera status could not be loaded."
          onRetry={() => void queue.refetch()}
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No camera status received"
          detail="Start an edge agent and wait for its next health update. Camera previews appear here automatically."
        />
      ) : (
        <div className="grid gap-4 xl:grid-cols-2">
          {rows.map((row) => (
            <CameraCard key={row.camera_id} row={row} canControl={canControl} />
          ))}
        </div>
      )}
    </section>
  );
};
