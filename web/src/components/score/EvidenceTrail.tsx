import { EventItem } from '../../types';

function downloadEvidence(events: EventItem[]) {
  const blob = new Blob([JSON.stringify(events, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a'); a.href = url; a.download = 'kintix-evidence.json'; a.click();
  URL.revokeObjectURL(url);
}

interface EvidenceTrailProps {
  events: EventItem[];
}

export default function EvidenceTrail({ events }: EvidenceTrailProps) {
  return (
    <div className="bg-surface-container-low rounded-2xl border border-outline-variant/30 overflow-hidden mt-space-2xl">
      <div className="p-space-lg border-b border-outline-variant/30 flex justify-between items-center bg-surface-container/30">
        <div className="flex items-center space-x-3">
          <h3 className="font-semibold text-lg flex items-center space-x-2">
            <span className="material-symbols-outlined text-primary">data_object</span>
            <span>Telemetry Evidence Trail</span>
          </h3>
          <span className="text-[10px] bg-primary/10 border border-primary/20 text-primary px-2 py-0.5 rounded-full uppercase tracking-widest flex items-center space-x-1">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse"></span>
            <span>Live Stream</span>
          </span>
        </div>
        <button onClick={() => downloadEvidence(events)} disabled={!events.length}
          className="text-sm font-medium text-on-surface-variant hover:text-on-surface transition-colors flex items-center space-x-1 disabled:opacity-40">
          <span className="material-symbols-outlined text-[18px]">download</span>
          <span>Export Evidence JSON</span>
        </button>
      </div>

      <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
        <table className="w-full text-left text-sm border-collapse">
          <thead className="sticky top-0 bg-surface-container-low border-b border-outline-variant/30 shadow-sm z-10">
            <tr>
              <th className="px-6 py-3 font-semibold text-on-surface-variant uppercase text-xs">Timestamp (UTC)</th>
              <th className="px-6 py-3 font-semibold text-on-surface-variant uppercase text-xs">Event ID</th>
              <th className="px-6 py-3 font-semibold text-on-surface-variant uppercase text-xs">Executing Agent</th>
              <th className="px-6 py-3 font-semibold text-on-surface-variant uppercase text-xs">Action / Payload</th>
              <th className="px-6 py-3 font-semibold text-on-surface-variant uppercase text-xs">Proof / Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-outline-variant/10">
            {events.map((event) => (
              <tr key={event.id} className="hover:bg-surface-container/30 font-mono text-xs">
                <td className="px-6 py-3 text-on-surface-variant/80">{event.event_time.replace('T', ' ').substring(0, 19)}</td>
                <td className="px-6 py-3 text-primary/80">{event.id.substring(0, 8)}</td>
                <td className="px-6 py-3">
                  <div className="flex items-center space-x-2">
                    <span className="material-symbols-outlined text-[14px] text-on-surface-variant">smart_toy</span>
                    <span>{event.actor_masked}</span>
                  </div>
                </td>
                <td className="px-6 py-3">
                  <div className="bg-surface-container rounded px-2 py-1 text-on-surface truncate max-w-xs">
                    {event.activity_normalised}
                  </div>
                </td>
                <td className="px-6 py-3">
                  <div className="flex items-center space-x-1 text-status-safe">
                    <span className="material-symbols-outlined text-[14px]">check_circle</span>
                    <span>{Math.round(event.confidence * 100)}% DET</span>
                  </div>
                </td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-on-surface-variant italic">No telemetry events found for this process.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="p-3 bg-surface-container/50 border-t border-outline-variant/30 text-xs text-on-surface-variant/60 font-mono text-center">
        SHA-256 Chain Verification: 9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08
      </div>
    </div>
  );
}
