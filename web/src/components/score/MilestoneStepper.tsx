
interface MilestoneStepperProps {
  currentStep: number; // 1 to 4
}

const steps = [
  { num: 1, label: 'Audit', desc: 'Log Telemetry Ingestion' },
  { num: 2, label: 'Scoring', desc: 'Viability & Risk Matrix' },
  { num: 3, label: 'Deployment', desc: 'Supervised Pilot Live' },
  { num: 4, label: 'Full Sovereign', desc: 'Zero-Touch Scaling' }
];

export default function MilestoneStepper({ currentStep }: MilestoneStepperProps) {
  return (
    <div className="flex items-center justify-between w-full relative pt-4 pb-8">
      {/* Connector lines behind */}
      <div className="absolute top-8 left-10 right-10 h-0.5 bg-surface-container-high z-0"></div>
      <div 
        className="absolute top-8 left-10 h-0.5 bg-primary z-0 transition-all duration-1000"
        style={{ width: `calc(${(Math.min(currentStep, 4) - 1) * 33.33}% - 2.5rem)` }}
      ></div>

      {steps.map((step) => {
        const isCompleted = currentStep > step.num;
        const isActive = currentStep === step.num;

        return (
          <div key={step.num} className="relative z-10 flex flex-col items-center group">
            <div className={`w-9 h-9 rounded-full flex items-center justify-center border-2 transition-all duration-300 ${
              isCompleted ? 'bg-primary border-primary text-on-primary shadow-[0_0_10px_rgba(236,194,70,0.5)]' :
              isActive ? 'bg-surface-container-lowest border-primary text-primary' :
              'bg-surface-container-lowest border-surface-container-high text-on-surface-variant'
            }`}>
              {isCompleted ? (
                <span className="material-symbols-outlined text-[18px]">check</span>
              ) : isActive ? (
                <span className="material-symbols-outlined text-[18px] animate-pulse">bolt</span>
              ) : (
                <span className="text-sm font-bold font-mono">{step.num}</span>
              )}
            </div>
            <div className="absolute top-12 text-center w-32 -ml-16 left-1/2">
              <div className={`text-xs font-bold uppercase tracking-wider mb-1 ${
                isActive ? 'text-primary' : isCompleted ? 'text-on-surface' : 'text-on-surface-variant/50'
              }`}>{step.label}</div>
              <div className="text-[10px] text-on-surface-variant leading-tight">{step.desc}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
