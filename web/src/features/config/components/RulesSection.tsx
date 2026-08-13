import { useState } from 'react';

import { Button, Chip, ChipIcon } from '@/components/ui';
import { MESSAGES } from '@/constants/messages';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/hooks/useToast';

import { useRulesQuery } from '../api/useConfigQueries';
import { useSetRuleActive } from '../api/useSetRuleActive';
import { ConfigSection } from './ConfigSection';
import { RuleActivationDialog } from './RuleActivationDialog';

import type { RuleSummary } from '@/lib/api/types';

export const RulesSection = () => {
  const { principal } = useAuth();
  const rulesQuery = useRulesQuery();
  const setRuleActive = useSetRuleActive();
  const { showToast } = useToast();
  const [pendingRule, setPendingRule] = useState<RuleSummary | null>(null);

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

  return (
    <ConfigSection title="Detection rules" query={rulesQuery} emptyDetail="No rules are defined.">
      {(rules) => (
        <>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs font-medium uppercase tracking-wide text-fg-muted">
                <th scope="col" className="h-10 px-4">Rule</th>
                <th scope="col" className="h-10 px-4">Type</th>
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
