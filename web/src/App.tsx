import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import DashboardLayout from './components/layout/DashboardLayout';
import RequireAuth from './components/RequireAuth';
import LoginPage from './pages/LoginPage';
import RoadmapPage from './pages/RoadmapPage';
import ProcessDetailPage from './pages/ProcessDetailPage';
import BlueprintPage from './pages/BlueprintPage';
import SettingsPage from './pages/SettingsPage';
import AuditPage from './pages/AuditPage';
import BlueprintsPage from './pages/BlueprintsPage';
import ProcessIntelligencePage from './pages/ProcessIntelligencePage';

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    element: <RequireAuth />,
    children: [
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
        element: <ProcessIntelligencePage />,
      },
      {
        path: 'blueprints',
        element: <BlueprintsPage />,
      },
      {
        path: '*',
        element: <Navigate to="/" replace />,
      }
    ],
      },
    ],
  },
]);

function App() {
  return <RouterProvider router={router} />;
}

export default App;
