import { NavLink } from 'react-router-dom';

const navItems = [
  { path: '/', label: 'Roadmap', icon: 'view_kanban' },
  { path: '/process-intelligence', label: 'Process Intelligence', icon: 'account_tree' },
  { path: '/blueprints', label: 'Automation Blueprints', icon: 'architecture' },
  { path: '/audit', label: 'Risk Governance & Audit', icon: 'shield_locked' },
  { path: '/settings', label: 'Settings', icon: 'tune' },
];

export default function Sidebar() {
  return (
    <aside className="fixed top-0 left-0 h-screen w-72 bg-surface-container-low border-r border-outline-variant/30 flex flex-col z-20">
      <div className="p-space-lg flex items-center space-x-3 mt-4">
        <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center border border-primary/20">
          <span className="text-primary font-bold text-xl leading-none">K</span>
        </div>
        <div className="flex flex-col">
          <div className="flex text-xl tracking-wider font-bold">
            <span className="text-white">KINTI</span>
            <span className="text-primary">X</span>
          </div>
          <span className="text-[0.6rem] text-primary tracking-widest uppercase">Intelligent Automation, Human Control</span>
        </div>
      </div>

      <div className="px-space-lg py-space-md border-b border-outline-variant/30 flex justify-between items-center bg-surface-container/50">
        <span className="text-sm font-medium text-on-surface-variant">Enterprise Operations</span>
        <span className="text-xs px-2 py-0.5 bg-surface-container-high rounded text-on-surface-variant">Global</span>
      </div>

      <div className="px-space-lg py-space-md">
        <span className="text-xs text-on-surface-variant/70 uppercase tracking-widest font-semibold">Executive Navigation</span>
      </div>

      <nav className="flex-1 px-space-md space-y-1">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center space-x-3 px-3 py-2 rounded-lg transition-colors ${
                isActive
                  ? 'bg-primary-container text-on-primary-container font-semibold'
                  : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
              }`
            }
          >
            <span className="material-symbols-outlined text-xl">{item.icon}</span>
            <span className="text-sm">{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="p-space-lg border-t border-outline-variant/30 bg-surface-container/20">
        <div className="flex items-center space-x-2 mb-2">
          <div className="w-2 h-2 rounded-full bg-status-safe animate-pulse"></div>
          <span className="text-xs text-on-surface-variant font-mono">API v2.4 Connected</span>
          <span className="text-[10px] bg-status-safe/20 text-status-safe px-1.5 py-0.5 rounded uppercase tracking-wider ml-auto">Live</span>
        </div>
        <div className="text-[10px] text-on-surface-variant/50 font-mono flex justify-between">
          <span>FastAPI Backend Live</span>
          <span>12ms</span>
        </div>
      </div>
    </aside>
  );
}
