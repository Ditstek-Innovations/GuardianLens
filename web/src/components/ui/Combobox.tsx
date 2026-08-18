import { forwardRef, useEffect, useMemo, useRef, useState } from 'react';

import { Input } from '@/components/ui/Input';
import { cn } from '@/lib/utils/cn';

interface ComboboxProps {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  placeholder?: string;
  className?: string;
  id?: string;
  required?: boolean;
  'aria-invalid'?: boolean;
  'aria-describedby'?: string;
}

export const Combobox = forwardRef<HTMLInputElement, ComboboxProps>(
  (
    {
      value,
      onChange,
      options,
      placeholder,
      className,
      id,
      required,
      'aria-invalid': ariaInvalid,
      'aria-describedby': ariaDescribedby,
    },
    ref,
  ) => {
    const [isOpen, setIsOpen] = useState(false);
    const [highlightedIndex, setHighlightedIndex] = useState(-1);
    const containerRef = useRef<HTMLDivElement>(null);
    const listRef = useRef<HTMLUListElement>(null);
    const fallbackInputRef = useRef<HTMLInputElement>(null);
    const inputRef = (ref as React.RefObject<HTMLInputElement>) || fallbackInputRef;

    // Filter options based on input value
    const filteredOptions = useMemo(() => {
      if (!value) return options;
      const query = value.toLowerCase();
      return options.filter((option) => option.toLowerCase().includes(query));
    }, [options, value]);

    // Reset highlight index when filter changes
    useEffect(() => {
      setHighlightedIndex(-1);
    }, [filteredOptions]);

    // Handle clicking outside to close
    useEffect(() => {
      const handleClickOutside = (event: MouseEvent) => {
        if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
          setIsOpen(false);
        }
      };
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Keyboard navigation
    const handleKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
      if (!isOpen) {
        if (event.key === 'ArrowDown' || event.key === 'ArrowUp' || event.key === 'Enter') {
          setIsOpen(true);
          event.preventDefault();
        }
        return;
      }

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          setHighlightedIndex((prev) => {
            const next = prev + 1;
            return next >= filteredOptions.length ? 0 : next;
          });
          break;
        case 'ArrowUp':
          event.preventDefault();
          setHighlightedIndex((prev) => {
            const next = prev - 1;
            return next < 0 ? filteredOptions.length - 1 : next;
          });
          break;
        case 'Enter':
          event.preventDefault();
          if (highlightedIndex >= 0 && highlightedIndex < filteredOptions.length) {
            const selectedOption = filteredOptions[highlightedIndex];
            if (selectedOption !== undefined) {
              onChange(selectedOption);
            }
            setIsOpen(false);
          } else {
            setIsOpen(false);
          }
          break;
        case 'Escape':
          event.preventDefault();
          setIsOpen(false);
          break;
        case 'Tab':
          setIsOpen(false);
          break;
        default:
          break;
      }
    };

    // Scroll active option into view
    useEffect(() => {
      if (highlightedIndex >= 0 && listRef.current) {
        const activeEl = listRef.current.children[highlightedIndex] as HTMLElement;
        if (activeEl) {
          activeEl.scrollIntoView({ block: 'nearest' });
        }
      }
    }, [highlightedIndex]);

    return (
      <div ref={containerRef} className={cn('relative w-full', className)}>
        <div className="relative">
          <Input
            ref={inputRef}
            value={value}
            onChange={(e) => {
              onChange(e.target.value);
              setIsOpen(true);
            }}
            onFocus={() => setIsOpen(true)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            id={id}
            required={required}
            aria-invalid={ariaInvalid}
            aria-describedby={ariaDescribedby}
            aria-expanded={isOpen}
            aria-haspopup="listbox"
            role="combobox"
            className="pr-10"
          />
          <button
            type="button"
            tabIndex={-1}
            onClick={() => {
              setIsOpen((prev) => !prev);
              inputRef.current?.focus();
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-fg-muted hover:text-fg transition-colors duration-120"
          >
            <svg
              aria-hidden="true"
              focusable="false"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              className={cn('transition-transform duration-160 ease-out', isOpen && 'rotate-180')}
            >
              <path d="m6 9.5 6 6 6-6" />
            </svg>
          </button>
        </div>

        {isOpen && (
          <div className="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-control border border-border bg-surface-2 shadow-ambient animate-fade-in focus:outline-none custom-scrollbar">
            <ul ref={listRef} role="listbox" className="p-1 space-y-0.5">
              {filteredOptions.length > 0 ? (
                filteredOptions.map((option, index) => {
                  const isSelected = option === value;
                  const isHighlighted = index === highlightedIndex;
                  return (
                    <li
                      key={option}
                      role="option"
                      aria-selected={isSelected}
                      onClick={() => {
                        onChange(option);
                        setIsOpen(false);
                      }}
                      onMouseEnter={() => setHighlightedIndex(index)}
                      className={cn(
                        'flex items-center justify-between px-3 py-2 text-sm rounded-sm cursor-pointer select-none transition-colors duration-120',
                        isHighlighted && 'bg-surface-3 text-fg',
                        !isHighlighted && isSelected && 'bg-brand-subtle text-brand-ink',
                        !isHighlighted && !isSelected && 'text-fg-muted hover:bg-surface-3 hover:text-fg',
                      )}
                    >
                      <span>{option}</span>
                      {isSelected && (
                        <svg
                          width="16"
                          height="16"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth={2.5}
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          className="text-brand-500"
                        >
                          <polyline points="20 6 9 17 4 12" />
                        </svg>
                      )}
                    </li>
                  );
                })
              ) : (
                <li className="px-3 py-2.5 text-xs text-fg-faint italic select-none">
                  No matching classes (type custom value)
                </li>
              )}
            </ul>
          </div>
        )}
      </div>
    );
  },
);

Combobox.displayName = 'Combobox';
