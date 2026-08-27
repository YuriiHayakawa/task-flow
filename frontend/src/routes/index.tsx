import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "@/contexts/AuthContext";
import { AuthenticatedLayout } from "@/layouts/AuthenticatedLayout";
import { PublicLayout } from "@/layouts/PublicLayout";
import { AdminUsersPage } from "@/pages/AdminUsersPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { LoginPage } from "@/pages/LoginPage";
import { NotificationsPage } from "@/pages/NotificationsPage";
import { PersonalTasksPage } from "@/pages/PersonalTasksPage";
import { ProfilePage } from "@/pages/ProfilePage";
import { ProjectDetailPage } from "@/pages/ProjectDetailPage";
import { ProjectsPage } from "@/pages/ProjectsPage";
import { RecurringTasksPage } from "@/pages/RecurringTasksPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { TaskDetailPage } from "@/pages/TaskDetailPage";
import { TaskFormPage } from "@/pages/TaskFormPage";
import { WorkspaceDetailPage } from "@/pages/WorkspaceDetailPage";
import { WorkspaceMembersPage } from "@/pages/WorkspaceMembersPage";
import { WorkspacesPage } from "@/pages/WorkspacesPage";

function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function PublicOnlyRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }
  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}

function AdminRoute({ children }: { children: ReactNode }) {
  const { isSystemAdmin, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }
  if (!isSystemAdmin) {
    return <Navigate to="/dashboard" replace />;
  }
  return <>{children}</>;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route
        element={
          <PublicOnlyRoute>
            <PublicLayout />
          </PublicOnlyRoute>
        }
      >
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      <Route
        element={
          <ProtectedRoute>
            <AuthenticatedLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/workspaces" element={<WorkspacesPage />} />
        <Route path="/workspaces/:workspaceId" element={<WorkspaceDetailPage />} />
        <Route path="/workspaces/:workspaceId/members" element={<WorkspaceMembersPage />} />
        <Route path="/workspaces/:workspaceId/projects" element={<ProjectsPage />} />
        <Route
          path="/workspaces/:workspaceId/projects/:projectId"
          element={<ProjectDetailPage />}
        />
        <Route path="/tasks" element={<PersonalTasksPage />} />
        <Route path="/tasks/recurring" element={<RecurringTasksPage />} />
        <Route path="/tasks/new" element={<TaskFormPage />} />
        <Route path="/tasks/:taskId" element={<TaskDetailPage />} />
        <Route path="/tasks/:taskId/edit" element={<TaskFormPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <AdminUsersPage />
            </AdminRoute>
          }
        />
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
