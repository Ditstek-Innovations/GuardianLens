import { useEffect, useRef, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';

import { Button, FormField, Input } from '@/components/ui';
import { ROUTES } from '@/constants/routes';

import { requestPasswordReset } from '../api/authApi';
import { forgotSchema } from '../schemas';

import { AuthLayout } from './AuthLayout';

import type { ForgotValues } from '../schemas';

// FRONTEND_CODING_STANDARDS §23.3 — SCR-1b (CS-AU-17).
//
// One email field, and ONE acceptance line whatever the server knows about
// the address (CS-AU-10): the copy below never varies, and the response body
// is never read.

export const ForgotPasswordPage = () => {
  const [accepted, setAccepted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const acceptedRef = useRef<HTMLParagraphElement>(null);
  const { register, handleSubmit, formState } = useForm<ForgotValues>({
    resolver: zodResolver(forgotSchema),
    mode: 'onSubmit',
    reValidateMode: 'onChange',
    defaultValues: { email: '' },
  });

  useEffect(() => {
    if (serverError !== null) errorRef.current?.focus();
  }, [serverError]);
  useEffect(() => {
    if (accepted) acceptedRef.current?.focus();
  }, [accepted]);

  const onValid = async (values: ForgotValues): Promise<void> => {
    setServerError(null);
    try {
      await requestPasswordReset({ email: values.email });
      setAccepted(true);
    } catch {
      // CS-FM-06 — transport failure only; the server itself always 202s.
      setServerError('Something went wrong. Check your connection and try again.');
    }
  };

  return (
    <AuthLayout
      title="Forgot password"
      footer={
        // CS-AU-18 — sibling auth screens only.
        <Link to={ROUTES.login} className="text-brand-ink underline-offset-2 hover:underline">
          Back to sign in
        </Link>
      }
    >
      {accepted ? (
        // CS-AU-17 — the exact acceptance, account or no account.
        <p ref={acceptedRef} tabIndex={-1} role="status" className="text-sm text-fg">
          If that address has an account, a reset link has been sent.
        </p>
      ) : (
        <form
          onSubmit={(event) => void handleSubmit(onValid)(event)}
          noValidate
          className="space-y-4"
        >
          <p className="text-sm text-fg-muted">
            Enter your email address and we will send a link to reset your
            password.
          </p>

          <FormField label="Email" required error={formState.errors.email?.message}>
            <Input type="email" autoComplete="email" autoFocus {...register('email')} />
          </FormField>

          {/* CS-FM-05 — disabled only while the request is in flight. */}
          <Button type="submit" isLoading={formState.isSubmitting} className="w-full">
            Send reset link
          </Button>

          {serverError !== null ? (
            <p ref={errorRef} tabIndex={-1} role="alert" className="text-sm text-danger">
              {serverError}
            </p>
          ) : null}
        </form>
      )}
    </AuthLayout>
  );
};
