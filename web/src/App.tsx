import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import DashboardLayout from './components/layout/DashboardLayout';
import RoadmapPage from './pages/RoadmapPage';
import ProcessDetailPage from './pages/ProcessDetailPage';
import BlueprintPage from './pages/BlueprintPage';
import SettingsPage from './pages/SettingsPage';
import AuditPage from './pages/AuditPage';

const router = createBrowserRouter([
  {
    path: '/',
    element: <DashboardLayout />,
    children: [
      {
        index: true,
        element: <RoadmapPage />,
      },
      {
        path: 'process/:id',
        element: <ProcessDetailPage />,
      },
      {
        path: 'process/:id/blueprint',
        element: <BlueprintPage />,
      },
      {
        path: 'settings',
        element: <SettingsPage />,
      },
      {
        path: 'audit',
        element: <AuditPage />,
      },
      {
        path: 'process-intelligence',
        element: <div className="p-8">Process Intelligence Coming Soon</div>,
      },
      {
        path: 'blueprints',
        element: <div className="p-8">All Blueprints Coming Soon</div>,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      }
    ],
  },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
