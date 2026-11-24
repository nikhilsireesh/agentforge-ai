import { Bot, Eye, EyeOff, Lock, Mail, PlayCircle, User } from "lucide-react";
import { useState } from "react";
import { Button, ErrorBanner } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { errorMessage } from "../services/api";

const fieldBase =
  "w-full rounded-lg border border-slate-200 bg-white py-2.5 pl-10 pr-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-violet-400 focus:outline-none focus:ring-4 focus:ring-violet-100 transition";

function IconInput({ icon: Icon, label, children }) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-sm font-medium text-slate-700">{label}</span>
      <span className="relative block">
        <Icon size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
        {children}
      </span>
    </label>
  );
}

export default function Login() {
  const { login, register, demoLogin, system } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(null); // "form" | "demo" | null

  const isLogin = mode === "login";
  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  const run = async (kind, action) => {
    setBusy(kind);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const submit = (event) => {
    event.preventDefault();
    run("form", () => (isLogin ? login(form.email, form.password) : register(form.name, form.email, form.password)));
  };

  const switchMode = (next) => {
    setMode(next);
    setError(null);
  };

  return (
    <div className="flex min-h-full bg-white">
      {/* Brand panel (hidden on small screens) */}
      <aside className="relative hidden w-[46%] items-center justify-center overflow-hidden bg-gradient-to-br from-violet-700 via-violet-600 to-indigo-700 p-12 text-white lg:flex">
        <div aria-hidden className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-white/10 blur-2xl" />
        <div aria-hidden className="pointer-events-none absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-indigo-400/20 blur-3xl" />
        <div className="relative flex items-center gap-4">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/15 ring-1 ring-white/25"><Bot size={32} /></div>
          <p className="text-4xl font-semibold tracking-tight">AgentForge AI</p>
        </div>
      </aside>

      {/* Sign-in form */}
      <main className="flex flex-1 items-center justify-center bg-gradient-to-br from-slate-50 via-white to-violet-50/60 px-4 py-10 sm:px-8">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600 text-white"><Bot size={20} /></div>
            <p className="text-lg font-semibold text-slate-900">AgentForge AI</p>
          </div>

          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">{isLogin ? "Welcome back" : "Create your account"}</h1>
          <p className="mt-1 text-sm text-slate-500">{isLogin ? "Sign in to continue to your workspace." : "Start delivering software with your AI team."}</p>

          <div role="tablist" aria-label="Sign in or create account" className="mt-6 grid grid-cols-2 rounded-lg bg-slate-100 p-1 text-sm">
            {[["login", "Sign in"], ["register", "Create account"]].map(([key, label]) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={mode === key}
                onClick={() => switchMode(key)}
                className={`cursor-pointer rounded-md py-1.5 font-medium transition ${mode === key ? "bg-white text-slate-900 shadow-sm" : "text-slate-500 hover:text-slate-700"}`}
              >
                {label}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="mt-6 space-y-4">
            {!isLogin && (
              <IconInput icon={User} label="Full name">
                <input className={fieldBase} value={form.name} onChange={set("name")} autoComplete="name" placeholder="Jane Doe" required />
              </IconInput>
            )}
            <IconInput icon={Mail} label="Email">
              <input type="email" className={fieldBase} value={form.email} onChange={set("email")} autoComplete="email" placeholder="you@company.com" required />
            </IconInput>
            <div>
              <IconInput icon={Lock} label="Password">
                <input
                  type={showPassword ? "text" : "password"}
                  className={`${fieldBase} pr-10`}
                  value={form.password}
                  onChange={set("password")}
                  autoComplete={isLogin ? "current-password" : "new-password"}
                  placeholder={isLogin ? "Your password" : "At least 8 characters"}
                  minLength={isLogin ? 1 : 8}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 cursor-pointer rounded-md p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </IconInput>
              {!isLogin && <p className="mt-1.5 text-xs text-slate-500">Use at least 8 characters.</p>}
            </div>

            <ErrorBanner error={error} />

            <Button type="submit" size="lg" loading={busy === "form"} disabled={busy !== null} className="w-full">
              {isLogin ? "Sign in" : "Create account"}
            </Button>
          </form>

          {system?.demo_login_enabled && (
            <>
              <div className="my-6 flex items-center gap-3 text-xs text-slate-400">
                <span className="h-px flex-1 bg-slate-200" /> or <span className="h-px flex-1 bg-slate-200" />
              </div>
              <Button
                variant="secondary"
                size="lg"
                icon={PlayCircle}
                loading={busy === "demo"}
                disabled={busy !== null}
                onClick={() => run("demo", demoLogin)}
                className="w-full"
              >
                Try the demo, no sign-up
              </Button>
              <p className="mt-2 text-center text-xs text-slate-500">Signs you in as a shared guest reviewer who can run and approve workflows.</p>
            </>
          )}

          {!isLogin && <p className="mt-6 text-center text-xs text-slate-400">The first account created becomes the administrator.</p>}
        </div>
      </main>
    </div>
  );
}
