import { useState } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

import { createQueryClient } from '@/lib/queryClient';

import { AuthProvider } from './providers/AuthProvider';
import { ErrorBoundary } from './providers/ErrorBoundary';
import { AppRouter } from './router';

/** Composition root only (CS-F-05) — provider tree, nothing else. */
export const App = () => {
  const [queryClient] = useState(createQueryClient);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <AppRouter />
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};
