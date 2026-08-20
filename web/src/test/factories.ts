import type { IncidentGroup, IncidentQueueResponse, QueueEventItem, QueuePage } from '@/lib/api/types';

// CS-Q-04 — test data comes from typed factories, not inline literals.

export const makeQueueEvent = (overrides: Partial<QueueEventItem> = {}): QueueEventItem => ({
  id: 'event-1',
  camera: { id: 'camera-1', name: 'Bay 3 entrance' },
  zone: { id: 'zone-1', name: 'Bay 3 PPE area' },
  rule: { human_readable: 'Helmet required in Bay 3' },
  source: 'guardian_lens',
  confidence: 0.81,
  occurred_at: '2026-07-31T09:14:22Z',
  status: 'unverified',
  evidence_url: '/api/v1/events/event-1/evidence',
  version: 1,
  site_timezone: 'Asia/Kolkata',
  ...overrides,
});

export const makeQueuePage = (
  items: QueueEventItem[],
  queueDepth: number = items.length,
  nextCursor: string | null = null,
): QueuePage => ({
  items,
  queue_depth: queueDepth,
  next_cursor: nextCursor,
});

export const makeIncidentGroup = (overrides: Partial<IncidentGroup> = {}): IncidentGroup => ({
  incident_key: 'event-1',
  camera: { id: 'camera-1', name: 'Bay 3 entrance' },
  zone: { id: 'zone-1', name: 'Bay 3 PPE area' },
  rule: { human_readable: 'Helmet required in Bay 3' },
  count: 3,
  first_occurred_at: '2026-07-31T09:14:22Z',
  last_occurred_at: '2026-07-31T09:16:22Z',
  max_confidence: 0.87,
  status: 'unverified',
  event_ids: ['event-1', 'event-2', 'event-3'],
  ...overrides,
});

export const makeIncidentsResponse = (
  incidents: IncidentGroup[],
  queueDepth: number = incidents.reduce((sum, group) => sum + group.count, 0),
  whyNotReview: IncidentQueueResponse['why_not_review'] = [],
): IncidentQueueResponse => ({
  incidents,
  queue_depth: queueDepth,
  gap_seconds: 300,
  capped: false,
  why_not_review: whyNotReview,
});

export const jsonResponse = (body: unknown, status = 200): Response =>
  new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
