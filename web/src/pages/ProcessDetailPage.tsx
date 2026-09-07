import { useParams, Link } from 'react-router-dom';
import { useProcess, useReevaluate, useWeights } from '../hooks/useProcesses';
import { RiskClass, annualHours, annualSavings, formatMoney } from '../constants';
import ScoreGauge from '../components/score/ScoreGauge';
import FactorBars from '../components/score/FactorBars';
import EvidenceTrail from '../components/score/EvidenceTrail';
import MilestoneStepper from '../components/score/MilestoneStepper';
import RiskBadge from '../components/roadmap/RiskBadge';

export default function ProcessDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: process, isLoading, isError } = useProcess(id);
  const { data: weightsConfig } = useWeights();
  const reevaluate = useReevaluate();

  if (isLoading) return <div className="p-8 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div></div>;
  if (isError || !process) return <div className="p-8 text-error">Failed to load process details.</div>;

  const isRisky = process.score.risk_decision === RiskClass.TOO_RISKY;

  // Per-process effort/savings, derived from this process's own data.
  const hoursPerYear = annualHours(process.cases_per_month, process.score.manual_time);
  const savingsPerYear = annualSavings(process.cases_per_month, process.score.manual_time);
  // Confidence = mean completeness of the evidence backing this process.
  const evidence = process.evidence_trail || [];
  const confidencePct = evidence.length
    ? (evidence.reduce((s, e) => s + (e.confidence ?? 0), 0) / evidence.length) * 100
    : null;

  const factors = {
    frequency_volume: process.score.frequency_volume,
    manual_time: process.score.manual_time,
    rule_determinism: process.score.rule_determinism,
    api_readiness: process.score.api_readiness,
    exception_frequency: process.score.exception_frequency,
    privacy_risk: process.score.privacy_risk,
  };

  return (
    <div className="space-y-space-2xl max-w-7xl mx-auto">
      {/* Breadcrumb & Meta */}
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center space-x-2 text-sm text-on-surface-variant mb-4">
            <Link to="/" className="hover:text-primary transition-colors">Roadmap</Link>
            <span className="material-symbols-outlined text-[16px]">chevron_right</span>
            <span>{process.department}</span>
            <span className="material-symbols-outlined text-[16px]">chevron_right</span>
            <span className="text-on-surface">{process.name}</span>
            <span className="text-primary font-mono ml-2">#{process.rank}</span>
          </div>
          <div className="flex items-center space-x-4">
            <h1 className="text-3xl font-bold tracking-tight">{process.name}</h1>
            <RiskBadge riskClass={process.score.risk_decision} />
            <span className="text-xs font-mono bg-surface-container px-2 py-1 rounded text-on-surface-variant border border-outline-variant/30">FASTAPI_PID: {process.id.substring(0,8)}</span>
          </div>
        </div>
        <div className="flex space-x-3">
          <button 
            onClick={() => reevaluate.mutate(process.id)}
            disabled={reevaluate.isPending}
            className="px-4 py-2 rounded-lg bg-surface-container-high border border-outline-variant/30 text-sm font-medium hover:bg-surface-container-highest transition-colors flex items-center space-x-2 disabled:opacity-50"
          >
            <span className={`material-symbols-outlined text-[18px] ${reevaluate.isPending ? 'animate-spin' : ''}`}>sync</span>
            <span>Re-evaluate Telemetry</span>
          </button>
          {!isRisky && (
            <Link 
              to={`/process/${process.id}/blueprint`}
              className="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm font-bold hover:bg-primary/90 transition-colors flex items-center space-x-2 shadow-[0_0_15px_rgba(236,194,70,0.3)]"
            >
              <span className="material-symbols-outlined text-[18px]">architecture</span>
              <span>View Generated Blueprint</span>
            </Link>
          )}
        </div>
      </div>

      <div className="flex items-center space-x-4 bg-surface-container-low p-4 rounded-xl border border-outline-variant/30 w-fit">
        <div className="flex items-center space-x-2">
          <span className="material-symbols-outlined text-status-safe text-xl">savings</span>
          <span className="text-lg font-mono font-bold">{formatMoney(savingsPerYear)}<span className="text-xs text-on-surface-variant font-sans">/yr</span></span>
        </div>
        <div className="w-px h-6 bg-outline-variant/50"></div>
        <div className="flex items-center space-x-2">
          <span className="material-symbols-outlined text-primary text-xl">schedule</span>
          <span className="text-lg font-mono font-bold">{Math.round(hoursPerYear).toLocaleString()}<span className="text-xs text-on-surface-variant font-sans"> hrs/yr</span></span>
        </div>
      </div>

      <div className="bg-surface-container-low/50 rounded-2xl p-8 border border-outline-variant/30 mt-8 mb-12">
        <MilestoneStepper currentStep={2} />
      </div>

      <div className="grid grid-cols-12 gap-space-lg">
        <div className="col-span-5">
          <ScoreGauge
            score={process.score.value_score}
            riskClass={process.score.risk_decision}
            confidence={confidencePct}
            casesPerMonth={process.cases_per_month}
          />
        </div>
        <div className="col-span-7">
          <FactorBars factors={factors} weights={weightsConfig?.weights || {}} />
        </div>
      </div>

      <div className="mt-space-2xl">
        <h3 className="text-lg font-semibold mb-4 flex items-center space-x-2">
          <span className="material-symbols-outlined text-on-surface-variant">dns</span>
          <span>Connected Infrastructure</span>
        </h3>
        <div className="grid grid-cols-4 gap-4">
          {process.systems.map(sys => (
            <div key={sys} className="bg-surface-container-low p-4 rounded-xl border border-outline-variant/30 flex justify-between items-center group hover:bg-surface-container transition-colors cursor-pointer">
              <div className="flex items-center space-x-3">
                <span className="material-symbols-outlined text-on-surface-variant/70 text-2xl group-hover:text-primary transition-colors">memory</span>
                <span className="font-mono text-sm">{sys}</span>
              </div>
              <div className="flex items-center space-x-2 text-[10px]">
                <span className="w-2 h-2 rounded-full bg-status-safe"></span>
                <span className="text-on-surface-variant font-mono">12ms</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <EvidenceTrail events={process.evidence_trail || []} />
    </div>
  );
}
