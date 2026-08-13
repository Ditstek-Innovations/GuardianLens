import { useEffect, useRef, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';

import { Button, FormField, Input, PasswordInput } from '@/components/ui';
import { ROUTES } from '@/constants/routes';
import { useAuth } from '@/hooks/useAuth';
import { ApiError } from '@/lib/api/errors';

import { loginSchema } from '../schemas';

import { AuthLayout } from './AuthLayout';

import type { LoginValues } from '../schemas';

// FRONTEND_CODING_STANDARDS §23.3 — SCR-1.
//
// CS-AU-10 (amended 1.4): self-service sign-up and password reset EXIST and
// are linked below; social sign-in does not and must stay absent from the
// build. CS-AU-18: this screen links only to its sibling auth screens.

type FailureKind = 'credentials' | 'rate-limited' | null;

/** CS-AU-08 — an internal path only: same-origin, relative, no `//` host trick. */
const safeRedirect = (value: unknown): string => {
  if (typeof value !== 'string') return ROUTES.queue;
  if (!value.startsWith('/') || value.startsWith('//')) return ROUTES.queue;
  return value;
};

export const LoginPage = () => {
  const { principal, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [failure, setFailure] = useState<FailureKind>(null);
  const errorRef = useRef<HTMLParagraphElement>(null);
  // CS-AU-13 / CS-FM-01/02 — schema resolver; validate on submit, then
  // re-validate on change after the first failure. RHF focuses the first
  // invalid field on a failed submit (CS-FM-04).
  const { register, handleSubmit, formState } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    mode: 'onSubmit',
    reValidateMode: 'onChange',
    defaultValues: { email: '', password: '' },
  });

  // CS-AU-11 / CS-FM-04 — a failed submit moves focus to the error text.
  useEffect(() => {
    if (failure !== null) errorRef.current?.focus();
  }, [failure]);

  const onValid = async (values: LoginValues): Promise<void> => {
    setFailure(null);
    try {
      await signIn(values.email, values.password);
      navigate(safeRedirect((location.state as { from?: unknown } | null)?.from), {
        replace: true,
      });
    } catch (error) {
      // CS-AU-05: a rate limit is an honest, distinct message — never folded
      // into the credential error, never auto-retried. Everything else gets
      // the one generic line (CS-AU-04): no enumeration, no cause detail.
      setFailure(error instanceof ApiError && error.status === 429 ? 'rate-limited' : 'credentials');
    }
  };

  if (principal !== null) return <Navigate to={ROUTES.queue} replace />;

  return (
    <AuthLayout
      title="Sign in"
      footer={
        // CS-AU-18 — sibling auth screens only; never a link into the app.
        <div className="flex flex-col gap-2">
          <Link to={ROUTES.signup} className="text-brand-ink underline-offset-2 hover:underline">
            Create an account
          </Link>
          <Link to={ROUTES.forgotPassword} className="text-brand-ink underline-offset-2 hover:underline">
            Forgot password?
          </Link>
        </div>
      }
    >
      <form onSubmit={(event) => void handleSubmit(onValid)(event)} noValidate className="space-y-4">
        <FormField label="Email" required error={formState.errors.email?.message}>
          <Input type="email" autoComplete="username" autoFocus {...register('email')} />
        </FormField>

        <FormField label="Password" required error={formState.errors.password?.message}>
          <PasswordInput autoComplete="current-password" {...register('password')} />
        </FormField>

        {/* CS-AU-03 — Button defaults to type="button"; submit is explicit.
            CS-AU-06 / CS-FM-05 — disabled only while the request is in flight. */}
        <Button type="submit" isLoading={formState.isSubmitting} className="w-full">
          Sign in
        </Button>

        {failure === 'credentials' ? (
          // CS-AU-04 — one generic message, persistent, focusable.
          <p ref={errorRef} tabIndex={-1} role="alert" className="text-sm text-danger">
            Email or password is incorrect.
          </p>
        ) : null}
        {failure === 'rate-limited' ? (
          // CS-AU-05 — TRD §12.7: 5/min per IP, 10/hour per account.
          <p ref={errorRef} tabIndex={-1} role="alert" className="text-sm text-danger">
            Too many sign-in attempts. Wait a minute before trying again.
          </p>
        ) : null}
      </form>
    </AuthLayout>
  );
};
