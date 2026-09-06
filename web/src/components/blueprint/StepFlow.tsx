import { BlueprintStep } from '../../types';
import HumanGateBadge from './HumanGateBadge';

interface StepFlowProps {
  steps: BlueprintStep[];
  humanGateIndex: number | null;
}

export default function StepFlow({ steps, humanGateIndex }: StepFlowProps) {
  return (
    <div className="bg-surface-container-lowest rounded-xl border border-outline-variant/30 p-space-2xl overflow-x-auto">
      <div className="flex items-start min-w-max pb-8 relative">
        {steps.map((step, idx) => {
          const isGate = idx === humanGateIndex;
          const isLast = idx === steps.length - 1;

          return (
            <div key={idx} className="flex items-center">
              <div className={`relative flex flex-col w-64 ${isGate ? 'transform -translate-y-4' : ''}`}>
                {isGate && <HumanGateBadge condition={step.approval_condition || 'Manual review required'} />}
                <div className={`bg-surface-container-low p-4 rounded-xl border relative z-10 ${
                  isGate 
                    ? 'border-primary shadow-[0_0_20px_rgba(236,194,70,0.15)] ring-1 ring-primary/50' 
                    : 'border-outline-variant/30 hover:border-outline-variant/60 transition-colors'
                }`}>
                  <div className="flex justify-between items-start mb-3">
                    <span className="text-[10px] font-mono bg-surface-container-high px-2 py-1 rounded text-on-surface-variant border border-outline-variant/20">
                      NODE_{String(idx + 1).padStart(2, '0')}
                    </span>
                    <span className="material-symbols-outlined text-on-surface-variant/50">integration_instructions</span>
                  </div>
                  <h4 className="font-semibold text-sm mb-1">{step.name}</h4>
                  <p className="text-xs text-on-surface-variant mb-4 h-8 line-clamp-2">{step.description}</p>
                  <div className="flex justify-between items-center text-[10px] font-mono border-t border-outline-variant/20 pt-2">
                    <span className="text-primary truncate max-w-[120px]">{step.system}</span>
                    <span className="text-on-surface-variant/50">~1.2s</span>
                  </div>
                </div>
              </div>
              
              {!isLast && (
                <div className="w-16 h-0.5 relative mx-2">
                  <div className="absolute inset-0 bg-outline-variant/30"></div>
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/50 to-transparent -translate-x-full animate-[shimmer_2s_infinite]"></div>
                  <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1.5 h-1.5 border-t-2 border-r-2 border-outline-variant/50 rotate-45"></div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
