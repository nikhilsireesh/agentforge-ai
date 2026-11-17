import { AlertTriangle, Bug, CheckCircle2, ChevronDown, FlaskConical, ListChecks, MinusCircle, RotateCw, XCircle } from "lucide-react";
import { Fragment, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ApprovalPanel } from "../components/ApprovalPanel";
import { CHART, ChartTooltip, LegendRow, axisProps } from "../components/charts";
import { ExecutionPicker } from "../components/ExecutionPicker";
import { NoExecution } from "../components/NoExecution";
import { Card, CardHeader, EmptyState, ErrorBanner, Notice, PageHeader, Spinner, StatCard, StatusBadge, Table, cx, inlineInputClass } from "../components/ui";
import { useSelectedExecution } from "../context/ExecutionContext";
import { useApi } from "../hooks/useApi";
import { useExecutionDetail } from "../hooks/useExecution";
import { Api } from "../services/api";
import { formatDuration } from "../utils/format";

export default function TestingCenter() {
  const { selectedId, loaded } = useSelectedExecution();
  const detail = useExecutionDetail(selectedId);
  const ex = detail.data;
  const tests = useApi(() => Api.tests(selectedId), [selectedId, ex?.status, ex?.current_agent], { enabled: Boolean(selectedId) });
  const [iteration, setIteration] = useState("latest");
  const [expanded, setExpanded] = useState(null);

  const results = tests.data || [];
  const iterations = [...new Set(results.map((t) => t.iteration))].sort((a, b) => a - b);
  const active = iteration === "latest" ? iterations[iterations.length - 1] : Number(iteration);
  const rows = results.filter((t) => t.iteration === active);
  const count = (status) => rows.filter((t) => (status === "failed" ? ["failed", "error"].includes(t.test_status) : t.test_status === status)).length;
  const byIteration = useMemo(() => iterations.map((i) => {
    const subset = results.filter((t) => t.iteration === i);
    return {
      label: i === 0 ? "Initial run" : `Correction ${i}`,
      passed: subset.filter((t) => t.test_status === "passed").length,
      failed: subset.filter((t) => ["failed", "error"].includes(t.test_status)).length,
      skipped: subset.filter((t) => t.test_status === "skipped").length,
    };
  }), [results, iterations]);

  const review = ex?.outputs?.review_testing;
  const pending = ex?.pending_approval && ["test_execution", "deployment"].includes(ex.pending_approval.checkpoint);

  return (
    <div>
      <PageHeader title="Testing Center" description="Real results of static checks and sandboxed tests, review findings, correction attempts and requirement coverage."
        actions={<ExecutionPicker detail={ex} />} />
      {!selectedId && loaded ? <NoExecution /> : !ex ? <Spinner /> : (
        <div className="space-y-5">
          <ErrorBanner error={detail.error || tests.error} />
          {pending && <ApprovalPanel approval={ex.pending_approval} executionId={ex.id} showLink={false} onDecided={() => { detail.reload(); tests.reload(); }} />}
          {!results.length ? (
            <Card><EmptyState icon={FlaskConical} title="No tests executed yet" description="Tests run only after the code and test-execution checkpoints are approved." /></Card>
          ) : (
            <>
              {results.some((t) => t.test_status === "skipped" && t.test_name.startsWith("pytest")) && (
                <Notice tone="warning" icon={AlertTriangle}>
                  The pytest suite was <b>not executed</b> because the Docker sandbox is unavailable, so it is counted as skipped, never as passed. Static checks (syntax, Ruff) did run. See README → “Test sandbox” to enable it.
                </Notice>
              )}
              <div className="flex flex-wrap items-center gap-3">
                <select className={inlineInputClass} value={iteration} onChange={(e) => setIteration(e.target.value)} aria-label="Test iteration">
                  <option value="latest">Latest iteration</option>
                  {iterations.map((i) => <option key={i} value={i}>{i === 0 ? "Initial run" : `Correction ${i}`}</option>)}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
                <StatCard label="Passed" value={count("passed")} icon={CheckCircle2} tone="green" />
                <StatCard label="Failed" value={count("failed")} icon={XCircle} tone="red" />
                <StatCard label="Skipped" value={count("skipped")} icon={MinusCircle} tone="slate" />
                <StatCard label="Correction attempts" value={`${ex.correction_attempts} / 2`} icon={RotateCw} tone="amber" />
                <StatCard label="Latest review status" value={<StatusBadge status={review?.review_status || "pending"} />} icon={ListChecks} />
              </div>

              <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
                <Card>
                  <CardHeader title="Results by iteration" subtitle="Failures should disappear after correction" />
                  <LegendRow items={[["Passed", CHART.good], ["Failed", CHART.critical], ["Skipped", CHART.neutral]]} />
                  <div className="h-60 px-2 pb-4">
                    <ResponsiveContainer>
                      <BarChart data={byIteration} barGap={2}>
                        <CartesianGrid vertical={false} stroke={CHART.grid} />
                        <XAxis dataKey="label" {...axisProps} />
                        <YAxis allowDecimals={false} width={30} {...axisProps} />
                        <Tooltip content={<ChartTooltip />} cursor={{ fill: "#f1f5f9" }} />
                        <Bar isAnimationActive={false} dataKey="passed" name="Passed" fill={CHART.good} radius={[4, 4, 0, 0]} />
                        <Bar isAnimationActive={false} dataKey="failed" name="Failed" fill={CHART.critical} radius={[4, 4, 0, 0]} />
                        <Bar isAnimationActive={false} dataKey="skipped" name="Skipped" fill={CHART.neutral} radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </Card>
                <Card className="xl:col-span-2">
                  <CardHeader title="Executed checks" icon={FlaskConical} subtitle="Click a row to see its output log" />
                  <div className="max-h-[420px] overflow-y-auto">
                    <table className="w-full text-sm">
                      <thead className="sticky top-0 bg-white"><tr className="border-b border-slate-100 text-left text-xs uppercase tracking-wide text-slate-400">
                        <th className="px-5 py-2 font-medium">Check</th><th className="px-3 py-2 font-medium">Status</th><th className="px-3 py-2 font-medium">Time</th><th />
                      </tr></thead>
                      <tbody className="divide-y divide-slate-100">
                        {rows.map((t) => (
                          <Fragment key={t.id}>
                            <tr className="cursor-pointer hover:bg-slate-50" onClick={() => setExpanded(expanded === t.id ? null : t.id)}>
                              <td className="px-5 py-2.5 font-mono text-xs text-slate-700 break-all">{t.test_name}</td>
                              <td className="px-3 py-2.5"><StatusBadge status={t.test_status} /></td>
                              <td className="px-3 py-2.5 text-xs text-slate-500">{formatDuration(t.duration_seconds)}</td>
                              <td className="pr-4"><ChevronDown size={14} className={cx("text-slate-400 transition", expanded === t.id && "rotate-180")} /></td>
                            </tr>
                            {expanded === t.id && (
                              <tr><td colSpan={4} className="bg-slate-950 px-5 py-3">
                                <pre className="max-h-60 overflow-auto whitespace-pre-wrap font-mono text-[11.5px] text-slate-200">{[t.error_message, t.execution_output].filter(Boolean).join("\n\n") || "No output captured."}</pre>
                              </td></tr>
                            )}
                          </Fragment>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </div>
            </>
          )}

          {review && (
            <>
              <Card>
                <CardHeader title="Review findings" icon={Bug} subtitle={review.summary} />
                <Table rowKey={(i) => i.id} rows={review.issues} empty="No issues found." columns={[
                  { key: "id", label: "ID", className: "font-mono text-xs w-20" },
                  { key: "severity", label: "Severity", render: (i) => <StatusBadge status={i.severity} /> },
                  { key: "category", label: "Category" },
                  { key: "file", label: "File", className: "font-mono text-xs", render: (i) => i.file_path || "—" },
                  { key: "description", label: "Description" },
                  { key: "recommendation", label: "Recommendation", className: "text-slate-500" },
                ]} />
              </Card>
              <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
                <Card>
                  <CardHeader title="Requirement coverage" icon={ListChecks} />
                  <Table rowKey={(c) => c.requirement_id} rows={review.requirement_coverage} columns={[
                    { key: "requirement_id", label: "Req.", className: "font-mono text-xs" },
                    { key: "status", label: "Coverage", render: (c) => <StatusBadge status={c.status} /> },
                    { key: "evidence", label: "Evidence", className: "text-slate-500" },
                  ]} />
                </Card>
                <Card>
                  <CardHeader title={`Designed test cases (${review.test_cases.length})`} icon={FlaskConical} />
                  <Table rowKey={(t) => t.id} rows={review.test_cases} columns={[
                    { key: "name", label: "Test", className: "font-mono text-xs" },
                    { key: "category", label: "Category", render: (t) => t.category.replace("_", " ") },
                    { key: "req", label: "Req.", render: (t) => t.requirement_id || "—" },
                  ]} />
                </Card>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
