import { RiskClass } from '../../constants';

interface ScoreGaugeProps {
  score: number;
  riskClass: RiskClass;
}

export default function ScoreGauge({ score, riskClass }: ScoreGaugeProps) {
  const radius = 90;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  let colorClass = 'text-primary drop-shadow-[0_0_10px_rgba(236,194,70,0.5)]';
  if (riskClass === RiskClass.HUMAN_IN_THE_LOOP) colorClass = 'text-secondary drop-shadow-[0_0_10px_rgba(226,196,102,0.5)]';
  if (riskClass === RiskClass.TOO_RISKY) colorClass = 'text-error drop-shadow-[0_0_10px_rgba(255,180,171,0.5)]';

  return (
    <div className="bg-surface-container-low rounded-2xl p-space-2xl border border-outline-variant/30 flex flex-col items-center justify-center relative overflow-hidden">
      {/* Decorative background grid/radial */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-surface-container-high/30 via-surface-container-low to-transparent"></div>
      
      <div className="relative w-56 h-56 flex items-center justify-center z-10">
        <svg className="transform -rotate-90 w-full h-full" viewBox="0 0 200 200">
          <circle cx="100" cy="100" r="90" fill="none" stroke="currentColor" strokeWidth="8" className="text-surface-container-highest" />
          <circle
            cx="100" cy="100" r="90" fill="none" stroke="currentColor" strokeWidth="8"
            strokeDasharray={circumference} strokeDashoffset={strokeDashoffset}
            className={`${colorClass} transition-all duration-1500 ease-out`} strokeLinecap="round"
          />
          {/* Tick marks */}
          {Array.from({ length: 40 }).map((_, i) => (
            <line
              key={i}
              x1="100" y1="20" x2="100" y2="26"
              stroke="currentColor" strokeWidth="2"
              className={i < (score / 100) * 40 ? 'text-surface-container-highest opacity-50' : 'text-surface-container opacity-20'}
              transform={`rotate(${i * 9} 100 100)`}
            />
          ))}
        </svg>
        
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-[10px] text-on-surface-variant uppercase tracking-widest font-semibold mb-1">Score Index</span>
          <span className="text-6xl font-mono font-bold text-on-surface">{Math.round(score)}</span>
          <span className="text-[10px] text-on-surface-variant/70 uppercase mt-2">Max Viability 100</span>
        </div>
      </div>

      <div className="w-full grid grid-cols-3 gap-2 mt-8 z-10 border-t border-outline-variant/30 pt-4">
        <div className="flex flex-col items-center text-center">
          <span className="text-xs text-on-surface-variant mb-1">Historical</span>
          <span className="text-sm font-mono text-status-safe flex items-center"><span className="material-symbols-outlined text-[14px]">arrow_upward</span>+4.2</span>
        </div>
        <div className="flex flex-col items-center text-center border-l border-r border-outline-variant/30">
          <span className="text-xs text-on-surface-variant mb-1">Confidence</span>
          <span className="text-sm font-mono text-on-surface">94.8%</span>
        </div>
        <div className="flex flex-col items-center text-center">
          <span className="text-xs text-on-surface-variant mb-1">Class</span>
          <span className="text-sm font-mono text-on-surface font-semibold uppercase">{riskClass.split('_')[0]}</span>
        </div>
      </div>
    </div>
  );
}
