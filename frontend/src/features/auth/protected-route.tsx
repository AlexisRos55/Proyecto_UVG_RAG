import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/features/auth/auth-context";

export function ProtectedRoute() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  // Se conserva el destino para devolver al usuario justo donde iba tras
  // autenticarse. Sin esto, cualquier enlace compartido acababa en el chat.
  return isAuthenticated ? (
    <Outlet />
  ) : (
    <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  );
}

export function AdminRoute() {
  const { isAdmin } = useAuth();
  // Un usuario sin permiso no se expulsa en silencio: la pantalla explica por qué.
  return isAdmin ? <Outlet /> : <Navigate to="/sin-permiso" replace />;
}
