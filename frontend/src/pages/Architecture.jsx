import { AlertCircle, Database, ExternalLink, Layers, Monitor, Network, Server } from "lucide-react";
import { useState } from "react";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { ExecutionPicker } from "../components/ExecutionPicker";
import { NoExecution } from "../components/NoExecution";
import { BulletList, Card, CardHeader, EmptyState, ErrorBanner, Notice, PageHeader, Spinner, StatusBadge, Table, Tabs, cx } from "../components/ui";
import { useSelectedExecution } from "../context/ExecutionContext";
import { useExecutionDetail } from "../hooks/useExecution";

const METHOD_COLORS = { GET: "bg-sky-50 text-sky-700", POST: "bg-emerald-50 text-emerald-700", PUT: "bg-amber-50 text-amber-700", PATCH: "bg-amber-50 text-amber-700", DELETE: "bg-red-50 text-red-700" };

function Layer({ title, icon: Icon, items, tone }) {
  return (
    <div className={cx("rounded-2xl border p-4", tone)}>
      <p className="mb-3 flex items-center gap-2 text-sm font-semibold"><Icon size={16} /> {title}</p>
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <span key={item.name} title={item.responsibility || item.description} className="rounded-lg bg-white/80 px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm ring-1 ring-black/5">
            {item.name}
          </span>
        ))}
      </div>
    </div>
  );
}

function Arrow({ label }) {
  return (
    <div className="flex flex-col items-center py-1 text-[11px] text-slate-400">
      <div className="h-4 w-px bg-slate-300" />
      <span>{label}</span>
      <div className="h-4 w-px bg-slate-300" />
      <div className="-mt-1 h-0 w-0 border-x-4 border-t-[6px] border-x-transparent border-t-slate-300" />
    </div>
  );
}

