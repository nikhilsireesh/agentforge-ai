import { AlertTriangle } from "lucide-react";
import { Route, Routes } from "react-router-dom";
import { Spinner } from "./components/ui";
import { useAuth } from "./context/AuthContext";
import { ExecutionProvider } from "./context/ExecutionContext";
import AppLayout from "./layouts/AppLayout";
import AgentWorkspace from "./pages/AgentWorkspace";
import Analytics from "./pages/Analytics";
import ApprovalCenter from "./pages/ApprovalCenter";
import Architecture from "./pages/Architecture";
import CodeArtifacts from "./pages/CodeArtifacts";
import Documentation from "./pages/Documentation";
import Login from "./pages/Login";
import NewProject from "./pages/NewProject";
import NotFound from "./pages/NotFound";
import Overview from "./pages/Overview";
import ProjectDetail from "./pages/ProjectDetail";
import Projects from "./pages/Projects";
import RequirementAnalysis from "./pages/RequirementAnalysis";
import SettingsPage from "./pages/Settings";
import TestingCenter from "./pages/TestingCenter";
import WorkflowMonitor from "./pages/WorkflowMonitor";

export default function App() {
  const { ready, user, system, backendError } = useAuth();

  if (!ready) return <Spinner label="Connecting to AgentForge…" className="h-full" />;
  if (backendError)
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="max-w-md rounded-2xl border border-red-200 bg-white p-6 text-center shadow-sm">
          <AlertTriangle className="mx-auto text-red-500" />
          <h1 className="mt-2 font-semibold">Backend unavailable</h1>
          <p className="mt-1 text-sm text-slate-500">{backendError}</p>
          <pre className="mt-3 rounded-lg bg-slate-50 p-2 text-left text-xs text-slate-600">cd backend && uvicorn app.main:app --reload</pre>
        </div>
      </div>
    );
  if (system?.auth_enabled && !user) return <Login />;

  return (
    <ExecutionProvider>
      <Routes>
        <Route element={<AppLayout />}>
          <Route index element={<Overview />} />
          <Route path="projects" element={<Projects />} />
          <Route path="projects/new" element={<NewProject />} />
          <Route path="projects/:projectId" element={<ProjectDetail />} />
          <Route path="agents" element={<AgentWorkspace />} />
          <Route path="workflow" element={<WorkflowMonitor />} />
          <Route path="requirements" element={<RequirementAnalysis />} />
          <Route path="architecture" element={<Architecture />} />
          <Route path="code" element={<CodeArtifacts />} />
          <Route path="testing" element={<TestingCenter />} />
          <Route path="approvals" element={<ApprovalCenter />} />
          <Route path="documentation" element={<Documentation />} />
          <Route path="analytics" element={<Analytics />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </ExecutionProvider>
  );
}
