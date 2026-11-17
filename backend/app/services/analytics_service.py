"""Analytics computed from real execution data. Nothing here is hard-coded."""

from collections import Counter
from datetime import UTC, datetime, timedelta

from sqlalchemy import Integer, func, select
from sqlalchemy.orm import Session

from app.agents import AGENTS
from app.config import get_settings
from app.middleware.metrics import latency_tracker
from app.models import AgentRun, Approval, Execution, ExecutionLog, Project, TestResult
from app.models.enums import AgentRunStatus, ApprovalDecision, ExecutionStatus, TestStatus


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def overview(db: Session) -> dict:
    by_status = dict(db.execute(select(Execution.status, func.count(Execution.id))
                                .group_by(Execution.status)).all())
    count = lambda s: by_status.get(s, 0)  # noqa: E731
    finished_runs = db.scalar(select(func.count(AgentRun.id)).where(
        AgentRun.status.in_([AgentRunStatus.COMPLETED, AgentRunStatus.FAILED]))) or 0
    completed_runs = db.scalar(select(func.count(AgentRun.id)).where(
        AgentRun.status == AgentRunStatus.COMPLETED)) or 0
    avg_duration = db.scalar(select(func.avg(Execution.total_duration)).where(
        Execution.status == ExecutionStatus.COMPLETED))
    avg_processing = db.scalar(
        select(func.avg(select(func.sum(AgentRun.duration_seconds))
                        .where(AgentRun.execution_id == Execution.id)
                        .correlate(Execution).scalar_subquery()))
        .where(Execution.status == ExecutionStatus.COMPLETED))

    recent_logs = db.execute(
        select(ExecutionLog, Project.name).join(Execution, ExecutionLog.execution_id ==
                                                Execution.id)
        .join(Project, Execution.project_id == Project.id)
        .order_by(ExecutionLog.id.desc()).limit(12)).all()
    recent_projects = db.scalars(select(Project).order_by(Project.updated_at.desc()).limit(5))

    agent_status = []
    for name, agent in AGENTS.items():
        last = db.scalar(select(AgentRun).where(AgentRun.agent_name == name)
                         .order_by(AgentRun.id.desc()))
        agent_status.append({
            "agent": name, "display_name": agent.display_name,
            "last_status": str(last.status) if last else None,
            "last_run_at": last.started_at if last else None,
            "total_runs": db.scalar(select(func.count(AgentRun.id))
                                    .where(AgentRun.agent_name == name)) or 0,
        })

    return {
        "total_projects": db.scalar(select(func.count(Project.id))) or 0,
        "total_executions": sum(by_status.values()),
        "active_executions": count(ExecutionStatus.RUNNING) + count(ExecutionStatus.PENDING)
        + count(ExecutionStatus.WAITING_APPROVAL),
        "waiting_approval": count(ExecutionStatus.WAITING_APPROVAL),
        "successful_executions": count(ExecutionStatus.COMPLETED),
        "failed_executions": count(ExecutionStatus.FAILED),
        "cancelled_executions": count(ExecutionStatus.CANCELLED),
        "pending_approvals": db.scalar(select(func.count(Approval.id)).where(
            Approval.decision == ApprovalDecision.PENDING)) or 0,
        "agent_completion_rate": _rate(completed_runs, finished_runs),
        "avg_workflow_duration_seconds": round(avg_duration, 2) if avg_duration else None,
        "avg_agent_processing_seconds": round(avg_processing, 2) if avg_processing else None,
        "executions_by_status": {str(k): v for k, v in by_status.items()},
        "recent_activity": [{
            "id": log.id, "execution_id": log.execution_id, "project_name": project_name,
            "agent_name": log.agent_name, "level": str(log.log_level), "message": log.message,
            "timestamp": log.timestamp,
        } for log, project_name in recent_logs],
        "recent_projects": [{"id": p.id, "name": p.name, "status": str(p.status),
                             "business_domain": p.business_domain, "updated_at": p.updated_at}
                            for p in recent_projects],
        "agent_status": agent_status,
    }


