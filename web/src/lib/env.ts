// CS-ENV-01 — the only module that reads import.meta.env.
const DEFAULT_API_URL = 'http://localhost:8000';

const configured = import.meta.env.VITE_API_URL;
const apiUrl = (configured === undefined || configured === '' ? DEFAULT_API_URL : configured).replace(
  /\/+$/,
  '',
);

// CS-ENV-02 — a malformed required value fails the boot loudly, never a silent
// request to "undefined/api/v1/events".
if (!/^https?:\/\//.test(apiUrl)) {
  throw new Error(`VITE_API_URL must be an absolute http(s) URL, got "${apiUrl}"`);
}

export const env = { apiUrl } as const;
