import { ArrowLeft, ClipboardList, History, Pencil, Play, Plus, Workflow } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ProjectFormModal } from "../components/ProjectFormModal";
import { Button, Card, CardHeader, ErrorBanner, KeyValue, Spinner, StatusBadge, Table, inputClass } from "../components/ui";
import { useExecutions } from "../context/ExecutionContext";
import { useApi } from "../hooks/useApi";
import { Api, errorMessage } from "../services/api";
import { ACTIVE_STATUSES, formatDate, formatDuration, humanize } from "../utils/format";

export default function ProjectDetail() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const { refresh: refreshExecutions } = useExecutions();
  const [editing, setEditing] = useState(false);
  const [newRequirement, setNewRequirement] = useState("");
  const [busy, setBusy] = useState(null);
  const [actionError, setActionError] = useState(null);

  const project = useApi(() => Api.getProject(projectId), [projectId], { interval: 5000 });
  const requirements = useApi(() => Api.listRequirements(projectId), [projectId]);

  if (project.loading && !project.data) return <Spinner />;
  if (project.error && !project.data) return <ErrorBanner error={project.error} />;
  const p = project.data;
  const active = p.executions.some((e) => ACTIVE_STATUSES.includes(e.status));

  const run = async (requirementId) => {
    setBusy("run");
    setActionError(null);
    try {
      const execution = await Api.execute(p.id, requirementId);
      await refreshExecutions();
      navigate(`/workflow?execution=${execution.id}`);
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const addRequirement = async () => {
    setBusy("req");
    setActionError(null);
    try {
      await Api.addRequirement(p.id, newRequirement);
      setNewRequirement("");
      requirements.reload();
      project.reload();
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <Link to="/projects" className="mb-3 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-violet-700"><ArrowLeft size={14} /> Projects</Link>
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">{p.name}</h1>
            <StatusBadge status={p.status} />
          </div>
          <p className="mt-1 max-w-2xl text-sm text-slate-500">{p.description || "No description"}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" icon={Pencil} onClick={() => setEditing(true)}>Edit</Button>
          <Button icon={Play} loading={busy === "run"} disabled={!p.requirement_count || active} onClick={() => run()}
            title={active ? "An execution is already active" : undefined}>
            Run AI workflow
          </Button>
        </div>
      </div>
      <ErrorBanner error={actionError} className="mb-4" />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-1">
          <CardHeader title="Project details" />
          <div className="px-5 pb-5">
            <KeyValue items={[
              ["Business domain", p.business_domain],
              ["Complexity", humanize(p.complexity) || "—"],
              ["Preferred stack", p.preferred_tech_stack],
              ["Constraints", p.constraints],
              ["Created", formatDate(p.created_at)],
              ["Updated", formatDate(p.updated_at)],
            ]} />
          </div>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader title="Requirements" icon={ClipboardList} subtitle="Natural-language requirements submitted by the client. The latest one is analysed by default." />
          <div className="space-y-3 px-5 pb-5">
            {(requirements.data || []).map((r, index) => (
              <div key={r.id} className="rounded-xl border border-slate-200 p-4">
                <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <span className="font-medium text-slate-700">Requirement #{r.id}</span>
                    {index === 0 && <span className="rounded bg-violet-50 px-1.5 py-0.5 text-violet-700">latest</span>}
                    <StatusBadge status={r.approval_status} />
                    <span>{formatDate(r.created_at)}</span>
                  </div>
                  <Button variant="ghost" size="sm" icon={Play} disabled={active || !!busy} onClick={() => run(r.id)}>Run with this</Button>
                </div>
                <p className="whitespace-pre-wrap text-sm text-slate-700">{r.raw_requirement}</p>
              </div>
            ))}
            <div className="rounded-xl border border-dashed border-slate-300 p-4">
              <textarea rows={3} className={inputClass} placeholder="Add a new or refined requirement (at least 10 characters)…" value={newRequirement} onChange={(e) => setNewRequirement(e.target.value)} aria-label="New requirement" />
              <div className="mt-2 flex justify-end">
                <Button size="sm" icon={Plus} loading={busy === "req"} disabled={newRequirement.trim().length < 10} onClick={addRequirement}>Add requirement</Button>
              </div>
            </div>
          </div>
        </Card>

        <Card className="xl:col-span-3">
          <CardHeader title="Execution history" icon={History} />
          <Table
            rowKey={(e) => e.id}
            empty="No executions yet. Click “Run AI workflow” to start the agents."
            rows={p.executions}
            columns={[
              { key: "id", label: "Execution", render: (e) => <span className="font-medium">#{e.id}</span> },
              { key: "status", label: "Status", render: (e) => <StatusBadge status={e.status} /> },
              { key: "current", label: "Current step", render: (e) => humanize(e.current_agent) || "—" },
              { key: "mode", label: "LLM", render: (e) => <StatusBadge status={e.llm_mode} /> },
              { key: "corr", label: "Corrections", render: (e) => `${e.correction_attempts}/2` },
              { key: "started", label: "Started", render: (e) => formatDate(e.started_at) },
              { key: "dur", label: "Duration", render: (e) => formatDuration(e.total_duration) },
              { key: "open", label: "", className: "text-right", render: (e) => (
                <Link to={`/workflow?execution=${e.id}`}><Button variant="ghost" size="sm" icon={Workflow}>Monitor</Button></Link>
              ) },
            ]}
          />
        </Card>
      </div>

      <ProjectFormModal project={p} open={editing} onClose={() => setEditing(false)} onSaved={() => { setEditing(false); project.reload(); }} />
    </div>
  );
}
