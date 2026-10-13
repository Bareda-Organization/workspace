"""goal-table-gate.py 확인 — python3 .claude/bin/test_goal_table_gate.py"""
import importlib.util
import os
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("gate", os.path.join(os.path.dirname(__file__), "goal-table-gate.py"))
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

GOOD = "| # | 완료 조건 | 실행 명령 | 무엇이 깨지면 |\n|---|---|---|---|\n| G1 | 시험 통과 | `./gradlew test` | 실패 |\n"
NO_CMD = "| # | 조건 |\n|---|---|\n| G1 | 시험 통과 |\n"


def run(cmd, cwd):
    return gate.decide({"tool_name": "Bash", "tool_input": {"command": cmd}, "cwd": cwd})[0]


class GateTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        for rnd, body in (("r90", GOOD), ("r91", NO_CMD)):
            os.makedirs(os.path.join(self.root, ".claude", rnd, "cycle"))
            with open(os.path.join(self.root, ".claude", rnd, "PLAN.md"), "w", encoding="utf-8") as f:
                f.write(body)
        os.makedirs(os.path.join(self.root, ".claude", "r92", "cycle"))
        with open(os.path.join(self.root, ".claude", "r92", "cycle", "GOALS.md"), "w", encoding="utf-8") as f:
            f.write(GOOD)  # 라운드 안의 하위 작업은 그 하위 폴더에 목표 표를 둘 수 있다
        os.makedirs(os.path.join(self.root, ".claude", "r93"))
        for name, body in (("PLAN.md", NO_CMD), ("BRIEF-a.md", GOOD), ("BRIEF-b.md", NO_CMD)):
            with open(os.path.join(self.root, ".claude", "r93", name), "w", encoding="utf-8") as f:
                f.write(body)  # 표가 작업 지시서마다 있는 라운드(R51·R52 형태)
        with open(os.path.join(self.root, ".claude", "r91", "report-x.md"), "w", encoding="utf-8") as f:
            f.write(GOOD)  # 작업 창 보고서의 표는 목표 표로 치지 않는다

    def test_dispatch_needs_a_goal_table_with_a_command_column(self):
        start = "orca orchestration worker-start --agent claude --spec "
        self.assertTrue(run(start + '"지시서 .claude/r90/BRIEF-be.md 를 읽어라"', self.root))
        self.assertFalse(run(start + '"지시서 .claude/r91/BRIEF-be.md 를 읽어라"', self.root))
        self.assertTrue(run(start + '"$(cat .claude/r90/cycle/spec-t1.md)"', self.root))  # 하위 폴더 경로 → 라운드 폴더
        self.assertFalse(run(start + '"아무 경로 없음"', self.root))
        self.assertTrue(run(start + '"$(cat .claude/r92/cycle/spec-t1.md)"', self.root))
        self.assertFalse(run(start + '"지시서 .claude/r92/BRIEF.md"', self.root))

    def test_table_must_be_in_the_referenced_brief_not_any_file_of_the_round(self):
        start = "orca orchestration worker-start --agent claude --spec "
        self.assertTrue(run(start + '"지시서 .claude/r93/BRIEF-$n.md"', self.root))  # 셸 변수는 * 로
        self.assertTrue(run(start + '"지시서 .claude/r93/BRIEF-a.md"', self.root))
        self.assertFalse(run(start + '"지시서 .claude/r93/BRIEF-b.md"', self.root))
        self.assertFalse(run(start + '"아무거나 .claude/r93/ 참고"', self.root))
        self.assertTrue(run('R=.claude/r93; ' + start + '"지시서 $R/BRIEF-$n.md"', self.root))  # R51 형태
        self.assertFalse(run('R=.claude/r93; ' + start + '"지시서 $R/BRIEF-b.md"', self.root))
        self.assertTrue(run(start + '"지시서 .claude/r93/BRIEF-${p%%:*}.md"', self.root))  # R52 형태 셸 치환

    def test_skip_counts_only_as_env_prefix_of_the_orca_command(self):
        cmd = 'orca orchestration worker-start --spec "x"'
        self.assertTrue(run("cd /tmp && GOAL_TABLE_SKIP=조사 " + cmd, self.root))
        self.assertFalse(run("# GOAL_TABLE_SKIP=a\n" + cmd, self.root))
        self.assertFalse(run('echo "GOAL_TABLE_SKIP=a" ; ' + cmd, self.root))

    def test_text_that_only_mentions_the_command_is_not_a_dispatch(self):
        self.assertTrue(run("python3 -c \"s = 'orca orchestration worker-start --spec x'\"", self.root))
        self.assertTrue(run("grep -n 'orca orchestration worker-start --spec' SKILL.md", self.root))
        self.assertFalse(run('for n in a b; do orca orchestration worker-start --spec "x"; done', self.root))

    def test_non_dispatch_and_explicit_skips_pass(self):
        self.assertTrue(run("orca orchestration worker-start --help", self.root))
        self.assertTrue(run("ls .claude/r91", self.root))
        self.assertTrue(run('orca orchestration worker-start --spec "x .claude/r91/a.md" --retry-of ctx_1', self.root))
        self.assertTrue(run('GOAL_TABLE_SKIP=조사 orca orchestration worker-start --spec "x"', self.root))


if __name__ == "__main__":
    unittest.main()
