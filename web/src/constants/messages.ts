/**
 * FRONTEND_CODING_STANDARDS §12.2 — THE outcome-message catalogue
 * (CS-MSG-02). Every user-facing operation outcome lives here, typed by
 * operation; a component that inlines an outcome string is duplicating this
 * file.
 *
 * Voice (CS-MSG-01): sentence case, outcome — consequence, no jargon, no
 * exclamation marks. "Success" / "Failed" / "Error occurred" are banned
 * strings — messages.test.ts enforces this over every value below.
 * Failures state the next step and never expose status codes or internal
 * error text (CS-MSG-05).
 */
export const MESSAGES = {
  decision: {
    /** BR-005 — an accept is attribution: the record carries the reviewer. */
    accepted: "Recorded as a verified event — it now carries your name.",
    /** BR-007 — rejections are retained and visible, never discarded. */
    rejected: "Recorded as rejected — it stays visible in the rejection log.",
    corrected:
      "Correction recorded — the original model output is retained alongside it.",
    /** 409 — first decision wins (BR-V-04); the queue invalidates on settle. */
    conflict: "Another reviewer decided this first — the queue has refreshed.",
    failed:
      "The decision was not recorded. Check the connection and try again — nothing was saved.",
    allAccepted: (count: number): string =>
      `${count} records accepted — each verified record now carries your name.`,
    allAcceptedPartial: (result: {
      accepted: number;
      failed: number;
    }): string =>
      `${result.accepted} records accepted; ${result.failed} could not be accepted. The queue has refreshed.`,
    allAcceptFailed:
      "The records could not be accepted. Check the connection and try again — the queue has refreshed.",
  },
  config: {
    ruleActivated: (ruleName: string): string =>
      `Rule active — “${ruleName}” is now monitored. Activation is recorded under your name.`,
    ruleDeactivated: (ruleName: string): string =>
      `Rule inactive — “${ruleName}” is no longer monitored. The change is recorded under your name.`,
    ruleChangeFailed:
      "The rule change was not applied. Check the connection and try again — monitoring is unchanged.",
    /** The creator's grant is part of the transaction (site.created audit). */
    siteSaved:
      "Site created — you hold site admin there, recorded under your name.",
    siteSaveFailed:
      "The site was not created. Check the connection and try again — nothing was stored.",
    /** BR-S-03 / CS-AD-06 — the credential is write-only, stated plainly. */
    cameraSaved:
      "Camera saved — the stream credential is stored and never shown again.",
    cameraSaveFailed:
      "The camera was not saved. Check the connection and try again — nothing was stored.",
    cameraCredentialReplaced:
      "Credential replaced — the new stream credential is sealed and never shown again.",
    cameraCredentialReplaceFailed:
      "The credential was not replaced. Check the connection and try again — the previous credential is unchanged.",
    cameraDisabled: (cameraName: string): string =>
      `Camera disabled — “${cameraName}” is no longer watched from the next edge sync.`,
    cameraEnabled: (cameraName: string): string =>
      `Camera enabled — “${cameraName}” is watched again from the next edge sync.`,
    cameraStatusChangeFailed:
      "The camera change was not applied. Check the connection and try again — monitoring is unchanged.",
    cameraDeleted: (cameraName: string): string =>
      `Camera deleted — “${cameraName}” has been permanently removed.`,
    cameraDeleteBlocked:
      "This camera has zones or monitoring records and cannot be deleted. Disable it to stop monitoring while preserving history.",
    cameraDeleteFailed:
      "The camera was not deleted. Check the connection and try again — nothing was removed.",
    zoneSaved: "Zone saved — its rules apply from the next edge sync.",
    zoneSaveFailed:
      "The zone was not saved. Check the connection and try again — nothing was stored.",
    zoneDeleted: (zoneName: string): string =>
      `Zone deleted — “${zoneName}” has been permanently removed.`,
    zoneDeleteBlocked:
      "This zone has rules or monitoring records. Delete its rules first; monitoring history cannot be removed.",
    zoneDeleteFailed:
      "The zone was not deleted. Check the connection and try again — nothing was removed.",
    /** BR-001 — creation is inert; activation is a separate, confirmed act. */
    ruleCreated:
      "Rule created inactive — nothing is monitored until you activate it explicitly.",
    ruleCreateFailed:
      "The rule was not created. Check the connection and try again — nothing was stored.",
    ruleDeleted: (ruleName: string): string =>
      `Rule deleted — “${ruleName}” is no longer sent to the edge agent.`,
    ruleDeleteFailed:
      "The rule was not deleted. Check the connection and try again — nothing was removed.",
    /** The one-time credential contract, stated at the moment it matters. */
    agentRegistered:
      "Agent registered — copy its credential now; it is never shown again.",
    agentRegisterFailed:
      "The agent was not registered. Check the connection and try again — nothing was stored.",
    agentDeleted: (agentName: string): string =>
      `Agent deleted — “${agentName}” can no longer authenticate after its current token expires.`,
    agentDeleteBlocked:
      "This agent has monitoring records and cannot be deleted because their provenance must be preserved.",
    agentDeleteFailed:
      "The agent was not deleted. Check the connection and try again — nothing was removed.",
    /** Gate G1 — registration records identity; it does not admit the model. */
    modelRegistered:
      "Model version registered — it is not approved and not deployed until you record an approval.",
    modelRegisterFailed:
      "The model version was not registered. Check the connection and try again — nothing was stored.",
    modelRegisterConflict:
      "That version is already registered. Versions are immutable identity — use a new version string.",
    modelApproved:
      "Approval recorded under your name. This is gate G1 evidence, not a site deployment.",
    modelApproveFailed:
      "The approval was not recorded. Check the connection and try again — the model is unchanged.",
    modelApproveNeedsEvidence:
      "Approval needs a model card and a datasheet reference on this version. Nothing was changed.",
    modelDeleted: (version: string): string =>
      `Model version deleted — “${version}” has been removed from the registry.`,
    modelDeleteBlocked:
      "This model version has monitoring records and cannot be deleted because their evidence provenance must be preserved.",
    modelDeleteFailed:
      "The model version was not deleted. Check the connection and try again — nothing was removed.",
  },
  reports: {
    /** BR-R-02 — provenance rides along in the exported file. */
    exportReady:
      "Export ready — the file includes the period and your name as generator.",
    exportFailed:
      "The export did not complete. Check the connection and try again.",
  },
} as const;
