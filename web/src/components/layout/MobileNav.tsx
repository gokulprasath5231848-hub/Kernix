import { NavLink } from 'react-router-dom';

// Mobile-only bottom tab bar. Mirrors the Sidebar routes so navigation is
// reachable when the sidebar is hidden below the `md` breakpoint.
const navItems = [
  { path: '/', label: 'Roadmap', icon: 'view_kanban', end: true },
  { path: '/process-intelligence', label: 'Process', icon: 'account_tree', end: false },
  { path: '/blueprints', label: 'Blueprint', icon: 'architecture', end: false },
  { path: '/audit', label: 'Audit', icon: 'shield_locked', end: false },
  { path: '/settings', label: 'Settings', icon: 'tune', end: false },
];

export default function MobileNav() {
  return (
    <nav
      className="md:hidden fixed bottom-0 inset-x-0 z-30 bg-surface-container-lowest/95 backdrop-blur-xl border-t border-outline-variant/30 pb-safe"
      aria-label="Primary"
    >
      <div className="flex justify-around items-stretch h-16">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.end}
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-0.5 flex-1 min-w-0 transition-colors ${
                isActive ? 'text-primary' : 'text-on-surface-variant'
              }`
            }
          >
            <span className="material-symbols-outlined text-[22px]">{item.icon}</span>
            <span className="text-[10px] font-medium tracking-wide">{item.label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
