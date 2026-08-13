import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Vitest runs with globals disabled, so Testing Library's automatic cleanup
// never self-registers — register it explicitly or renders leak across tests.
afterEach(() => {
  cleanup();
});
