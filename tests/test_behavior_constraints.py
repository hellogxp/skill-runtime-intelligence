import tempfile
import unittest
from pathlib import Path

from skill_runtime_intelligence.behavior_constraints import (
    assess_skill_behavior,
    extract_behavior_constraints,
)


def run_with(*events, completeness="complete"):
    return {
        "session_completeness": completeness,
        "events": list(events),
    }


def tool_event(name):
    return {
        "event_id": f"event-{name}",
        "event_type": "tool.completed",
        "stage": "execution",
        "status": "completed",
        "summary": f"Tool `{name}` completed",
        "payload": {"tool_name": name},
    }


class BehaviorConstraintTests(unittest.TestCase):
    def test_exact_required_tool_is_satisfied_by_runtime_event(self):
        constraints = extract_behavior_constraints(
            "Must call <tool>aone-km::searchDocChunk</tool> before coding."
        )
        evaluated = assess_single(
            constraints[0],
            run_with(tool_event("mcp__aone_km.searchDocChunk")),
        )

        self.assertEqual(evaluated["status"], "satisfied")
        self.assertEqual(evaluated["evidence_grade"], "observed")

    def test_unconditional_required_tool_missing_from_complete_run_is_visible(self):
        constraints = extract_behavior_constraints(
            "You must call <tool>audit::verifyRun</tool>."
        )
        evaluated = assess_single(constraints[0], run_with(tool_event("other")))

        self.assertEqual(evaluated["status"], "expected_not_observed")

    def test_conditional_table_rule_is_not_mislabeled_as_deviation(self):
        constraints = extract_behavior_constraints(
            "| Scenario | Action |\n| Repo name known | Call <tool>aone-km::getCodeWikiStructure</tool> |"
        )
        evaluated = assess_single(constraints[0], run_with(tool_event("other")))

        self.assertTrue(constraints[0]["conditional"])
        self.assertEqual(evaluated["status"], "not_evaluable")

    def test_redacted_command_requirement_remains_not_evaluable(self):
        constraints = extract_behavior_constraints(
            "回复前必须执行以下命令：\n\n```\na1 skill report example --location /tmp/example\n```"
        )
        evaluated = assess_single(
            constraints[0], run_with(tool_event("exec_command"))
        )

        self.assertEqual(constraints[0]["kind"], "command")
        self.assertEqual(evaluated["status"], "not_evaluable")

    def test_prohibited_observed_tool_is_a_deviation(self):
        constraints = extract_behavior_constraints(
            "Never call <tool>unsafe::deleteEverything</tool>."
        )
        evaluated = assess_single(
            constraints[0], run_with(tool_event("mcp__unsafe.deleteEverything"))
        )

        self.assertEqual(evaluated["status"], "deviation")

    def test_assessment_reads_current_definition_without_storing_raw_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SKILL.md"
            content = "---\nname: demo\ndescription: demo\n---\nMust call <tool>demo::inspect</tool>.\n"
            path.write_text(content, encoding="utf-8")
            run = {
                **run_with(tool_event("mcp__demo.inspect")),
                "source_path": str(path),
            }

            result = assess_skill_behavior(run)

        self.assertEqual(result["status"], "satisfied_observed_scope")
        self.assertEqual(result["counts"]["satisfied"], 1)
        self.assertNotIn("content", result)
        self.assertNotIn("raw_instruction", result["constraints"][0])


def assess_single(constraint, run):
    # Exercise the public assessment path with a temporary definition so the
    # private matching implementation remains free to evolve.
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "SKILL.md"
        if constraint["kind"] == "tool":
            verb = "Never call" if constraint["polarity"] == "prohibited" else "Must call"
            conditional = "When needed, " if constraint["conditional"] else ""
            body = f"{conditional}{verb} <tool>x::{constraint['target_label']}</tool>."
        else:
            body = "回复前必须执行以下命令：\n```\n" + constraint["target"] + "\n```"
        path.write_text(
            f"---\nname: demo\ndescription: demo\n---\n{body}\n",
            encoding="utf-8",
        )
        return assess_skill_behavior({**run, "source_path": str(path)})[
            "constraints"
        ][0]


if __name__ == "__main__":
    unittest.main()
