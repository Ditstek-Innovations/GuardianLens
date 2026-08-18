import { apiClient } from '@/lib/api/client';

import type {
  AcceptedResponse,
  PasswordResetBody,
  PasswordResetRequestBody,
  SignupRequestBody,
} from '@/lib/api/types';

/**
 * SCR-1a…SCR-1c calls (TRD §10.2). Sign-up and reset-request always resolve
 * `202` with one generic acceptance (CS-AU-10) — callers render their own
 * fixed copy and never branch on the response body.
 */

export const requestSignup = (body: SignupRequestBody): Promise<AcceptedResponse> =>
  apiClient.post<AcceptedResponse>('/api/v1/auth/signup', body);

export const requestPasswordReset = (
  body: PasswordResetRequestBody,
): Promise<AcceptedResponse> =>
  apiClient.post<AcceptedResponse>('/api/v1/auth/password-reset-request', body);

export const submitPasswordReset = (body: PasswordResetBody): Promise<unknown> =>
  apiClient.post<unknown>('/api/v1/auth/password-reset', body);
