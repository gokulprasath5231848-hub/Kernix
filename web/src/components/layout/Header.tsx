import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProcesses } from '../../hooks/useProcesses';

export default function Header() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const { data: processes } = useProcesses();
  const evaluatedCount = processes?.length ?? 0;

  const submitSearch = (e: React.FormEvent) => {
    e.preventDefault();
    navigate(`/?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <header className="fixed top-0 left-72 right-0 h-16 bg-surface-container-lowest/90 backdrop-blur border-b border-outline-variant/30 flex items-center justify-between px-space-xl z-10">
      <div className="flex items-center space-x-3">
        <div className="flex items-center space-x-2 bg-surface-container px-3 py-1.5 rounded-lg border border-outline-variant/50">
          <span className="material-symbols-outlined text-sm text-primary">sync</span>
          <span className="text-xs text-on-surface-variant">Nightly Audit: Synced 04:00 AM UTC</span>
          <span className="text-xs text-on-surface font-medium ml-2 border-l border-outline-variant/50 pl-2">{evaluatedCount} Processes Evaluated</span>
        </div>
      </div>
      <div className="flex items-center space-x-6">
        <form onSubmit={submitSearch} className="relative">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant/50 text-xl">search</span>
          <input
            type="text" value={query} onChange={e => setQuery(e.target.value)}
            placeholder="Search processes..." aria-label="Search processes"
            className="bg-surface-container border border-outline-variant/50 rounded-full pl-10 pr-4 py-1.5 text-sm focus:outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/50 text-on-surface placeholder:text-on-surface-variant/50 w-64 transition-all"
          />
        </form>
        <div className="flex items-center space-x-4 border-l border-outline-variant/30 pl-6">
          <button className="relative text-on-surface-variant hover:text-on-surface transition-colors">
            <span className="material-symbols-outlined">notifications</span>
            <span className="absolute top-0 right-0 w-2 h-2 bg-primary rounded-full ring-2 ring-surface-container-lowest"></span>
          </button>
          <div className="flex items-center space-x-3 cursor-pointer hover:bg-surface-container px-2 py-1 rounded-lg transition-colors">
            <div className="text-right">
              <div className="text-sm font-medium text-on-surface">Alastair Sterling</div>
              <div className="text-xs text-primary font-mono tracking-wider">Chief Operations</div>
            </div>
            <div className="w-8 h-8 rounded-full bg-surface-container-high border border-primary/30 flex items-center justify-center text-primary font-semibold">AS</div>
          </div>
        </div>
      </div>
    </header>
  );
}
