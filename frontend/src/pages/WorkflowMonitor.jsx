import "@xyflow/react/dist/style.css";
import { Background, Controls, Handle, MarkerType, Position, ReactFlow } from "@xyflow/react";
import { Bot, Download, GitBranch, ScrollText, ShieldCheck, StopCircle, Wrench } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { ExecutionPicker } from "../components/ExecutionPicker";
import { NoExecution } from "../components/NoExecution";
import { Button, Card, CardHeader, ErrorBanner, Modal, PageHeader, Spinner, StatusBadge, cx } from "../components/ui";
import { useSelectedExecution } from "../context/ExecutionContext";
import { useApi } from "../hooks/useApi";
import { useExecutionDetail } from "../hooks/useExecution";
import { Api, errorMessage } from "../services/api";
import { ACTIVE_STATUSES, formatDuration, formatTime, humanize } from "../utils/format";

const POSITIONS = {
  requirement_analyst: [0, 0], approval_requirements: [250, 0], research: [500, 0], solution_architect: [750, 0], approval_architecture: [1000, 0],
  developer: [1000, 170], approval_code: [750, 170], approval_test_execution: [500, 170], review_testing: [250, 170],
  correction: [625, 330], approval_deployment: [0, 170], documentation: [0, 330],
};
const HANDLES = {
  approval_architecture: { source: Position.Bottom },
  developer: { target: Position.Top, source: Position.Left },
  approval_code: { target: Position.Right, source: Position.Left },
  approval_test_execution: { target: Position.Right, source: Position.Left },
  review_testing: { target: Position.Right, source: Position.Left },
  approval_deployment: { target: Position.Right, source: Position.Bottom },
  documentation: { target: Position.Top },
  correction: { target: Position.Left, source: Position.Right },
};
const NODE_COLORS = {
  pending: "border-slate-200 bg-white text-slate-500",
  skipped: "border-slate-200 bg-slate-50 text-slate-400 border-dashed",
  running: "border-blue-400 bg-blue-50 text-blue-800 ring-4 ring-blue-100",
  completed: "border-emerald-300 bg-emerald-50 text-emerald-800",
  failed: "border-red-300 bg-red-50 text-red-800",
  waiting_approval: "border-amber-400 bg-amber-50 text-amber-900 ring-4 ring-amber-100",
};
const STROKE = { completed: "#10b981", running: "#3b82f6", waiting_approval: "#f59e0b", failed: "#ef4444" };

function AgentNode({ data }) {
  const Icon = data.kind === "approval" ? ShieldCheck : data.kind === "control" ? Wrench : Bot;
  const handles = HANDLES[data.id] || {};
  return (
    <div className={cx("w-[190px] rounded-xl border-2 px-3 py-2.5 shadow-sm transition-all", NODE_COLORS[data.status])} data-testid={`node-${data.id}`} data-status={data.status}>
      <Handle type="target" position={handles.target || Position.Left} className="!bg-slate-300 !border-0" />
      <div className="flex items-center gap-2">
        <Icon size={15} className={data.status === "running" ? "animate-pulse" : ""} />
        <span className="text-[13px] font-semibold leading-tight">{data.label}</span>
      </div>
      <div className="mt-1 flex items-center justify-between text-[11px] opacity-80">
        <span className="capitalize">{data.status.replace("_", " ")}</span>
        {data.detail && <span className="capitalize">{data.detail}</span>}
      </div>
      <Handle type="source" position={handles.source || Position.Right} className="!bg-slate-300 !border-0" />
    </div>
  );
}
const nodeTypes = { agent: AgentNode };

function LiveLog({ executionId, active }) {
  const [logs, setLogs] = useState([]);
  const lastId = useRef(0);
  const box = useRef(null);

  useEffect(() => {
    setLogs([]);
    lastId.current = 0;
  }, [executionId]);

  useApi(async () => {
    const fresh = await Api.logs(executionId, lastId.current);
    if (fresh.length) {
      lastId.current = fresh[fresh.length - 1].id;
      // Overlapping polls can return the same entries; keep each log id once.
      setLogs((current) => {
        const seen = new Set(current.map((log) => log.id));
        return [...current, ...fresh.filter((log) => !seen.has(log.id))].slice(-400);
      });
    }
    return fresh;
  }, [executionId], { interval: active ? 1500 : 6000 });

  useEffect(() => {
    if (box.current) box.current.scrollTop = box.current.scrollHeight;
  }, [logs]);

  const tone = { ERROR: "text-red-400", WARNING: "text-amber-300", INFO: "text-slate-300", DEBUG: "text-slate-500" };
  return (
    <div ref={box} className="h-80 overflow-y-auto rounded-xl bg-slate-950 p-3 font-mono text-[11.5px] leading-relaxed" data-testid="live-log">
      {!logs.length && <p className="text-slate-500">Waiting for log entries…</p>}
      {logs.map((log) => (
        <div key={log.id} className="flex gap-2">
          <span className="shrink-0 text-slate-600">{formatTime(log.timestamp)}</span>
          <span className="shrink-0 text-violet-300">{(log.agent_name || "system").padEnd(19).slice(0, 19)}</span>
          <span className={tone[log.log_level]}>{log.message}</span>
        </div>
      ))}
    </div>
  );
}

