
interface StatCardProps {
  label: string;
  value: string;
  unit?: string;
  icon: string;
  trend?: string;
  accentColor?: string;
  topBorder?: boolean;
}

export default function StatCard({ label, value, unit, icon, trend, accentColor = 'border-primary', topBorder = true }: StatCardProps) {
  return (
    <div className={`bg-surface-container-low rounded-xl p-space-md md:p-space-lg relative overflow-hidden ${topBorder ? `border-t-2 ${accentColor}` : ''}`}>
      <div className="flex justify-between items-start mb-2 md:mb-4 gap-2">
        <span className="text-xs md:text-sm font-medium text-on-surface-variant leading-tight">{label}</span>
        <span className={`material-symbols-outlined text-lg md:text-xl text-on-surface-variant/50 flex-none`}>{icon}</span>
      </div>
      <div className="flex items-baseline space-x-1">
        <span className="text-2xl md:text-3xl font-mono font-bold text-on-surface">{value}</span>
        {unit && <span className="text-xs md:text-sm text-on-surface-variant font-medium">{unit}</span>}
      </div>
      {trend && (
        <div className="mt-2 text-xs font-medium text-status-safe flex items-center">
          <span className="material-symbols-outlined text-[14px] mr-1">trending_up</span>
          {trend}
        </div>
      )}
    </div>
  );
}
