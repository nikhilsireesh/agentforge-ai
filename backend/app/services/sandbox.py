"""Checks run against generated code.

1. Static checks (always): Python's `ast` parser and Ruff. Neither one
   executes the code, so they are safe to run on the host.
2. Tests (pytest): run ONLY inside a locked-down Docker container:
   no network, non-root user, read-only filesystem, CPU/memory/process
   limits, all capabilities dropped, hard timeout. The command is fixed
   (allowlisted); nothing produced by an LLM is ever used as a command.
   If Docker is unavailable, tests are reported as SKIPPED, never as passed.
"""

import ast
import json
import logging
import shutil
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ElementTree
from dataclasses import asdict, dataclass
from pathlib import Path

from app.config import Settings, get_settings
from app.services.artifact_store import generated_root

logger = logging.getLogger(__name__)

RUFF_RULES = "E9,F63,F7,F82"  # syntax errors, invalid comparisons, undefined names
MAX_OUTPUT_CHARS = 8000
_availability_cache: dict[str, tuple[float, bool, str]] = {}


@dataclass
class CheckOutcome:
    name: str
    status: str  # passed | failed | skipped | error
    category: str  # static | pytest
    output: str = ""
    error: str | None = None
    duration_seconds: float = 0.0
    file_path: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _ruff_binary() -> str | None:
    candidate = Path(sys.executable).parent / "ruff"
    return str(candidate) if candidate.exists() else shutil.which("ruff")


