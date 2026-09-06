import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';

export default function DashboardLayout() {
  return (
    <div className="min-h-screen bg-background text-on-surface flex">
      <Sidebar />
      <Header />
      <main className="flex-1 pl-72 pt-16 min-h-screen">
        <div className="p-margin-page">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
