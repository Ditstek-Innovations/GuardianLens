import { useState } from "react";

import {
  Button,
  Chip,
  ChipIcon,
  FormField,
  Input,
  Modal,
  Select,
} from "@/components/ui";
import { MESSAGES } from "@/constants/messages";
import { useToast } from "@/hooks/useToast";
import { ApiError } from "@/lib/api/errors";
import { formatTimestamp } from "@/lib/format/formatTimestamp";

import { useAgentsQuery, useRegisterAgent } from "../api/useAgentsQueries";
import { useSitesQuery } from "../api/useConfigQueries";
import { useDeleteConfigRecord } from "../api/useDeleteConfigRecord";
import { ConfigSection } from "./ConfigSection";
import { DeleteConfigDialog } from "./DeleteConfigDialog";

import type { FormEvent } from "react";
import type { ChipGlyph } from "@/components/ui";
import type { AgentSummary } from "@/lib/api/types";

interface AgentStatusPresentation {
  readonly label: string;
  readonly glyph: ChipGlyph;
  readonly variant: "ok" | "warn" | "neutral";
}

// Never colour alone (NFR-ACC-02); a silent agent renders as what it is.
const STATUS_PRESENTATION: Partial<Record<string, AgentStatusPresentation>> = {
  active: { label: "Active", glyph: "check", variant: "ok" },
  degraded: { label: "Degraded", glyph: "alert", variant: "warn" },
  offline: { label: "Offline", glyph: "circle", variant: "neutral" },
};

const statusPresentation = (status: string): AgentStatusPresentation =>
  STATUS_PRESENTATION[status] ?? {
    label: status,
    glyph: "dot",
    variant: "neutral",
  };

interface PendingRegistration {
  readonly siteId: string;
  readonly siteName: string;
  readonly name: string;
}

/**
 * CS-AD-03 — registering an agent is an explicit, confirmed submit that
 * names in plain words what will change and where.
 */
