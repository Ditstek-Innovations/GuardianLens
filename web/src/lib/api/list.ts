import type { ListResponse } from './types';

/**
 * ASSUMPTION A-7 — TRD §10.6 does not specify the list-response envelope for
 * configuration endpoints. Tolerates both a bare array and { items } while the
 * contract settles (trust-boundary check, CS-G-10).
 */
export const unwrapItems = <T>(data: ListResponse<T> | T[]): T[] =>
  Array.isArray(data) ? data : data.items;
