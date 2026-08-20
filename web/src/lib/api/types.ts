import type { EventStatus } from '@/constants/events';
import type { Role } from '@/constants/roles';

/**
 * Wire types for the control-plane API (TRD §10).
 *
 * Hand-written stand-in for openapi-typescript output (CS-T-01): the backend
 * is being built in parallel (TRD §20.2 step 3) and /api/v1/openapi.json does
 * not exist yet. Replace with generated types when it does. Members marked
 * ASSUMPTION are not specified by TRD §10 and are listed in the build report.
 */

export interface ApiUser {
  id: string;
  full_name: string;
  roles: Role[];
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: ApiUser;
}

/**
 * CS-AU-10 / CS-AU-16 / CS-AU-17 — sign-up and reset-request are
 * enumeration-safe by construction: the server always answers `202` with this
 * one shape whether or not the account, site code or address is known. The
 * client never branches on the payload.
 */
export interface AcceptedResponse {
  status: 'accepted';
  message: string;
}

export interface SignupRequestBody {
  full_name: string;
  email: string;
  password: string;
  site_code: string;
}

export interface PasswordResetRequestBody {
  email: string;
}

export interface PasswordResetBody {
  email: string;
  token: string;
  new_password: string;
}

export interface QueueEventItem {
  id: string;
  camera: { id: string; name: string };
  zone: { id: string; name: string };
  rule: { human_readable: string };
  source: string;
  confidence: number;
  occurred_at: string;
  status: EventStatus;
  evidence_url: string;
  version: number;
  /** FR-013 — which model produced the detection; null for nvr-sourced. */
  model_version?: string | null;
  /** ASSUMPTION A-2 — IANA zone for display (NFR-L-02); not in the TRD §10.4 sample. */
  site_timezone?: string;
}

export interface WhyNotReview {
  camera_id: string;
  camera_name: string;
  stream: string;
  last_seen_classes: string[];
  watched_classes: string[];
  why_not_review: string[];
  matched: boolean;
  observed_at?: string | null;
}

export interface QueuePage {
  items: QueueEventItem[];
  /** Returned on every queue response so the UI honours DP-4 without a second request. */
  queue_depth: number;
  next_cursor: string | null;
  /** Latest edge miss snapshot — why a camera has not produced a Review item. */
  why_not_review?: WhyNotReview[];
}

/**
 * One ongoing condition shown as one queue row. Display grouping ONLY:
 * `event_ids` are the members, each decided individually — there is no
 * incident-level decision anywhere (BR-V-02).
 */
export interface IncidentGroup {
  incident_key: string;
  camera: { id: string; name: string };
  zone: { id: string | null; name: string | null };
  rule: { human_readable: string | null };
  count: number;
  first_occurred_at: string;
  last_occurred_at: string;
  max_confidence: number | null;
  status: string;
  /** NFR-L-02 — times on this group render in the site's clock. */
  site_timezone?: string | null;
  event_ids: string[];
}

export interface IncidentQueueResponse {
  incidents: IncidentGroup[];
  queue_depth: number;
  gap_seconds: number;
  /** True when the grouping scan hit its row cap — counts may be partial. */
  capped: boolean;
  why_not_review?: WhyNotReview[];
}

export interface EventDetail extends QueueEventItem {
  /** ASSUMPTION A-3 — receipt time on the detail response (ADR-007 delay display). */
  received_at?: string;
  /** BR-005 — present exactly when the event is decided; null while unverified. */
  reviewer?: { id: string; full_name: string } | null;
  decided_at?: string | null;
  decision_type?: 'accept' | 'reject' | 'correct' | null;
  rejection_reason?: string | null;
  /** The rule exactly as it stood when the event fired — frozen at ingest,
   * independent of any later edit to the live rule row. */
  rule_snapshot: {
    human_readable: string;
    rule_type: string;
    confidence_threshold: number;
    debounce_seconds: number;
    dwell_seconds: number | null;
    detection_class: string;
  };
}

