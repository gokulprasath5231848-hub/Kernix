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
