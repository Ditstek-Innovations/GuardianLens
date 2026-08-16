import { useState } from 'react';

import { Button, Chip, ChipIcon, FormField, Input, Select } from '@/components/ui';
import { MESSAGES } from '@/constants/messages';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';

import { useRulesQuery, useZonesQuery } from '../api/useConfigQueries';
import { useCreateRule } from '../api/useCreateRule';
import { useSetRuleActive } from '../api/useSetRuleActive';
import { ConfigSection } from './ConfigSection';
import { RuleActivationDialog } from './RuleActivationDialog';

import type { FormEvent } from 'react';
import type { RuleSummary } from '@/lib/api/types';

/**
 * The rule vocabulary the product currently demos and tests end to end.
 * rule_type is an open string at the API; the UI offers the known one so a
 * typo cannot silently create a rule no evaluator understands.
 */
const RULE_TYPE_OPTIONS = [
  { value: 'ppe_helmet', label: 'PPE — helmet required' },
] as const;

export const RulesSection = () => {
  const { principal } = useAuth();
  const rulesQuery = useRulesQuery();
  const zonesQuery = useZonesQuery();
  const createRule = useCreateRule();
  const setRuleActive = useSetRuleActive();
  const { showToast } = useToast();
  const [pendingRule, setPendingRule] = useState<RuleSummary | null>(null);
  const [ruleName, setRuleName] = useState('');
  const [zoneId, setZoneId] = useState('');
  const [ruleType, setRuleType] = useState<string>(RULE_TYPE_OPTIONS[0].value);
  const [threshold, setThreshold] = useState('0.5');
  const [debounce, setDebounce] = useState('30');
  const [dwell, setDwell] = useState('');
  const [writtenRef, setWrittenRef] = useState('');
  const [detectionClass, setDetectionClass] = useState('person_without_helmet');
  const [formError, setFormError] = useState<string | null>(null);

  const zones = zonesQuery.data ?? [];
  const effectiveZoneId = zoneId !== '' ? zoneId : (zones[0]?.id ?? '');

  const handleCreate = (event: FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const trimmedName = ruleName.trim();
    const parsedThreshold = Number(threshold);
    const parsedDebounce = Number(debounce);
    if (trimmedName === '' || effectiveZoneId === '') {
      setFormError('Rule text and zone are required.');
      return;
    }
    if (Number.isNaN(parsedThreshold) || parsedThreshold < 0 || parsedThreshold > 1) {
      setFormError('Confidence threshold must be between 0 and 1.');
      return;
    }
    if (!Number.isInteger(parsedDebounce) || parsedDebounce < 0) {
      setFormError('Debounce must be a whole number of seconds, 0 or more.');
      return;
    }
    const trimmedDwell = dwell.trim();
    const parsedDwell = trimmedDwell === '' ? null : Number(trimmedDwell);
    if (parsedDwell !== null && (!Number.isInteger(parsedDwell) || parsedDwell < 0)) {
      setFormError('Dwell must be empty, or a whole number of seconds, 0 or more.');
      return;
    }
    const trimmedDetectionClass = detectionClass.trim();
    if (trimmedDetectionClass === '') {
      setFormError('Detection class is required — the model-output class this rule watches for.');
      return;
    }
    setFormError(null);
    // No confirmation dialog here on purpose: creation is inert (BR-001,
    // created inactive always); activation below is the confirmed act.
    createRule.mutate(
      {
        zoneId: effectiveZoneId,
        ruleType,
        confidenceThreshold: parsedThreshold,
        debounceSeconds: parsedDebounce,
        dwellSeconds: parsedDwell,
        humanReadable: trimmedName,
        writtenRuleReference: writtenRef.trim() === '' ? null : writtenRef.trim(),
        detectionClass: trimmedDetectionClass,
      },
      {
        onSuccess: () => {
          setRuleName('');
          setWrittenRef('');
          setDwell('');
          showToast({ tone: 'success', message: MESSAGES.config.ruleCreated });
        },
        onError: () => {
          showToast({ tone: 'failure', message: MESSAGES.config.ruleCreateFailed });
        },
      },
    );
  };

  const handleConfirm = (): void => {
    if (pendingRule === null) return;
    const willBeActive = !pendingRule.is_active;
    const ruleName = pendingRule.human_readable;
    setRuleActive.mutate(
      { ruleId: pendingRule.id, isActive: willBeActive },
      {
        onSuccess: () => {
          setPendingRule(null);
          // CS-MSG-01/02 — outcome + consequence from the catalogue;
          // activation is attributable (BR-C-02).
          showToast({
            tone: 'success',
            message: willBeActive
              ? MESSAGES.config.ruleActivated(ruleName)
              : MESSAGES.config.ruleDeactivated(ruleName),
          });
        },
        onError: () => {
          // The dialog stays open for retry; the toast names the next step
          // (CS-MSG-05). The list is server-truth: nothing shown optimistically
          // (CS-AD-04).
          showToast({ tone: 'failure', message: MESSAGES.config.ruleChangeFailed });
        },
      },
    );
  };

  const handleCancel = (): void => {
    setPendingRule(null);
  };

  const form = (
    <form
      onSubmit={handleCreate}
      noValidate
      aria-label="Create rule"
      className="grid gap-4 lg:grid-cols-12"
    >
      <FormField
        label="Rule text"
        required
        hint="Shown to reviewers exactly as written, e.g. “Helmet required in Bay 3”."
        error={formError ?? undefined}
        className="lg:col-span-4"
      >
        <Input value={ruleName} onChange={(event) => setRuleName(event.target.value)} />
      </FormField>
      <FormField label="Zone" required className="lg:col-span-3">
        <Select value={effectiveZoneId} onChange={(event) => setZoneId(event.target.value)}>
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name}
            </option>
          ))}
        </Select>
      </FormField>
      <FormField label="Type" required className="lg:col-span-3">
        <Select value={ruleType} onChange={(event) => setRuleType(event.target.value)}>
          {RULE_TYPE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </FormField>
      <FormField
        label="Detection class"
        required
        hint="The model-output class this rule watches for, e.g. person_without_helmet, backpack. Must match a class the approved model actually emits."
        className="lg:col-span-4"
      >
        <Input
          value={detectionClass}
          onChange={(event) => setDetectionClass(event.target.value)}
        />
      </FormField>
      <FormField
        label="Confidence threshold"
        required
        hint="0–1. Orders and annotates candidates; it never decides (BR-V-03)."
        className="lg:col-span-2"
      >
        <Input
          type="number"
          min={0}
          max={1}
          step={0.05}
          inputMode="decimal"
          value={threshold}
          onChange={(event) => setThreshold(event.target.value)}
        />
      </FormField>
      <FormField
        label="Debounce (seconds)"
        required
        hint="Quiet period before the same rule can fire again."
        className="lg:col-span-2"
      >
        <Input
          type="number"
          min={0}
          step={1}
          inputMode="numeric"
          value={debounce}
          onChange={(event) => setDebounce(event.target.value)}
        />
      </FormField>
      <FormField
        label="Dwell (seconds)"
        hint="How long the condition must persist before firing. Empty fires on the first frame."
        className="lg:col-span-2"
      >
        <Input
          type="number"
          min={0}
          step={1}
          inputMode="numeric"
          value={dwell}
          onChange={(event) => setDwell(event.target.value)}
        />
      </FormField>
      <FormField
        label="Written rule reference"
        hint="The site safety rule this enforces (BR-011 — advisory, but expected)."
        className="lg:col-span-5"
      >
        <Input value={writtenRef} onChange={(event) => setWrittenRef(event.target.value)} />
      </FormField>
      <div className="flex items-end justify-end lg:col-span-3">
        <Button type="submit" isLoading={createRule.isPending}>
          Create inactive rule
        </Button>
      </div>
    </form>
  );

  return (
    <ConfigSection
      title="Detection rules"
      description="What is monitored, and where. Nothing is monitored until a rule is explicitly activated (BR-001)."
      query={rulesQuery}
      emptyDetail="No rules are defined."
      actions={form}
    >
      {(rules) => (
        <>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs font-medium uppercase tracking-wide text-fg-muted">
                <th scope="col" className="h-10 px-4">Rule</th>
                <th scope="col" className="h-10 px-4">Type</th>
                <th scope="col" className="h-10 px-4">Detection class</th>
                <th scope="col" className="h-10 px-4">Timing</th>
                <th scope="col" className="h-10 px-4">State</th>
                <th scope="col" className="h-10 px-4">Activated by</th>
                <th scope="col" className="h-10 px-4">Written rule reference</th>
                <th scope="col" className="h-10 px-4">
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {rules.map((rule) => (
                <tr key={rule.id} className="h-10 transition-colors duration-120 hover:bg-surface-2">
                  <td className="px-4 py-2 text-fg">{rule.human_readable}</td>
                  <td className="px-4 py-2 text-fg-muted">{rule.rule_type}</td>
                  <td className="px-4 py-2 font-mono text-xs text-fg-muted">{rule.detection_class}</td>
                  <td className="px-4 py-2 text-fg-muted">
                    {rule.debounce_seconds}s debounce
                    {rule.dwell_seconds != null ? `, ${rule.dwell_seconds}s dwell` : ''}
                  </td>
                  <td className="px-4 py-2">
                    {rule.is_active ? (
                      <Chip variant="ok" icon={<ChipIcon glyph="check" />}>
                        Active
                      </Chip>
                    ) : (
                      <Chip variant="neutral" icon={<ChipIcon glyph="circle" />}>
                        Inactive
                      </Chip>
                    )}
                  </td>
                  <td className="px-4 py-2 text-fg-muted">
                    {rule.activated_by?.full_name ?? '—'}
                  </td>
                  <td className="px-4 py-2">
                    {rule.written_rule_reference ?? (
                      // BR-011 (ADVISORY) — the absence is flagged, not blocked.
                      <Chip variant="warn" icon={<ChipIcon glyph="alert" />}>
                        No written rule reference
                      </Chip>
                    )}
                  </td>
                  <td className="px-4 py-2">
                    <Button size="sm" variant="secondary" onClick={() => setPendingRule(rule)}>
                      {rule.is_active ? 'Deactivate' : 'Activate'}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {pendingRule !== null && principal !== null ? (
            <RuleActivationDialog
              rule={pendingRule}
              actorName={principal.fullName}
              isSubmitting={setRuleActive.isPending}
              onConfirm={handleConfirm}
              onCancel={handleCancel}
            />
          ) : null}
        </>
      )}
    </ConfigSection>
  );
};