def agents(db: Session) -> list[dict]:
    rows = []
    for name, agent in AGENTS.items():
        base = select(AgentRun).where(AgentRun.agent_name == name).subquery()
        stats = db.execute(select(
            func.count(base.c.id),
            func.sum((base.c.status == AgentRunStatus.COMPLETED).cast(Integer)),
            func.sum((base.c.status == AgentRunStatus.FAILED).cast(Integer)),
            func.avg(base.c.duration_seconds),
            func.sum(base.c.token_usage),
            func.sum((base.c.attempt > 1).cast(Integer)),
            func.sum(base.c.is_mock.cast(Integer)),
        )).one()
        total, completed, failed, avg_duration, tokens, retried, mock_runs = stats
        completed, failed = completed or 0, failed or 0
        rows.append({
            "agent": name, "display_name": agent.display_name, "description": agent.description,
            "total_runs": total or 0, "completed": completed, "failed": failed,
            "success_rate": _rate(completed, completed + failed),
            "avg_duration_seconds": round(avg_duration, 3) if avg_duration else None,
            "total_tokens": tokens or 0,
            "runs_with_retries": retried or 0,
            "mock_runs": mock_runs or 0,
        })
    return rows


def executions(db: Session) -> dict:
    settings = get_settings()
    all_execs = db.scalars(select(Execution)).all()
    finished = [e for e in all_execs if e.status in (
        ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED)]
    completed = [e for e in all_execs if e.status == ExecutionStatus.COMPLETED]
    durations = [e.total_duration for e in completed if e.total_duration]

    test_counts = Counter(dict(db.execute(select(TestResult.test_status,
                                                 func.count(TestResult.id))
                                          .group_by(TestResult.test_status)).all()))
    passed = test_counts.get(TestStatus.PASSED, 0)
    failed = test_counts.get(TestStatus.FAILED, 0) + test_counts.get(TestStatus.ERROR, 0)

    live = select(AgentRun).where(AgentRun.is_mock.is_(False)).subquery()
    prompt_tokens, completion_tokens, live_runs, llm_avg = db.execute(select(
        func.coalesce(func.sum(live.c.prompt_tokens), 0),
        func.coalesce(func.sum(live.c.completion_tokens), 0),
        func.count(live.c.id), func.avg(live.c.duration_seconds))).one()
    cost = (prompt_tokens * settings.llm_input_cost_per_1m
            + completion_tokens * settings.llm_output_cost_per_1m) / 1_000_000

    since = datetime.now(UTC) - timedelta(days=13)
    per_day: dict[str, dict[str, int]] = {}
    for offset in range(14):
        day = (since + timedelta(days=offset)).strftime("%Y-%m-%d")
        per_day[day] = {"completed": 0, "failed": 0, "cancelled": 0, "active": 0}
    for e in all_execs:
        started = e.started_at if e.started_at.tzinfo else e.started_at.replace(tzinfo=UTC)
        day = started.strftime("%Y-%m-%d")
        if day in per_day:
            key = {ExecutionStatus.COMPLETED: "completed", ExecutionStatus.FAILED: "failed",
                   ExecutionStatus.CANCELLED: "cancelled"}.get(e.status, "active")
            per_day[day][key] += 1

    iterations = Counter(dict(db.execute(
        select(TestResult.iteration, func.count(TestResult.id))
        .where(TestResult.test_status == TestStatus.PASSED)
        .group_by(TestResult.iteration)).all()))
    iteration_fail = Counter(dict(db.execute(
        select(TestResult.iteration, func.count(TestResult.id))
        .where(TestResult.test_status.in_([TestStatus.FAILED, TestStatus.ERROR]))
        .group_by(TestResult.iteration)).all()))

    return {
        "total_executions": len(all_execs),
        "workflow_completion_rate": _rate(len(completed), len(finished)),
        "avg_execution_duration_seconds": round(sum(durations) / len(durations), 2)
        if durations else None,
        "test_totals": {"passed": passed, "failed": failed,
                        "skipped": test_counts.get(TestStatus.SKIPPED, 0)},
        "test_pass_rate": _rate(passed, passed + failed),
        "tests_by_iteration": [{"iteration": i, "passed": iterations.get(i, 0),
                                "failed": iteration_fail.get(i, 0)}
                               for i in sorted(set(iterations) | set(iteration_fail))],
        "executions_with_corrections": sum(1 for e in all_execs if e.correction_attempts),
        "avg_correction_attempts": round(sum(e.correction_attempts for e in all_execs)
                                         / len(all_execs), 2) if all_execs else None,
        "retry_frequency": _rate(sum(1 for e in finished if e.correction_attempts),
                                 len(finished)),
        "llm": {
            "mode": settings.llm_mode, "model": settings.llm_model, "live_agent_runs": live_runs,
            "prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "estimated_cost_usd": round(cost, 6),
            "pricing_configured": bool(settings.llm_input_cost_per_1m
                                       or settings.llm_output_cost_per_1m),
            "avg_live_agent_latency_seconds": round(llm_avg, 3) if llm_avg else None,
        },
        "executions_per_day": [{"date": d, **v} for d, v in per_day.items()],
        "api_latency": latency_tracker.summary(),
    }
