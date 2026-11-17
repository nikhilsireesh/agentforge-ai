import { CheckCheck, ClipboardCheck } from "lucide-react";
import { useState } from "react";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { Card, EmptyState, ErrorBanner, PageHeader, Spinner, StatusBadge, Table, Tabs } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { Api } from "../services/api";
import { CHECKPOINT_LABELS, formatDate } from "../utils/format";

export default function ApprovalCenter() {
  const [tab, setTab] = useState("pending");
  const pending = useApi(() => Api.approvals({ decision: "pending", page_size: 50 }), [], { interval: 3000 });
  const history = useApi(() => Api.approvals({ page_size: 100 }), [tab], { interval: tab === "history" ? 5000 : null });

  const decided = (history.data?.items || []).filter((a) => a.decision !== "pending");
  return (
    <div>
      <PageHeader title="Approval Center" description="Human-in-the-loop checkpoints. Workflows stay paused until a reviewer approves, requests a revision, or rejects." />
      <Tabs active={tab} onChange={setTab} tabs={[
        { id: "pending", label: "Pending", count: pending.data?.total ?? 0 },
        { id: "history", label: "Approval history", count: decided.length || undefined },
      ]} />
      <ErrorBanner error={pending.error || history.error} className="mb-4" />

      {tab === "pending" && (
        pending.loading && !pending.data ? <Spinner /> : !pending.data?.items.length ? (
          <Card><EmptyState icon={CheckCheck} title="No pending approvals" description="When an agent reaches a checkpoint, the request will appear here." /></Card>
        ) : (
          <div className="space-y-4">
            {pending.data.items.map((approval) => (
              <ApprovalPanel key={approval.id} approval={approval} executionId={approval.execution_id} onDecided={() => { pending.reload(); history.reload(); }} />
            ))}
          </div>
        )
      )}

      {tab === "history" && (
        <Card>
          {history.loading && !history.data ? <Spinner /> : (
            <Table rowKey={(a) => a.id} rows={decided} empty="No decisions recorded yet." columns={[
              { key: "project", label: "Project", render: (a) => <><p className="font-medium text-slate-800">{a.project_name}</p><p className="text-xs text-slate-400">Execution #{a.execution_id}</p></> },
              { key: "checkpoint", label: "Checkpoint", render: (a) => CHECKPOINT_LABELS[a.checkpoint] },
              { key: "decision", label: "Decision", render: (a) => <StatusBadge status={a.decision} /> },
              { key: "reviewer", label: "Reviewer", render: (a) => a.reviewer_name || "—" },
              { key: "feedback", label: "Feedback", className: "max-w-xs text-slate-500", render: (a) => a.feedback || "—" },
              { key: "requested", label: "Requested", render: (a) => formatDate(a.created_at) },
              { key: "decided", label: "Decided", render: (a) => formatDate(a.decided_at) },
            ]} />
          )}
        </Card>
      )}
      <p className="mt-4 flex items-center gap-1.5 text-xs text-slate-400"><ClipboardCheck size={13} /> Every decision is stored with reviewer identity and timestamp and included in the final delivery report.</p>
    </div>
  );
}
