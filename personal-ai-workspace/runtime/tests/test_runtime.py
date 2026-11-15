from __future__ import annotations

import json
import unittest
from datetime import date

from agent_runtime import prompts, tools
from agent_runtime.config import load_workspace, validate
from agent_runtime.model import DryRunModel
from agent_runtime.orchestrator import Orchestrator
from agent_runtime.policy import Policy, PolicyError, approve_all, deny_all
from agent_runtime.store import TaskStore

from helpers import WORKSPACE, ScriptedModel, TempWorkspace, text_turn, tool_turn

DAY = date(2026, 11, 15)


def make_store(root):
    return TaskStore(root / "runtime" / "data" / "runtime.sqlite", root / "tasks" / "INDEX.md")


def plan(agent="engineering", needs_qa=True, clarification=""):
    return text_turn(json.dumps({
        "title": "Test task", "project": "global", "primary_agent": agent, "objective": "Do the thing",
        "acceptance_criteria": ["It works"], "needs_qa": needs_qa, "clarification_needed": clarification,
    }))


class ConfigTests(unittest.TestCase):
    def test_real_workspace_is_consistent(self):
        ws = load_workspace(WORKSPACE)
        self.assertEqual(validate(ws), [])
        self.assertEqual(ws.agent("qa_auditor").permission_level, 2)
        self.assertEqual(ws.profile_for("engineering").model, "claude-opus-5-5")

    def test_system_prompt_is_stable_and_cached(self):
        ws = load_workspace(WORKSPACE)
        a = prompts.system_blocks(ws, ws.agent("engineering"), "execute")
        b = prompts.system_blocks(ws, ws.agent("engineering"), "execute")
        self.assertEqual(a, b)  # byte-identical -> cacheable
        self.assertIn("cache_control", a[-1])
        self.assertTrue(any("software-engineer" in blk["text"] for blk in a))


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempWorkspace()
        self.root = self._tmp.__enter__()
        self.ws = load_workspace(self.root)

    def tearDown(self):
        self._tmp.__exit__(None, None, None)

    def test_secret_and_outside_paths_denied(self):
        policy = Policy(self.ws, approve_all)
        for bad in (".env", "../skills/x.md", "runtime/data/runtime.sqlite", "secrets/key.txt"):
            with self.assertRaises(PolicyError, msg=bad):
                policy.resolve(bad)
        self.assertEqual(policy.resolve("notes.md"), (self.root / "notes.md").resolve())

    def test_level_one_writes_only_in_task_folder(self):
        policy = Policy(self.ws, approve_all)
        research = self.ws.agent("research")  # level 1, no write tool, but check the rule itself
        policy.check_write(research, "tasks/TASK-X/drafts/a.md", "TASK-X")
        with self.assertRaises(PolicyError):
            policy.check_write(research, "notes.md", "TASK-X")

    def test_level_two_outside_task_needs_approval(self):
        eng = self.ws.agent("engineering")
        with self.assertRaises(PolicyError):
            Policy(self.ws, deny_all).check_write(eng, "notes.md", "TASK-X")
        Policy(self.ws, approve_all).check_write(eng, "notes.md", "TASK-X")

    def test_qa_never_edits_outside_task_folder(self):
        qa = self.ws.agent("qa_auditor")
        with self.assertRaises(PolicyError):
            Policy(self.ws, approve_all).check_write(qa, "notes.md", "TASK-X")
        Policy(self.ws, deny_all).check_write(qa, "tasks/TASK-X/QA_REVIEW.md", "TASK-X")

    def test_tool_level_and_registration(self):
        policy = Policy(self.ws)
        policy.check_tool(self.ws.agent("engineering"), "approved_file_edit")
        with self.assertRaises(PolicyError):
            policy.check_tool(self.ws.agent("research"), "approved_file_edit")  # not registered

    def test_list_dir_hides_secrets(self):
        store = make_store(self.root)
        ctx = tools.ToolContext(self.ws, Policy(self.ws), self.ws.agent("research"), "TASK-X", store)
        listing, err = tools.execute(ctx, "list_dir", {"path": "."})
        self.assertFalse(err)
        self.assertIn("notes.md", listing)
        self.assertNotIn(".env", listing)
        result, err = tools.execute(ctx, "read_file", {"path": ".env"})
        self.assertTrue(err)
        self.assertIn("secret", result)
        store.close()


class StoreTests(unittest.TestCase):
    def test_ids_continue_after_index_rows(self):
        with TempWorkspace() as root:
            store = make_store(root)
            index = (root / "tasks" / "INDEX.md").read_text(encoding="utf-8")
            highest = max(int(line.split("|")[1].strip()[-3:]) for line in index.splitlines()
                          if line.startswith("| TASK-20261115-"))
            first = store.create("hello", today=DAY)
            self.assertEqual(first, f"TASK-20261115-{highest + 1:03d}")
            self.assertEqual(store.next_task_id(DAY), f"TASK-20261115-{highest + 2:03d}")
            store.update(first, title="Renamed", status="completed", primary_agent="research")
            index = (root / "tasks" / "INDEX.md").read_text(encoding="utf-8")
            self.assertIn(f"| {first} | Renamed | global | research | completed |", index)
            with self.assertRaises(ValueError):
                store.update(first, status="done")
            store.close()


