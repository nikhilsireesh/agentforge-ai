import { AlertCircle, HelpCircle, ListChecks, Pencil, Save, Target, Users, X } from "lucide-react";
import { useEffect, useState } from "react";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { ExecutionPicker } from "../components/ExecutionPicker";
import { NoExecution } from "../components/NoExecution";
import { BulletList, Button, Card, CardHeader, EmptyState, ErrorBanner, Notice, PageHeader, Spinner, StatusBadge, Table, inputClass } from "../components/ui";
import { useSelectedExecution } from "../context/ExecutionContext";
import { useApi } from "../hooks/useApi";
import { useExecutionDetail } from "../hooks/useExecution";
import { Api, errorMessage } from "../services/api";

const LIST_FIELDS = [
  ["objectives", "Objectives"], ["user_roles", "User roles"], ["assumptions", "Assumptions"],
  ["missing_information", "Missing information"], ["ambiguities", "Ambiguities"], ["contradictions", "Contradictions"],
  ["clarification_questions", "Clarification questions"], ["dependencies", "Dependencies"], ["constraints", "Constraints"],
];

function RequirementTable({ items, editing, onChange }) {
  return (
    <Table rowKey={(r) => r.id} rows={items} columns={[
      { key: "id", label: "ID", className: "w-20 font-mono text-xs" },
      { key: "description", label: "Requirement", render: (r) => editing
        ? <textarea rows={2} className={inputClass} value={r.description} onChange={(e) => onChange(r.id, "description", e.target.value)} />
        : r.description },
      { key: "priority", label: "Priority", className: "w-28", render: (r) => editing
        ? <select className={inputClass} value={r.priority} onChange={(e) => onChange(r.id, "priority", e.target.value)}><option>must</option><option>should</option><option>could</option></select>
        : <span className="capitalize">{r.priority}</span> },
      { key: "source", label: "Source", className: "w-28", render: (r) => <StatusBadge status={r.source === "stated" ? "completed" : r.source === "inferred" ? "running" : "mock"} label={r.source} /> },
    ]} />
  );
}

export default function RequirementAnalysis() {
  const { selectedId, loaded } = useSelectedExecution();
  const detail = useExecutionDetail(selectedId);
  const ex = detail.data;
  const requirements = useApi(() => Api.listRequirements(ex.project_id), [ex?.project_id, ex?.status], { enabled: Boolean(ex) });
  const requirement = requirements.data?.find((r) => r.id === ex?.requirement_id);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!editing) setDraft(requirement?.structured_output || null);
  }, [requirement, editing]);

  const analysis = draft;
  const canEdit = ex?.pending_approval?.checkpoint === "requirements";

  const updateItem = (field) => (id, key, value) =>
    setDraft({ ...draft, [field]: draft[field].map((item) => (item.id === id ? { ...item, [key]: value } : item)) });

  const save = async () => {
    setSaving(true);
    setError(null);
    try {
      const cleaned = { ...draft };
      for (const [field] of LIST_FIELDS) cleaned[field] = (draft[field] || []).map((line) => line.trim()).filter(Boolean);
      await Api.updateRequirement(requirement.id, { structured_output: cleaned });
      setEditing(false);
      requirements.reload();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <PageHeader title="Requirement Analysis" description="Structured output of the Requirement Analyst. Review, edit, then approve before research and design begin."
        actions={<ExecutionPicker detail={ex} />} />
      {!selectedId && loaded ? <NoExecution /> : !ex ? <Spinner /> : !analysis ? (
        <Card><EmptyState icon={ListChecks} title="Analysis not available yet" description="The Requirement Analyst has not finished for this execution." /></Card>
      ) : (
        <div className="space-y-5">
          <ErrorBanner error={error || detail.error} />
          {ex.pending_approval?.checkpoint === "requirements" && (
            <ApprovalPanel approval={ex.pending_approval} executionId={ex.id} showLink={false} onDecided={() => { detail.reload(); requirements.reload(); }} />
          )}
          {ex.llm_mode === "mock" && <Notice tone="warning" icon={AlertCircle}>Produced in mock mode by keyword rules (no LLM). Items marked <b>assumed</b> were not stated by the client.</Notice>}

          <Card>
            <CardHeader title={analysis.project_name} icon={Target} subtitle={`Requirement #${requirement?.id} · ${requirement?.approval_status}`}
              actions={canEdit && (editing ? (
                <>
                  <Button variant="secondary" size="sm" icon={X} onClick={() => setEditing(false)}>Discard</Button>
                  <Button size="sm" icon={Save} loading={saving} onClick={save}>Save edits</Button>
                </>
              ) : <Button variant="secondary" size="sm" icon={Pencil} onClick={() => setEditing(true)}>Edit analysis</Button>)} />
            <div className="px-5 pb-5">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Business problem</p>
              {editing
                ? <textarea rows={3} className={`${inputClass} mt-1`} value={draft.business_problem} onChange={(e) => setDraft({ ...draft, business_problem: e.target.value })} />
                : <p className="mt-1 text-sm text-slate-700">{analysis.business_problem}</p>}
              <p className="mt-4 text-xs font-medium uppercase tracking-wide text-slate-400">Original client requirement</p>
              <p className="mt-1 rounded-xl bg-slate-50 p-3 text-sm italic text-slate-600">{requirement?.raw_requirement}</p>
            </div>
          </Card>

          <Card>
            <CardHeader title={`Functional requirements (${analysis.functional_requirements.length})`} icon={ListChecks} />
            <RequirementTable items={analysis.functional_requirements} editing={editing} onChange={updateItem("functional_requirements")} />
          </Card>
          <Card>
            <CardHeader title={`Non-functional requirements (${analysis.non_functional_requirements.length})`} icon={ListChecks} />
            <RequirementTable items={analysis.non_functional_requirements} editing={editing} onChange={updateItem("non_functional_requirements")} />
          </Card>

          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader title="User stories" icon={Users} />
              <div className="space-y-2 px-5 pb-5">
                {analysis.user_stories.map((s) => (
                  <div key={s.id} className="rounded-xl border border-slate-100 p-3">
                    <p className="text-xs text-slate-400">{s.id} · {s.role} · {s.related_requirements.join(", ")}</p>
                    <p className="text-sm text-slate-700">{s.story}</p>
                  </div>
                ))}
              </div>
            </Card>
            <Card>
              <CardHeader title="Acceptance criteria" icon={ListChecks} />
              <div className="space-y-2 px-5 pb-5">
                {analysis.acceptance_criteria.map((c) => (
                  <div key={c.id} className="rounded-xl border border-slate-100 p-3">
                    <p className="text-xs text-slate-400">{c.id} → {c.requirement_id}</p>
                    <p className="text-sm text-slate-700">{c.criterion}</p>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
            {LIST_FIELDS.map(([field, label]) => (
              <Card key={field}>
                <CardHeader title={label} icon={field.includes("question") || field.includes("missing") ? HelpCircle : Target} />
                <div className="px-5 pb-5">
                  {editing ? (
                    <textarea rows={5} className={inputClass} aria-label={label} value={(draft[field] || []).join("\n")}
                      onChange={(e) => setDraft({ ...draft, [field]: e.target.value.split("\n") })} />
                  ) : <BulletList items={analysis[field]} />}
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
