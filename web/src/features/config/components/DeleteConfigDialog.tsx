import { Button, Modal } from "@/components/ui";

interface DeleteConfigDialogProps {
  readonly title: string;
  readonly name: string;
  readonly detail: string;
  readonly isSubmitting: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

export const DeleteConfigDialog = ({
  title,
  name,
  detail,
  isSubmitting,
  onConfirm,
  onCancel,
}: DeleteConfigDialogProps) => (
  <Modal title={title} onClose={onCancel}>
    <div className="space-y-4">
      <p className="text-sm text-fg">
        Delete “{name}”? This action cannot be undone.
      </p>
      <p className="text-xs text-fg-muted">{detail}</p>
      <div className="flex justify-end gap-3">
        <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button variant="danger" onClick={onConfirm} isLoading={isSubmitting}>
          Delete
        </Button>
      </div>
    </div>
  </Modal>
);
