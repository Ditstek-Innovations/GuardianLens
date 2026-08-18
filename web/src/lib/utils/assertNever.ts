/** CS-T-14 — exhaustiveness backstop for discriminated unions. */
export const assertNever = (value: never): never => {
  throw new Error(`Unhandled variant: ${JSON.stringify(value)}`);
};
