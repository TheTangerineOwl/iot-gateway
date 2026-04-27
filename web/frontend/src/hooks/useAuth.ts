import { isAuthenticated } from '../api/client';

export function useAuth() {
  return { authenticated: isAuthenticated() };
}