const RegisterAgentDialog = ({
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
  <Modal title="Register agent" onClose={onCancel}>
    <div className="space-y-4">
      <p className="text-sm text-fg">
        “{pending.name}” will be registered as an edge agent at{" "}
        {pending.siteName}. It receives a credential for publishing candidate
        events from that site only.
      </p>
      <p className="text-xs text-fg-muted">
        An agent can never decide an event (BR-S-02) and watches nothing until a
        rule is activated (BR-001). The registration is audited.
      </p>
      <div className="flex justify-end gap-3">
        <Button variant="ghost" onClick={onCancel} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button variant="primary" onClick={onConfirm} isLoading={isSubmitting}>
          Register agent
        </Button>
      </div>
    </div>
  </Modal>
);

/**
 * The one-time credential reveal. The value exists only in this dialog's
 * props — never in the query cache, storage or any later response
 * (the CS-AD-06 write-only discipline, applied to agent credentials).
 */
const CredentialDialog = ({
  agentName,
  credential,
  onClose,
}: {
  readonly agentName: string;
  readonly credential: string;
  readonly onClose: () => void;
}) => {
  const [hasCopied, setHasCopied] = useState(false);

  const handleCopy = (): void => {
    void navigator.clipboard
      .writeText(credential)
      .then(() => setHasCopied(true))
      .catch(() => setHasCopied(false));
  };

  return (
    <Modal title="Agent credential" onClose={onClose}>
      <div className="space-y-4">
        <p className="text-sm text-fg">
          This is the only time the credential for “{agentName}” is shown. The
          server stores a hash and cannot reproduce it — set it as{" "}
          <code className="text-fg">GL_AGENT_CREDENTIAL</code> on the edge
          device now.
        </p>
        <p className="select-all break-all rounded-control border border-border bg-surface-2 p-3 font-mono text-sm text-fg">
          {credential}
        </p>
        <div className="flex justify-end gap-3">
          <Button variant="secondary" onClick={handleCopy}>
            {hasCopied ? "Copied" : "Copy credential"}
          </Button>
          <Button variant="primary" onClick={onClose}>
            Done
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export const AgentsSection = () => {
  const agentsQuery = useAgentsQuery();
  const sitesQuery = useSitesQuery(true);
  const registerAgent = useRegisterAgent();
  const deleteAgent = useDeleteConfigRecord("agents");
  const { showToast } = useToast();
  const [name, setName] = useState("");
  const [siteId, setSiteId] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingRegistration | null>(null);
  const [revealed, setRevealed] = useState<{
    name: string;
    credential: string;
  } | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AgentSummary | null>(null);

  const sites = sitesQuery.data ?? [];
  const effectiveSiteId = siteId !== "" ? siteId : (sites[0]?.id ?? "");

  const handleSubmit = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const trimmed = name.trim();
    const site = sites.find((candidate) => candidate.id === effectiveSiteId);
    if (trimmed === "" || site === undefined) {
      setFormError("Name and site are required.");
      return;
    }
    setFormError(null);
    setPending({ siteId: site.id, siteName: site.name, name: trimmed });
  };

  const handleConfirm = (): void => {
    if (pending === null) return;
    registerAgent.mutate(
      { siteId: pending.siteId, name: pending.name },
      {
        onSuccess: (agent) => {
          setPending(null);
          setName("");
          setRevealed({ name: agent.name, credential: agent.credential });
          showToast({
            tone: "success",
            message: MESSAGES.config.agentRegistered,
          });
        },
        onError: () => {
          // The dialog stays open for retry (CS-MSG-05); nothing was stored.
          showToast({
            tone: "failure",
            message: MESSAGES.config.agentRegisterFailed,
          });
        },
      },
    );
  };

  const handleDelete = (): void => {
    if (deleteTarget === null) return;
    const name = deleteTarget.name;
    deleteAgent.mutate(deleteTarget.id, {
      onSuccess: () => {
        setDeleteTarget(null);
        showToast({
          tone: "success",
          message: MESSAGES.config.agentDeleted(name),
        });
      },
      onError: (error) => {
        showToast({
          tone: "failure",
          message:
            error instanceof ApiError && error.status === 409
              ? MESSAGES.config.agentDeleteBlocked
              : MESSAGES.config.agentDeleteFailed,
        });
      },
    });
  };

  const form = (
    <form
      onSubmit={handleSubmit}
      noValidate
      aria-label="Register agent"
      className="grid gap-4 lg:grid-cols-12"
    >
      <FormField
        label="Name"
        required
        error={formError ?? undefined}
        className="lg:col-span-5"
      >
        <Input value={name} onChange={(event) => setName(event.target.value)} />
      </FormField>
      <FormField label="Site" required className="lg:col-span-4">
        <Select
          value={effectiveSiteId}
          onChange={(event) => setSiteId(event.target.value)}
        >
          {sites.map((site) => (
            <option key={site.id} value={site.id}>
              {site.name}
            </option>
          ))}
        </Select>
      </FormField>
      <div className="flex items-end justify-end lg:col-span-3">
        <Button type="submit" isLoading={registerAgent.isPending}>
          Register agent
        </Button>
      </div>
    </form>
  );

  return (
    <>
      <ConfigSection
        title="Edge agents"
        description="Devices that watch this tenant's cameras and publish candidate events. Each receives a one-time credential at registration."
        query={agentsQuery}
        emptyDetail="No agents are registered."
        actions={form}
        actionLabel="Add agent"
      >
        {(agents) => (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs font-medium uppercase tracking-wide text-fg-muted">
                <th scope="col" className="h-10 px-4">
                  Name
                </th>
                <th scope="col" className="h-10 px-4">
                  Status
                </th>
                <th scope="col" className="h-10 px-4">
                  Last seen
                </th>
                <th scope="col" className="h-10 px-4">
                  Agent version
                </th>
                <th scope="col" className="h-10 px-4">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {agents.map((agent) => {
                const presentation = statusPresentation(agent.status);
                return (
                  <tr
                    key={agent.id}
                    className="h-10 transition-colors duration-120 hover:bg-surface-2"
                  >
                    <td className="px-4 py-2 text-fg">{agent.name}</td>
                    <td className="px-4 py-2">
                      <Chip
                        variant={presentation.variant}
                        icon={<ChipIcon glyph={presentation.glyph} />}
                      >
                        {presentation.label}
                      </Chip>
                    </td>
                    <td className="px-4 py-2 tabular-nums text-fg-muted">
                      {agent.last_seen_at != null
                        ? formatTimestamp(agent.last_seen_at)
                        : "—"}
                    </td>
                    <td className="px-4 py-2 text-fg-muted">
                      {agent.agent_version ?? "—"}
                    </td>
                    <td className="px-4 py-2 text-right">
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => setDeleteTarget(agent)}
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </ConfigSection>
      {pending !== null ? (
        <RegisterAgentDialog
          pending={pending}
          isSubmitting={registerAgent.isPending}
          onConfirm={handleConfirm}
          onCancel={() => setPending(null)}
        />
      ) : null}
      {revealed !== null ? (
        <CredentialDialog
          agentName={revealed.name}
          credential={revealed.credential}
          onClose={() => setRevealed(null)}
        />
      ) : null}
      {deleteTarget !== null ? (
        <DeleteConfigDialog
          title="Delete edge agent"
          name={deleteTarget.name}
          detail="Agents with monitoring records cannot be deleted because event provenance must remain intact."
          isSubmitting={deleteAgent.isPending}
          onConfirm={handleDelete}
          onCancel={() => setDeleteTarget(null)}
        />
      ) : null}
    </>
  );
};
