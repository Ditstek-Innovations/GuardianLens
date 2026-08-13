import { Button, Modal } from '@/components/ui';

import type { RuleSummary } from '@/lib/api/types';

export interface RuleActivationDialogProps {
  readonly rule: RuleSummary;
  readonly actorName: string;
  readonly isSubmitting: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

/**
 * BR-C-02 / ARCHITECTURE RS-4 — rule activation is explicit and attributable:
 * the confirmation names the acting user before the change is made.
 */
export const RuleActivationDialog = ({
  rule,
  actorName,
  isSubmitting,
  onConfirm,
  onCancel,
}: RuleActivationDialogProps) => {
  const verb = rule.is_active ? 'deactivating' : 'activating';
  const confirmLabel = rule.is_active ? 'Deactivate rule' : 'Activate rule';

  return (
    <Modal title={confirmLabel} onClose={onCancel}>
      <div className="space-y-4">
        <p className="text-sm text-fg">
          You ({actorName}) are {verb} this rule: “{rule.human_readable}”.
        </p>
        {!rule.is_active && rule.written_rule_reference === null ? (
          // BR-011 (ADVISORY) — flag the absence; do not block.
          <p className="rounded-control bg-warn-subtle px-3 py-2 text-sm text-warn">
            This rule references no written site safety rule (BR-011). Activation is allowed, but
            the reference should be added.
          </p>
        ) : null}
        <p className="text-xs text-fg-muted">
          The change is audited and takes effect at the edge within one sync interval
          (ARCHITECTURE RS-4).
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button
            variant={rule.is_active ? 'danger' : 'primary'}
            onClick={onConfirm}
            isLoading={isSubmitting}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  );
};
