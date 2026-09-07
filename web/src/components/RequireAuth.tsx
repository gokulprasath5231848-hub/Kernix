import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { isAuthenticated } from '../auth';

/** Route guard: renders child routes only when a valid session exists,
 *  otherwise redirects to the login page. */
export default function RequireAuth() {
  const location = useLocation();
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  return <Outlet />;
}
