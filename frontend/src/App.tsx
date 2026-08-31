import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { Layout } from "./components/Layout";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { ProjectList } from "./pages/ProjectList";
import { ProjectDetail } from "./pages/ProjectDetail";
import { CreateProject } from "./pages/CreateProject";
import { Settings } from "./pages/Settings";
import { Notifications } from "./pages/Notifications";
import { ResearchReview } from "./pages/ResearchReview";
import { ScriptEditor } from "./pages/ScriptEditor";
import { CharacterSetup } from "./pages/CharacterSetup";
import { SceneBuilderPage } from "./pages/SceneBuilder";
import { SceneMediaControls } from "./pages/SceneMediaControls";
import { GenerationTasks } from "./pages/GenerationTasks";
import { VideoStatus } from "./pages/VideoStatus";
import { Preview } from "./pages/Preview";
import { Scheduler } from "./pages/Scheduler";
import { PublishingApproval } from "./pages/PublishingApproval";

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-screen"><p>Loading…</p></div>;
  if (user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route
            path="/login"
            element={
              <PublicRoute>
                <Login />
              </PublicRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicRoute>
                <Register />
              </PublicRoute>
            }
          />

          {/* Protected routes */}
          <Route
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<Dashboard />} />
            <Route path="/projects" element={<ProjectList />} />
            <Route path="/projects/new" element={<CreateProject />} />
            <Route path="/projects/:id" element={<ProjectDetail />} />
            <Route path="/projects/:id/research" element={<ResearchReview />} />
            <Route path="/projects/:id/script" element={<ScriptEditor />} />
            <Route path="/projects/:id/characters" element={<CharacterSetup />} />
            <Route path="/projects/:id/scenes" element={<SceneBuilderPage />} />
            <Route path="/projects/:id/scene-media" element={<SceneMediaControls />} />
            <Route path="/projects/:id/tasks" element={<GenerationTasks />} />
            <Route path="/projects/:id/video" element={<VideoStatus />} />
            <Route path="/projects/:id/preview" element={<Preview />} />
            <Route path="/projects/:id/schedule" element={<Scheduler />} />
            <Route path="/projects/:id/approvals" element={<PublishingApproval />} />
            <Route path="/notifications" element={<Notifications />} />
            <Route path="/settings" element={<Settings />} />
          </Route>

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
