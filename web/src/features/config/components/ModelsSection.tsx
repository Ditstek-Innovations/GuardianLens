import { useState } from "react";

import {
  Button,
  Chip,
  ChipIcon,
  FormField,
  Input,
  Modal,
  Textarea,
} from "@/components/ui";
import { MESSAGES } from "@/constants/messages";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/useToast";
import { ApiError } from "@/lib/api/errors";
import { formatTimestamp } from "@/lib/format/formatTimestamp";

import {
  modelClassNames,
  useModelVersionsQuery,
} from "../api/useConfigQueries";
import { useDeleteConfigRecord } from "../api/useDeleteConfigRecord";
import {
  useApproveModelVersion,
  useRegisterModelVersion,
} from "../api/useModelVersionMutations";
import { ConfigSection } from "./ConfigSection";
import { DeleteConfigDialog } from "./DeleteConfigDialog";

import type { FormEvent } from "react";
import type { ModelVersionSummary } from "@/lib/api/types";

/** Matches ModelVersionCreate.version max_length on the API. */
const VERSION_MAX = 40;

interface PendingRegistration {
  readonly version: string;
  readonly artefactHash: string;
  readonly classes: readonly string[];
  readonly modelCardRef: string;
  readonly datasheetRef: string;
  readonly notes: string | null;
}

const parseClasses = (raw: string): string[] =>
  raw
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part !== "");

const normalizeArtefactHash = (raw: string): string => {
  const trimmed = raw.trim();
  if (trimmed.startsWith("sha256:")) return trimmed;
  if (/^[a-fA-F0-9]{64}$/.test(trimmed)) return `sha256:${trimmed}`;
  return trimmed;
};

const hasG1Evidence = (model: ModelVersionSummary): boolean =>
  model.model_card_ref !== null &&
  model.model_card_ref !== "" &&
  model.datasheet_ref !== null &&
  model.datasheet_ref !== "";

const RegisterModelDialog = ({
  pending,
  isSubmitting,
  onConfirm,
  onCancel,
}: {
  readonly pending: PendingRegistration;
  readonly isSubmitting: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}) => (
  <Modal title="Register model version" onClose={onCancel}>
    <div className="space-y-4">
      <p className="text-sm text-fg">
        “{pending.version}” will be recorded as a detection model for this
        tenant, with classes {pending.classes.join(", ")}. Registration is the
        evidence trail — it is not approval and not a site deployment.
      </p>
      <p className="text-xs text-fg-muted">
        The artefact hash is stored as identity. The edge agent still verifies
        the ONNX file against its manifest before it will load. The registration
        is audited.
      </p>
      <div className="flex justify-end gap-3">
        <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button variant="primary" onClick={onConfirm} isLoading={isSubmitting}>
          Register model
        </Button>
      </div>
    </div>
  </Modal>
);

const ApproveModelDialog = ({
  model,
  actorName,
  isSubmitting,
  onConfirm,
  onCancel,
}: {
  readonly model: ModelVersionSummary;
  readonly actorName: string;
  readonly isSubmitting: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}) => (
  <Modal title="Approve model version" onClose={onCancel}>
    <div className="space-y-4">
      <p className="text-sm text-fg">
        You ({actorName}) are recording gate G1 approval for “{model.version}”.
        The approver is taken from your session — it cannot be typed.
      </p>
      <p className="text-xs text-fg-muted">
        Approval is evidence that the card and datasheet were reviewed. It does
        not mark the model deployed at a customer site. The approval is audited.
      </p>
      <div className="flex justify-end gap-3">
        <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button variant="primary" onClick={onConfirm} isLoading={isSubmitting}>
          Record approval
        </Button>
      </div>
    </div>
  </Modal>
);

