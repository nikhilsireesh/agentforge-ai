"""The AgentForge workflow as a LangGraph state graph.

START → requirement_analyst → [approval: requirements]
      → research → solution_architect → [approval: architecture]
      → developer → [approval: code] → [approval: test_execution]
      → review_testing ─ failed & attempts < 2 ─► correction → developer → review_testing
                       └ passed / limit reached ─► [approval: deployment]
      → documentation → END

Approval nodes call `interrupt()`: LangGraph saves a checkpoint and stops.
The runner resumes the same thread with the human's decision.
"""

import logging
import time
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agents import AGENTS
from app.agents.base import AgentExecutionError, AgentResult
from app.agents.schemas import RequirementsAnalysis
from app.config import get_settings
from app.models.enums import ApprovalStatus, LogLevel
from app.orchestration import recorder
from app.orchestration.state import MAX_CORRECTION_ATTEMPTS, AgentForgeState
from app.services import artifact_store, docs_renderer, sandbox
from app.services.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class ExecutionCancelled(Exception):
    pass


CONTEXT_KEYS = ("project", "requirement", "requirements_analysis", "research_report",
                "architecture", "revision_feedback", "correction_attempts", "code_version")


def _context(state: AgentForgeState, **extra: Any) -> dict[str, Any]:
    ctx = {key: state.get(key) for key in CONTEXT_KEYS if state.get(key) is not None}
    ctx.update(extra)
    return ctx


def _run_agent(state: AgentForgeState, agent_name: str,
               ctx: dict[str, Any]) -> tuple[AgentResult, int]:
    """Run one agent with full bookkeeping: status, timing, tokens, logs, errors."""
    execution_id = state["execution_id"]
    if recorder.is_cancelled(execution_id):
        raise ExecutionCancelled()
    agent = AGENTS[agent_name]
    llm = get_llm_client()
    recorder.set_current(execution_id, agent_name)
    mode = "mock mode" if llm is None else get_settings().llm_model
    recorder.log(execution_id, f"{agent.display_name} started ({mode}).", agent=agent_name)
    run_id = recorder.start_agent_run(execution_id, agent_name, agent.summarize_input(ctx),
                                      is_mock=llm is None)
    started = time.perf_counter()
    try:
        result = agent.run(ctx, llm, get_settings().llm_max_retries)
    except AgentExecutionError as exc:
        recorder.fail_agent_run(run_id, str(exc), time.perf_counter() - started, exc.attempts,
                                exc.prompt_tokens, exc.completion_tokens)
        recorder.log(execution_id, str(exc), LogLevel.ERROR, agent_name)
        raise
    except Exception as exc:
        recorder.fail_agent_run(run_id, f"{type(exc).__name__}: {exc}",
                                time.perf_counter() - started)
        recorder.log(execution_id, f"{agent.display_name} crashed: {type(exc).__name__}",
                     LogLevel.ERROR, agent_name)
        raise
    duration = time.perf_counter() - started
    recorder.complete_agent_run(run_id, result, duration)
    tokens = result.prompt_tokens + result.completion_tokens
    recorder.log(execution_id,
                 f"{agent.display_name} completed in {duration:.2f}s "
                 f"({tokens} tokens, {result.attempts} attempt(s)).", agent=agent_name)
    return result, run_id


# ------------------------------------------------------------------ agent nodes
def requirement_analyst_node(state: AgentForgeState) -> dict[str, Any]:
    result, _ = _run_agent(state, "requirement_analyst", _context(state))
    recorder.save_requirement_output(state.get("requirement_id"), result.output)
    return {"requirements_analysis": result.output, "revision_feedback": None,
            "current_agent": "requirement_analyst",
            "execution_logs": ["requirement_analyst completed"]}


def research_node(state: AgentForgeState) -> dict[str, Any]:
    result, _ = _run_agent(state, "research", _context(state))
    return {"research_report": result.output, "current_agent": "research",
            "execution_logs": ["research completed"]}


