
interface HumanGateBadgeProps {
  condition: string;
}

export default function HumanGateBadge({ condition }: HumanGateBadgeProps) {
  return (
    <div className="absolute -top-16 left-1/2 -translate-x-1/2 w-max max-w-[280px] z-20 flex flex-col items-center">
      <div className="bg-secondary-container/20 border border-secondary/30 backdrop-blur rounded-lg p-3 shadow-lg">
        <div className="flex items-center justify-center space-x-2 mb-1.5">
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
          <span className="text-[10px] font-bold uppercase tracking-widest text-secondary">Conditional Human Gate</span>
        </div>
        <div className="text-xs text-on-surface text-center leading-tight mb-2">
          {condition}
        </div>
        <div className="flex justify-center items-center space-x-1 text-[10px] text-on-surface-variant/70 border-t border-secondary/20 pt-1.5">
          <span className="material-symbols-outlined text-[12px]">how_to_reg</span>
          <span>Assignee: L2 Operations (Round Robin)</span>
        </div>
      </div>
      <div className="w-px h-6 bg-gradient-to-b from-secondary/50 to-transparent mt-1"></div>
    </div>
  );
}
