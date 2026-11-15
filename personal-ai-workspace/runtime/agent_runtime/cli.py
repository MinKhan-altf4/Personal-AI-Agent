"""Command-line entry point: python -m agent_runtime <command>."""

from __future__ import annotations

import argparse
import sys

from . import __version__, tools
from .config import ConfigError, load_workspace, validate
from .model import AnthropicModel, DryRunModel, ModelError
from .orchestrator import Orchestrator
from .policy import Policy, approve_all
from .store import TaskStore


def _console_approver(message: str) -> bool:
    if not sys.stdin or not sys.stdin.isatty():
        return False  # never auto-approve when nobody can answer
    answer = input(f"\n[Cần phê duyệt] {message}. Đồng ý? [y/N] ").strip().lower()
    return answer in {"y", "yes", "c", "co", "có"}


def _store(ws) -> TaskStore:
    return TaskStore(ws.data_dir / "runtime.sqlite", ws.tasks_dir / "INDEX.md")


def cmd_check(ws, _args) -> int:
    problems = validate(ws)
    print(f"Workspace: {ws.root}")
    for agent in ws.agents.values():
        if not agent.active:
            print(f"  - {agent.id:<18} {agent.status}")
            continue
        profile = ws.profile_for(agent.id)
        given = sorted({t.registry_tool for t in tools.tools_for(agent)})
        missing = tools.unimplemented_registry_tools(agent)
        print(f"  + {agent.id:<18} level {agent.permission_level}  {profile.model}/{profile.effort}")
        print(f"      tools: {', '.join(given) or '-'}" + (f"  (not in v0.1: {', '.join(missing)})" if missing else ""))
    if problems:
        print("\nVấn đề cấu hình:")
        for p in problems:
            print(f"  ! {p}")
        return 1
    print("\nCấu hình hợp lệ.")
    return 0


def cmd_run(ws, args) -> int:
    problems = validate(ws)
    if problems:
        print("Cấu hình không hợp lệ, chạy `check` để xem chi tiết.", file=sys.stderr)
        return 1
    executors = [a.id for a in ws.active_agents() if a.id != "orchestrator"]
    try:
        model = DryRunModel(executors) if args.dry_run else AnthropicModel(ws.refusal_fallback)
    except ImportError:
        print("Thiếu thư viện `anthropic`. Chạy: pip install -r runtime/requirements.txt", file=sys.stderr)
        return 1
    policy = Policy(ws, approver=approve_all if args.yes else _console_approver)
    store = _store(ws)
    try:
        orch = Orchestrator(ws, store, model, policy, progress=print)
        result = orch.run(args.request)
    except ModelError as exc:
        print(f"Lỗi model: {exc}", file=sys.stderr)
        return 2
    finally:
        store.close()
    print(f"\nTask:      {result.task_id}")
    print(f"Trạng thái: {result.status}" + (f"  (QA: {result.review_outcome})" if result.review_outcome else ""))
    print(f"Báo cáo:   {result.report_path}")
    return 0 if result.status != "blocked" else 3


def cmd_list(ws, args) -> int:
    store = _store(ws)
    try:
        rows = store.list(args.limit)
    finally:
        store.close()
    if not rows:
        print("Chưa có task nào do runtime tạo.")
    for r in rows:
        print(f"{r.id}  {r.status:<11} {(r.primary_agent or '-'):<18} {r.title}")
    return 0


def cmd_show(ws, args) -> int:
    store = _store(ws)
    try:
        task = store.get(args.task_id)
        if not task:
            print(f"Không tìm thấy {args.task_id}", file=sys.stderr)
            return 1
        print(f"{task.id} — {task.title}\nTrạng thái: {task.status} | Agent: {task.primary_agent} | Tạo: {task.created_at}")
        print(f"Yêu cầu: {task.request}\n\nNhật ký:")
        for e in store.events(task.id):
            p = e["payload"]
            if e["kind"] == "tool_call":
                flag = "REFUSED/FAILED" if p["is_error"] else "ok"
                detail = f"{p['tool']}({p['args']}) -> {flag}"
            elif e["kind"] == "model_turn":
                detail = f"{p['model']} stop={p['stop_reason']} usage={p['usage']}"
            else:
                detail = str(p)[:200]
            print(f"  {e['ts']}  {(e['agent'] or '-'):<18} {e['kind']:<11} {detail}")
        report = ws.tasks_dir / task.id / "REPORT.md"
        if report.is_file():
            print(f"\nBáo cáo: {report.relative_to(ws.root).as_posix()}")
    finally:
        store.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = argparse.ArgumentParser(prog="agent_runtime", description="Personal AI-Agent Workspace runtime")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("check", help="Kiểm tra cấu hình workspace")
    p_run = sub.add_parser("run", help="Giao một yêu cầu cho hệ thống agent")
    p_run.add_argument("request", help="Yêu cầu bằng ngôn ngữ tự nhiên")
    p_run.add_argument("--dry-run", action="store_true", help="Chạy offline bằng model giả lập, không tốn phí")
    p_run.add_argument("--yes", action="store_true", help="Tự động duyệt các lệnh ghi file ngoài thư mục task")
    p_list = sub.add_parser("list", help="Liệt kê task gần đây")
    p_list.add_argument("--limit", type=int, default=20)
    p_show = sub.add_parser("show", help="Xem chi tiết và nhật ký của một task")
    p_show.add_argument("task_id")
    args = parser.parse_args(argv)

    try:
        ws = load_workspace()
    except ConfigError as exc:
        print(f"Lỗi cấu hình: {exc}", file=sys.stderr)
        return 1
    handlers = {"check": cmd_check, "run": cmd_run, "list": cmd_list, "show": cmd_show}
    return handlers[args.command](ws, args)
