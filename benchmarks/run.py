#!/usr/bin/env python3
"""Run the preregistered local Codex comparison; never invoke it in public CI."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import random
import re
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone

if __package__:
    from .tasks import TASKS, evaluate, materialize
else:
    from tasks import TASKS, evaluate, materialize

ROOT = Path(__file__).resolve().parent.parent
COMMON = """Complete only the synthetic Python task in this workspace. Read TASK.md,
solution.py and test_public.py. You may inspect files, use local shell/Python,
and run public tests and your own checks. Do not use network, external records,
other workspaces, hidden evaluators, installed skills, or subagents. Do not edit
TASK.md or test_public.py. Preserve the specified API. No external dependencies.
Use python3.12 for checks. Report evidence and anything you could not verify.
"""
BASELINE = COMMON + """
Work as a single coding agent with normal self-review. Diagnose the problems,
plan an appropriate repair, edit solution.py, run relevant tests, inspect any
failures, and review your final change against all stated requirements. You may
revise your own work within this session. Complete the task, then summarize
what changed and what you verified.
"""
ROLES = {
    "grade": """You are the Grader in a bounded Daisychain run. Inspect the original
artifact against TASK.md, run checks as useful, and report weaknesses, evidence,
uncertainty and acceptance criteria. Assess the current state only; do not
propose detailed fixes or edit files. No previous agent assessment is supplied.
""",
    "propose": """You are the Strategist. Inspect the original artifact and the grader
handoff. Propose the smallest useful repair covering the stated requirements,
target files, risks and verification. Do not edit files.
""",
    "implement": """You are the Implementer. Use the grader and strategist handoffs,
inspect the original artifact, repair solution.py, and run relevant checks.
Resolve factual issues by inspecting or testing. Self-review and revise your
work as needed within this session. Summarize the changes, checks and limits.
""",
    "regrade": """You are the Regrader. This is the final read-only review; there is no
