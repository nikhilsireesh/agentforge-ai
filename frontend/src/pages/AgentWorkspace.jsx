import { AlertTriangle, Bot, ChevronDown, Clock, Coins, FileInput, FileOutput, RotateCw } from "lucide-react";
import { useState } from "react";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { ExecutionPicker } from "../components/ExecutionPicker";
import { NoExecution } from "../components/NoExecution";
import { Card, ErrorBanner, PageHeader, Spinner, StatusBadge, cx } from "../components/ui";
import { useSelectedExecution } from "../context/ExecutionContext";
import { useApi } from "../hooks/useApi";
import { useExecutionDetail } from "../hooks/useExecution";
import { Api } from "../services/api";
import { ACTIVE_STATUSES, formatDuration, formatNumber, formatTime, humanize, summarizeOutput } from "../utils/format";

function SummaryList({ entries }) {
  if (!entries.length) return <p className="text-xs text-slate-400">—</p>;
  return (
    <dl className="space-y-1">
      {entries.map(({ key, text }) => (
        <div key={key} className="flex justify-between gap-3 text-xs">
          <dt className="text-slate-500">{key}</dt>
          <dd className="text-right font-medium text-slate-700 truncate max-w-[60%]">{text}</dd>
        </div>
      ))}
    </dl>
  );
}

function AgentCard({ agent, runs, execution }) {
  const [open, setOpen] = useState(false);
  const latest = runs[runs.length - 1];
  const status = latest?.status || (execution && !ACTIVE_STATUSES.includes(execution.status) ? "skipped" : "pending");
  const isCurrent = execution?.current_agent === agent.name;
  const tokens = runs.reduce((sum, r) => sum + r.token_usage, 0);

  return (
    <Card className={cx("flex flex-col p-5 transition", isCurrent && "ring-2 ring-blue-300")} data-testid={`agent-card-${agent.name}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className={cx("rounded-xl p-2.5", status === "completed" ? "bg-emerald-50 text-emerald-600" : status === "running" ? "bg-blue-50 text-blue-600" : status === "failed" ? "bg-red-50 text-red-600" : "bg-slate-100 text-slate-500")}>
            <Bot size={18} className={status === "running" ? "animate-pulse" : ""} />
          </div>
          <div>
            <h3 className="font-semibold text-slate-900">{agent.display_name}</h3>
            <p className="mt-0.5 text-xs text-slate-500 leading-relaxed">{agent.description}</p>
          </div>
        </div>
        <StatusBadge status={status} />
      </div>

      <div className="mt-4 rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-600">
        <span className="font-medium text-slate-700">Current task: </span>
        {status === "running" ? "Working on its step now…" : status === "completed" ? "Step completed; output handed to the orchestrator." : status === "failed" ? "Failed — see error below." : "Waiting for upstream steps."}
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
        <div className="flex items-center gap-1.5 text-slate-500"><Clock size={13} /> Start <b className="ml-auto text-slate-700">{formatTime(latest?.started_at)}</b></div>
        <div className="flex items-center gap-1.5 text-slate-500"><Clock size={13} /> End <b className="ml-auto text-slate-700">{formatTime(latest?.completed_at)}</b></div>
        <div className="flex items-center gap-1.5 text-slate-500"><RotateCw size={13} /> Runs / attempts <b className="ml-auto text-slate-700">{runs.length} / {latest?.attempt ?? "—"}</b></div>
        <div className="flex items-center gap-1.5 text-slate-500"><Coins size={13} /> Tokens <b className="ml-auto text-slate-700">{latest ? (latest.is_mock ? "0 (mock)" : formatNumber(tokens)) : "—"}</b></div>
        <div className="col-span-2 flex items-center gap-1.5 text-slate-500"><Clock size={13} /> Duration <b className="ml-auto text-slate-700">{formatDuration(latest?.duration_seconds)}</b></div>
      </div>

      {latest?.error_message && (
        <div className="mt-3 flex gap-2 rounded-lg bg-red-50 p-2.5 text-xs text-red-700"><AlertTriangle size={14} className="shrink-0" />{latest.error_message}</div>
      )}

      {latest && (
        <button onClick={() => setOpen(!open)} className="mt-4 flex items-center gap-1 text-xs font-medium text-violet-700 cursor-pointer">
          <ChevronDown size={14} className={cx("transition", open && "rotate-180")} /> Input & output summary
        </button>
      )}
      {open && latest && (
        <div className="mt-3 grid gap-3 border-t border-slate-100 pt-3">
          <div>
            <p className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400"><FileInput size={12} /> Input</p>
            <SummaryList entries={summarizeOutput(latest.input_data)} />
          </div>
          <div>
            <p className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400"><FileOutput size={12} /> Output</p>
            <SummaryList entries={summarizeOutput(latest.output_data)} />
          </div>
          {latest.is_mock && <p className="text-[11px] text-amber-700">Output produced in mock mode (rule-based, no LLM).</p>}
        </div>
      )}
    </Card>
  );
}

export default function AgentWorkspace() {
  const { selectedId, loaded } = useSelectedExecution();
  const detail = useExecutionDetail(selectedId);
  const active = detail.data && ACTIVE_STATUSES.includes(detail.data.status);
  const catalogue = useApi(() => Api.agentCatalogue(), []);
  const runs = useApi(() => Api.agentRuns(selectedId), [selectedId], { enabled: Boolean(selectedId), interval: active ? 2000 : null });

  const ex = detail.data;
  return (
    <div>
      <PageHeader title="Agent Workspace" description="Each specialised agent, what it is doing, how long it took and what it produced."
        actions={<ExecutionPicker detail={ex} />} />
      {!selectedId && loaded ? <NoExecution /> : !ex || !catalogue.data ? <Spinner /> : (
        <div className="space-y-5">
          <ErrorBanner error={detail.error || runs.error} />
          {ex.pending_approval && <ApprovalPanel approval={ex.pending_approval} executionId={ex.id} onDecided={detail.reload} compact />}
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
            {catalogue.data.map((agent) => (
              <AgentCard key={agent.name} agent={agent} execution={ex} runs={(runs.data || []).filter((r) => r.agent_name === agent.name)} />
            ))}
          </div>
          <p className="text-xs text-slate-400">Current orchestrator step: {humanize(ex.current_agent) || "—"}</p>
        </div>
      )}
    </div>
  );
}
