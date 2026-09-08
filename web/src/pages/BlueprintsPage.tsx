import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useBlueprintsCatalog, useGenerateBlueprint, useSubmitForApproval } from '../hooks/useProcesses';
import StatCard from '../components/roadmap/StatCard';
import RiskBadge from '../components/roadmap/RiskBadge';
import { RiskClass } from '../constants';
import { BlueprintCatalogItem } from '../types';
import { APIError } from '../api/client';

// Status → colored pill styling
const STATUS_STYLES: Record<string, { text: string; bg: string }> = {
  'Blocked':            { text: 'text-rose-400',    bg: 'bg-rose-950/40' },
  'Not Generated':      { text: 'text-on-surface-variant', bg: 'bg-surface-container-high' },
  'Draft':              { text: 'text-amber-400',   bg: 'bg-amber-950/40' },
  'Awaiting Approval':  { text: 'text-emerald-400', bg: 'bg-emerald-950/40' },
};

type StatusFilter = 'ALL' | BlueprintCatalogItem['status'];

export default function BlueprintsPage() {
  const { data: catalog, isLoading, isError } = useBlueprintsCatalog();
  const generateMutation = useGenerateBlueprint();
  const submitMutation = useSubmitForApproval();
  const navigate = useNavigate();

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL');
  const [generatingId, setGeneratingId] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const items = useMemo(() => catalog || [], [catalog]);

  const filtered = useMemo(() => {
    if (statusFilter === 'ALL') return items;
    return items.filter(i => i.status === statusFilter);
  }, [items, statusFilter]);

  // Stats
  const total = items.length;
  const generated = items.filter(i => i.blueprint_id).length;
  const awaiting = items.filter(i => i.status === 'Awaiting Approval').length;
  const blocked = items.filter(i => i.status === 'Blocked').length;

  const handleGenerate = async (processId: string) => {
    setGeneratingId(processId);
    setErrorMsg(null);
    try {
      await generateMutation.mutateAsync(processId);
    } catch (err) {
      const msg = err instanceof APIError ? err.message : 'Blueprint generation failed';
      setErrorMsg(msg);
    } finally {
      setGeneratingId(null);
    }
  };

  const handleSubmit = async (processId: string) => {
    setErrorMsg(null);
    try {
      await submitMutation.mutateAsync(processId);
    } catch (err) {
      const msg = err instanceof APIError ? err.message : 'Submission failed';
      setErrorMsg(msg);
    }
  };

  const filterOptions: { label: string; value: StatusFilter; count: number }[] = [
    { label: 'All', value: 'ALL', count: total },
    { label: 'Not Generated', value: 'Not Generated', count: items.filter(i => i.status === 'Not Generated').length },
    { label: 'Draft', value: 'Draft', count: items.filter(i => i.status === 'Draft').length },
    { label: 'Awaiting Approval', value: 'Awaiting Approval', count: awaiting },
    { label: 'Blocked', value: 'Blocked', count: blocked },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold mb-2">Automation Blueprints</h1>
        <p className="text-on-surface-variant text-sm">
          Catalog of every process's automation blueprint — generate, review, and submit for approval.
        </p>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Processes" value={String(total)} icon="inventory_2" />
        <StatCard label="Blueprints Generated" value={String(generated)} icon="draw" accentColor="border-amber-400" />
        <StatCard label="Awaiting Approval" value={String(awaiting)} icon="pending_actions" accentColor="border-emerald-400" />
        <StatCard label="Blocked" value={String(blocked)} icon="block" accentColor="border-rose-400" />
      </div>

      {/* Error banner */}
      {errorMsg && (
        <div className="bg-rose-950/40 border border-rose-400/30 text-rose-300 px-4 py-3 rounded-lg text-sm flex items-center space-x-2">
          <span className="material-symbols-outlined text-[18px]">error</span>
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="ml-auto text-rose-400 hover:text-rose-200">
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      )}

      {/* Filter chips */}
      <div className="flex items-center space-x-2 bg-surface-container-low p-2 rounded-xl border border-outline-variant/30 w-fit">
        {filterOptions.map(opt => (
          <button
            key={opt.value}
            onClick={() => setStatusFilter(opt.value)}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors flex items-center space-x-2 ${
              statusFilter === opt.value
                ? 'bg-primary text-on-primary'
                : 'text-on-surface-variant hover:text-on-surface hover:bg-surface-container'
            }`}
          >
            <span>{opt.label}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded-md ${statusFilter === opt.value ? 'bg-on-primary/20' : 'bg-surface-container-high'}`}>
              {opt.count}
            </span>
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-surface-container-low rounded-xl border border-outline-variant/30 overflow-x-auto">
        {isLoading ? (
          <div className="p-12 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>
        ) : isError ? (
          <div className="p-12 text-center text-error">Failed to load blueprint catalog.</div>
        ) : (
          <table className="w-full min-w-[680px] text-left text-sm">
            <thead className="bg-surface-container/50 border-b border-outline-variant/30">
              <tr>
                <th className="px-6 py-4 font-semibold text-on-surface-variant uppercase text-xs">Process</th>
                <th className="px-6 py-4 font-semibold text-on-surface-variant uppercase text-xs text-center">Risk</th>
                <th className="px-6 py-4 font-semibold text-on-surface-variant uppercase text-xs text-center">Score</th>
                <th className="px-6 py-4 font-semibold text-on-surface-variant uppercase text-xs text-center">Status</th>
                <th className="px-6 py-4 font-semibold text-on-surface-variant uppercase text-xs text-right">Est. Hours</th>
                <th className="px-6 py-4 font-semibold text-on-surface-variant uppercase text-xs text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/20">
              {filtered.map(item => {
                const style = STATUS_STYLES[item.status] || STATUS_STYLES['Not Generated'];
                const isGenerating = generatingId === item.process_id;
                const isBlocked = item.status === 'Blocked';

                return (
                  <tr key={item.process_id} className="hover:bg-surface-container/30">
                    {/* Process name + dept */}
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold text-on-surface">{item.process_name}</span>
                        <span className="text-xs text-on-surface-variant">{item.department || '—'}</span>
                      </div>
                    </td>

                    {/* Risk badge */}
                    <td className="px-6 py-4 text-center">
                      <RiskBadge riskClass={item.risk_decision as RiskClass} />
                    </td>

                    {/* Value score */}
                    <td className="px-6 py-4 text-center">
                      <span className="font-mono text-sm">{item.value_score.toFixed(1)}</span>
                    </td>

                    {/* Status pill */}
                    <td className="px-6 py-4 text-center">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold tracking-wider uppercase border border-current/20 ${style.bg} ${style.text}`}>
                        {item.status}
                      </span>
                    </td>

                    {/* Estimated savings hours */}
                    <td className="px-6 py-4 text-right font-mono text-sm text-on-surface-variant">
                      {item.estimated_savings_hours != null ? `${item.estimated_savings_hours.toFixed(1)}h` : '—'}
                    </td>

                    {/* Actions */}
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        {item.status === 'Not Generated' && (
                          <button
                            onClick={() => handleGenerate(item.process_id)}
                            disabled={isBlocked || isGenerating}
                            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-primary text-on-primary hover:bg-primary/80 transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center space-x-1"
                          >
                            {isGenerating ? (
                              <><div className="animate-spin rounded-full h-3 w-3 border-b-2 border-on-primary" /><span>Generating…</span></>
                            ) : (
                              <><span className="material-symbols-outlined text-[14px]">auto_awesome</span><span>Generate</span></>
                            )}
                          </button>
                        )}
                        {item.status === 'Draft' && (
                          <>
                            <button
                              onClick={() => navigate(`/process/${item.process_id}/blueprint`)}
                              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface transition-colors border border-outline-variant/30"
                            >
                              View
                            </button>
                            <button
                              onClick={() => handleSubmit(item.process_id)}
                              disabled={submitMutation.isPending}
                              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 transition-colors disabled:opacity-40"
                            >
                              Submit
                            </button>
                          </>
                        )}
                        {item.status === 'Awaiting Approval' && (
                          <button
                            onClick={() => navigate(`/process/${item.process_id}/blueprint`)}
                            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-surface-container-high hover:bg-surface-container-highest text-on-surface transition-colors border border-outline-variant/30"
                          >
                            View
                          </button>
                        )}
                        {item.status === 'Blocked' && (
                          <span className="text-xs text-on-surface-variant/50 italic" title="Process is TOO_RISKY — blueprint generation is forbidden">
                            Blocked
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!filtered.length && (
                <tr><td colSpan={6} className="px-6 py-8 text-center text-on-surface-variant italic text-sm">No processes match this filter.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
