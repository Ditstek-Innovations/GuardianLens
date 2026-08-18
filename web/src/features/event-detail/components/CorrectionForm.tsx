import { useState } from 'react';

import { Button, FormField, Input, Modal, Select } from '@/components/ui';
import { CORRECTABLE_FIELD } from '@/constants/events';
import { assertNever } from '@/lib/utils/assertNever';

import type { ChangeEvent, FormEvent } from 'react';
import type { CorrectableField } from '@/constants/events';
import type { EventDetail } from '@/lib/api/types';
import type { FieldCorrection } from '@/types/decision';

export interface CorrectionFormProps {
  readonly event: EventDetail;
  readonly isSubmitting: boolean;
  readonly onSubmit: (correction: FieldCorrection) => void;
  readonly onCancel: () => void;
}

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// TRD §7.4 CorrectionForm — the original model output is displayed alongside.
const originalValueFor = (event: EventDetail, field: CorrectableField): string => {
  switch (field) {
    case CORRECTABLE_FIELD.ZONE:
      return `${event.zone.name} (${event.zone.id})`;
    case CORRECTABLE_FIELD.RULE:
      return event.rule.human_readable;
    default:
      return assertNever(field);
  }
};

export const CorrectionForm = ({ event, isSubmitting, onSubmit, onCancel }: CorrectionFormProps) => {
  const [field, setField] = useState<CorrectableField>(CORRECTABLE_FIELD.ZONE);
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleFieldChange = (changeEvent: ChangeEvent<HTMLSelectElement>): void => {
    const next = changeEvent.target.value;
    if (next === CORRECTABLE_FIELD.ZONE || next === CORRECTABLE_FIELD.RULE) setField(next);
  };

  const handleValueChange = (changeEvent: ChangeEvent<HTMLInputElement>): void => {
    setValue(changeEvent.target.value);
    if (error !== null && changeEvent.target.value.trim() !== '') setError(null);
  };

  const handleSubmit = (submitEvent: FormEvent<HTMLFormElement>): void => {
    submitEvent.preventDefault();
    const trimmed = value.trim();
    if (trimmed === '') {
      setError('A corrected value is required.');
      return;
    }
    if (!UUID_PATTERN.test(trimmed)) {
      setError('The corrected value must be a UUID (TRD §10.1 identifiers).');
      return;
    }
    onSubmit({ field, value: trimmed });
  };

  const originalValue = originalValueFor(event, field);

  return (
    <Modal title="Correct candidate" onClose={onCancel}>
      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        <FormField label="Field to correct">
          <Select value={field} onChange={handleFieldChange}>
            <option value={CORRECTABLE_FIELD.ZONE}>Zone</option>
            <option value={CORRECTABLE_FIELD.RULE}>Rule</option>
          </Select>
        </FormField>
        <div>
          <p className="text-sm font-medium text-fg">Original value</p>
          <p className="mt-1 rounded-control bg-surface-2 px-3 py-2 text-sm text-fg-muted">
            {originalValue}
          </p>
        </div>
        <FormField
          label="Corrected value"
          required
          error={error ?? undefined}
          hint="UUID of the correct zone or rule"
        >
          <Input value={value} onChange={handleValueChange} autoComplete="off" />
        </FormField>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Submit correction
          </Button>
        </div>
      </form>
    </Modal>
  );
};
