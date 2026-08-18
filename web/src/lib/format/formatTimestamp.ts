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
 * (CS-FMT-02, NFR-L-02, ADR-007 — an incident reads in the site's clock,
 * matching shift logs). When the API supplies no zone, falls back to the
 * VIEWER'S system clock — a labelled local time beats labelled UTC nobody
 * on site thinks in. The zone abbreviation always shows, so which clock a
 * time is in is never ambiguous.
 */
export const formatTimestamp = (iso: string, siteTimeZone?: string): string => {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  try {
    return new Intl.DateTimeFormat('en-GB', {
      ...TIMESTAMP_OPTIONS,
      ...(siteTimeZone !== undefined ? { timeZone: siteTimeZone } : {}),
    }).format(date);
  } catch {
    // Unknown IANA zone from the API — degrade to the system clock,
    // never crash the queue.
    return new Intl.DateTimeFormat('en-GB', TIMESTAMP_OPTIONS).format(date);
  }
};
