import { useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useProcesses } from '../hooks/useProcesses';
import { api, APIError } from '../api/client';
import { RiskClass, RISK_LABELS } from '../constants';
import StatCard from '../components/roadmap/StatCard';
import RiskFilterBar from '../components/roadmap/RiskFilterBar';
import RoadmapTable from '../components/roadmap/RoadmapTable';

function downloadFile(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function RoadmapPage() {
  const [activeFilter, setActiveFilter] = useState<RiskClass | 'ALL'>('ALL');
  const [department, setDepartment] = useState('All');
  const [sort, setSort] = useState<'value_score' | 'frequency'>('value_score');
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchMessage, setBatchMessage] = useState('');
  const [uploading, setUploading] = useState(false);
  const [ingestResult, setIngestResult] = useState<{
    message: string;
    events: number;
    processes: number;
    risk: Record<string, number>;
  } | null>(null);
  const [ingestError, setIngestError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const search = (searchParams.get('q') || '').trim().toLowerCase();

  const { data: allProcesses, isLoading: allLoading, isError: allError, refetch } = useProcesses();
  const { data: processes, isLoading, isError } = useProcesses({
    risk_class: activeFilter !== 'ALL' ? activeFilter : undefined,
    sort_by: sort,
  });

  const departments = useMemo(
    () => ['All', ...Array.from(new Set((allProcesses || []).map(p => p.department).filter(Boolean) as string[])).sort()],
    [allProcesses]
  );

  const visibleProcesses = useMemo(() => {
    const rows = (processes || []).filter(p =>
      (department === 'All' || p.department === department) &&
      (!search || `${p.name} ${p.department} ${p.systems.join(' ')}`.toLowerCase().includes(search))
    );
    return [...rows].sort((a, b) =>
      sort === 'value_score'
        ? b.score.value_score - a.score.value_score
        : b.cases_per_month - a.cases_per_month
    );
  }, [processes, department, sort, search]);

  const byRisk = (rc: RiskClass) =>
    allProcesses?.filter((p) => p.score?.risk_decision === rc).length || 0;

  const counts = {
    all: allProcesses?.length || 0,
    safe: byRisk(RiskClass.PRE_APPROVED),
    hitl: byRisk(RiskClass.HUMAN_IN_THE_LOOP),
    risky: byRisk(RiskClass.TOO_RISKY),
  };

  const pct = (n: number) => (counts.all > 0 ? (n / counts.all) * 100 : 0);

  const handleBatchRun = async () => {
    if (!allProcesses?.length || batchRunning) return;
    setBatchRunning(true);
    setBatchMessage('');
    const results = await Promise.allSettled(allProcesses.map(p => api.reevaluate(p.id)));
    const failed = results.filter(r => r.status === 'rejected').length;
    await refetch();
    setBatchMessage(failed ? `Batch completed with ${failed} failure${failed === 1 ? '' : 's'}.` : `Batch run completed — ${results.length} processes re-evaluated.`);
    setBatchRunning(false);
  };

  const handleUploadClick = () => fileInputRef.current?.click();

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    // Reset the input so selecting the same file again still fires onChange.
    e.target.value = '';
    if (!file || uploading) return;

    setUploading(true);
    setIngestError('');
    setIngestResult(null);
    try {
      const res = await api.ingest(file);
      const discovered = res.discovery?.processes ?? [];
      const risk: Record<string, number> = {};
      for (const p of discovered) {
        risk[p.risk_decision] = (risk[p.risk_decision] || 0) + 1;
      }
      setIngestResult({
        message: res.message,
        events: res.events_ingested,
        processes: res.discovery?.processes_created ?? 0,
        risk,
      });
      // Re-fetch the roadmap so the newly discovered processes appear at once.
      await queryClient.invalidateQueries({ queryKey: ['processes'] });
    } catch (err) {
      const detail =
        err instanceof APIError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Upload failed. Please try again.';
      setIngestError(detail);
    } finally {
      setUploading(false);
    }
  };

  const exportCSV = () => {
    const header = ['rank', 'process', 'department', 'cases_per_month', 'viability_score', 'risk'];
    const rows = visibleProcesses.map(p => [
      p.rank, JSON.stringify(p.name), JSON.stringify(p.department || ''),
      p.cases_per_month, p.score.value_score, p.score.risk_decision
    ].join(','));
    downloadFile('kintix-roadmap.csv', [header.join(','), ...rows].join('\n'), 'text/csv;charset=utf-8');
  };

  const exportJSON = () => {
    downloadFile('kintix-roadmap.json', JSON.stringify(visibleProcesses, null, 2), 'application/json');
  };

  const handleInspect = (id: string) => navigate(`/process/${id}`);
  const handleAudit = (id: string) => navigate(`/audit?process_id=${encodeURIComponent(id)}`);

  return (
    <div className="space-y-space-2xl">
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Automation Opportunity Roadmap</h1>
          <p className="text-on-surface-variant">Continuous telemetry evaluated against enterprise risk constraints.</p>{search && <p className="text-xs text-primary mt-2">Search: “{searchParams.get('q')}”</p>}
          {batchMessage && <p className="text-xs text-primary mt-2">{batchMessage}</p>}
        </div>
        <div className="flex space-x-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            onClick={handleUploadClick}
            disabled={uploading}
            className="px-4 py-2 rounded-lg bg-surface-container-high border border-outline-variant/30 text-sm font-medium hover:bg-surface-container-highest transition-colors flex items-center space-x-2 disabled:opacity-60"
          >
            <span className={`material-symbols-outlined text-[18px] ${uploading ? 'animate-spin' : ''}`}>{uploading ? 'sync' : 'upload_file'}</span>
            <span>{uploading ? 'Uploading…' : 'Upload CSV'}</span>
          </button>
          <button
            onClick={() => navigate('/settings')}
            className="px-4 py-2 rounded-lg bg-surface-container-high border border-outline-variant/30 text-sm font-medium hover:bg-surface-container-highest transition-colors flex items-center space-x-2"
          >
            <span className="material-symbols-outlined text-[18px]">tune</span>
            <span>Threshold Matrix</span>
          </button>
          <button
            onClick={handleBatchRun}
            disabled={batchRunning || allLoading || !allProcesses?.length}
            className="px-4 py-2 rounded-lg bg-primary text-on-primary text-sm font-bold hover:bg-primary/90 transition-colors flex items-center space-x-2 shadow-[0_0_15px_rgba(236,194,70,0.3)] disabled:opacity-60"
          >
            <span className={`material-symbols-outlined text-[18px] ${batchRunning ? 'animate-spin' : ''}`}>{batchRunning ? 'sync' : 'play_arrow'}</span>
            <span>{batchRunning ? 'Running Batch…' : 'Initiate Batch Run'}</span>
          </button>
        </div>
      </div>

      {(ingestResult || ingestError) && (
        <div
          className={`rounded-xl border px-4 py-3 flex items-start justify-between text-sm ${
            ingestError
              ? 'bg-rose-950/30 border-error/40 text-rose-300'
              : 'bg-surface-container-low border-status-safe/40 text-on-surface'
          }`}
        >
          <div className="flex items-start space-x-2">
            <span className="material-symbols-outlined text-[18px]">{ingestError ? 'error' : 'check_circle'}</span>
            {ingestError ? (
              <span>Upload failed: {ingestError}</span>
            ) : (
              <div>
                <span className="font-medium">{ingestResult!.message}</span>
                <div className="text-xs text-on-surface-variant mt-1 flex flex-wrap gap-x-4 gap-y-1">
                  <span>{ingestResult!.events} events ingested</span>
                  <span>{ingestResult!.processes} process(es) discovered</span>
                  {Object.entries(ingestResult!.risk).map(([rc, n]) => (
                    <span key={rc}>{RISK_LABELS[rc as RiskClass] ?? rc}: {n}</span>
                  ))}
                </div>
              </div>
            )}
          </div>
          <button
            onClick={() => { setIngestResult(null); setIngestError(''); }}
            className="text-on-surface-variant hover:text-on-surface transition-colors"
            aria-label="Dismiss"
          >
            <span className="material-symbols-outlined text-[18px]">close</span>
          </button>
        </div>
      )}

      <div className="grid grid-cols-4 gap-space-lg">
        <StatCard label="Evaluated Catalog" value={counts.all.toString()} icon="library_books" />
        <StatCard label="Immediate Yield" value="1,420" unit="hrs/mo" icon="savings" trend="+$186K / yr" accentColor="border-status-safe" />
        <StatCard label="Viability Index" value="81.4" unit="/100" icon="speed" />
        <div className="bg-surface-container-low rounded-xl p-space-lg border-t-2 border-outline-variant overflow-hidden">
          <div className="flex justify-between items-start mb-4">
            <span className="text-sm font-medium text-on-surface-variant">Risk Distribution</span>
            <span className="material-symbols-outlined text-xl text-on-surface-variant/50">pie_chart</span>
          </div>
          <div className="flex space-x-4 mb-3">
            <div className="flex flex-col"><span className="text-lg font-mono font-bold text-status-safe">{counts.safe}</span><span className="text-[10px] uppercase text-on-surface-variant">Safe</span></div>
            <div className="flex flex-col"><span className="text-lg font-mono font-bold text-status-hitl">{counts.hitl}</span><span className="text-[10px] uppercase text-on-surface-variant">HITL</span></div>
            <div className="flex flex-col"><span className="text-lg font-mono font-bold text-status-risk">{counts.risky}</span><span className="text-[10px] uppercase text-on-surface-variant">Block</span></div>
          </div>
          <div className="h-1.5 w-full bg-surface-container-high rounded-full overflow-hidden flex">
            <div className="bg-status-safe h-full" style={{ width: `${pct(counts.safe)}%` }} />
            <div className="bg-status-hitl h-full" style={{ width: `${pct(counts.hitl)}%` }} />
            <div className="bg-status-risk h-full" style={{ width: `${pct(counts.risky)}%` }} />
          </div>
        </div>
      </div>

      <div className="flex justify-between items-center">
        <RiskFilterBar activeFilter={activeFilter} onFilterChange={setActiveFilter} counts={counts} />
        <div className="flex space-x-3">
          <select value={department} onChange={e => setDepartment(e.target.value)}
            className="px-3 py-1.5 rounded-lg border border-outline-variant/30 text-sm text-on-surface-variant bg-surface-container-low">
            {departments.map(d => <option key={d} value={d}>Department: {d}</option>)}
          </select>
          <select value={sort} onChange={e => setSort(e.target.value as 'value_score' | 'frequency')}
            className="px-3 py-1.5 rounded-lg border border-outline-variant/30 text-sm text-on-surface-variant bg-surface-container-low">
            <option value="value_score">Viability (Desc)</option>
            <option value="frequency">Frequency (Desc)</option>
          </select>
        </div>
      </div>

      {isLoading || allLoading ? (
        <div className="h-64 flex items-center justify-center bg-surface-container-low rounded-xl border border-outline-variant/30">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
        </div>
      ) : isError || allError ? (
        <div className="h-64 flex items-center justify-center bg-surface-container-low rounded-xl border border-error/30 text-error">Error loading processes.</div>
      ) : (
        <RoadmapTable processes={visibleProcesses} onInspect={handleInspect} onAudit={handleAudit} />
      )}

      <div className="flex justify-between items-center text-sm text-on-surface-variant pt-4 border-t border-outline-variant/20">
        <span>Showing {visibleProcesses.length} of {counts.all} evaluated processes</span>
        <div className="flex space-x-4">
          <button onClick={exportCSV} className="hover:text-primary transition-colors flex items-center space-x-1"><span className="material-symbols-outlined text-[16px]">download</span><span>Export CSV</span></button>
          <button onClick={exportJSON} className="hover:text-primary transition-colors flex items-center space-x-1"><span className="material-symbols-outlined text-[16px]">data_object</span><span>Export JSON</span></button>
        </div>
      </div>
    </div>
  );
}