export default function Architecture() {
  const { selectedId, loaded } = useSelectedExecution();
  const detail = useExecutionDetail(selectedId);
  const [tab, setTab] = useState("overview");
  const ex = detail.data;
  const arch = ex?.outputs?.solution_architect;
  const research = ex?.outputs?.research;

  return (
    <div>
      <PageHeader title="Architecture" description="Solution design from the Solution Architect, informed by the Research Agent's recommendations."
        actions={<ExecutionPicker detail={ex} />} />
      {!selectedId && loaded ? <NoExecution /> : !ex ? <Spinner /> : !arch ? (
        <Card><EmptyState icon={Network} title="Architecture not ready yet" description="Approve the requirements checkpoint so research and architecture can run." /></Card>
      ) : (
        <div className="space-y-5">
          <ErrorBanner error={detail.error} />
          {ex.pending_approval?.checkpoint === "architecture" && <ApprovalPanel approval={ex.pending_approval} executionId={ex.id} showLink={false} onDecided={detail.reload} />}
          <Tabs active={tab} onChange={setTab} tabs={[
            { id: "overview", label: "Overview & diagram" },
            { id: "data", label: "Database entities", count: arch.database_entities.length },
            { id: "api", label: "API endpoints", count: arch.api_specifications.length },
            { id: "tech", label: "Technology research" },
            { id: "decisions", label: "Decisions & security" },
          ]} />

          {tab === "overview" && (
            <div className="grid grid-cols-1 gap-5 xl:grid-cols-5">
              <Card className="p-5 xl:col-span-3">
                <h3 className="mb-4 font-semibold">System architecture diagram</h3>
                <Layer title="Frontend (React SPA)" icon={Monitor} items={arch.frontend_components} tone="border-violet-200 bg-violet-50/60 text-violet-800" />
                <Arrow label="HTTPS · REST/JSON" />
                <Layer title="Backend (API service)" icon={Server} items={arch.backend_components} tone="border-sky-200 bg-sky-50/60 text-sky-800" />
                <Arrow label="ORM" />
                <Layer title="Database" icon={Database} items={arch.database_entities} tone="border-emerald-200 bg-emerald-50/60 text-emerald-800" />
              </Card>
              <div className="space-y-5 xl:col-span-2">
                <Card>
                  <CardHeader title="Overview" icon={Layers} />
                  <p className="px-5 pb-5 text-sm leading-relaxed text-slate-700">{arch.architecture_overview}</p>
                </Card>
                <Card>
                  <CardHeader title="Implementation plan" />
                  <ol className="space-y-3 px-5 pb-5">
                    {arch.implementation_plan.map((step) => (
                      <li key={step.step} className="flex gap-3">
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-violet-100 text-xs font-semibold text-violet-700">{step.step}</span>
                        <div>
                          <p className="text-sm font-medium text-slate-800">{step.title}</p>
                          <p className="text-xs text-slate-500">{step.description}</p>
                        </div>
                      </li>
                    ))}
                  </ol>
                </Card>
              </div>
            </div>
          )}

          {tab === "data" && (
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              {arch.database_entities.map((entity) => (
                <Card key={entity.name}>
                  <CardHeader title={entity.name} icon={Database} subtitle={entity.description} />
                  <Table rowKey={(f) => f.name} rows={[{ name: "id", type: "int", required: true, description: "Primary key" }, ...entity.fields]} columns={[
                    { key: "name", label: "Field", className: "font-mono text-xs" },
                    { key: "type", label: "Type", className: "font-mono text-xs text-violet-700" },
                    { key: "required", label: "Required", render: (f) => (f.required ? "Yes" : "No") },
                    { key: "description", label: "Description", className: "text-slate-500" },
                  ]} />
                  {entity.relationships.length > 0 && (
                    <p className="border-t border-slate-100 px-5 py-3 text-xs text-slate-500"><b>Relationships:</b> {entity.relationships.join("; ")}</p>
                  )}
                </Card>
              ))}
            </div>
          )}

          {tab === "api" && (
            <Card>
              <Table rowKey={(a) => a.method + a.path} rows={arch.api_specifications} columns={[
                { key: "method", label: "Method", className: "w-24", render: (a) => <span className={cx("rounded-md px-2 py-0.5 font-mono text-xs font-semibold", METHOD_COLORS[a.method])}>{a.method}</span> },
                { key: "path", label: "Path", className: "font-mono text-xs" },
                { key: "description", label: "Description" },
                { key: "auth", label: "Auth", render: (a) => (a.auth_required ? "Required" : "Public") },
                { key: "roles", label: "Roles", render: (a) => a.roles.join(", ") || "—" },
              ]} />
            </Card>
          )}

          {tab === "tech" && research && (
            <div className="space-y-5">
              <Notice tone="warning" icon={AlertCircle}>{research.verification_note}</Notice>
              <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
                <Card>
                  <CardHeader title="Recommended stack" subtitle={`Complexity estimate: ${research.complexity_estimate}`} />
                  <Table rowKey={(r) => r[0]} rows={Object.entries(research.recommended_stack)} columns={[
                    { key: "layer", label: "Layer", render: (r) => <span className="capitalize">{r[0].replace(/_/g, " ")}</span> },
                    { key: "tech", label: "Technology", render: (r) => <span className="font-medium">{r[1]}</span> },
                  ]} />
                </Card>
                <Card>
                  <CardHeader title="Framework comparison" />
                  <div className="space-y-3 px-5 pb-5">
                    {research.framework_comparison.map((c) => (
                      <div key={c.category} className="rounded-xl border border-slate-100 p-3">
                        <p className="text-xs text-slate-400">{c.category}: {c.options.join(" vs ")}</p>
                        <p className="text-sm font-medium text-slate-800">Recommended: {c.recommended}</p>
                        <p className="text-xs text-slate-500">{c.rationale}</p>
                      </div>
                    ))}
                  </div>
                </Card>
                <Card>
                  <CardHeader title="Technical risks" />
                  <Table rowKey={(r) => r.risk} rows={research.technical_risks} columns={[
                    { key: "risk", label: "Risk" },
                    { key: "impact", label: "Impact", render: (r) => <StatusBadge status={r.impact} /> },
                    { key: "mitigation", label: "Mitigation", className: "text-slate-500" },
                  ]} />
                </Card>
                <Card>
                  <CardHeader title="Libraries, integrations & sources" />
                  <div className="space-y-4 px-5 pb-5">
                    <BulletList items={research.library_recommendations.map((l) => `${l.name} — ${l.purpose}`)} />
                    <BulletList items={research.api_integrations} />
                    <div className="space-y-1.5">
                      {research.sources.map((s) => (
                        <div key={s.title} className="flex items-center justify-between gap-2 text-sm">
                          {s.url ? <a href={s.url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1 text-violet-700 hover:underline">{s.title} <ExternalLink size={12} /></a> : <span>{s.title}</span>}
                          <StatusBadge status={s.verification === "reachable" ? "completed" : "unverified"} label={s.verification} />
                        </div>
                      ))}
                    </div>
                  </div>
                </Card>
              </div>
            </div>
          )}

          {tab === "decisions" && (
            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <Card className="lg:col-span-2">
                <CardHeader title="Architecture decisions" />
                <Table rowKey={(d) => d.decision} rows={arch.architecture_decisions} columns={[
                  { key: "decision", label: "Decision", className: "font-medium" },
                  { key: "rationale", label: "Rationale" },
                  { key: "alternatives", label: "Alternatives", render: (d) => d.alternatives.join(", ") },
                  { key: "trade_offs", label: "Trade-offs", className: "text-slate-500" },
                ]} />
              </Card>
              <Card><CardHeader title="Authentication strategy" /><p className="px-5 pb-5 text-sm text-slate-700">{arch.authentication_strategy}</p></Card>
              <Card><CardHeader title="Security considerations" /><div className="px-5 pb-5"><BulletList items={arch.security_considerations} /></div></Card>
              <Card><CardHeader title="Scalability considerations" /><div className="px-5 pb-5"><BulletList items={arch.scalability_considerations} /></div></Card>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
