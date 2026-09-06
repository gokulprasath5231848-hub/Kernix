import { RiskClass } from '../../constants';

interface RiskVerificationBannerProps {
  passed: boolean;
  riskClass: RiskClass;
  apiEndpoint: string;
}

export default function RiskVerificationBanner({ passed, riskClass, apiEndpoint }: RiskVerificationBannerProps) {
  const isHITL = riskClass === RiskClass.HUMAN_IN_THE_LOOP;
  const isSafe = riskClass === RiskClass.PRE_APPROVED;

  return (
    <div className={`rounded-xl p-4 flex items-center justify-between border ${
      passed ? 'bg-surface-container-low border-status-safe/30' : 'bg-rose-950/20 border-error/30'
    }`}>
      <div className="flex items-center space-x-4">
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
          passed ? 'bg-status-safe/10 text-status-safe' : 'bg-error/10 text-error'
        }`}>
          <span className="material-symbols-outlined text-2xl">{passed ? 'gpp_good' : 'gpp_bad'}</span>
        </div>
        <div>
          <div className="text-xs text-on-surface-variant font-mono uppercase tracking-widest mb-1">Risk Class Verification</div>
          <div className="flex items-center space-x-3">
            <h3 className="font-bold text-lg">{passed ? 'Automated Server-Side Gate Passed' : 'EXECUTION BLOCKED'}</h3>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
              isSafe ? 'bg-status-safe/20 text-status-safe' : isHITL ? 'bg-status-hitl/20 text-status-hitl' : 'bg-error/20 text-error'
            }`}>
              {riskClass.replace(/_/g, ' ')}
            </span>
          </div>
        </div>
      </div>
      <div className="flex space-x-6 text-sm font-mono border-l border-outline-variant/30 pl-6">
        <div>
          <div className="text-xs text-on-surface-variant mb-1">Deterministic Coverage</div>
          <div className="text-on-surface">100.0%</div>
        </div>
        <div>
          <div className="text-xs text-on-surface-variant mb-1">End-to-End Budget</div>
          <div className="text-on-surface">{'< 4500ms'}</div>
        </div>
        <div>
          <div className="text-xs text-on-surface-variant mb-1">Target Checkpoint</div>
          <div className="text-primary truncate max-w-[150px]" title={apiEndpoint}>{apiEndpoint}</div>
        </div>
      </div>
    </div>
  );
}
