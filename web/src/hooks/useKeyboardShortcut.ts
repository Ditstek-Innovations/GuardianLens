import { useEffect } from 'react';

interface KeyboardShortcutOptions {
  readonly enabled?: boolean;
}

const isTextEntryTarget = (target: EventTarget | null): boolean =>
  target instanceof HTMLElement &&
  (target.tagName === 'INPUT' ||
    target.tagName === 'TEXTAREA' ||
    target.tagName === 'SELECT' ||
    target.isContentEditable);

/**
 * NFR-ACC-01 keyboard operation. CS-A-11 — shortcuts never fire while focus is
 * in a text field, and modified keystrokes (Ctrl/Alt/Meta) pass through.
 */
export const useKeyboardShortcut = (
  keys: string | readonly string[],
  handler: () => void,
  options: KeyboardShortcutOptions = {},
): void => {
  const { enabled = true } = options;
  // Serialised so the effect dependency is a stable primitive.
  const keyList = typeof keys === 'string' ? keys : keys.join('|');

  useEffect(() => {
    if (!enabled) return undefined;
    const matches = keyList.split('|');
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
      if (isTextEntryTarget(event.target)) return;
      if (!matches.includes(event.key.toLowerCase())) return;
      event.preventDefault();
      handler();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [keyList, handler, enabled]);
};
