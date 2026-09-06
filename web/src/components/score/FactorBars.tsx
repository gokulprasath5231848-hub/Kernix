
interface FactorBarsProps {
  factors: Record<string, number>;
  weights: Record<string, number>;
}

export default function FactorBars({ factors, weights }: FactorBarsProps) {
  const formatName = (key: string) => key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');

  return (
    <div className="bg-surface-container-low rounded-2xl p-space-xl border border-outline-variant/30 flex flex-col justify-between">
      <div className="space-y-4">
        {Object.entries(factors).map(([key, value]) => {
          const weight = weights[key] || 0;
          return (
            <div key={key} className="space-y-1.5">
              <div className="flex justify-between items-end">
                <div className="flex items-center space-x-2">
                  <span className="text-sm font-medium text-on-surface">{formatName(key)}</span>
                  <span className="text-[10px] bg-surface-container-high text-on-surface-variant px-1.5 py-0.5 rounded uppercase">Wt {(weight * 100).toFixed(0)}%</span>
                </div>
                <span className="text-sm font-mono text-on-surface">{Math.round(value)}<span className="text-xs text-on-surface-variant">/100</span></span>
              </div>
              <div className="h-2 w-full bg-surface-container rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-secondary-container via-primary-container to-primary transition-all duration-1000 ease-out rounded-full"
                  style={{ width: `${value}%` }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 p-3 bg-surface-container/50 rounded-lg border border-outline-variant/20 flex justify-between items-center text-xs">
        <div className="flex items-center space-x-2 text-on-surface-variant">
          <span className="material-symbols-outlined text-[16px]">verified</span>
          <span>Evaluated via Matrix v2.1</span>
        </div>
        <span className="font-mono text-on-surface-variant/70">Window: Last 30d</span>
      </div>
    </div>
  );
}
