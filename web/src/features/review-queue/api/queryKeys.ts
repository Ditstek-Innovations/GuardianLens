// CS-D-03 — key factory; never an inline array literal.
export const queueKeys = {
  all: ['queue'] as const,
  lists: () => [...queueKeys.all, 'list'] as const,
  list: (status: string) => [...queueKeys.lists(), status] as const,
};
