import { useEffect, useRef } from 'react';

import type { ReactNode } from 'react';

export interface PageHeadingProps {
  readonly children: ReactNode;
}

/**
 * CS-RT-07 — on navigation, focus moves to the main heading so keyboard and
 * screen-reader users get a signal that the page changed.
 */
export const PageHeading = ({ children }: PageHeadingProps) => {
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    headingRef.current?.focus();
  }, []);

  return (
    // §12.1 type scale — 22px semibold; tracking-tight is baked into the
    // 2xl step in tailwind.config.js.
    <h1 ref={headingRef} tabIndex={-1} className="text-2xl font-semibold text-fg focus:outline-none">
      {children}
    </h1>
  );
};
