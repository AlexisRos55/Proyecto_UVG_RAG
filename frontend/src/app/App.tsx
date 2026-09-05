import { Navigate, Route, Routes } from "react-router-dom";

import { AdminDocumentsPage } from "@/features/admin/AdminDocumentsPage";
import { AdminRoute, ProtectedRoute } from "@/features/auth/protected-route";
import { LoginPage } from "@/features/auth/LoginPage";
import { RegisterPage } from "@/features/auth/RegisterPage";
import { ChatPage } from "@/features/chat/ChatPage";

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route path="/chat" element={<ChatPage />} />

        <Route element={<AdminRoute />}>
          <Route path="/admin" element={<AdminDocumentsPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/chat" replace />} />
    </Routes>
  );
}
