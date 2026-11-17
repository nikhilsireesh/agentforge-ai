import {
  BarChart3,
  Bot,
  ClipboardCheck,
  ClipboardList,
  Code2,
  FileText,
  FlaskConical,
  FolderKanban,
  LayoutDashboard,
  LogOut,
  Menu,
  Network,
  PlusCircle,
  Settings,
  Workflow,
  X,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { cx, StatusBadge } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { Api } from "../services/api";

const NAV = [
  {
    section: "Workspace",
    items: [
      { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
      { to: "/projects", label: "Projects", icon: FolderKanban, end: true },
      { to: "/projects/new", label: "New Project", icon: PlusCircle },
    ],
  },
  {
    section: "Delivery",
    items: [
      { to: "/agents", label: "Agent Workspace", icon: Bot },
      { to: "/workflow", label: "Workflow Monitor", icon: Workflow },
      { to: "/requirements", label: "Requirements", icon: ClipboardList },
      { to: "/architecture", label: "Architecture", icon: Network },
      { to: "/code", label: "Code Artifacts", icon: Code2 },
      { to: "/testing", label: "Testing Center", icon: FlaskConical },
      { to: "/approvals", label: "Approval Center", icon: ClipboardCheck, badge: true },
      { to: "/documentation", label: "Documentation", icon: FileText },
    ],
  },
  {
    section: "Insights",
    items: [
      { to: "/analytics", label: "Analytics", icon: BarChart3 },
      { to: "/settings", label: "Settings", icon: Settings },
    ],
  },
];

function Sidebar({ pending, onNavigate }) {
  const { pathname, search } = useLocation();
  const executionParam = new URLSearchParams(search).get("execution");
  const keepExecution = ["/agents", "/workflow", "/requirements", "/architecture", "/code", "/testing", "/documentation"];
  return (
    <nav className="flex h-full flex-col gap-6 overflow-y-auto px-3 py-5" aria-label="Main navigation">
      <div className="flex items-center gap-2.5 px-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-violet-600 to-indigo-600 text-white shadow-md shadow-violet-500/30">
          <Bot size={19} />
        </div>
        <div>
          <p className="font-semibold leading-tight text-slate-900">AgentForge AI</p>
          <p className="text-[11px] leading-tight text-slate-500">Multi-agent delivery</p>
        </div>
      </div>
      {NAV.map((group) => (
        <div key={group.section}>
          <p className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{group.section}</p>
          <div className="space-y-0.5">
            {group.items.map((item) => {
              const carry = executionParam && keepExecution.includes(item.to) && keepExecution.includes(pathname);
              return (
                <NavLink
                  key={item.to}
                  to={carry ? `${item.to}?execution=${executionParam}` : item.to}
                  end={item.end}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cx(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                      isActive ? "bg-violet-50 text-violet-700" : "text-slate-600 hover:bg-slate-100 hover:text-slate-900",
                    )
                  }
                >
                  <item.icon size={17} />
                  <span className="flex-1">{item.label}</span>
                  {item.badge && pending > 0 && (
                    <span className="rounded-full bg-amber-500 px-1.5 py-0.5 text-[10px] font-semibold text-white" aria-label={`${pending} pending approvals`}>
                      {pending}
                    </span>
                  )}
                </NavLink>
              );
            })}
          </div>
        </div>
      ))}
    </nav>
  );
}

export default function AppLayout() {
  const { system, user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { data: pendingPage } = useApi(() => Api.approvals({ decision: "pending", page_size: 1 }), [], { interval: 5000 });
  const pending = pendingPage?.total || 0;

  return (
    <div className="flex h-full">
      <aside className="hidden w-64 shrink-0 border-r border-slate-200/80 bg-white lg:block">
        <Sidebar pending={pending} />
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-slate-900/30" onClick={() => setMobileOpen(false)} />
          <aside className="absolute inset-y-0 left-0 w-64 bg-white shadow-xl">
            <button className="absolute right-3 top-4 p-1 text-slate-500" onClick={() => setMobileOpen(false)} aria-label="Close menu">
              <X size={18} />
            </button>
            <Sidebar pending={pending} onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-slate-200/80 bg-white/85 px-4 backdrop-blur sm:px-6">
          <button className="rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <Menu size={20} />
          </button>
          <div className="hidden text-sm text-slate-500 sm:block">From business requirements to working software, powered by AI agents.</div>
          <div className="flex items-center gap-2">
            {system && (
              <>
                <StatusBadge status={system.llm_mode} label={system.llm_mode === "mock" ? "Mock LLM mode" : `Live · ${system.llm_model}`} />
                <StatusBadge status={system.sandbox.status === "ok" ? "ok" : "unavailable"} label={system.sandbox.status === "ok" ? "Sandbox ready" : "Sandbox off"} className="hidden md:inline-flex" />
              </>
            )}
            {user && (
              <div className="ml-2 flex items-center gap-2 border-l border-slate-200 pl-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-violet-100 text-sm font-semibold text-violet-700">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                <div className="hidden leading-tight md:block">
                  <p className="text-sm font-medium text-slate-800">{user.name}</p>
                  <p className="text-[11px] capitalize text-slate-500">{user.role}</p>
                </div>
                {system?.auth_enabled && (
                  <button onClick={logout} className="ml-1 rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700" aria-label="Sign out">
                    <LogOut size={16} />
                  </button>
                )}
              </div>
            )}
          </div>
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:px-8">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
