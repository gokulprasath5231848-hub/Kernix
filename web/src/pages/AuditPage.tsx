import { useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuditLog } from '../hooks/useProcesses';

function downloadCSV(logs: any[]) {
  const esc = (v: unknown) => JSON.stringify(v ?? '');
  const header = ['timestamp_utc', 'process_id', 'action', 'actor', 'detail'];
  const rows = logs.map(log => [
    esc(new Date(log.timestamp).toISOString()), esc(log.process_id),
    esc(log.action), esc(log.actor), esc(log.detail)
  ].join(','));
  const blob = new Blob([[header.join(','), ...rows].join('\n')], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'kintix-audit-log.csv'; a.click();
  URL.revokeObjectURL(url);
}

export default function AuditPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialProcessId = searchParams.get('process_id') || '';
  const [processId, setProcessId] = useState(initialProcessId);
  const { data: logs, isLoading, isError } = useAuditLog(processId ? { process_id: processId } : undefined);
  const displayLogs = useMemo(() => logs || [], [logs]);

  const handleFilter = (value: string) => {
    setProcessId(value);
    if (value) setSearchParams({ process_id: value });
    else setSearchParams({});
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col gap-4 md:flex-row md:justify-between md:items-end">
        <div>
          <h1 className="text-2xl font-bold mb-2">Risk Governance & Audit Log</h1>
          <p className="text-on-surface-variant text-sm">Immutable ledger of platform actions and risk decisions.</p>
          {processId && <p className="text-xs text-primary mt-2 break-all">Filtered to process {processId}</p>}
        </div>
        <div className="flex items-center gap-2 md:space-x-4">
          <input
            type="text"
            placeholder="Filter by Process ID..."
            value={processId}
            onChange={(e) => handleFilter(e.target.value)}
            className="flex-1 md:flex-none bg-surface-container border border-outline-variant/30 rounded-lg px-4 py-2 text-sm focus:outline-none focus:border-primary md:w-64"
          />
          <button onClick={() => downloadCSV(displayLogs)} disabled={!displayLogs.length}
            className="px-4 py-2 bg-surface-container-high rounded-lg text-sm hover:bg-surface-container-highest transition-colors flex items-center space-x-2 border border-outline-variant/30 disabled:opacity-40 flex-none">
            <span className="material-symbols-outlined text-[18px]">download</span>
            <span className="hidden sm:inline">Export CSV</span>
          </button>
        </div>
      </div>

      {/* Ledger table (desktop) */}
      <div className="hidden md:block bg-surface-container-low rounded-xl border border-outline-variant/30 overflow-x-auto">
        {isLoading ? (
          <div className="p-12 flex justify-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>
        ) : isError ? (
          <div className="p-12 text-center text-error">Failed to load audit logs.</div>
        ) : (
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-surface-container/50 border-b border-outline-variant/30">
              <tr>
                <th className="px-6 py-4 font-semibold text-on-surface-variant uppercase text-xs">Timestamp (UTC)</th>
                <th className="px-6 py-4 font-semibold text-on-surface-variant uppercase text-xs">Process ID</th>
                <th className="px-6 py-4 font-semibold text-on-surface-variant uppercase text-xs">Action</th>
                <th className="px-6 py-4 font-semibold text-on-surface-variant uppercase text-xs">Actor</th>
                <th className="px-6 py-4 font-semibold text-on-surface-variant uppercase text-xs">Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/20 font-mono text-xs">
              {displayLogs.map(log => (
                <tr key={log.id} className="hover:bg-surface-container/30">
                  <td className="px-6 py-4 text-on-surface-variant">{new Date(log.timestamp).toISOString().replace('T', ' ').substring(0, 19)}</td>
                  <td className="px-6 py-4 text-primary truncate max-w-[180px]">{log.process_id || '—'}</td>
                  <td className="px-6 py-4"><span className="bg-surface-container px-2 py-1 rounded text-on-surface border border-outline-variant/20">{log.action}</span></td>
                  <td className="px-6 py-4 text-on-surface-variant">{log.actor}</td>
                  <td className="px-6 py-4 truncate max-w-[300px]">{log.detail || '—'}</td>
                </tr>
              ))}
              {!displayLogs.length && (
                <tr><td colSpan={5} className="px-6 py-8 text-center text-on-surface-variant italic font-sans text-sm">No audit logs found.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Ledger cards (mobile) */}
      <div className="md:hidden flex flex-col gap-space-sm">
        {isLoading ? (
          <div className="p-12 flex justify-center bg-surface-container-low rounded-xl border border-outline-variant/30"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /></div>
        ) : isError ? (
          <div className="p-12 text-center text-error bg-surface-container-low rounded-xl border border-outline-variant/30">Failed to load audit logs.</div>
        ) : !displayLogs.length ? (
          <div className="p-8 text-center text-on-surface-variant italic text-sm bg-surface-container-low rounded-xl border border-outline-variant/30">No audit logs found.</div>
        ) : (
          displayLogs.map(log => (
            <div key={log.id} className="bg-surface-container-low rounded-xl border border-outline-variant/30 p-space-md flex flex-col gap-space-xs">
              <div className="flex items-center justify-between gap-space-sm">
                <span className="inline-flex items-center px-2 py-1 rounded bg-surface-container text-on-surface border border-outline-variant/20 text-[10px] font-mono uppercase tracking-wider">{log.action}</span>
                <span className="text-[11px] font-mono text-on-surface-variant">{new Date(log.timestamp).toISOString().replace('T', ' ').substring(0, 19)}</span>
              </div>
              {log.detail && <p className="text-xs text-on-surface leading-relaxed">{log.detail}</p>}
              <div className="flex items-center justify-between gap-space-sm pt-space-xxs border-t border-outline-variant/20 text-[11px] font-mono text-on-surface-variant">
                <span className="truncate">actor: {log.actor}</span>
                {log.process_id && <span className="text-primary/70 truncate max-w-[45%]">{log.process_id.slice(0, 8)}…</span>}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