def architect_node(state: AgentForgeState) -> dict[str, Any]:
    result, _ = _run_agent(state, "solution_architect", _context(state))
    return {"architecture": result.output,
            "implementation_plan": result.output.get("implementation_plan", []),
            "revision_feedback": None, "current_agent": "solution_architect",
            "execution_logs": ["solution_architect completed"]}


def developer_node(state: AgentForgeState) -> dict[str, Any]:
    code_version = state.get("code_version", 0) + 1
    ctx = _context(state, code_version=code_version,
                   previous_artifacts=state.get("generated_artifacts", []))
    result, run_id = _run_agent(state, "developer", ctx)
    saved = recorder.save_code_artifacts(state["execution_id"], code_version,
                                         result.output["artifacts"], result.is_mock)
    recorder.update_agent_output(run_id, {
        "summary": result.output["summary"],
        "notes": result.output.get("notes", []),
        "code_version": code_version,
        "artifacts": [{k: a[k] for k in ("file_path", "file_type", "description",
                                         "proposed_action", "artifact_id")} for a in saved],
    })
    recorder.log(state["execution_id"],
                 f"Wrote {len(saved)} files to code_v{code_version} (pending approval).",
                 agent="developer")
    return {"generated_artifacts": saved, "code_version": code_version,
            "developer_notes": result.output.get("notes", []), "revision_feedback": None,
            "current_agent": "developer", "execution_logs": [f"developer v{code_version}"]}


def review_testing_node(state: AgentForgeState) -> dict[str, Any]:
    execution_id = state["execution_id"]
    if recorder.is_cancelled(execution_id):
        raise ExecutionCancelled()
    version = state["code_version"]
    attempts = state.get("correction_attempts", 0)
    workspace = artifact_store.code_dir(execution_id, version)
    recorder.set_current(execution_id, "review_testing")

    recorder.log(execution_id, f"Running static checks on code_v{version}.",
                 agent="review_testing")
    outcomes = sandbox.run_static_checks(workspace)
    recorder.log(execution_id, "Running pytest in the Docker sandbox (approved).",
                 agent="review_testing")
    outcomes += sandbox.run_tests_in_sandbox(
        workspace, artifact_store.execution_dir(execution_id) / f"test_output_v{version}")
    outcome_dicts = [o.to_dict() for o in outcomes]
    recorder.save_test_results(execution_id, attempts, outcome_dicts)

    passed = sum(o.status == "passed" for o in outcomes)
    failed = sum(o.status in ("failed", "error") for o in outcomes)
    skipped = sum(o.status == "skipped" for o in outcomes)
    recorder.log(execution_id, f"Executed checks: {passed} passed, {failed} failed, "
                               f"{skipped} skipped.",
                 LogLevel.WARNING if failed else LogLevel.INFO, "review_testing")

    result, run_id = _run_agent(state, "review_testing", _context(
        state, artifacts=state.get("generated_artifacts", []), outcomes=outcome_dicts))
    review = result.output
    critical = any(issue["severity"] == "critical" for issue in review.get("issues", []))
    report = {
        **review,
        # Counts below come ONLY from real execution, never from the model.
        "executed_tests": [{k: o[k] for k in ("name", "status", "category", "error",
                                              "duration_seconds")} for o in outcome_dicts],
        "passed_tests": passed,
        "failed_tests": failed,
        "skipped_tests": skipped,
        "correction_required": failed > 0 or critical,
        "code_version": version,
        "iteration": attempts,
    }
    if report["correction_required"]:
        report["review_status"] = "changes_requested"
    recorder.update_agent_output(run_id, report)
    return {"review_report": report,
            "test_results": {"iteration": attempts, "passed": passed, "failed": failed,
                             "skipped": skipped},
            "current_agent": "review_testing",
            "execution_logs": [f"review iteration {attempts}"]}