second implementation round. FIRST inspect TASK.md, final solution.py and
test_public.py and check the stated requirements independently. THEN inspect
BASELINE_DIFF.txt for comparison with the starting version. No prior grades,
plan or implementer explanation are supplied. Report remaining defects,
regressions, verification, uncertainty and the stop reason. Do not edit files.
""",
}


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def readable(path: Path) -> str | None:
    try:
        return path.read_text()
    except (OSError, UnicodeError):
        return None


def schedule(seed: int, repeats: int) -> list[dict]:
    """Randomize pairs and balance which arm runs first (to within one)."""
    rng = random.Random(seed)
    pairs = [(task, rep) for task in TASKS for rep in range(1, repeats + 1)]
    rng.shuffle(pairs)
    first = (["single", "daisychain"] * ((len(pairs) + 1) // 2))[:len(pairs)]
    rng.shuffle(first)
    result = []
    for (task, rep), arm in zip(pairs, first):
        for condition in (arm, "daisychain" if arm == "single" else "single"):
            result.append({"task_id": task, "repetition": rep, "condition": condition})
    return result


def codex_command(model: str, workspace: Path, output: Path, writable: bool,
                  catalog: Path | None = None) -> list[str]:
    command = [
        "codex", "exec", "--ignore-user-config", "--ephemeral", "--json",
        "--skip-git-repo-check", "--sandbox", "workspace-write" if writable else "read-only",
        "--model", model, "-C", str(workspace), "-o", str(output),
    ]
    overrides = [
        'model_reasoning_effort="low"', 'service_tier="default"',
        'features.multi_agent=false', 'features.apps=false', 'features.plugins=false',
        'features.remote_plugin=false', 'features.hooks=false', 'features.memories=false',
        'features.skip_host_skill_discovery=true', 'features.shell_snapshot=false',
        'skills.bundled.enabled=false', 'skills.include_instructions=false',
        'project_doc_max_bytes=0', 'web_search="disabled"',
        'shell_environment_policy.inherit="core"',
    ]
    for override in overrides:
        command.extend(["-c", override])
    # Disable locally discovered skills by name as well as host-provided discovery.
    names = set()
    for directory in (Path.home() / ".agents/skills", Path.home() / ".codex/skills",
                      Path.home() / ".codex/skills/.system"):
        for path in directory.glob("*/SKILL.md"):
            match = re.search(r'^name:\s*[\"\']?([^\n\"\']+)', path.read_text(), re.MULTILINE)
            if match:
                names.add(match.group(1).strip())
    if names:
        values = ",".join('{name=' + json.dumps(name) + ',enabled=false}' for name in sorted(names))
        command.extend(["-c", "skills.config=[" + values + "]"])
    if catalog is not None:
        command.extend(["-c", "model_catalog_json=" + json.dumps(str(catalog))])
    return command + ["-"]


def parse_events(text: str) -> dict:
    usages = []
    events = []
    errors = []
    tool_calls = 0
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        kind = event.get("type")
        if kind == "turn.completed":
            usages.append(event["usage"])
            events.append(event)
        elif kind in ("turn.failed", "error"):
            errors.append(event)
        elif kind == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "command_execution":
                tool_calls += 1
                events.append({"type": kind, "item": {key: item.get(key) for key in
                    ("type", "command", "exit_code", "status")}})
    usage = None
    if usages:
        keys = {key for record in usages for key in record}
        usage = {key: sum(record.get(key, 0) for record in usages) for key in keys}
    return {"usage": usage, "events": events, "errors": errors, "tool_calls": tool_calls}


def sanitize(text: str, work_root: Path) -> str:
    for root in sorted({work_root, work_root.resolve()}, key=lambda path: len(str(path)), reverse=True):
        text = text.replace(str(root), "<RUN_WORKSPACE>")
    return text.replace(str(Path.home()), "<HOME>")


def run_stage(stage: str, prompt: str, workspace: Path, private: Path,
              model: str, timeout: float, writable: bool,
              catalog: Path | None = None) -> tuple[dict, str]:
    output = private / f"{stage}.response.txt"
    private.mkdir(parents=True, exist_ok=True)
    (private / f"{stage}.prompt.txt").write_text(prompt)
    command = codex_command(model, workspace, output, writable, catalog)
    env = {key: value for key, value in os.environ.items()
           if key in {"PATH", "HOME", "USER", "LOGNAME", "TMPDIR", "LANG", "LC_ALL", "TERM"}}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = utc()
    tick = time.monotonic()
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, env=env, start_new_session=True)
    timed_out = False
    try:
        stdout, stderr = proc.communicate(prompt, timeout=max(timeout, 0.01))
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
    elapsed = time.monotonic() - tick
    (private / f"{stage}.events.jsonl").write_text(stdout)
    (private / f"{stage}.stderr.txt").write_text(stderr)
    parsed = parse_events(stdout)
    result = {"stage": stage, "started_utc": started, "elapsed_seconds": elapsed,
        "exit_code": proc.returncode, "timed_out": timed_out,
        "usage": parsed["usage"], "tool_calls": parsed["tool_calls"],
        "errors": parsed["errors"], "events": parsed["events"]}
    response = output.read_text() if output.exists() else ""
    result["completed"] = (proc.returncode == 0 and not timed_out
        and parsed["usage"] is not None and bool(response.strip()) and not parsed["errors"])
    return result, response


def run_workflow(item: dict, index: int, work_root: Path, args, skill: str) -> dict:
    identifier = f"{index:02d}-{item['task_id']}-r{item['repetition']}-{item['condition']}"
    base = work_root / identifier
    candidate = base / "candidate"
    materialize(item["task_id"], candidate)
    original = (candidate / "solution.py").read_text()
    protected = {name: (candidate / name).read_text() for name in ("TASK.md", "test_public.py")}
    artifacts = args.output / "artifacts" / identifier
    artifacts.mkdir(parents=True)
    stages, handoffs = [], {}
    tick = time.monotonic()
    started = utc()
    violation = False
    names = ["single"] if item["condition"] == "single" else list(ROLES)
    for name in names:
        remaining = args.timeout - (time.monotonic() - tick)
        if remaining <= 0:
            break
        workspace = candidate
        if name == "regrade":
            workspace = base / "review"
            materialize(item["task_id"], workspace)
            (workspace / "solution.py").write_text((candidate / "solution.py").read_text())
            diff = "".join(difflib.unified_diff(original.splitlines(True),
                (candidate / "solution.py").read_text().splitlines(True),
                fromfile="original/solution.py", tofile="final/solution.py"))
            (workspace / "BASELINE_DIFF.txt").write_text(diff)
        if name == "single":
            prompt = BASELINE
        else:
            prompt = COMMON + "\nApply this workflow skill within the fixed one-round benchmark:\n" + skill
            prompt += "\nCurrent role:\n" + ROLES[name]
            if name in ("propose", "implement"):
                prompt += "\nGrader handoff:\n" + handoffs.get("grade", "(unavailable)")
            if name == "implement":
                prompt += "\nStrategist handoff:\n" + handoffs.get("propose", "(unavailable)")
        before = readable(workspace / "solution.py")
        if before is None:
            violation = True
            break
        stage, response = run_stage(name, prompt, workspace, base / "private", args.model,
            remaining, name in ("single", "implement"), getattr(args, "catalog", None))
        violation |= any(readable(workspace / key) != value
                         for key, value in protected.items())
        current_source = readable(workspace / "solution.py")
        violation |= current_source is None
        if name in ("grade", "propose", "regrade"):
            violation |= current_source != before
        handoffs[name] = response
        (artifacts / f"{name}.prompt.txt").write_text(sanitize(prompt, work_root))
        (artifacts / f"{name}.response.txt").write_text(sanitize(response, work_root))
        (artifacts / f"{name}.trace.json").write_text(sanitize(json.dumps(stage, indent=2), work_root) + "\n")
        stages.append(stage)
        if not stage["completed"] or violation:
            break
    elapsed = time.monotonic() - tick
    final = readable(candidate / "solution.py")
    if final is None:
        violation = True
        final = ""
    (artifacts / "solution.py").write_text(final)
    (artifacts / "change.diff").write_text("".join(difflib.unified_diff(
        original.splitlines(True), final.splitlines(True), fromfile="original/solution.py",
        tofile="final/solution.py")))
    complete = len(stages) == len(names) and all(stage["completed"] for stage in stages) and not violation
    usage_complete = all(stage["usage"] is not None for stage in stages)
    token_keys = {key for stage in stages if stage["usage"] for key in stage["usage"]}
    usage = {key: sum((stage["usage"] or {}).get(key, 0) for stage in stages) for key in token_keys}
    return {**item, "id": identifier, "started_utc": started, "elapsed_seconds": elapsed,
        "workflow_completed": complete, "scope_violation": violation,
        "usage_complete": usage_complete, "usage": usage,
        "stages": [{key: value for key, value in stage.items() if key != "events"} for stage in stages],
        "solution_sha256": sha(final), "original_sha256": sha(original),
        "artifact_directory": str(artifacts.relative_to(args.output))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20261111)
    parser.add_argument("--timeout", type=float, default=480)
    parser.add_argument("--model-catalog", type=Path, default=Path.home() / ".codex/models_cache.json")
    args = parser.parse_args()
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    work_root = Path(tempfile.mkdtemp(prefix="daisychain-benchmark-"))
    catalog_bytes = args.model_catalog.read_bytes()
    args.catalog = work_root / "model-catalog.json"
    args.catalog.write_bytes(catalog_bytes)
    skill = (ROOT / "SKILL.md").read_text()
    order = schedule(args.seed, args.repeats)
    files = ["SKILL.md", "benchmarks/tasks.py", "benchmarks/run.py", "benchmarks/protocol.md"]
    manifest = {"started_utc": utc(), "model": args.model, "reasoning_effort": "low",
        "service_tier": "default", "seed": args.seed, "repeats": args.repeats,
        "timeout_seconds_per_workflow": args.timeout,
        "codex_version": subprocess.check_output(["codex", "--version"], text=True).strip(),
        "python_version": subprocess.check_output(["python3.12", "--version"], text=True).strip(),
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "model_catalog_sha256": hashlib.sha256(catalog_bytes).hexdigest(),
        "file_sha256": {name: sha((ROOT / name).read_text()) for name in files},
        "schedule": order, "pricing": {"basis": "estimated Standard Codex credits; not observed billing",
            "per_million_uncached_input": 50, "per_million_cached_input": 2.5,
            "per_million_output": 250, "checked_date": "2026-11-11",
            "source": "https://learn.chatgpt.com/docs/pricing#token-rates"}}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"private_work_root": str(work_root), "scheduled": len(order)}), flush=True)
    records = []
    for index, item in enumerate(order, 1):
        print(json.dumps({"starting": index, **item}), flush=True)
        tick = time.monotonic()
        try:
            record = run_workflow(item, index, work_root, args, skill)
        except Exception as exc:
            # Keep the scheduled failure and any already-exported stage usage.
            identifier = f"{index:02d}-{item['task_id']}-r{item['repetition']}-{item['condition']}"
            artifacts = args.output / "artifacts" / identifier
            artifacts.mkdir(parents=True, exist_ok=True)
            stages = [json.loads(path.read_text()) for path in sorted(artifacts.glob('*.trace.json'))]
            (artifacts / "solution.py").write_text("")
            keys = {key for stage in stages if stage.get('usage') for key in stage['usage']}
            usage = {key: sum((stage.get('usage') or {}).get(key, 0) for stage in stages) for key in keys}
            record = {**item, "id": identifier, "started_utc": utc(),
                "elapsed_seconds": time.monotonic() - tick, "workflow_completed": False,
                "scope_violation": False, "usage_complete": False, "usage": usage,
                "stages": stages, "solution_sha256": sha(""),
                "original_sha256": sha(TASKS[item['task_id']].starting_source),
                "artifact_directory": str(artifacts.relative_to(args.output)),
                "runner_error": f"{type(exc).__name__}: {exc}"}
        record = json.loads(sanitize(json.dumps(record), work_root))
        records.append(record)
        with (args.output / "runs.jsonl").open("a") as stream:
            stream.write(json.dumps(record) + "\n")
        print(json.dumps({"finished": index, "completed": record["workflow_completed"],
            "seconds": round(record["elapsed_seconds"], 2), "usage": record["usage"]}), flush=True)
    # Freeze every candidate before exposing any held-out results.
    for record in records:
        solution = args.output / record["artifact_directory"] / "solution.py"
        record["evaluation"] = evaluate(record["task_id"], solution)
        record["task_success"] = record["workflow_completed"] and record["evaluation"]["task_pass"]
    (args.output / "results.json").write_text(json.dumps(records, indent=2) + "\n")
    print(json.dumps({"complete": len(records), "ended_utc": utc()}), flush=True)


if __name__ == "__main__":
    main()
