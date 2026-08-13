import { Component } from 'react';

import type { ErrorInfo, ReactNode } from 'react';

interface ErrorBoundaryProps {
  readonly children: ReactNode;
}

interface ErrorBoundaryState {
  readonly hasError: boolean;
}

/** CS-G-17 — rendering failures are caught and shown, never a white screen. */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  override componentDidCatch(error: unknown, info: ErrorInfo): void {
    // CS-D-08 — never silent. Console only in the MVP slice; an error
    // reporter with redaction arrives with [V1] observability.
    console.error('Unhandled render failure', error, info);
  }

  override render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div role="alert" className="p-8">
          <h1 className="text-lg font-semibold text-fg">Something went wrong</h1>
          <p className="mt-2 text-sm text-fg-muted">
            Reload the page to continue. If this repeats, contact support.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
