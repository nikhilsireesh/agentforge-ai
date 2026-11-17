import { Activity, Bot, CheckCircle2, Clock, FolderKanban, Gauge, PlayCircle, Plus, ShieldAlert, XCircle } from "lucide-react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CHART, ChartTooltip, LegendRow, axisProps } from "../components/charts";
import { Button, Card, CardHeader, EmptyState, ErrorBanner, Notice, PageHeader, Spinner, StatCard, StatusBadge } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { Api } from "../services/api";
import { formatDuration, formatPercent, timeAgo } from "../utils/format";

export default function Overview() {
  const overview = useApi(() => Api.analyticsOverview(), [], { interval: 5000 });
  const executions = useApi(() => Api.analyticsExecutions(), [], { interval: 10000 });
  const o = overview.data;

  if (overview.loading && !o) return <Spinner />;
  return (
    <div>
      <PageHeader title="Overview" description="Live status of every project, agent and workflow. All figures come from the database."
        actions={<Link to="/projects/new"><Button icon={Plus}>New project</Button></Link>} />
      <ErrorBanner error={overview.error} className="mb-4" />
      {o && (
        <div className="space-y-5">
          {o.pending_approvals > 0 && (
            <Notice tone="warning" icon={ShieldAlert}>
              <b>{o.pending_approvals}</b> workflow checkpoint{o.pending_approvals > 1 ? "s are" : " is"} waiting for human approval.{" "}
              <Link to="/approvals" className="font-semibold underline">Open Approval Center</Link>
            </Notice>
          )}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-3 2xl:grid-cols-6" data-testid="overview-stats">
            <StatCard label="Total projects" value={o.total_projects} icon={FolderKanban} />
            <StatCard label="Active executions" value={o.active_executions} icon={PlayCircle} tone="blue" hint={`${o.waiting_approval} waiting for approval`} />
            <StatCard label="Successful" value={o.successful_executions} icon={CheckCircle2} tone="green" />
            <StatCard label="Failed" value={o.failed_executions} icon={XCircle} tone="red" hint={`${o.cancelled_executions} cancelled/rejected`} />
            <StatCard label="Agent completion rate" value={formatPercent(o.agent_completion_rate)} icon={Gauge} tone="amber" hint="completed ÷ finished agent runs" />
            <StatCard label="Avg workflow duration" value={formatDuration(o.avg_workflow_duration_seconds)} icon={Clock} tone="slate" hint={`agent time ${formatDuration(o.avg_agent_processing_seconds)} · rest is human review`} />
          </div>

          <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
            <Card className="xl:col-span-2">
              <CardHeader title="Executions over the last 14 days" icon={Activity} subtitle="By final outcome on the day each run started" />
              <LegendRow items={[["Completed", CHART.good], ["Failed", CHART.critical], ["Cancelled", CHART.neutral], ["Active", CHART.blue]]} />
              <div className="h-64 px-2 pb-4">
                <ResponsiveContainer>
                  <BarChart data={(executions.data?.executions_per_day || []).map((d) => ({ ...d, label: d.date.slice(5) }))} barCategoryGap="25%">
                    <CartesianGrid vertical={false} stroke={CHART.grid} />
                    <XAxis dataKey="label" {...axisProps} />
                    <YAxis allowDecimals={false} width={30} {...axisProps} />
                    <Tooltip content={<ChartTooltip />} cursor={{ fill: "#f1f5f9" }} />
                    <Bar isAnimationActive={false} dataKey="completed" name="Completed" stackId="a" fill={CHART.good} stroke="#fff" strokeWidth={1} />
                    <Bar isAnimationActive={false} dataKey="failed" name="Failed" stackId="a" fill={CHART.critical} stroke="#fff" strokeWidth={1} />
                    <Bar isAnimationActive={false} dataKey="cancelled" name="Cancelled" stackId="a" fill={CHART.neutral} stroke="#fff" strokeWidth={1} />
                    <Bar isAnimationActive={false} dataKey="active" name="Active" stackId="a" fill={CHART.blue} stroke="#fff" strokeWidth={1} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <CardHeader title="Agent status" icon={Bot} subtitle="Most recent run of each agent" />
              <ul className="divide-y divide-slate-100 px-5 pb-3">
                {o.agent_status.map((a) => (
                  <li key={a.agent} className="flex items-center justify-between gap-3 py-2.5">
                    <div>
                      <p className="text-sm font-medium text-slate-800">{a.display_name}</p>
                      <p className="text-xs text-slate-400">{a.total_runs} runs · last {a.last_run_at ? timeAgo(a.last_run_at) : "never"}</p>
                    </div>
                    <StatusBadge status={a.last_status || "pending"} label={a.last_status ? undefined : "Idle"} />
                  </li>
                ))}
              </ul>
            </Card>

            <Card className="xl:col-span-2">
              <CardHeader title="Recent activity" icon={Activity} />
              {!o.recent_activity.length ? <EmptyState title="No activity yet" description="Agent and orchestrator events appear here as workflows run." /> : (
                <ul className="divide-y divide-slate-100 px-5 pb-3">
                  {o.recent_activity.map((item) => (
                    <li key={item.id} className="flex items-start gap-3 py-2.5">
                      <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${item.level === "ERROR" ? "bg-red-500" : item.level === "WARNING" ? "bg-amber-500" : "bg-violet-400"}`} />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm text-slate-700">{item.message}</p>
                        <p className="text-xs text-slate-400">
                          <Link to={`/workflow?execution=${item.execution_id}`} className="hover:text-violet-700">{item.project_name} · #{item.execution_id}</Link> · {item.agent_name || "system"} · {timeAgo(item.timestamp)}
                        </p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </Card>

            <Card>
              <CardHeader title="Recent projects" icon={FolderKanban} actions={<Link to="/projects" className="text-sm text-violet-700 hover:underline">All</Link>} />
              {!o.recent_projects.length ? <EmptyState title="No projects" action={<Link to="/projects/new"><Button size="sm" icon={Plus}>Create</Button></Link>} /> : (
                <ul className="divide-y divide-slate-100 px-5 pb-3">
                  {o.recent_projects.map((p) => (
                    <li key={p.id} className="flex items-center justify-between gap-3 py-2.5">
                      <Link to={`/projects/${p.id}`} className="min-w-0">
                        <p className="truncate text-sm font-medium text-slate-800 hover:text-violet-700">{p.name}</p>
                        <p className="text-xs text-slate-400">{p.business_domain || "—"} · {timeAgo(p.updated_at)}</p>
                      </Link>
                      <StatusBadge status={p.status} />
                    </li>
                  ))}
                </ul>
              )}
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