export interface DecisionResponse {
  id: string;
  status: EventStatus;
  reviewer: { id: string; full_name: string };
  decided_at: string;
  decision_type: 'accept' | 'reject' | 'correct';
  version: number;
}

/** BR-S-01 / CS-B-05 — no reviewer_id field exists in any request variant. */
export type DecisionRequestBody =
  | { decision: 'accept'; version: number }
  | { decision: 'reject'; rejection_reason: string; version: number }
  | { decision: 'correct'; corrections: Array<{ field: string; value: string }>; version: number };

/** TRD §10.8 — the single error envelope. */
export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    field?: string;
    trace_id?: string;
  };
}

export interface ReportGroup {
  zone?: string;
  rule?: string;
  day?: string;
  shift?: string;
  verified_count: number;
}

export interface ReportSummary {
  period: { from: string; to: string };
  generated_by: { id: string; full_name: string };
  generated_at: string;
  basis: string;
  groups: ReportGroup[];
  /** Mandatory — a count without coverage context is misleading (TRD §10.5). */
  coverage_gaps_minutes: number;
  /** RESOLVED A-6 — the server reports all three dispositions (BR-R-03). */
  decision_counts?: { accepted: number; corrected: number; rejected: number };
}

export interface Site {
  id: string;
  name: string;
  timezone: string;
}

export interface CameraSummary {
  id: string;
  site_id: string;
  name: string;
  location_description?: string | null;
  /** Which vendor stream the edge samples — 'primary' (HD) or 'secondary' (SD, lighter to decode). */
  stream_profile: string;
  sample_rate_fps: number;
  /** TRD §9.2 — active | degraded | disconnected | disabled; typed open for boundary honesty. */
  status: string;
  // NOTE deliberately absent: stream_url. The API never returns it (TRD §12.4/§12.5).
}

export interface ZoneSummary {
  id: string;
  camera_id: string;
  name: string;
}

export interface AgentSummary {
  id: string;
  site_id: string;
  name: string;
  /** TRD §9 — active | degraded | offline; typed open for boundary honesty. */
  status: string;
  last_seen_at?: string | null;
  last_health_at?: string | null;
  agent_version?: string | null;
  applied_config_version?: number | null;
  // NOTE deliberately absent: credential_hash. The API never returns it.
}

/** POST /agents only — the composite credential appears exactly once, here. */
export interface AgentRegistered extends AgentSummary {
  credential: string;
}

export interface RuleSummary {
  id: string;
  zone_id: string;
  rule_type: string;
  is_active: boolean;
  confidence_threshold: number;
  debounce_seconds: number;
  /** Seconds a condition must persist before the rule fires; null = fires immediately. */
  dwell_seconds: number | null;
  written_rule_reference: string | null;
  human_readable: string;
  /** The model-output class this rule watches for, e.g. "person_without_helmet". */
  detection_class: string;
  /** Fire only when the condition's box sits inside a detected person's box. */
  must_be_carried: boolean;
  /** ASSUMPTION A-8 — who activated the rule (BR-C-02); TRD §9.4 defines created_by only. */
  activated_by?: { id: string; full_name: string } | null;
}

export interface AuditEntry {
  id: string;
  /** ASSUMPTION A-9 — audit list shape; the TRD defines the table (§9.11), not the GET response. */
  created_at?: string;
  actor?: { id: string; full_name: string } | null;
  action: string;
  entity_type?: string;
  entity_id?: string;
}

export interface ListResponse<T> {
  items: T[];
  next_cursor?: string | null;
}

/** Gate-G1 evidence trail (TRD §10.6) — registration is not deployment. */
export interface ModelVersionSummary {
  id: string;
  version: string;
  artefact_hash: string;
  classes: string[];
  model_card_ref: string | null;
  datasheet_ref: string | null;
  approved_by: string | null;
  approved_at: string | null;
  deployed_at: string | null;
  notes: string | null;
}
