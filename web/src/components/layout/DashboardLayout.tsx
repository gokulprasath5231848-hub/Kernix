import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Header from './Header';
import MobileNav from './MobileNav';

export default function DashboardLayout() {
  return (
    <div className="min-h-screen bg-background text-on-surface flex">
      <Sidebar />
      <Header />
      <main className="flex-1 md:pl-72 pt-16 pb-20 md:pb-0 min-h-screen">
        <div className="p-gutter-mobile md:p-margin-page">
          <Outlet />
        </div>
      </main>
      <MobileNav />
    </div>
  );
}
