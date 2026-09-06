import { ProcessListItem } from '../../types';
import { RiskClass } from '../../constants';
import ScoreRing from './ScoreRing';
import RiskBadge from './RiskBadge';

interface RoadmapTableProps {
  processes: ProcessListItem[];
  onInspect: (id: string) => void;
  onAudit?: (id: string) => void;
}

export default function RoadmapTable({ processes, onInspect, onAudit }: RoadmapTableProps) {
  return (
    <div className="bg-surface-container-low rounded-xl border border-outline-variant/30 overflow-hidden">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-outline-variant/30 bg-surface-container/50">
            <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider w-16">Rank</th>
            <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Process Name & Dept</th>
            <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Frequency & Vol</th>
            <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider">Target Systems</th>
            <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider text-center">Viability Index</th>
            <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider text-center">Risk Tier</th>
            <th className="px-6 py-4 text-xs font-semibold text-on-surface-variant uppercase tracking-wider text-right">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-outline-variant/20">
          {processes.map((process, index) => {
            const isRisky = process.score.risk_decision === RiskClass.TOO_RISKY;
            const hoverColor = isRisky ? 'group-hover:text-error' : 'group-hover:text-primary';

            return (
              <tr key={process.id} className="group hover:bg-surface-container/50 transition-colors cursor-pointer" onClick={() => onInspect(process.id)}>
                <td className="px-6 py-4">
                  <span className="text-sm font-mono text-on-surface-variant">#{process.rank || index + 1}</span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-col">
                    <span className={`text-sm font-semibold text-on-surface transition-colors ${hoverColor}`}>{process.name}</span>
                    <span className="text-xs text-on-surface-variant">{process.department}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-col">
                    <span className="text-sm font-mono text-on-surface">{process.cases_per_month.toLocaleString()} <span className="text-xs text-on-surface-variant font-sans">cases/mo</span></span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-wrap gap-1.5">
                    {process.systems.slice(0, 3).map(sys => (
                      <span key={sys} className="px-2 py-0.5 rounded bg-surface-container-high text-[10px] uppercase tracking-wider text-on-surface-variant border border-outline-variant/20">
                        {sys}
                      </span>
                    ))}
                    {process.systems.length > 3 && (
                      <span className="px-2 py-0.5 rounded bg-surface-container-high text-[10px] text-on-surface-variant border border-outline-variant/20">
                        +{process.systems.length - 3}
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 text-center">
                  <ScoreRing score={process.score.value_score} riskClass={process.score.risk_decision} />
                </td>
                <td className="px-6 py-4 text-center">
                  <RiskBadge riskClass={process.score.risk_decision} />
                </td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      if (isRisky && onAudit) onAudit(process.id);
                      else onInspect(process.id);
                    }}
                    className="text-xs font-semibold px-4 py-2 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface transition-colors border border-outline-variant/30 flex items-center space-x-1 ml-auto"
                  >
                    <span>{isRisky ? 'Audit Trail' : 'Inspect'}</span>
                    <span className="material-symbols-outlined text-[16px]">chevron_right</span>
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
