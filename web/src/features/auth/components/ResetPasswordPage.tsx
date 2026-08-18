import { useEffect, useRef, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { Link, useSearchParams } from 'react-router-dom';

import { Button, FormField, PasswordInput } from '@/components/ui';
import { ROUTES } from '@/constants/routes';
import { ApiError } from '@/lib/api/errors';

import { submitPasswordReset } from '../api/authApi';
import { PASSWORD_POLICY_HINT, resetSchema } from '../schemas';

import { AuthLayout } from './AuthLayout';

import type { ResetValues } from '../schemas';

// FRONTEND_CODING_STANDARDS §23.3 — SCR-1c (CS-AU-17).
//
// The token arrives in the URL, is read once, and is NEVER rendered — not in
// the form, not in an error, not in the success state. An invalid or expired
// token gets ONE generic failure with a route back to SCR-1b: never a hint
// about why the token failed.

const GENERIC_FAILURE = 'The reset link is invalid or has expired.';

type Phase = 'form' | 'success' | 'failed';

interface ResetLink {
  readonly email: string;
  readonly token: string;
}

const readLink = (params: URLSearchParams): ResetLink | null => {
  const token = params.get('token');
  const email = params.get('email');
  if (token === null || token === '' || email === null || email === '') return null;
  return { email, token };
};

const FailureState = () => (
  <div className="space-y-4">
    <p role="alert" className="text-sm text-danger">
      {GENERIC_FAILURE}
    </p>
    <Link
      to={ROUTES.forgotPassword}
      className="inline-block text-sm text-brand-ink underline-offset-2 hover:underline"
    >
      Request a new reset link
    </Link>
  </div>
);

export const ResetPasswordPage = () => {
  const [searchParams] = useSearchParams();
  const link = readLink(searchParams);
  // A malformed link fails immediately — same generic state as a rejected
  // token, so the URL never reveals which part was wrong.
  const [phase, setPhase] = useState<Phase>(link === null ? 'failed' : 'form');
  const [serverError, setServerError] = useState<string | null>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const successRef = useRef<HTMLDivElement>(null);
  const { register, handleSubmit, formState } = useForm<ResetValues>({
    resolver: zodResolver(resetSchema),
    mode: 'onSubmit',
    reValidateMode: 'onChange',
    defaultValues: { password: '' },
  });

  useEffect(() => {
    if (serverError !== null) errorRef.current?.focus();
  }, [serverError]);
  useEffect(() => {
    if (phase === 'success') successRef.current?.focus();
  }, [phase]);

  const onValid = async (values: ResetValues): Promise<void> => {
    if (link === null) return;
    setServerError(null);
    try {
      await submitPasswordReset({
        email: link.email,
        token: link.token,
        new_password: values.password,
      });
      setPhase('success');
    } catch (error) {
      if (error instanceof ApiError && error.status === 400) {
        // CS-AU-17 — one generic failure, whatever the server said.
        setPhase('failed');
      } else {
        // CS-FM-06 — transport failure: form-level, input preserved.
        setServerError('Something went wrong. Check your connection and try again.');
      }
    }
  };

  return (
    <AuthLayout
      title="Reset password"
      footer={
        // CS-AU-18 — reset links to login (and SCR-1b from its failure state).
        <Link to={ROUTES.login} className="text-brand-ink underline-offset-2 hover:underline">
          Back to sign in
        </Link>
      }
    >
      {phase === 'failed' ? <FailureState /> : null}

      {phase === 'success' ? (
        <div ref={successRef} tabIndex={-1} role="status" className="space-y-4">
          <p className="text-sm text-fg">Your password has been reset.</p>
          <Link to={ROUTES.login} className="inline-block text-sm text-brand-ink underline-offset-2 hover:underline">
            Sign in
          </Link>
        </div>
      ) : null}

      {phase === 'form' ? (
        <form
          onSubmit={(event) => void handleSubmit(onValid)(event)}
          noValidate
          className="space-y-4"
        >
          {/* CS-AU-15 — the policy is stated in the hint BEFORE any failure. */}
          <FormField
            label="New password"
            required
            hint={PASSWORD_POLICY_HINT}
            error={formState.errors.password?.message}
          >
            <PasswordInput autoComplete="new-password" autoFocus {...register('password')} />
          </FormField>

          {/* CS-FM-05 — disabled only while the request is in flight. */}
          <Button type="submit" isLoading={formState.isSubmitting} className="w-full">
            Reset password
          </Button>

          {serverError !== null ? (
            <p ref={errorRef} tabIndex={-1} role="alert" className="text-sm text-danger">
              {serverError}
            </p>
          ) : null}
        </form>
      ) : null}
    </AuthLayout>
  );
};
