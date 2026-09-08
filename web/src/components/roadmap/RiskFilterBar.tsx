import { RiskClass, RISK_LABELS, RISK_COLORS } from '../../constants';

interface RiskFilterBarProps {
  activeFilter: RiskClass | 'ALL';
  onFilterChange: (filter: RiskClass | 'ALL') => void;
  counts: {
    all: number;
    safe: number;
    hitl: number;
    risky: number;
  };
}

export default function RiskFilterBar({ activeFilter, onFilterChange, counts }: RiskFilterBarProps) {
  return (
    <div className="flex items-center space-x-2 bg-surface-container-low p-2 rounded-xl border border-outline-variant/30 w-fit">
      <button
        onClick={() => onFilterChange('ALL')}
        className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center space-x-2 flex-none whitespace-nowrap ${
          activeFilter === 'ALL'
            ? 'bg-primary text-on-primary'
            : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
        }`}
      >
        <span>All Opportunities</span>
        <span className={`text-xs px-1.5 py-0.5 rounded-md ${activeFilter === 'ALL' ? 'bg-on-primary/20' : 'bg-surface-container-high'}`}>
          {counts.all}
        </span>
      </button>

      <div className="w-px h-6 bg-outline-variant/50 mx-1 flex-none"></div>

      {[RiskClass.PRE_APPROVED, RiskClass.HUMAN_IN_THE_LOOP, RiskClass.TOO_RISKY].map((rc) => {
        const isActive = activeFilter === rc;
        const color = RISK_COLORS[rc];
        let count = 0;
        if (rc === RiskClass.PRE_APPROVED) count = counts.safe;
        if (rc === RiskClass.HUMAN_IN_THE_LOOP) count = counts.hitl;
        if (rc === RiskClass.TOO_RISKY) count = counts.risky;

        return (
          <button
            key={rc}
            onClick={() => onFilterChange(rc)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center space-x-2 flex-none whitespace-nowrap ${
              isActive
                ? 'bg-surface-container-high text-on-surface border border-outline-variant/50'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container border border-transparent'
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${color.dot}`}></span>
            <span>{RISK_LABELS[rc]}</span>
            <span className="text-xs px-1.5 py-0.5 rounded-md bg-surface-container-highest text-on-surface-variant">
              {count}
            </span>
          </button>
        );
      })}
    </div>
  );
}