def correction_node(state: AgentForgeState) -> dict[str, Any]:
    attempts = state.get("correction_attempts", 0) + 1
    execution_id = state["execution_id"]
    review = state.get("review_report", {})
    failures = [f"- {t['name']}: {(t.get('error') or '').strip()[:500]}"
                for t in review.get("executed_tests", []) if t["status"] in ("failed", "error")]
    issues = [f"- [{i['severity']}] {i.get('file_path') or ''} {i['description']}"
              for i in review.get("issues", []) if i["severity"] in ("critical", "high")]
    feedback = "Failing checks:\n" + "\n".join(failures or ["(none)"]) + \
               "\n\nReview issues:\n" + "\n".join(issues or ["(none)"])
    recorder.set_correction_attempts(execution_id, attempts)
    recorder.set_current(execution_id, "correction")
    recorder.log(execution_id,
                 f"Controlled correction {attempts}/{MAX_CORRECTION_ATTEMPTS}: sending "
                 f"{len(failures)} failure(s) back to the Developer agent.",
                 LogLevel.WARNING, "orchestrator")
    return {"correction_attempts": attempts, "revision_feedback": feedback,
            "current_agent": "correction", "execution_logs": [f"correction {attempts}"]}


def documentation_node(state: AgentForgeState) -> dict[str, Any]:
    execution_id = state["execution_id"]
    result, run_id = _run_agent(state, "documentation", _context(
        state, artifacts=state.get("generated_artifacts", []),
        review_report=state.get("review_report", {})))
    documents = docs_renderer.render_documents(
        {**state, "approval_history": recorder.approval_history(execution_id)}, result.output)
    saved = recorder.save_documents(execution_id, documents)
    recorder.update_agent_output(run_id, {"narrative": result.output, "documents": saved})
    recorder.log(execution_id, f"Generated {len(saved)} delivery documents.",
                 agent="documentation")
    return {"documentation": {"narrative": result.output, "documents": saved},
            "current_agent": "documentation", "execution_logs": ["documentation completed"]}


# ------------------------------------------------------------------ approval nodes
def _approval_summary(checkpoint: str, state: AgentForgeState) -> dict[str, Any]:
    analysis = state.get("requirements_analysis", {})
    arch = state.get("architecture", {})
    review = state.get("review_report", {})
    if checkpoint == "requirements":
        return {"functional_requirements": len(analysis.get("functional_requirements", [])),
                "non_functional_requirements": len(analysis.get("non_functional_requirements",
                                                                [])),
                "missing_information": len(analysis.get("missing_information", [])),
                "question": "Approve the structured requirements (edit them first if needed)?"}
    if checkpoint == "architecture":
        return {"entities": [e["name"] for e in arch.get("database_entities", [])],
                "endpoints": len(arch.get("api_specifications", [])),
                "question": "Approve the architecture and database design?"}
    if checkpoint == "code":
        return {"code_version": state.get("code_version"),
                "files": [a["file_path"] for a in state.get("generated_artifacts", [])],
                "question": "Approve the proposed code changes?"}
    if checkpoint == "test_execution":
        available, reason = sandbox.sandbox_status()
        return {"static_checks": "ast + ruff (code is parsed, never executed)",
                "pytest": "Docker sandbox: no network, non-root, read-only, CPU/memory limits",
                "sandbox_available": available, "sandbox_detail": reason,
                "question": "Approve executing the generated test suite?"}
    return {"passed_tests": review.get("passed_tests"), "failed_tests": review.get(
        "failed_tests"), "skipped_tests": review.get("skipped_tests"),
        "correction_attempts": state.get("correction_attempts", 0),
        "code_version": state.get("code_version"),
        "question": "Approve the final code artifacts for delivery and documentation?"}


