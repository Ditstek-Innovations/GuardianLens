const FALLBACK_TIME_ZONE = 'UTC';

const TIMESTAMP_OPTIONS: Omit<Intl.DateTimeFormatOptions, 'timeZone'> = {
  year: 'numeric',
  month: 'short',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  timeZoneName: 'short',
  hour12: false,
};

/**
 * Renders an ISO timestamp in the SITE's IANA timezone with the zone shown
 * (CS-FMT-02, NFR-L-02, ADR-007 — display uses the site clock, never the
 * viewer's). Falls back to labelled UTC when the API supplies no zone.
 */
export const formatTimestamp = (iso: string, siteTimeZone?: string): string => {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  const timeZone = siteTimeZone ?? FALLBACK_TIME_ZONE;
  try {
    return new Intl.DateTimeFormat('en-GB', { ...TIMESTAMP_OPTIONS, timeZone }).format(date);
  } catch {
    // Unknown IANA zone from the API — degrade to labelled UTC, never crash the queue.
    return new Intl.DateTimeFormat('en-GB', {
      ...TIMESTAMP_OPTIONS,
      timeZone: FALLBACK_TIME_ZONE,
    }).format(date);
  }
};