def _assert_inside_generated(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(generated_root()):
        raise ValueError("Checks may only run on folders inside GENERATED_PROJECTS_DIR")
    return resolved


def run_static_checks(workspace: Path) -> list[CheckOutcome]:
    workspace = _assert_inside_generated(workspace)
    py_files = sorted(p for p in workspace.rglob("*.py") if p.is_file() and not p.is_symlink())
    outcomes: list[CheckOutcome] = []

    for path in py_files:
        rel = path.relative_to(workspace).as_posix()
        started = time.perf_counter()
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            outcomes.append(CheckOutcome(f"static::syntax::{rel}", "passed", "static",
                                         output="Parsed successfully",
                                         duration_seconds=time.perf_counter() - started,
                                         file_path=rel))
        except SyntaxError as exc:
            outcomes.append(CheckOutcome(f"static::syntax::{rel}", "failed", "static",
                                         error=f"line {exc.lineno}: {exc.msg}",
                                         duration_seconds=time.perf_counter() - started,
                                         file_path=rel))

    ruff = _ruff_binary()
    if ruff is None:
        outcomes.append(CheckOutcome("static::ruff", "skipped", "static",
                                     error="Ruff is not installed."))
    elif py_files:
        started = time.perf_counter()
        try:
            proc = subprocess.run(
                [ruff, "check", "--isolated", "--no-cache", "--output-format", "json",
                 "--select", RUFF_RULES, "--target-version", "py311", str(workspace)],
                capture_output=True, text=True, timeout=60, check=False,
            )
            diagnostics = json.loads(proc.stdout or "[]")
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            outcomes.append(CheckOutcome("static::ruff", "error", "static",
                                         error=f"Ruff could not run: {type(exc).__name__}"))
            diagnostics = None
        elapsed = time.perf_counter() - started
        if diagnostics is not None:
            by_file: dict[str, list[str]] = {}
            for item in diagnostics:
                rel = Path(item["filename"]).resolve().relative_to(workspace).as_posix()
                row = (item.get("location") or {}).get("row")
                by_file.setdefault(rel, []).append(f"line {row}: {item['code']} {item['message']}")
            for path in py_files:
                rel = path.relative_to(workspace).as_posix()
                problems = by_file.get(rel)
                outcomes.append(CheckOutcome(
                    f"static::ruff::{rel}", "failed" if problems else "passed", "static",
                    output="" if problems else f"No {RUFF_RULES} findings",
                    error="\n".join(problems) if problems else None,
                    duration_seconds=elapsed / max(len(py_files), 1), file_path=rel,
                ))

    test_files = [p for p in py_files if p.name.startswith("test_")]
    outcomes.append(CheckOutcome(
        "static::structure::test_files_present",
        "passed" if test_files else "failed", "static",
        output=f"{len(test_files)} test file(s) found",
        error=None if test_files else "No test_*.py files were generated.",
    ))
    return outcomes


def sandbox_status(settings: Settings | None = None) -> tuple[bool, str]:
    """Return (available, reason). Cached for 60 seconds."""
    settings = settings or get_settings()
    if settings.sandbox_mode == "disabled":
        return False, "Sandbox disabled by configuration (SANDBOX_MODE=disabled)."
    cached = _availability_cache.get(settings.sandbox_image)
    if cached and time.monotonic() - cached[0] < 60:
        return cached[1], cached[2]

    docker = shutil.which("docker")
    if docker is None:
        result = (False, "Docker is not installed, so generated tests cannot run safely.")
    else:
        try:
            proc = subprocess.run([docker, "image", "inspect", settings.sandbox_image],
                                  capture_output=True, timeout=15, check=False)
            result = (True, "Docker sandbox ready.") if proc.returncode == 0 else (
                False,
                f"Sandbox image '{settings.sandbox_image}' not found or Docker not running. "
                "Build it with: docker build -t agentforge-sandbox:latest "
                "-f docker/sandbox.Dockerfile docker",
            )
        except subprocess.TimeoutExpired:
            result = (False, "Docker did not respond.")
    _availability_cache[settings.sandbox_image] = (time.monotonic(), *result)
    return result


def build_docker_command(settings: Settings, workspace: Path, output_dir: Path,
                         container_name: str) -> list[str]:
    """The ONLY command ever used to execute generated code (allowlisted, fixed)."""
    return [
        "docker", "run", "--rm",
        "--name", container_name,
        "--network", "none",                     # no network access
        "--user", "10001:10001",                 # non-root
        "--cpus", settings.sandbox_cpus,         # CPU limit
        "--memory", settings.sandbox_memory,     # memory limit
        "--memory-swap", settings.sandbox_memory,
        "--pids-limit", "128",                   # fork-bomb protection
        "--read-only",                           # immutable root filesystem
        "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "-e", "PYTHONDONTWRITEBYTECODE=1",
        "-v", f"{workspace}:/workspace:ro",      # generated code, read-only
        "-v", f"{output_dir}:/output:rw",        # only place it may write
        "-w", "/workspace",
        settings.sandbox_image,
        "python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "--junitxml=/output/junit.xml",
    ]


def _parse_junit(path: Path) -> list[CheckOutcome]:
    if path.stat().st_size > 5_000_000:
        raise ValueError("junit report too large")
    root = ElementTree.parse(path).getroot()
    outcomes = []
    for case in root.iter("testcase"):
        name = f"pytest::{case.get('classname', '')}::{case.get('name', '')}"
        duration = float(case.get("time") or 0)
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        if failure is not None or error is not None:
            node = failure if failure is not None else error
            message = (node.get("message") or "") + "\n" + (node.text or "")
            outcomes.append(CheckOutcome(name, "failed" if failure is not None else "error",
                                         "pytest", output=(node.text or "")[:MAX_OUTPUT_CHARS],
                                         error=message.strip()[:2000],
                                         duration_seconds=duration))
        elif skipped is not None:
            outcomes.append(CheckOutcome(name, "skipped", "pytest",
                                         error=skipped.get("message"), duration_seconds=duration))
        else:
            outcomes.append(CheckOutcome(name, "passed", "pytest", output="passed",
                                         duration_seconds=duration))
    return outcomes


def run_tests_in_sandbox(workspace: Path, output_dir: Path) -> list[CheckOutcome]:
    settings = get_settings()
    workspace = _assert_inside_generated(workspace)
    available, reason = sandbox_status(settings)
    if not available:
        return [CheckOutcome("pytest::suite", "skipped", "pytest",
                             error=f"Tests NOT executed. {reason}")]

    output_dir = _assert_inside_generated(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir.chmod(0o777)  # the non-root container user must be able to write the report
    junit = output_dir / "junit.xml"
    junit.unlink(missing_ok=True)
    name = f"agentforge-test-{uuid.uuid4().hex[:12]}"
    command = build_docker_command(settings, workspace, output_dir, name)
    started = time.perf_counter()
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=settings.sandbox_timeout_seconds, check=False)
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], capture_output=True, check=False)
        return [CheckOutcome("pytest::suite", "error", "pytest",
                             error=f"Test run exceeded {settings.sandbox_timeout_seconds}s "
                                   "and was killed.",
                             duration_seconds=time.perf_counter() - started)]
    combined = (proc.stdout + "\n" + proc.stderr)[-MAX_OUTPUT_CHARS:]
    if not junit.exists():
        return [CheckOutcome("pytest::suite", "error", "pytest", output=combined,
                             error=f"pytest produced no report (exit code {proc.returncode}).",
                             duration_seconds=time.perf_counter() - started)]
    try:
        outcomes = _parse_junit(junit)
    except (ElementTree.ParseError, ValueError) as exc:
        return [CheckOutcome("pytest::suite", "error", "pytest", output=combined,
                             error=f"Could not read test report: {exc}")]
    if not outcomes:
        return [CheckOutcome("pytest::suite", "error", "pytest", output=combined,
                             error="No tests were collected.")]
    return outcomes
