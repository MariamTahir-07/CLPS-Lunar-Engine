export const MAX_STEPS = 4000, MIN_STEPS = 2
export const STEP_OPTIONS = [0.5, 1, 3, 6, 12, 24, 48]
/** Mirrors backend plan_samples so the UI can explain problems before calling the API. */
export function planSamples(days: number, stepHours: number): { n: number; error: string | null } {
  if (!Number.isFinite(days) || days < 0.5 || days > 120) return { n: 0, error: 'Duration must be between 0.5 and 120 days.' }
  if (!Number.isFinite(stepHours) || stepHours < 0.5 || stepHours > 48) return { n: 0, error: 'Step must be between 0.5 and 48 hours.' }
  const n = Math.floor((days * 24) / stepHours + 1e-9)
  if (n < MIN_STEPS) return { n, error: `Step (${stepHours} h) is too large for ${days} day(s): need at least ${MIN_STEPS} samples (step ≤ ${(days * 12).toFixed(1)} h).` }
  if (n > MAX_STEPS) return { n, error: `Too many samples (${n} > ${MAX_STEPS}). Shorten the period or increase the step.` }
  return { n, error: null }
}
export const fmtUTC = (iso: string) => iso.slice(0, 16).replace('T', ' ') + ' UTC'
export const toApiStart = (local: string) => (local.length === 16 ? local + ':00Z' : local)
