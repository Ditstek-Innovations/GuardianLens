import type { ApiErrorEnvelope } from './types';

interface ApiErrorDetails {
  readonly code?: string | null | undefined;
  readonly field?: string | null | undefined;
  readonly traceId?: string | null | undefined;
  readonly body?: unknown;
}

/**
 * CS-D-12 — transport and API failures map into one typed application error.
 * `body` keeps the raw parsed payload: the 409 conflict body carries the
 * existing decision (TRD §10.4), which the detail screen surfaces.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly field: string | null;
  readonly traceId: string | null;
  readonly body: unknown;

  constructor(status: number, message: string, details: ApiErrorDetails = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = details.code ?? null;
    this.field = details.field ?? null;
    this.traceId = details.traceId ?? null;
    this.body = details.body ?? null;
  }
}

// Trust-boundary narrowing of an unknown response body (CS-G-10, CS-G-12).
const isErrorEnvelope = (body: unknown): body is ApiErrorEnvelope => {
  if (typeof body !== 'object' || body === null || !('error' in body)) return false;
  const error = (body as { error: unknown }).error;
  return (
    typeof error === 'object' &&
    error !== null &&
    typeof (error as { message?: unknown }).message === 'string'
  );
};

export const toApiError = async (response: Response): Promise<ApiError> => {
  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // Non-JSON error body (proxy failure, empty 5xx) — keep the status only.
  }
  if (isErrorEnvelope(body)) {
    const { code, message, field, trace_id } = body.error;
    return new ApiError(response.status, message, {
      code,
      field: field ?? null,
      traceId: trace_id ?? null,
      body,
    });
  }
  return new ApiError(response.status, `Request failed (${response.status})`, { body });
};