class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = TempWorkspace()
        self.root = self._tmp.__enter__()
        self.ws = load_workspace(self.root)
        self.store = make_store(self.root)

    def tearDown(self):
        self.store.close()
        self._tmp.__exit__(None, None, None)

    def orch(self, model, approver=deny_all):
        return Orchestrator(self.ws, self.store, model, Policy(self.ws, approver), today=DAY)

    def test_dry_run_end_to_end(self):
        executors = [a.id for a in self.ws.active_agents() if a.id != "orchestrator"]
        result = self.orch(DryRunModel(executors)).run("Tóm tắt các quyết định trong DECISIONS.md")
        self.assertEqual(result.plan["title"], "Tóm tắt các quyết định trong DECISIONS.md")
        self.assertEqual(result.plan["primary_agent"], "knowledge_manager")
        self.assertEqual(result.status, "partial")
        self.assertEqual(result.review_outcome, "PASS WITH NOTES")
        task_dir = self.root / "tasks" / result.task_id
        self.assertTrue((task_dir / "TASK.md").is_file())
        report = (task_dir / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn("Runtime evidence", report)
        kinds = [e["kind"] for e in self.store.events(result.task_id)]
        self.assertIn("tool_call", kinds)
        self.assertEqual(kinds[-1], "finished")

    def test_completed_task_with_tool_use_and_qa_pass(self):
        expected_id = self.store.next_task_id(DAY)
        model = ScriptedModel({
            "classify": [plan("engineering")],
            "execute": [tool_turn(("read_file", {"path": "notes.md"})),
                        # engineering has no task_planning tool; write_file inside the task folder needs no approval
                        tool_turn(("write_file", {"path": f"tasks/{expected_id}/drafts/out.md", "content": "done"})),
                        text_turn("## Report\nDone.\nSTATUS: completed")],
            "review": [text_turn("Looks good.\nOUTCOME: PASS")],
        })
        result = self.orch(model).run("Write a draft")  # deny_all approver
        self.assertEqual(result.task_id, expected_id)
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.executor.tool_calls, 2)
        self.assertEqual(result.executor.tool_errors, 0)
        self.assertTrue((self.root / "tasks" / result.task_id / "drafts" / "out.md").is_file())
        # tool results go back in one user message, matching each tool_use id
        second_call = model.calls[2]["messages"]
        self.assertEqual(second_call[-1]["content"][0]["tool_use_id"], "call_0")
        # the classifier gets a schema restricted to active executors
        enum = model.calls[0]["output_schema"]["properties"]["primary_agent"]["enum"]
        self.assertNotIn("orchestrator", enum)
        self.assertNotIn("education", enum)

    def test_unapproved_write_is_refused_and_reported(self):
        model = ScriptedModel({
            "classify": [plan("engineering", needs_qa=False)],
            "execute": [tool_turn(("write_file", {"path": "notes.md", "content": "overwritten"})),
                        text_turn("Could not write.\nSTATUS: blocked")],
        })
        result = self.orch(model, approver=deny_all).run("Edit notes")
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.executor.tool_errors, 1)
        self.assertEqual((self.root / "notes.md").read_text(encoding="utf-8"), "hello\n")

    def test_qa_fail_downgrades_completed_to_partial(self):
        model = ScriptedModel({
            "classify": [plan("engineering")],
            "execute": [text_turn("Done.\nSTATUS: completed")],
            "review": [text_turn("Missing evidence.\nOUTCOME: FAIL")],
        })
        result = self.orch(model).run("Do it")
        self.assertEqual(result.review_outcome, "FAIL")
        self.assertEqual(result.status, "partial")

    def test_clarification_blocks_before_execution(self):
        model = ScriptedModel({"classify": [plan(clarification="Dự án nào?")]})
        result = self.orch(model).run("Làm cái đó")
        self.assertEqual(result.status, "blocked")
        self.assertEqual(len(model.calls), 1)

    def test_tool_not_registered_is_refused(self):
        model = ScriptedModel({
            "classify": [plan("research", needs_qa=False)],
            "execute": [tool_turn(("write_file", {"path": "notes.md", "content": "x"})),
                        text_turn("STATUS: partial")],
        })
        result = self.orch(model, approver=approve_all).run("Research")
        self.assertEqual(result.executor.tool_errors, 1)
        self.assertEqual([t["name"] for t in model.calls[1]["tools"]], ["read_file", "list_dir"])


if __name__ == "__main__":
    unittest.main()