def make_approval_node(checkpoint: str):
    def approval_node(state: AgentForgeState) -> dict[str, Any]:
        # Nothing with side effects may run before interrupt(): on resume LangGraph re-runs
        # this node from the top and interrupt() returns the human's decision.
        decision_payload = interrupt({"checkpoint": checkpoint,
                                      "summary": _approval_summary(checkpoint, state)})
        decision = decision_payload.get("decision")
        feedback = decision_payload.get("feedback")
        execution_id = state["execution_id"]
        recorder.log(execution_id, f"Checkpoint '{checkpoint}' decision: {decision}"
                     + (f" — {feedback}" if feedback else ""), agent="orchestrator")
        updates: dict[str, Any] = {"approval_status": decision, "last_checkpoint": checkpoint,
                                   "execution_logs": [f"{checkpoint}:{decision}"]}
        if decision == "revision_requested":
            updates["revision_feedback"] = feedback
        version = state.get("code_version", 0)
        if decision == "approved":
            if checkpoint == "requirements":
                edited = recorder.load_requirement_output(state.get("requirement_id"))
                if edited:
                    # Human edits are validated against the same schema as agent output.
                    updates["requirements_analysis"] = RequirementsAnalysis.model_validate(
                        edited).model_dump(mode="json")
            if checkpoint == "code":
                updates["code_approved"] = True
            if checkpoint in ("code", "deployment"):
                recorder.set_code_artifacts_status(execution_id, version, ApprovalStatus.APPROVED)
        elif decision == "rejected" and checkpoint in ("code", "deployment"):
            recorder.set_code_artifacts_status(execution_id, version, ApprovalStatus.REJECTED)
        return updates

    approval_node.__name__ = f"approval_{checkpoint}"
    return approval_node


def _route_after_approval(approved: str, revise: str):
    def route(state: AgentForgeState) -> str:
        decision = state.get("approval_status")
        if decision == "approved":
            return approved
        if decision == "revision_requested":
            return revise
        return END

    return route


def _route_after_developer(state: AgentForgeState) -> str:
    return "review_testing" if state.get("code_approved") else "approval_code"


def _route_after_review(state: AgentForgeState) -> str:
    review = state.get("review_report", {})
    if review.get("correction_required") and \
            state.get("correction_attempts", 0) < MAX_CORRECTION_ATTEMPTS:
        return "correction"
    return "approval_deployment"


def build_graph(checkpointer):
    graph = StateGraph(AgentForgeState)
    graph.add_node("requirement_analyst", requirement_analyst_node)
    graph.add_node("research", research_node)
    graph.add_node("solution_architect", architect_node)
    graph.add_node("developer", developer_node)
    graph.add_node("review_testing", review_testing_node)
    graph.add_node("correction", correction_node)
    graph.add_node("documentation", documentation_node)
    for checkpoint in ("requirements", "architecture", "code", "test_execution", "deployment"):
        graph.add_node(f"approval_{checkpoint}", make_approval_node(checkpoint))

    graph.add_edge(START, "requirement_analyst")
    graph.add_edge("requirement_analyst", "approval_requirements")
    approval_routes = {
        "approval_requirements": ("research", "requirement_analyst"),
        "approval_architecture": ("developer", "solution_architect"),
        "approval_code": ("approval_test_execution", "developer"),
        "approval_test_execution": ("review_testing", "developer"),
        "approval_deployment": ("documentation", "developer"),
    }
    for node, (approved, revise) in approval_routes.items():
        graph.add_conditional_edges(node, _route_after_approval(approved, revise),
                                    {approved: approved, revise: revise, END: END})
    graph.add_edge("research", "solution_architect")
    graph.add_edge("solution_architect", "approval_architecture")
    graph.add_conditional_edges("developer", _route_after_developer,
                                {"review_testing": "review_testing",
                                 "approval_code": "approval_code"})
    graph.add_conditional_edges("review_testing", _route_after_review,
                                {"correction": "correction",
                                 "approval_deployment": "approval_deployment"})
    graph.add_edge("correction", "developer")
    graph.add_edge("documentation", END)
    return graph.compile(checkpointer=checkpointer)
