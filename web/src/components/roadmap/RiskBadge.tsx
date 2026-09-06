import { RiskClass, RISK_LABELS, RISK_COLORS } from '../../constants';

interface RiskBadgeProps {
  riskClass: RiskClass;
}

export default function RiskBadge({ riskClass }: RiskBadgeProps) {
  const label = RISK_LABELS[riskClass];
  const { text, bg, dot } = RISK_COLORS[riskClass];

  return (
    <div className={`inline-flex items-center px-2.5 py-1 rounded-full ${bg} ${text} text-xs font-semibold tracking-wider uppercase border border-current/20`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot} mr-1.5 animate-pulse`}></span>
      {label}
    </div>
  );
}
