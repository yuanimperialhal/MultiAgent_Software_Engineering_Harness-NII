import unittest
from workflow import graph

class PlanningLoopTest(unittest.TestCase):
    def test_explorer_rejects_first_plan_then_enters_implementer(self,)->None:
        build_graph = getattr(graph, "build_planning_graph",None,)

        self.assertTrue(callable(build_graph), "workflow.graph 尚未实现 build_planning_graph",)

        def planner_node(state:dict)->dict:
            revision=state.get("plan_revision", 0)+1

            return {"plan": f"第 {revision} 版计划",
                    "plan_revision": revision,#revision是修改的意思
                    "replan_count": max(0, revision - 1),
                    "phase": "exploring",
                    "next_role": "explorer",
                }

        def explorer_node(state:dict)->dict:
            approved = state["plan_revision"] >= 2

            return {
                "plan_approved": approved,
                "replan_feedback": (
                    []
                    if approved
                    else ["第 1 版计划与项目现状冲突"]
                ),
                "next_role": "main_agent",
            }            

        def planning_main_node(state: dict) -> dict:
            if state["plan_approved"]:
                return {"next_role": "implementer"}

            if state["replan_count"] >= state["max_replans"]:
                return {
                    "next_role": None,
                    "phase": "failed",
                    "status": "failed",
                }

            return {"next_role": "planner"}

        implementer_calls = 0

        def implementer_node(state: dict) -> dict:
            nonlocal implementer_calls
            implementer_calls += 1
            return {
                "phase": "reviewing",
                "status": "running",
                "next_role": "reviewer",
            }

        def reviewer_node(state: dict) -> dict:
            return {
                "phase": "reviewing",
                "status": "running",
                "next_role": "main_agent",
            }

        def review_main_node(state: dict) -> dict:
            return {
                "phase": "testing",
                "status": "running",
                "next_role": "tester",
            }

        def tester_node(state: dict) -> dict:
            return {
                "phase": "testing",
                "status": "running",
                "next_role": "main_agent",
            }

        def test_main_node(state: dict) -> dict:
            return {
                "phase": "verifying",
                "status": "running",
                "next_role": "verifier",
            }

        def verifier_node(state: dict) -> dict:
            return {
                "phase": "verifying",
                "status": "running",
                "next_role": "main_agent",
            }

        def verifier_main_node(state: dict) -> dict:
            return {
                "phase": "completed",
                "status": "completed",
                "next_role": None,
            }

        app = build_graph(
            planner_node=planner_node,
            explorer_node=explorer_node,
            implementer_node=implementer_node,
            reviewer_node=reviewer_node,
            tester_node=tester_node,
            planning_main_node=planning_main_node,
            review_main_node=review_main_node,
            test_main_node=test_main_node,
            verifier_node=verifier_node,
            verifier_main_node=verifier_main_node,
        )

        result = app.invoke(
            {
                "user_request": "实现待办程序",
                "phase": "planning",
                "status": "running",
                "next_role": "planner",
                "plan_revision": 0,
                "replan_count": 0,
                "max_replans": 2,
                "plan": "",
                "plan_approved": None,
                "replan_feedback": [],
            }
        )

        self.assertEqual(result["plan_revision"], 2)
        self.assertEqual(result["replan_count"], 1)
        self.assertEqual(implementer_calls, 1)
        self.assertEqual(result["phase"], "completed")
        self.assertEqual(result["status"], "completed")
        self.assertIsNone(result["next_role"])


if __name__ == "__main__":
    unittest.main()