export const ModelsSection = () => {
  const modelsQuery = useModelVersionsQuery();
  const registerModel = useRegisterModelVersion();
  const approveModel = useApproveModelVersion();
  const deleteModel = useDeleteConfigRecord("model-versions");
  const { principal } = useAuth();
  const { showToast } = useToast();

  const [version, setVersion] = useState("");
  const [artefactHash, setArtefactHash] = useState("");
  const [classes, setClasses] = useState("");
  const [modelCardRef, setModelCardRef] = useState("");
  const [datasheetRef, setDatasheetRef] = useState("");
  const [notes, setNotes] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingRegistration | null>(null);
  const [approveTarget, setApproveTarget] =
    useState<ModelVersionSummary | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ModelVersionSummary | null>(
    null,
  );

  const actorName = principal?.fullName ?? "this session";

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const trimmedVersion = version.trim();
    const hashed = normalizeArtefactHash(artefactHash);
    const parsedClasses = parseClasses(classes);
    const trimmedCard = modelCardRef.trim();
    const trimmedDatasheet = datasheetRef.trim();
    if (trimmedVersion === "" || hashed === "" || parsedClasses.length === 0) {
      setFormError(
        "Version, artefact hash and at least one class are required.",
      );
      return;
    }
    if (trimmedVersion.length > VERSION_MAX) {
      setFormError(`Version must be at most ${VERSION_MAX} characters.`);
      return;
    }
    if (trimmedCard === "" || trimmedDatasheet === "") {
      setFormError(
        "Model card and datasheet references are required so this version can be approved.",
      );
      return;
    }
    setFormError(null);
    setPending({
      version: trimmedVersion,
      artefactHash: hashed,
      classes: parsedClasses,
      modelCardRef: trimmedCard,
      datasheetRef: trimmedDatasheet,
      notes: notes.trim() === "" ? null : notes.trim(),
    });
  };

  const handleConfirmRegister = (): void => {
    if (pending === null) return;
    registerModel.mutate(pending, {
      onSuccess: () => {
        setPending(null);
        setVersion("");
        setArtefactHash("");
        setClasses("");
        setModelCardRef("");
        setDatasheetRef("");
        setNotes("");
        showToast({
          tone: "success",
          message: MESSAGES.config.modelRegistered,
        });
      },
      onError: (error) => {
        showToast({
          tone: "failure",
          message:
            error instanceof ApiError && error.status === 409
              ? MESSAGES.config.modelRegisterConflict
              : MESSAGES.config.modelRegisterFailed,
        });
      },
    });
  };

  const handleConfirmApprove = (): void => {
    if (approveTarget === null) return;
    approveModel.mutate(approveTarget.id, {
      onSuccess: () => {
        setApproveTarget(null);
        showToast({ tone: "success", message: MESSAGES.config.modelApproved });
      },
      onError: (error) => {
        showToast({
          tone: "failure",
          message:
            error instanceof ApiError && error.status === 422
              ? MESSAGES.config.modelApproveNeedsEvidence
              : MESSAGES.config.modelApproveFailed,
        });
      },
    });
  };

  const handleDelete = (): void => {
    if (deleteTarget === null) return;
    const version = deleteTarget.version;
    deleteModel.mutate(deleteTarget.id, {
      onSuccess: () => {
        setDeleteTarget(null);
        showToast({
          tone: "success",
          message: MESSAGES.config.modelDeleted(version),
        });
      },
      onError: (error) => {
        showToast({
          tone: "failure",
          message:
            error instanceof ApiError && error.status === 409
              ? MESSAGES.config.modelDeleteBlocked
              : MESSAGES.config.modelDeleteFailed,
        });
      },
    });
  };

  const form = (
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-label="Register model version"
      className="grid gap-4 lg:grid-cols-12"
    >
      <FormField
        label="Version"
        required
        hint={`Immutable identity, at most ${VERSION_MAX} characters, e.g. hardhat-yolov8n-0.1.0-dev.`}
        error={formError ?? undefined}
        className="lg:col-span-4"
      >
        <Input
          value={version}
          maxLength={VERSION_MAX}
          onChange={(event) => setVersion(event.target.value)}
        />
      </FormField>
      <FormField
        label="Artefact hash"
        required
        hint="SHA-256 of the ONNX file. A bare 64-character hex is stored as sha256:…"
        className="lg:col-span-8"
      >
        <Input
          value={artefactHash}
          onChange={(event) => setArtefactHash(event.target.value)}
          autoComplete="off"
          spellCheck={false}
        />
      </FormField>
      <FormField
        label="Detects"
        required
        hint="Comma-separated class names the model emits. Rules watch these exact strings."
        className="lg:col-span-12"
      >
        <Input
          value={classes}
          onChange={(event) => setClasses(event.target.value)}
          placeholder="hardhat, person_without_helmet"
        />
      </FormField>
      <FormField
        label="Model card"
        required
        hint="Path or URL of the card that was reviewed (gate G1)."
        className="lg:col-span-6"
      >
        <Input
          value={modelCardRef}
          onChange={(event) => setModelCardRef(event.target.value)}
          placeholder="Docs/models/hardhat-yolov8n-0.1.0-dev/CARD.md"
        />
      </FormField>
      <FormField
        label="Datasheet"
        required
        hint="Path or URL of the dataset datasheet. Approval is refused without both references."
        className="lg:col-span-6"
      >
        <Input
          value={datasheetRef}
          onChange={(event) => setDatasheetRef(event.target.value)}
          placeholder="Docs/models/hardhat-yolov8n-0.1.0-dev/DATASHEET.md"
        />
      </FormField>
      <FormField
        label="Notes"
        hint="Known weak conditions, evaluation caveats — documented rather than averaged away."
        className="lg:col-span-12"
      >
        <Textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          rows={3}
        />
      </FormField>
      <div className="flex items-end justify-end lg:col-span-12">
        <Button type="submit" isLoading={registerModel.isPending}>
          Register model
        </Button>
      </div>
    </form>
  );

  return (
    <>
      <ConfigSection
        title="Detection models"
        description="Registered model versions and their approval state (gate G1 evidence trail). The edge agent names one of these on every capture it analyses. Registration is not deployment."
        query={modelsQuery}
        emptyDetail="No model versions are registered. Detection runs as NullDetector — ingestion only — until one is registered and approved."
        actions={form}
        actionLabel="Register model"
      >
        {(models) => (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs font-medium uppercase tracking-wide text-fg-muted">
                <th scope="col" className="h-10 px-4">
                  Version
                </th>
                <th scope="col" className="h-10 px-4">
                  Detects
                </th>
                <th scope="col" className="h-10 px-4">
                  Evidence
                </th>
                <th scope="col" className="h-10 px-4">
                  Approval
                </th>
                <th scope="col" className="h-10 px-4">
                  Deployment
                </th>
                <th scope="col" className="h-10 px-4">
                  Notes
                </th>
                <th scope="col" className="h-10 px-4">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {models.map((model) => {
                const detects = modelClassNames(model.classes);
                const evidenced = hasG1Evidence(model);
                return (
                  <tr
                    key={model.id}
                    className="transition-colors duration-120 hover:bg-surface-2"
                  >
                    <td className="px-4 py-2">
                      <div className="font-mono text-xs text-fg">
                        {model.version}
                      </div>
                      <div
                        className="mt-0.5 max-w-[14rem] truncate font-mono text-[11px] text-fg-muted"
                        title={model.artefact_hash}
                      >
                        {model.artefact_hash}
                      </div>
                    </td>
                    <td className="px-4 py-2 text-fg-muted">
                      {detects.length > 0 ? detects.join(", ") : "—"}
                    </td>
                    <td className="px-4 py-2">
                      {evidenced ? (
                        <Chip variant="ok" icon={<ChipIcon glyph="check" />}>
                          Card and datasheet
                        </Chip>
                      ) : (
                        <Chip variant="warn" icon={<ChipIcon glyph="alert" />}>
                          Evidence incomplete
                        </Chip>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      {model.approved_at !== null ? (
                        <div>
                          <Chip variant="ok" icon={<ChipIcon glyph="check" />}>
                            Approved
                          </Chip>
                          <p className="mt-1 text-xs tabular-nums text-fg-muted">
                            {formatTimestamp(model.approved_at)}
                          </p>
                        </div>
                      ) : (
                        <Chip variant="warn" icon={<ChipIcon glyph="alert" />}>
                          Not approved
                        </Chip>
                      )}
                    </td>
                    <td className="px-4 py-2">
                      {model.deployed_at !== null ? (
                        <Chip variant="ok" icon={<ChipIcon glyph="check" />}>
                          Deployed
                        </Chip>
                      ) : (
                        <Chip
                          variant="neutral"
                          icon={<ChipIcon glyph="circle" />}
                        >
                          Not deployed
                        </Chip>
                      )}
                    </td>
                    <td
                      className="max-w-xs truncate px-4 py-2 text-fg-muted"
                      title={model.notes ?? ""}
                    >
                      {model.notes ?? "—"}
                    </td>
                    <td className="px-4 py-2">
                      <div className="flex justify-end gap-2">
                        {model.approved_at === null ? (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => setApproveTarget(model)}
                            disabled={!evidenced}
                            title={
                              evidenced
                                ? undefined
                                : "Approval needs a model card and a datasheet reference."
                            }
                          >
                            Approve
                          </Button>
                        ) : null}
                        <Button
                          size="sm"
                          variant="danger"
                          onClick={() => setDeleteTarget(model)}
                        >
                          Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </ConfigSection>
      {pending !== null ? (
        <RegisterModelDialog
          pending={pending}
          isSubmitting={registerModel.isPending}
          onConfirm={handleConfirmRegister}
          onCancel={() => setPending(null)}
        />
      ) : null}
      {approveTarget !== null ? (
        <ApproveModelDialog
          model={approveTarget}
          actorName={actorName}
          isSubmitting={approveModel.isPending}
          onConfirm={handleConfirmApprove}
          onCancel={() => setApproveTarget(null)}
        />
      ) : null}
      {deleteTarget !== null ? (
        <DeleteConfigDialog
          title="Delete detection model"
          name={deleteTarget.version}
          detail="Model versions used by monitoring records cannot be deleted because event evidence must remain reproducible."
          isSubmitting={deleteModel.isPending}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      ) : null}
    </>
  );
};
