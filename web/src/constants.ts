export enum RiskClass {
  PRE_APPROVED = 'PRE_APPROVED',
  HUMAN_IN_THE_LOOP = 'HUMAN_IN_THE_LOOP',
  TOO_RISKY = 'TOO_RISKY',
}

export const RISK_LABELS: Record<RiskClass, string> = {
  [RiskClass.PRE_APPROVED]: 'Pre-Approved',
  [RiskClass.HUMAN_IN_THE_LOOP]: 'Human-in-the-Loop',
  [RiskClass.TOO_RISKY]: 'Too Risky',
};

export const RISK_COLORS: Record<RiskClass, { text: string; bg: string; dot: string }> = {
  [RiskClass.PRE_APPROVED]: { text: 'text-emerald-400', bg: 'bg-emerald-950/40', dot: 'bg-emerald-400' },
  [RiskClass.HUMAN_IN_THE_LOOP]: { text: 'text-secondary', bg: 'bg-secondary-container/40', dot: 'bg-secondary' },
  [RiskClass.TOO_RISKY]: { text: 'text-rose-400', bg: 'bg-rose-950/40', dot: 'bg-error' },
};

// --- Effort & savings estimation ------------------------------------------
// Fully-loaded labour cost used to turn reclaimable hours into a dollar figure.
// Single knob: change this one value to reprice every $ estimate in the UI.
export const LOADED_HOURLY_RATE = 40; // USD per hour

// Hours a process consumes per month, derived from real data — not a constant.
// The `manual_time` factor is a 0-100 scale where 100 == 60 minutes of handling
// per case, so minutes/case = manual_time * 0.6 and
// hours/month = cases_per_month * minutes/case / 60 = cases_per_month * manual_time / 100.
export function hoursPerMonth(casesPerMonth: number, manualTime: number): number {
  return (casesPerMonth * (manualTime || 0)) / 100;
}

export function annualHours(casesPerMonth: number, manualTime: number): number {
  return hoursPerMonth(casesPerMonth, manualTime) * 12;
}

export function annualSavings(casesPerMonth: number, manualTime: number): number {
  return annualHours(casesPerMonth, manualTime) * LOADED_HOURLY_RATE;
}

// Compact money formatter: 186000 -> "$186K", 1_250_000 -> "$1.3M".
export function formatMoney(amount: number): string {
  if (amount >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000) return `$${Math.round(amount / 1_000)}K`;
  return `$${Math.round(amount)}`;
}
