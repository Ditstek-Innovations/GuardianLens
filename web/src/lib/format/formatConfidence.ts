/**
 * BR-V-03 — confidence may annotate; it never decides. One formatter, one
 * precision, always with its unit (CS-FMT-04).
 */
export const formatConfidence = (confidence: number): string =>
  `${Math.round(confidence * 100)}%`;
