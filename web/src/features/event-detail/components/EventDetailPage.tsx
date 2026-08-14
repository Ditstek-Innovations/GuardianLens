import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';

import { StatusChip } from '@/components/StatusChip';
import { PageHeading } from '@/components/layout/PageHeading';
import { Button, Chip, ErrorState, Skeleton } from '@/components/ui';
import { EVENT_STATUS } from '@/constants/events';
import { MESSAGES } from '@/constants/messages';
import { DECIDING_ROLES } from '@/constants/roles';
import { ROUTES } from '@/constants/routes';
import { CONFLICT_ADVANCE_DELAY_MS, DELAYED_EVENT_THRESHOLD_MS } from '@/constants/time';
import { flattenQueueItems, useQueueQuery } from '@/features/review-queue';
import { useAuth } from '@/hooks/useAuth';
import { usePageTitle } from '@/hooks/usePageTitle';
import { useSessionDraft } from '@/hooks/useSessionDraft';
import { useToast } from '@/hooks/useToast';
import { ApiError } from '@/lib/api/errors';
import { formatConfidence } from '@/lib/format/formatConfidence';
import { formatDurationMs } from '@/lib/format/formatDurationMs';
import { formatTimestamp } from '@/lib/format/formatTimestamp';
import { assertNever } from '@/lib/utils/assertNever';

import { useEventQuery } from '../api/useEventQuery';
import { useEvidence } from '../api/useEvidence';
import { useSubmitDecision } from '../api/useSubmitDecision';
import { CorrectionForm } from './CorrectionForm';
import { DecisionBar } from './DecisionBar';
import { EvidenceFrame } from './EvidenceFrame';
import { RejectionReasonDialog } from './RejectionReasonDialog';

import type { ReactNode } from 'react';
import type { DecisionIntent } from './DecisionBar';
import type { DecisionResponse } from '@/lib/api/types';
import type { Decision, FieldCorrection } from '@/types/decision';

type DialogState = 'none' | 'reject' | 'correct';

interface ConflictState {
  readonly existing: DecisionResponse | null;
}

// RESOLVED A-4 — the server nests it inside the §10.8 envelope as
// `error.existing_decision` (the envelope has no field for the mandated
// payload, so it is additive there). The top-level spelling is kept as a
// fallback; absence still degrades gracefully.
const extractExistingDecision = (body: unknown): DecisionResponse | null => {
  if (typeof body !== 'object' || body === null) return null;
  const record = body as { existing_decision?: unknown; error?: { existing_decision?: unknown } };
  const existing = record.error?.existing_decision ?? record.existing_decision;
  if (typeof existing !== 'object' || existing === null) return null;
  return existing as DecisionResponse;
};

const ClockIcon = () => (
  <svg
    aria-hidden="true"
    focusable="false"
    width="12"
    height="12"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2.5}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </svg>
);

const InfoIcon = () => (
  <svg
    aria-hidden="true"
    focusable="false"
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    className="mt-0.5 shrink-0 text-fg-faint"
  >
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5" />
    <path d="M12 8h.01" />
  </svg>
);

const Detail = ({
  label,
  value,
  wide = false,
}: {
  label: string;
  value: ReactNode;
  wide?: boolean;
}) => (
  <div className={wide ? 'sm:col-span-2' : undefined}>
    <dt className="text-xs font-medium uppercase tracking-wide text-fg-muted">{label}</dt>
    <dd className="mt-0.5 text-sm tabular-nums text-fg">{value}</dd>
  </div>
);

export const EventDetailPage = () => {
  // Route params are external input (CS-RT-02 / CS-G-13).
  const params = useParams<{ eventId: string }>();
  const eventId = params.eventId ?? '';
  if (eventId === '') {
    return <ErrorState title="Candidate not found." detail="The address has no candidate id." />;
  }
  // key resets all per-candidate state (evidence gate, dialogs) on navigation.
  return <EventDetailView key={eventId} eventId={eventId} />;
};

