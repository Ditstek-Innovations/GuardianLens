import { useState } from 'react';

import { Button, FormField, Modal, Select } from '@/components/ui';
import { CORRECTABLE_FIELD } from '@/constants/events';
import { assertNever } from '@/lib/utils/assertNever';

import type { ChangeEvent, FormEvent } from 'react';
import type { CorrectableField } from '@/constants/events';
import type { EventDetail } from '@/lib/api/types';
import type { CorrectionOptions } from '@/lib/api/types';
import type { FieldCorrection } from '@/types/decision';

export interface CorrectionFormProps {
  readonly event: EventDetail;
  readonly isSubmitting: boolean;
  readonly options: CorrectionOptions | undefined;
  readonly isLoadingOptions: boolean;
  readonly onSubmit: (correction: FieldCorrection) => void;
  readonly onCancel: () => void;
}

// TRD §7.4 CorrectionForm — the original model output is displayed alongside.
const originalValueFor = (event: EventDetail, field: CorrectableField): string => {
  switch (field) {
    case CORRECTABLE_FIELD.ZONE:
      return event.zone.name ?? 'No zone';
    case CORRECTABLE_FIELD.RULE:
      return event.rule.human_readable;
    default:
      return assertNever(field);
  }
};

export const CorrectionForm = ({
  event,
  isSubmitting,
  options,
  isLoadingOptions,
  onSubmit,
  onCancel,
}: CorrectionFormProps) => {
  const [field, setField] = useState<CorrectableField>(CORRECTABLE_FIELD.ZONE);
  const [value, setValue] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleFieldChange = (changeEvent: ChangeEvent<HTMLSelectElement>): void => {
    const next = changeEvent.target.value;
    if (next === CORRECTABLE_FIELD.ZONE || next === CORRECTABLE_FIELD.RULE) {
      setField(next);
      setValue('');
      setError(null);
    }
  };

  const handleValueChange = (changeEvent: ChangeEvent<HTMLSelectElement>): void => {
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
    onSubmit({ field, value: trimmed });
  };

  const originalValue = originalValueFor(event, field);
  const choices = field === CORRECTABLE_FIELD.ZONE ? options?.zones : options?.rules;

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
          hint="Choose by name; Guardian Lens handles the internal identifier."
        >
          <Select
            value={value}
            onChange={handleValueChange}
            disabled={isLoadingOptions || choices === undefined || choices.length === 0}
          >
            <option value="">
              {isLoadingOptions ? 'Loading choices…' : 'Select the correct value'}
            </option>
            {choices?.map((choice) => (
              <option key={choice.id} value={choice.id}>
                {choice.name}
              </option>
            ))}
          </Select>
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
