// CS-D-03 — key factory for the candidate-detail feature.
export const eventKeys = {
  all: ['event'] as const,
  detail: (eventId: string) => [...eventKeys.all, 'detail', eventId] as const,
  evidence: (eventId: string) => [...eventKeys.all, 'evidence', eventId] as const,
};
