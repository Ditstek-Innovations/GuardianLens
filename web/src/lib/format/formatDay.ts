const FALLBACK_TIME_ZONE = 'UTC';

const DAY_OPTIONS: Omit<Intl.DateTimeFormatOptions, 'timeZone'> = {
  year: 'numeric',
  month: 'short',
  day: '2-digit',
};

/**
 * Renders an ISO timestamp as a calendar day in the SITE's zone
 * (CS-FMT-02, NFR-L-02) — for period ranges where the time of day is
 * noise, e.g. "16 Aug 2026".
 */
export const formatDay = (iso: string, siteTimeZone?: string): string => {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  try {
    return new Intl.DateTimeFormat('en-GB', {
      ...DAY_OPTIONS,
      timeZone: siteTimeZone ?? FALLBACK_TIME_ZONE,
    }).format(date);
  } catch {
    return new Intl.DateTimeFormat('en-GB', {
      ...DAY_OPTIONS,
      timeZone: FALLBACK_TIME_ZONE,
    }).format(date);
  }
};
