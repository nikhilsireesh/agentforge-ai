import { Activity, Bot, CheckCircle2, Clock, Coins, Gauge, RotateCw, Timer } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CHART, ChartTooltip, LegendRow, axisProps } from "../components/charts";
import { Card, CardHeader, ErrorBanner, Notice, PageHeader, Spinner, StatCard, Table } from "../components/ui";
import { useApi } from "../hooks/useApi";
import { Api } from "../services/api";
import { formatDuration, formatNumber, formatPercent } from "../utils/format";

export default function Analytics() {
  const executions = useApi(() => Api.analyticsExecutions(), [], { interval: 10000 });
  const agents = useApi(() => Api.analyticsAgents(), [], { interval: 10000 });
  const e = executions.data;
  const a = agents.data || [];

  if (!e) return executions.error ? <ErrorBanner error={executions.error} /> : <Spinner />;
  const finishedRuns = a.reduce((s, x) => s + x.completed + x.failed, 0);
  const agentSuccess = finishedRuns ? a.reduce((s, x) => s + x.completed, 0) / finishedRuns : null;
  const agentRows = a.map((x) => ({ ...x, success_pct: x.success_rate === null ? 0 : Math.round(x.success_rate * 100), short: x.display_name.replace(" Agent", "").replace("Code Review & Testing", "Review & Test") }));

  return (
    <div>
      <PageHeader title="Analytics" description="Measured from real executions, agent runs, test results and API requests. Nothing on this page is estimated except the labelled LLM cost." />
      <ErrorBanner error={executions.error || agents.error} className="mb-4" />
      {e.llm.mode === "mock" && (
        <Notice tone="warning" className="mb-5">Mock LLM mode: no tokens are consumed, so token usage and cost stay at zero. They are recorded from provider responses when <code>LLM_API_KEY</code> is set.</Notice>
      )}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4" data-testid="analytics-kpis">
        <StatCard label="Workflow completion rate" value={formatPercent(e.workflow_completion_rate)} icon={CheckCircle2} tone="green" hint={`${e.total_executions} executions total`} />
        <StatCard label="Avg execution duration" value={formatDuration(e.avg_execution_duration_seconds)} icon={Clock} hint="Completed runs, incl. human review time" />
        <StatCard label="Agent success rate" value={formatPercent(agentSuccess)} icon={Bot} tone="blue" hint={`${finishedRuns} finished agent runs`} />
        <StatCard label="Test pass rate" value={formatPercent(e.test_pass_rate)} icon={Gauge} tone="green" hint={`${e.test_totals.passed} passed · ${e.test_totals.failed} failed · ${e.test_totals.skipped} skipped`} />
        <StatCard label="Retry (correction) frequency" value={formatPercent(e.retry_frequency)} icon={RotateCw} tone="amber" hint={`${e.executions_with_corrections} runs needed correction · avg ${e.avg_correction_attempts ?? "—"}`} />
        <StatCard label="LLM tokens" value={formatNumber(e.llm.total_tokens)} icon={Activity} tone="slate" hint={`${formatNumber(e.llm.prompt_tokens)} prompt · ${formatNumber(e.llm.completion_tokens)} completion`} />
        <StatCard label="Estimated LLM cost" value={`$${e.llm.estimated_cost_usd.toFixed(4)}`} icon={Coins} tone="slate" hint={e.llm.pricing_configured ? "From configured per-token prices" : "Set LLM_*_COST_PER_1M to estimate"} />
        <StatCard label="API latency (p50 / p95)" value={e.api_latency.count ? `${e.api_latency.p50_ms} / ${e.api_latency.p95_ms} ms` : "—"} icon={Timer} tone="violet" hint={`${formatNumber(e.api_latency.count)} requests since server start`} />
      </div>

      <div className="mt-5 grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Card>
          <CardHeader title="Agent success rate" subtitle="Completed ÷ finished runs per agent (%)" />
          <div className="h-64 px-2 pb-4">
            <ResponsiveContainer>
              <BarChart data={agentRows} layout="vertical" margin={{ left: 10, right: 20 }}>
                <CartesianGrid horizontal={false} stroke={CHART.grid} />
                <XAxis type="number" domain={[0, 100]} unit="%" {...axisProps} />
                <YAxis type="category" dataKey="short" width={120} {...axisProps} />
                <Tooltip content={<ChartTooltip formatter={(v) => `${v}%`} />} cursor={{ fill: "#f1f5f9" }} />
                <Bar isAnimationActive={false} dataKey="success_pct" name="Success rate" fill={CHART.blue} radius={[0, 4, 4, 0]} barSize={14} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <CardHeader title="Average agent duration" subtitle="Seconds per run (LLM latency included in live mode)" />
          <div className="h-64 px-2 pb-4">
            <ResponsiveContainer>
              <BarChart data={agentRows} layout="vertical" margin={{ left: 10, right: 20 }}>
                <CartesianGrid horizontal={false} stroke={CHART.grid} />
                <XAxis type="number" {...axisProps} />
                <YAxis type="category" dataKey="short" width={120} {...axisProps} />
                <Tooltip content={<ChartTooltip formatter={(v) => formatDuration(v)} />} cursor={{ fill: "#f1f5f9" }} />
                <Bar isAnimationActive={false} dataKey="avg_duration_seconds" name="Avg duration" fill={CHART.blue} radius={[0, 4, 4, 0]} barSize={14} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <CardHeader title="Test outcomes by correction iteration" subtitle="Across all executions" />
          <LegendRow items={[["Passed", CHART.good], ["Failed", CHART.critical]]} />
          <div className="h-60 px-2 pb-4">
            <ResponsiveContainer>
              <BarChart data={e.tests_by_iteration.map((t) => ({ ...t, label: t.iteration === 0 ? "Initial" : `Correction ${t.iteration}` }))} barGap={2}>
                <CartesianGrid vertical={false} stroke={CHART.grid} />
                <XAxis dataKey="label" {...axisProps} />
                <YAxis allowDecimals={false} width={34} {...axisProps} />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "#f1f5f9" }} />
                <Bar isAnimationActive={false} dataKey="passed" name="Passed" fill={CHART.good} radius={[4, 4, 0, 0]} />
                <Bar isAnimationActive={false} dataKey="failed" name="Failed" fill={CHART.critical} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card>
          <CardHeader title="API latency by route" subtitle={e.api_latency.note || "No requests recorded yet"} />
          <Table rowKey={(r) => r.route} rows={e.api_latency.routes || []} columns={[
            { key: "route", label: "Route", className: "font-mono text-xs" },
            { key: "count", label: "Requests" },
            { key: "avg_ms", label: "Avg (ms)" },
          ]} />
        </Card>
        <Card className="xl:col-span-2">
          <CardHeader title="Agent metrics" icon={Bot} />
          <Table rowKey={(r) => r.agent} rows={a} columns={[
            { key: "display_name", label: "Agent", className: "font-medium" },
            { key: "total_runs", label: "Runs" },
            { key: "completed", label: "Completed" },
            { key: "failed", label: "Failed" },
            { key: "success_rate", label: "Success", render: (r) => formatPercent(r.success_rate) },
            { key: "avg", label: "Avg duration", render: (r) => formatDuration(r.avg_duration_seconds) },
            { key: "runs_with_retries", label: "LLM retries" },
            { key: "total_tokens", label: "Tokens", render: (r) => formatNumber(r.total_tokens) },
            { key: "mock_runs", label: "Mock runs" },
          ]} />
        </Card>
      </div>
    </div>
  );
}
