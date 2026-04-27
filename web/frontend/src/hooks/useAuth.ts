import { Navigate } from 'react-router-dom';

export function useUnauthorizedRedirect(unauthorized: boolean): React.ReactElement | null {
  if (unauthorized) {
    return <Navigate to="/login" replace />;
  }
  return null;
}
