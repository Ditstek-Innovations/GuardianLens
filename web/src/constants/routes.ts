// CS-RT-01 — routes are declared once and referenced through these constants.
export const ROUTES = {
  login: '/login',
  // SCR-1a…SCR-1c (§23.1) — public auth family. These screens link only to
  // each other (CS-AU-18); no application screen links back to signup.
  signup: '/signup',
  forgotPassword: '/forgot-password',
  resetPassword: '/reset-password',
  queue: '/queue',
  liveFeeding: '/live-feeding',
  queueEvent: (eventId: string): string => `/queue/${eventId}`,
  history: '/history',
  reports: '/reports',
  config: '/config',
  audit: '/audit',
  cameraDiscovery: (siteId: string): string => `/config/discovery/${siteId}`,
} as const;

export const ROUTE_PATTERNS = {
  queueEvent: '/queue/:eventId',
  cameraDiscovery: '/config/discovery/:siteId',
} as const;
