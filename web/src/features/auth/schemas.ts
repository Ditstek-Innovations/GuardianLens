import { z } from 'zod';

/**
 * CS-FM-01 / CS-AU-13 — one schema per auth form; every submitted value's
 * type is derived from its schema (z.infer), never hand-written beside it.
 */

/**
 * CS-AU-15 — NIST-style policy, mirrored from the server: minimum 12,
 * maximum 128, NO composition rules ("one uppercase, one symbol" theatre is
 * banned). The hint below is shown on the field BEFORE the first failed
 * submit, not revealed by it.
 */
export const PASSWORD_MIN_LENGTH = 12;
export const PASSWORD_MAX_LENGTH = 128;
export const PASSWORD_POLICY_HINT = `${PASSWORD_MIN_LENGTH} to ${PASSWORD_MAX_LENGTH} characters. No other requirements — any characters are allowed, and pasting is fine.`;
export const PASSWORD_TOO_SHORT_MESSAGE = `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`;
export const PASSWORD_TOO_LONG_MESSAGE = `Password must be at most ${PASSWORD_MAX_LENGTH} characters.`;

const emailField = z.email('Enter a valid email address.');

/** A NEW password — policy-checked (signup, reset). */
const newPasswordField = z
  .string()
  .min(PASSWORD_MIN_LENGTH, PASSWORD_TOO_SHORT_MESSAGE)
  .max(PASSWORD_MAX_LENGTH, PASSWORD_TOO_LONG_MESSAGE);

/**
 * Login deliberately checks presence only: an existing credential predates
 * the policy, and rejecting it client-side would lock the account out of the
 * screen that could use it. The server is the authority (CS-AU-13).
 */
export const loginSchema = z.object({
  email: emailField,
  password: z.string().min(1, 'Enter your password.'),
});
export type LoginValues = z.infer<typeof loginSchema>;

export const signupSchema = z.object({
  fullName: z.string().trim().min(1, 'Enter your full name.'),
  email: emailField,
  siteCode: z.string().trim().min(1, 'Enter your site code.'),
  password: newPasswordField,
});
export type SignupValues = z.infer<typeof signupSchema>;

export const forgotSchema = z.object({
  email: emailField,
});
export type ForgotValues = z.infer<typeof forgotSchema>;

export const resetSchema = z.object({
  password: newPasswordField,
});
export type ResetValues = z.infer<typeof resetSchema>;
