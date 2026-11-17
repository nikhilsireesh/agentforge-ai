import { Bot } from "lucide-react";
import { useState } from "react";
import { Button, ErrorBanner, Field, inputClass } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { errorMessage } from "../services/api";

export default function Login() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await register(form.name, form.email, form.password);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  return (
    <div className="flex min-h-full items-center justify-center bg-gradient-to-br from-violet-50 via-white to-indigo-50 p-6">
      <form onSubmit={submit} className="w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-7 shadow-xl shadow-violet-500/5">
        <div className="mb-6 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-600 text-white"><Bot size={20} /></div>
          <div>
            <h1 className="font-semibold text-slate-900">AgentForge AI</h1>
            <p className="text-xs text-slate-500">{mode === "login" ? "Sign in to continue" : "Create your account"}</p>
          </div>
        </div>
        <div className="space-y-4">
          {mode === "register" && (
            <Field label="Name" required><input className={inputClass} value={form.name} onChange={set("name")} required /></Field>
          )}
          <Field label="Email" required><input type="email" className={inputClass} value={form.email} onChange={set("email")} required /></Field>
          <Field label="Password" required hint={mode === "register" ? "At least 8 characters." : undefined}>
            <input type="password" className={inputClass} value={form.password} onChange={set("password")} required minLength={mode === "register" ? 8 : 1} />
          </Field>
          <ErrorBanner error={error} />
          <Button type="submit" loading={busy} className="w-full">{mode === "login" ? "Sign in" : "Create account"}</Button>
        </div>
        <p className="mt-5 text-center text-sm text-slate-500">
          {mode === "login" ? "No account yet?" : "Already registered?"}{" "}
          <button type="button" className="font-medium text-violet-700 hover:underline cursor-pointer" onClick={() => setMode(mode === "login" ? "register" : "login")}>
            {mode === "login" ? "Create one" : "Sign in"}
          </button>
        </p>
        {mode === "register" && <p className="mt-2 text-center text-xs text-slate-400">The first account becomes the administrator.</p>}
      </form>
    </div>
  );
}
