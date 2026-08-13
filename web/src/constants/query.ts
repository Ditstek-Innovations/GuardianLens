// CS-D-09 — poll intervals, stale times and page sizes live here, not scattered.
export const QUEUE_POLL_INTERVAL_MS = 15_000; // TRD §7.3 — poll every 15 s [MVP]
export const QUEUE_STALE_TIME_MS = 15_000;
export const QUEUE_PAGE_SIZE = 25;
/** Mirrors the evidence Cache-Control: private, max-age=300 (TRD §10.4). */
export const EVIDENCE_STALE_TIME_MS = 300_000;
