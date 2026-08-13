import { useEffect } from 'react';

/** CS-RT-07 — every route sets the document title on navigation. */
export const usePageTitle = (title: string): void => {
  useEffect(() => {
    document.title = `${title} · Guardian Lens`;
  }, [title]);
};
