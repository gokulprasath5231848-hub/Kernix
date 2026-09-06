import { RiskClass } from '../../constants';

interface ScoreRingProps {
  score: number;
  size?: number;
  riskClass: RiskClass;
}

export default function ScoreRing({ score, size = 32, riskClass }: ScoreRingProps) {
  const radius = 16;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  let colorClass = 'text-primary';
  if (riskClass === RiskClass.HUMAN_IN_THE_LOOP) colorClass = 'text-secondary';
  if (riskClass === RiskClass.TOO_RISKY) colorClass = 'text-error';

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg className="transform -rotate-90 w-full h-full" viewBox="0 0 36 36">
        <circle
          cx="18"
          cy="18"
          r="16"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          className="text-surface-container-highest"
        />
        <circle
          cx="18"
          cy="18"
          r="16"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className={`${colorClass} transition-all duration-1000 ease-out`}
          strokeLinecap="round"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-[10px] font-mono font-bold text-on-surface">{Math.round(score)}</span>
      </div>
    </div>
  );
}
