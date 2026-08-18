import { useEffect, useRef, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router-dom';

import { Button, FormField, Input, PasswordInput } from '@/components/ui';
import { ROUTES } from '@/constants/routes';
import { ApiError } from '@/lib/api/errors';

import { requestSignup } from '../api/authApi';
import { PASSWORD_POLICY_HINT, signupSchema } from '../schemas';

import { AuthLayout } from './AuthLayout';

import type { SignupValues } from '../schemas';

// FRONTEND_CODING_STANDARDS §23.3 — SCR-1a (CS-AU-16).
//
// Enumeration-safe by construction (CS-AU-10): the server always answers 202
// with one generic acceptance, and this screen NEVER branches on whether
// anything was created — the same outcome renders whether the email or site
// code was already known, and whether the deployment has sign-up enabled.

/** CS-FM-06 — the server names fields on the wire; map them onto the form. */
const SERVER_FIELD_MAP: Readonly<Partial<Record<string, keyof SignupValues>>> = {
  full_name: 'fullName',
  email: 'email',
  password: 'password',
  site_code: 'siteCode',
};

export const SignupPage = () => {
  const [accepted, setAccepted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);
  const acceptedRef = useRef<HTMLDivElement>(null);
  const { register, handleSubmit, setError, formState } = useForm<SignupValues>({
    resolver: zodResolver(signupSchema),
    mode: 'onSubmit',
    reValidateMode: 'onChange',
    defaultValues: { fullName: '', email: '', siteCode: '', password: '' },
  });

  // CS-FM-04 — a failed submit announces itself; acceptance does too.
  useEffect(() => {
    if (serverError !== null) errorRef.current?.focus();
  }, [serverError]);
  useEffect(() => {
    if (accepted) acceptedRef.current?.focus();
  }, [accepted]);

  const onValid = async (values: SignupValues): Promise<void> => {
    setServerError(null);
    try {
      // The response body is deliberately ignored — one acceptance, no
      // branching on payload (CS-AU-16).
      await requestSignup({
        full_name: values.fullName,
        email: values.email,
        password: values.password,
        site_code: values.siteCode,
      });
      setAccepted(true);
    } catch (error) {
      const field = error instanceof ApiError ? SERVER_FIELD_MAP[error.field ?? ''] : undefined;
      if (error instanceof ApiError && field !== undefined) {
        setError(field, { type: 'server', message: error.message }, { shouldFocus: true });
      } else {
        // CS-FM-06 — no identified field: form-level, input preserved.
        setServerError('Something went wrong. Check your connection and try again.');
      }
    }
  };

  return (
    <AuthLayout
      title="Create an account"
      footer={
        // CS-AU-18 — sibling auth screens only.
        <p className="text-fg-muted">
          Already have an account?{' '}
          <Link to={ROUTES.login} className="text-brand-ink underline-offset-2 hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      {accepted ? (
        // CS-AU-16 — the one generic outcome: account requested; a site
        // admin assigns access. Never a word about what already existed.
        <div ref={acceptedRef} tabIndex={-1} role="status" className="space-y-4">
          <p className="text-sm text-fg">Your account has been requested.</p>
          <p className="text-sm text-fg-muted">
            A site administrator assigns access. You will be able to sign in
            once that is done.
          </p>
          <Link to={ROUTES.login} className="inline-block text-sm text-brand-ink underline-offset-2 hover:underline">
            Back to sign in
          </Link>
        </div>
      ) : (
        <form
          onSubmit={(event) => void handleSubmit(onValid)(event)}
          noValidate
          className="space-y-4"
        >
          <FormField label="Full name" required error={formState.errors.fullName?.message}>
            <Input type="text" autoComplete="name" {...register('fullName')} />
          </FormField>

          <FormField label="Email" required error={formState.errors.email?.message}>
            {/* Email-field autofocus is the family rule (§23.3 brief). */}
            <Input type="email" autoComplete="email" autoFocus {...register('email')} />
          </FormField>

          <FormField
            label="Site code"
            required
            hint="Provided by your site administrator."
            error={formState.errors.siteCode?.message}
          >
            <Input type="text" autoComplete="off" {...register('siteCode')} />
          </FormField>

          {/* CS-AU-15 — the policy is stated in the hint BEFORE any failure. */}
          <FormField
            label="Password"
            required
            hint={PASSWORD_POLICY_HINT}
            error={formState.errors.password?.message}
          >
            <PasswordInput autoComplete="new-password" {...register('password')} />
          </FormField>

          {/* CS-FM-05 — disabled only while the request is in flight. */}
          <Button type="submit" isLoading={formState.isSubmitting} className="w-full">
            Request an account
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
