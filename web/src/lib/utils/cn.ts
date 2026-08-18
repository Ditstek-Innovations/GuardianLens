import { clsx } from 'clsx';
import { extendTailwindMerge } from 'tailwind-merge';

import type { ClassValue } from 'clsx';

/**
 * CS-Y-03 — THE class composer: clsx for conditional composition,
 * tailwind-merge so a caller's override actually wins over a primitive's
 * default. The merger is taught the custom §12.1 scale names from
 * tailwind.config.js so it resolves conflicts on them too.
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      rounded: [{ rounded: ['control', 'card', 'modal'] }],
      shadow: [{ shadow: ['ambient', 'glow', 'modal'] }],
      duration: [{ duration: ['120', '160', '240'] }],
    },
  },
});

export const cn = (...parts: ClassValue[]): string => twMerge(clsx(parts));
