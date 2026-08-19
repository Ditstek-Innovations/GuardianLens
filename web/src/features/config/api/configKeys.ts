// CS-D-03 — key factory for configuration resources.
export const configKeys = {
  all: ['config'] as const,
  sites: () => [...configKeys.all, 'sites'] as const,
  cameras: () => [...configKeys.all, 'cameras'] as const,
  zones: () => [...configKeys.all, 'zones'] as const,
  rules: () => [...configKeys.all, 'rules'] as const,
  agents: () => [...configKeys.all, 'agents'] as const,
  models: () => [...configKeys.all, 'models'] as const,
};