export default function WorkflowMonitor() {
  const { selectedId, loaded } = useSelectedExecution();
  const detail = useExecutionDetail(selectedId);
  const active = detail.data && ACTIVE_STATUSES.includes(detail.data.status);
  const workflow = useApi(() => Api.workflow(selectedId), [selectedId], { enabled: Boolean(selectedId), interval: active ? 2000 : null });
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [actionError, setActionError] = useState(null);

  useEffect(() => {
    if (detail.data) workflow.reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail.data?.status, detail.data?.current_agent]);

  const { nodes, edges } = useMemo(() => {
    if (!workflow.data) return { nodes: [], edges: [] };
    const status = Object.fromEntries(workflow.data.nodes.map((n) => [n.id, n.status]));
    return {
      nodes: workflow.data.nodes.map((n) => ({
        id: n.id, type: "agent", position: { x: POSITIONS[n.id][0], y: POSITIONS[n.id][1] }, data: { ...n }, draggable: false,
      })),
      edges: workflow.data.edges.map((e) => {
        const color = e.traversed ? STROKE[status[e.target]] || STROKE.completed : "#cbd5e1";
        return {
          id: `${e.source}-${e.target}`, source: e.source, target: e.target, label: e.label || undefined,
          animated: status[e.target] === "running" || status[e.target] === "waiting_approval",
          type: "smoothstep",
          style: { stroke: color, strokeWidth: e.traversed ? 2.2 : 1.4, strokeDasharray: e.source === "correction" || e.target === "correction" ? "6 4" : undefined },
          markerEnd: { type: MarkerType.ArrowClosed, color },
          labelStyle: { fontSize: 10, fill: "#64748b" },
          labelBgStyle: { fill: "#f8fafc" },
        };
      }),
    };
  }, [workflow.data]);

  const cancel = async () => {
    setActionError(null);
    try {
      await Api.cancel(selectedId);
      setConfirmCancel(false);
      detail.reload();
    } catch (err) {
      setActionError(errorMessage(err));
    }
  };

  const ex = detail.data;
  return (
    <div>
      <PageHeader title="Workflow Monitor" description="Live view of the LangGraph orchestration: every agent, approval checkpoint and correction loop."
        actions={<ExecutionPicker detail={ex} />} />
      {!selectedId && loaded ? <NoExecution /> : !ex ? <Spinner /> : (
        <div className="space-y-5">
          <ErrorBanner error={detail.error || workflow.error || actionError} />
          {ex.pending_approval && <ApprovalPanel approval={ex.pending_approval} executionId={ex.id} onDecided={() => { detail.reload(); workflow.reload(); }} />}

          <Card>
            <CardHeader title={`${ex.project_name} · execution #${ex.id}`} icon={GitBranch}
              subtitle={`Current step: ${humanize(ex.current_agent) || "—"} · corrections ${ex.correction_attempts}/2 · duration ${formatDuration(ex.total_duration)}`}
              actions={
                <>
                  {ex.status === "completed" && <Button variant="secondary" size="sm" icon={Download} onClick={() => Api.downloadPackage(ex.id)}>Delivery package</Button>}
                  {ACTIVE_STATUSES.includes(ex.status) && <Button variant="secondary" size="sm" icon={StopCircle} className="text-red-600" onClick={() => setConfirmCancel(true)}>Cancel</Button>}
                </>
              } />
            {ex.error_message && <div className="px-5"><ErrorBanner error={ex.error_message} /></div>}
            <div className="h-[470px] px-2 pb-2" data-testid="workflow-graph">
              {nodes.length ? (
                <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} fitView fitViewOptions={{ padding: 0.12 }} nodesConnectable={false} elementsSelectable={false} proOptions={{ hideAttribution: true }} minZoom={0.3}>
                  <Background color="#e2e8f0" gap={20} />
                  <Controls showInteractive={false} />
                </ReactFlow>
              ) : <Spinner />}
            </div>
            <div className="flex flex-wrap gap-3 border-t border-slate-100 px-5 py-3 text-xs text-slate-500">
              {["pending", "running", "completed", "failed", "waiting_approval", "skipped"].map((s) => <StatusBadge key={s} status={s} />)}
              <span className="ml-auto">Dashed edges = controlled correction loop (max 2)</span>
            </div>
          </Card>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader title="Execution log" icon={ScrollText} subtitle="Streamed from the backend as agents work" />
              <div className="px-5 pb-5"><LiveLog executionId={ex.id} active={active} /></div>
            </Card>
            <Card>
              <CardHeader title="Workflow transitions" icon={GitBranch} subtitle="Orchestrator decisions" />
              <ol className="max-h-80 space-y-2 overflow-y-auto px-5 pb-5">
                {(workflow.data?.transitions || []).map((t) => (
                  <li key={t.id} className="border-l-2 border-violet-200 pl-3">
                    <p className="text-xs text-slate-400">{formatTime(t.timestamp)}</p>
                    <p className="text-sm text-slate-700">{t.message}</p>
                  </li>
                ))}
                {!workflow.data?.transitions?.length && <p className="text-sm text-slate-400">No transitions yet.</p>}
              </ol>
            </Card>
          </div>
        </div>
      )}
      <Modal open={confirmCancel} title="Cancel this execution?" onClose={() => setConfirmCancel(false)}
        footer={<><Button variant="secondary" onClick={() => setConfirmCancel(false)}>Keep running</Button><Button variant="danger" onClick={cancel}>Cancel execution</Button></>}>
        <p className="text-sm text-slate-600">The current agent finishes its step, then the workflow stops. Pending approvals are closed.</p>
      </Modal>
    </div>
  );
}
