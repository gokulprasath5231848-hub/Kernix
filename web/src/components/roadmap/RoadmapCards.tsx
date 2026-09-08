import { ProcessListItem } from '../../types';
import { RiskClass } from '../../constants';
import ScoreRing from './ScoreRing';
import RiskBadge from './RiskBadge';

interface RoadmapCardsProps {
  processes: ProcessListItem[];
  onInspect: (id: string) => void;
  onAudit?: (id: string) => void;
}

// Mobile card layout for the process catalog — the wide table restacks into
// self-contained cards below the `md` breakpoint. Same data, same actions.
export default function RoadmapCards({ processes, onInspect, onAudit }: RoadmapCardsProps) {
  return (
    <div className="flex flex-col gap-space-md">
      {processes.map((process, index) => {
        const isRisky = process.score.risk_decision === RiskClass.TOO_RISKY;
        return (
          <div
            key={process.id}
            onClick={() => onInspect(process.id)}
            className="bg-surface-container-low rounded-xl border border-outline-variant/30 p-space-md flex flex-col gap-space-sm active:bg-surface-container transition-colors"
          >
            <div className="flex items-start justify-between gap-space-sm">
              <div className="flex items-start gap-space-sm min-w-0">
                <span className="text-xs font-mono text-on-surface-variant mt-1 flex-none">#{process.rank || index + 1}</span>
                <div className="flex flex-col min-w-0">
                  <span className="text-sm font-semibold text-on-surface leading-snug">{process.name}</span>
                  {process.department && <span className="text-xs text-on-surface-variant">{process.department}</span>}
                </div>
              </div>
              <div className="flex-none">
                <ScoreRing score={process.score.value_score} riskClass={process.score.risk_decision} />
              </div>
            </div>

            <div className="flex items-center justify-between gap-space-sm">
              <span className="text-sm font-mono text-on-surface">
                {process.cases_per_month.toLocaleString()} <span className="text-xs text-on-surface-variant font-sans">cases/mo</span>
              </span>
              <RiskBadge riskClass={process.score.risk_decision} />
            </div>

            {process.systems.length > 0 && (
              <div className="flex flex-wrap gap-1.5">
                {process.systems.slice(0, 4).map((sys) => (
                  <span key={sys} className="px-2 py-0.5 rounded bg-surface-container-high text-[10px] uppercase tracking-wider text-on-surface-variant border border-outline-variant/20">
                    {sys}
                  </span>
                ))}
                {process.systems.length > 4 && (
                  <span className="px-2 py-0.5 rounded bg-surface-container-high text-[10px] text-on-surface-variant border border-outline-variant/20">
                    +{process.systems.length - 4}
                  </span>
                )}
              </div>
            )}

            <button
              onClick={(e) => {
                e.stopPropagation();
                if (isRisky && onAudit) onAudit(process.id);
                else onInspect(process.id);
              }}
              className="mt-space-xxs text-xs font-semibold px-4 py-2 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface transition-colors border border-outline-variant/30 flex items-center justify-center gap-1"
            >
              <span>{isRisky ? 'Audit Trail' : 'Inspect'}</span>
              <span className="material-symbols-outlined text-[16px]">chevron_right</span>
            </button>
          </div>
        );
      })}
    </div>
  );
}
