import { Cpu, Database, KeyRound, RefreshCw, Shield, User } from "lucide-react";
import { Button, Card, CardHeader, KeyValue, Notice, PageHeader, StatusBadge } from "../components/ui";
import { useAuth } from "../context/AuthContext";
import { formatDate } from "../utils/format";

const ENV_SETTINGS = [
  ["LLM_API_KEY", "API key for an OpenAI-compatible provider. Empty = mock mode."],
  ["LLM_BASE_URL / LLM_MODEL", "Provider endpoint and model name."],
  ["LLM_INPUT_COST_PER_1M / LLM_OUTPUT_COST_PER_1M", "Prices used to estimate cost from real token counts."],
  ["AUTH_ENABLED / JWT_SECRET", "Turn on login and role-based access control."],
  ["SANDBOX_MODE", "auto | docker | disabled — where generated tests run."],
  ["MOCK_INJECT_DEFECT", "Mock mode only: inject one defect to demo the correction loop."],
  ["RATE_LIMIT_PER_MINUTE", "Per-client limit for workflow starts and logins."],
];

export default function SettingsPage() {
  const { system, user, refresh } = useAuth();
  return (
    <div>
      <PageHeader title="Settings" description="Runtime configuration reported by the backend. Values are set with environment variables in backend/.env (restart required)."
        actions={<Button variant="secondary" icon={RefreshCw} onClick={refresh}>Refresh</Button>} />
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader title="AI model" icon={Cpu} />
          <div className="px-5 pb-5">
            <KeyValue items={[
              ["Mode", <StatusBadge key="m" status={system?.llm_mode} label={system?.llm_mode === "mock" ? "Mock (no API key)" : "Live LLM"} />],
              ["Model", system?.llm_model],
              ["Input price / 1M tokens", system?.cost_per_1m_input ? `$${system.cost_per_1m_input}` : "Not configured"],
              ["Output price / 1M tokens", system?.cost_per_1m_output ? `$${system.cost_per_1m_output}` : "Not configured"],
              ["Mock defect injection", system?.mock_inject_defect ? "On" : "Off"],
            ]} />
            {system?.llm_mode === "mock" && (
              <Notice tone="warning" className="mt-4">Mock mode: agents use transparent rule-based logic. Outputs are labelled and never presented as real LLM work. Add <code>LLM_API_KEY</code> to run real agents.</Notice>
            )}
          </div>
        </Card>
        <Card>
          <CardHeader title="Platform" icon={Database} />
          <div className="px-5 pb-5">
            <KeyValue items={[
              ["Version", system?.version],
              ["Environment", system?.environment],
              ["Database", <StatusBadge key="d" status={system?.database.status} />],
              ["Test sandbox", <StatusBadge key="s" status={system?.sandbox.status === "ok" ? "ok" : "unavailable"} />],
              ["Sandbox detail", system?.sandbox.detail],
              ["Checked", formatDate(system?.timestamp)],
            ]} />
          </div>
        </Card>
        <Card>
          <CardHeader title="Your account" icon={User} />
          <div className="px-5 pb-5">
            <KeyValue items={[["Name", user?.name], ["Email", user?.email], ["Role", <span key="r" className="capitalize">{user?.role}</span>], ["Authentication", system?.auth_enabled ? "Enabled (JWT)" : "Disabled — demo user"]]} />
          </div>
        </Card>
        <Card>
          <CardHeader title="Security controls" icon={Shield} />
          <ul className="space-y-2 px-5 pb-5 text-sm text-slate-700">
            <li>• Generated code is never executed on the host; tests run only in a Docker sandbox (no network, non-root, read-only, resource limits).</li>
            <li>• Every agent output is validated against a schema; user and agent content is passed to LLMs as untrusted data.</li>
            <li>• Workflows pause at five human approval checkpoints; nothing is deployed automatically.</li>
            <li>• Artifact paths are validated against traversal; downloads are served as attachments.</li>
            <li>• Passwords are salted PBKDF2 hashes; secrets come only from environment variables.</li>
          </ul>
        </Card>
        <Card className="lg:col-span-2">
          <CardHeader title="Environment variables" icon={KeyRound} subtitle="Edit backend/.env, then restart the backend." />
          <div className="divide-y divide-slate-100 px-5 pb-3">
            {ENV_SETTINGS.map(([name, description]) => (
              <div key={name} className="flex flex-col gap-1 py-2.5 sm:flex-row sm:gap-6">
                <code className="w-80 shrink-0 text-xs font-semibold text-violet-700">{name}</code>
                <span className="text-sm text-slate-600">{description}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
