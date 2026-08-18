import { useRef, useState } from 'react';

import { Button, FormField, Modal, Textarea } from '@/components/ui';

import type { ChangeEvent, FormEvent } from 'react';

export interface RejectionReasonDialogProps {
  readonly draft: string;
  readonly onDraftChange: (value: string) => void;
  readonly isSubmitting: boolean;
  readonly onSubmit: (reason: string) => void;
  readonly onCancel: () => void;
}

/**
 * FR-043 / CS-FM-07 — the rejection reason is mandatory: there is no submit
 * path that records a rejection without one, and no default value that could
 * stand in for the reviewer's words.
 */
export const RejectionReasonDialog = ({
  draft,
  onDraftChange,
  isSubmitting,
  onSubmit,
  onCancel,
}: RejectionReasonDialogProps) => {
  const [error, setError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleChange = (event: ChangeEvent<HTMLTextAreaElement>): void => {
    onDraftChange(event.target.value);
    // CS-FM-02 — re-validate on change only after the first failed submit.
    if (error !== null && event.target.value.trim() !== '') setError(null);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const reason = draft.trim();
    if (reason === '') {
      setError('A rejection reason is required.');
      textareaRef.current?.focus(); // CS-FM-04 — focus the invalid field
      return;
    }
    onSubmit(reason);
  };

  return (
    <Modal title="Reject candidate" onClose={onCancel}>
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <FormField label="Rejection reason" required error={error ?? undefined}>
          <Textarea ref={textareaRef} rows={3} value={draft} onChange={handleChange} />
        </FormField>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
          {/* CS-FM-05 — disabled while the request is in flight, not while invalid. */}
          <Button type="submit" variant="danger" isLoading={isSubmitting}>
            Reject candidate
          </Button>
        </div>
      </form>
    </Modal>
  );
};
