import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "@/features/auth/auth-context";

export function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />;
}

export function AdminRoute() {
  const { isAdmin } = useAuth();
  return isAdmin ? <Outlet /> : <Navigate to="/chat" replace />;
}
