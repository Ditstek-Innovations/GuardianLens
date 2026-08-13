import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

// CS-C-03 — default export permitted in vite.config.ts only.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': new URL('./src', import.meta.url).pathname },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
