// CS-RT-01 — routes are declared once and referenced through these constants.
export const ROUTES = {
  login: '/login',
  // SCR-1a…SCR-1c (§23.1) — public auth family. These screens link only to
  // each other (CS-AU-18); no application screen links back to signup.
  signup: '/signup',
  forgotPassword: '/forgot-password',
  resetPassword: '/reset-password',
  queue: '/queue',
  queueEvent: (eventId: string): string => `/queue/${eventId}`,
  reports: '/reports',
  config: '/config',
  audit: '/audit',
} as const;

export const ROUTE_PATTERNS = {
  queueEvent: '/queue/:eventId',
} as const;