const EventDetailView = ({ eventId }: { eventId: string }) => {
  usePageTitle('Candidate detail');
  const navigate = useNavigate();
  const { principal } = useAuth();
  const eventQuery = useEventQuery(eventId);
  const evidence = useEvidence(eventId);
  // Shares the queue cache — used to compute the next candidate to open.
  const queueQuery = useQueueQuery();
  const submitDecision = useSubmitDecision(eventId);
  const { draft, setDraft, clearDraft } = useSessionDraft(eventId);
  const { showToast } = useToast();

  const [dialog, setDialog] = useState<DialogState>('none');
  const [isFrameRendered, setIsFrameRendered] = useState(false);
  const [hasFrameFailed, setHasFrameFailed] = useState(false);
  const [conflict, setConflict] = useState<ConflictState | null>(null);

  const queueItems = queueQuery.data === undefined ? [] : flattenQueueItems(queueQuery.data.pages);
  const currentIndex = queueItems.findIndex((item) => item.id === eventId);
  const nextEventId =
    (currentIndex >= 0
      ? queueItems[currentIndex + 1]?.id
      : queueItems.find((item) => item.id !== eventId)?.id) ?? null;

  // PRD P-02 — median review time is a survival metric: on success the UI
  // advances to the next queue item automatically.
  const goToNext = useCallback(() => {
    if (nextEventId !== null) navigate(ROUTES.queueEvent(nextEventId), { replace: true });
    else navigate(ROUTES.queue);
  }, [navigate, nextEventId]);

  // F-2/F-3 — after showing who already decided, move on automatically.
  useEffect(() => {
    if (conflict === null) return undefined;
    const timer = window.setTimeout(goToNext, CONFLICT_ADVANCE_DELAY_MS);
    return () => {
      window.clearTimeout(timer);
    };
  }, [conflict, goToNext]);

  if (eventQuery.isPending) {
    // CS-Y-13 — a skeleton of the real layout: frame, facts card, decision
    // bar. No layout shift on resolve; text carries the loading signal.
    return (
      <div aria-label="Loading candidate" className="space-y-5">
        <p className="sr-only">Loading candidate…</p>
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-7 w-2/3" />
        <Skeleton className="aspect-video w-full rounded-card" />
        <Skeleton className="h-36 w-full rounded-card" />
        <Skeleton className="h-20 w-full rounded-card" />
      </div>
    );
  }
  if (eventQuery.isError || eventQuery.data === undefined) {
    return (
      <ErrorState
        title="The candidate could not be loaded."
        onRetry={() => void eventQuery.refetch()}
      />
    );
  }

  const event = eventQuery.data;
  const isDecided = event.status !== EVENT_STATUS.UNVERIFIED;
  const canDecide = principal !== null && principal.roles.some((role) => DECIDING_ROLES.includes(role));

  // ADR-013 / F-6 — the gate: fetched AND rendered, with failure explicit.
  const isEvidenceBlocked = evidence.isError || hasFrameFailed;
  const areDecisionsDisabled = !isFrameRendered || isEvidenceBlocked;

  const receivedAt = event.received_at;
  const delayMs =
    receivedAt === undefined
      ? 0
      : new Date(receivedAt).getTime() - new Date(event.occurred_at).getTime();
  const isDelayed = Number.isFinite(delayMs) && delayMs > DELAYED_EVENT_THRESHOLD_MS;

  const evidenceAlt = `Evidence frame — ${event.camera.name}, ${event.zone.name}, ${formatTimestamp(
    event.occurred_at,
    event.site_timezone,
  )}`;

  const handleFrameLoaded = (): void => {
    setIsFrameRendered(true);
  };
  const handleFrameFailed = (): void => {
    setHasFrameFailed(true);
  };

  // CS-MSG-02/04 — outcome copy comes from the catalogue: an accept names
  // the attribution (BR-005), a reject names the retention (BR-007).
  const successMessageFor = (decision: Decision): string => {
    switch (decision.type) {
      case 'accept':
        return MESSAGES.decision.accepted;
      case 'reject':
        return MESSAGES.decision.rejected;
      case 'correct':
        return MESSAGES.decision.corrected;
      default:
        return assertNever(decision);
    }
  };

  const submit = (decision: Decision): void => {
    submitDecision.mutate(
      { decision, version: event.version },
      {
        onSuccess: () => {
          clearDraft();
          setDialog('none');
          showToast({ tone: 'success', message: successMessageFor(decision) });
          goToNext();
        },
        onError: (error) => {
          if (error instanceof ApiError && error.status === 409) {
            setDialog('none');
            setConflict({ existing: extractExistingDecision(error.body) });
            // Informational, not actionable — first decision wins (BR-V-04).
            showToast({ tone: 'notice', message: MESSAGES.decision.conflict });
          } else {
            // CS-MSG-05 — next step stated; no status codes, no error text.
            showToast({ tone: 'failure', message: MESSAGES.decision.failed });
          }
        },
      },
    );
  };

  const handleIntent = (intent: DecisionIntent): void => {
    switch (intent) {
      case 'accept':
        submit({ type: 'accept' });
        break;
      case 'reject':
        setDialog('reject');
        break;
      case 'correct':
        setDialog('correct');
        break;
      default:
        assertNever(intent);
    }
  };

  const handleRejectSubmit = (reason: string): void => {
    submit({ type: 'reject', reason });
  };
  const handleCorrectSubmit = (correction: FieldCorrection): void => {
    submit({ type: 'correct', correction });
  };
  const handleRejectCancel = (): void => {
    setDialog('none');
    clearDraft(); // abandoned draft — CS-FM-08
  };
  const handleDialogClose = (): void => {
    setDialog('none');
  };

  let decisionArea: ReactNode;
  if (isDecided) {
    // CS-B-07 — no edit affordance on a decided event.
    decisionArea = (
      <p className="flex items-start gap-2 rounded-control border border-border bg-surface-2 px-3 py-2.5 text-sm text-fg-muted">
        <InfoIcon />
        <span>
          This candidate has been decided. Decisions are immutable (BR-V-01); a reviewer error is
          addressed by a new correcting record, never by editing this one.
        </span>
      </p>
    );
  } else if (!canDecide) {
    decisionArea = (
      <p className="flex items-start gap-2 rounded-control border border-border bg-surface-2 px-3 py-2.5 text-sm text-fg-muted">
        <InfoIcon />
        <span>Read-only — your role cannot decide candidates (TRD §12.3).</span>
      </p>
    );
  } else if (conflict !== null) {
    decisionArea = null;
  } else {
    decisionArea = (
      <DecisionBar
        disabled={areDecisionsDisabled}
        isSubmitting={submitDecision.isPending}
        onIntent={handleIntent}
      />
    );
  }

  return (
    <article className="space-y-5">
      <header className="space-y-2">
        <Link
          to={ROUTES.queue}
          className="text-sm text-brand-ink underline-offset-2 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-400"
        >
          ← Back to queue
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <PageHeading>{event.rule.human_readable}</PageHeading>
          <StatusChip status={event.status} />
        </div>
      </header>

      <EvidenceFrame
        url={evidence.url}
        isPending={evidence.isPending}
        isError={isEvidenceBlocked}
        alt={evidenceAlt}
        onLoaded={handleFrameLoaded}
        onFailed={handleFrameFailed}
      />

      {isDelayed ? (
        // ADR-007 — replayed events show their true observation time visibly.
        <Chip variant="warn" icon={<ClockIcon />} className="tabular-nums">
          Delayed observation — occurred {formatDurationMs(delayMs)} before receipt
        </Chip>
      ) : null}

      <dl className="grid grid-cols-1 gap-x-8 gap-y-3 rounded-card border border-border bg-surface-1 p-4 shadow-ambient sm:grid-cols-2">
        <Detail label="Camera · Zone" value={`${event.camera.name} · ${event.zone.name}`} />
        <Detail
          label="Occurred at (site time)"
          value={formatTimestamp(event.occurred_at, event.site_timezone)}
        />
        <Detail
          label="Received at"
          value={receivedAt === undefined ? '—' : formatTimestamp(receivedAt, event.site_timezone)}
        />
        {/* BR-V-03 — an annotation for attention, never an input to the decision. */}
        <Detail label="Confidence (annotation only)" value={formatConfidence(event.confidence)} />
        <Detail
          wide
          label="Rule as it fired (snapshot)"
          value={`${event.rule_snapshot.human_readable} · type ${event.rule_snapshot.rule_type} · threshold ${event.rule_snapshot.confidence_threshold}`}
        />
      </dl>

      {conflict !== null ? (
        <div className="rounded-card border border-warn bg-warn-subtle p-4">
          <p className="font-medium text-warn">
            Already decided by {conflict.existing?.reviewer.full_name ?? 'another reviewer'}
            {conflict.existing !== null
              ? ` — ${conflict.existing.decision_type} at ${formatTimestamp(
                  conflict.existing.decided_at,
                  event.site_timezone,
                )}`
              : ''}
          </p>
          <p className="mt-1 text-sm text-warn">Moving to the next candidate…</p>
          <Button variant="secondary" size="sm" className="mt-3" onClick={goToNext}>
            Next candidate
          </Button>
        </div>
      ) : null}

      {decisionArea}

      {dialog === 'reject' ? (
        <RejectionReasonDialog
          draft={draft}
          onDraftChange={setDraft}
          isSubmitting={submitDecision.isPending}
          onSubmit={handleRejectSubmit}
          onCancel={handleRejectCancel}
        />
      ) : null}
      {dialog === 'correct' ? (
        <CorrectionForm
          event={event}
          isSubmitting={submitDecision.isPending}
          onSubmit={handleCorrectSubmit}
          onCancel={handleDialogClose}
        />
      ) : null}

    </article>
  );
};
