import unittest
from contextlib import nullcontext
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import chat_cli
import checkpoint_reader
import langgraph_main
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from project_manager import ProjectContext
from project_manager import resolve_project_context
from workflow.state import MultiAgentState


class FakeApp:
    def __init__(self) -> None:
        self.initial_state: dict[str, object] | None = None

    def invoke(
        self,
        initial_state: dict[str, object],
        config: dict[str, object],
    ) -> dict[str, object]:
        self.initial_state = initial_state
        return {
            "plan_revision": 1,
            "replan_count": 0,
            "plan_approved": True,
            "phase": "completed",
            "status": "completed",
            "next_role": None,
            "review_repair_count": 0,
            "tester_repair_count": 0,
            "max_tester_repairs": 3,
            "verifier_repair_count": 0,
            "max_verifier_repairs": 3,
            "reviewer_report": None,
            "tester_report": None,
            "verifier_report": None,
        }

    def get_state(
        self,
        config: dict[str, object],
    ) -> SimpleNamespace:
        return SimpleNamespace(
            values={"status": "completed"}
        )


class ProjectRuntimeTests(unittest.TestCase):
    def test_same_thread_is_isolated_between_project_databases(
        self,
    ) -> None:
        def keep_state(
            state: MultiAgentState,
        ) -> dict[str, object]:
            return {}

        def build_graph(checkpointer: SqliteSaver):
            builder = StateGraph(MultiAgentState)
            builder.add_node("keep_state", keep_state)
            builder.add_edge(START, "keep_state")
            builder.add_edge("keep_state", END)
            return builder.compile(checkpointer=checkpointer)

        thread_config = {
            "configurable": {"thread_id": "main"}
        }

        with TemporaryDirectory() as temporary_directory:
            managed_sandbox = Path(temporary_directory)
            robot_arm = resolve_project_context(
                managed_sandbox=managed_sandbox,
                project_id="robot-arm",
            )
            inspection_car = resolve_project_context(
                managed_sandbox=managed_sandbox,
                project_id="inspection-car",
            )

            with SqliteSaver.from_conn_string(
                str(robot_arm.checkpoint_path)
            ) as checkpointer:
                robot_graph = build_graph(checkpointer)
                robot_graph.invoke(
                    {
                        "conversation_history": [
                            "机械臂第一轮"
                        ]
                    },
                    config=thread_config,
                )

            with SqliteSaver.from_conn_string(
                str(inspection_car.checkpoint_path)
            ) as checkpointer:
                car_graph = build_graph(checkpointer)
                car_result = car_graph.invoke(
                    {
                        "conversation_history": [
                            "巡检车第一轮"
                        ]
                    },
                    config=thread_config,
                )

            self.assertEqual(
                car_result["conversation_history"],
                ["巡检车第一轮"],
            )

            with SqliteSaver.from_conn_string(
                str(robot_arm.checkpoint_path)
            ) as checkpointer:
                robot_graph = build_graph(checkpointer)
                robot_result = robot_graph.invoke(
                    {
                        "conversation_history": [
                            "机械臂第二轮"
                        ]
                    },
                    config=thread_config,
                )

            self.assertEqual(
                robot_result["conversation_history"],
                [
                    "机械臂第一轮",
                    "机械臂第二轮",
                ],
            )

    def test_state_schema_keeps_project_id(self) -> None:
        self.assertIn(
            "project_id",
            MultiAgentState.__annotations__,
        )

    def test_run_task_uses_selected_project_paths(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            managed_sandbox = (
                Path(temporary_directory)
                / "practice_sandbox"
            )
            project_context = ProjectContext(
                project_id="robot-arm",
                sandbox_root=(
                    managed_sandbox
                    / "projects"
                    / "robot-arm"
                ),
                checkpoint_path=(
                    managed_sandbox
                    / "data"
                    / "projects"
                    / "robot-arm"
                    / "checkpoint.db"
                ),
                reports_root=(
                    managed_sandbox
                    / "data"
                    / "projects"
                    / "robot-arm"
                    / "reports"
                ),
            )

            fake_app = FakeApp()
            fake_registry = object()
            sqlite_context = MagicMock()
            sqlite_context.__enter__.return_value = object()

            with patch.object(
                langgraph_main,
                "resolve_project_context",
                return_value=project_context,
            ) as resolve_project:
                with patch.object(
                    langgraph_main,
                    "project_lock",
                    return_value=nullcontext(),
                ):
                    with patch.object(
                        langgraph_main.SqliteSaver,
                        "from_conn_string",
                        return_value=sqlite_context,
                    ) as open_sqlite:
                        with patch.object(
                            langgraph_main,
                            "create_llm",
                            return_value=object(),
                        ):
                            with patch.object(
                                langgraph_main,
                                "build_tool_registry",
                                return_value=fake_registry,
                            ) as build_registry:
                                with patch.object(
                                    langgraph_main,
                                    "build_planning_nodes",
                                    return_value={},
                                ) as build_nodes:
                                    with patch.object(
                                        langgraph_main,
                                        "build_planning_graph",
                                        return_value=fake_app,
                                    ):
                                        with patch.object(
                                            langgraph_main,
                                            "build_project_snapshot",
                                            return_value="snapshot",
                                        ):
                                            with patch.object(
                                                langgraph_main,
                                                "save_quality_reports",
                                            ) as save_reports:
                                                langgraph_main.run_task(
                                                    "检查机械臂",
                                                    project_id="robot-arm",
                                                    thread_id="main",
                                                )

            expected_managed_sandbox = (
                Path(langgraph_main.__file__).parent
                / "practice_sandbox"
            )
            with self.subTest("managed sandbox"):
                resolve_project.assert_called_once_with(
                    managed_sandbox=expected_managed_sandbox,
                    project_id="robot-arm",
                )
            with self.subTest("tool registry sandbox"):
                build_registry.assert_called_once_with(
                    project_context.sandbox_root
                )
            with self.subTest("registry reaches workflow"):
                build_nodes.assert_called_once_with(
                    unittest.mock.ANY,
                    tool_registry=fake_registry,
                )
            with self.subTest("project checkpoint"):
                open_sqlite.assert_called_once_with(
                    str(project_context.checkpoint_path)
                )

            self.assertIsNotNone(fake_app.initial_state)
            with self.subTest("project state"):
                self.assertEqual(
                    fake_app.initial_state["project_id"],
                    "robot-arm",
                )
            with self.subTest("project state sandbox"):
                self.assertEqual(
                    fake_app.initial_state["sandbox_root"],
                    str(project_context.sandbox_root),
                )
            with self.subTest("project reports"):
                save_reports.assert_called_once_with(
                    reports_root=project_context.reports_root,
                    thread_id="main",
                    result=unittest.mock.ANY,
                )

    def test_cli_passes_project_and_thread_to_run_task(
        self,
    ) -> None:
        received_calls: list[tuple[str | None, str, str]] = []

        def fake_run_task(
            user_request: str,
            **kwargs: str,
        ) -> None:
            received_calls.append(
                (
                    kwargs.get("project_id"),
                    kwargs["thread_id"],
                    user_request,
                )
            )

        with patch(
            "builtins.input",
            side_effect=[
                "robot-arm",
                "main",
                "检查机械臂状态",
                "exit",
            ],
        ):
            with patch.object(
                chat_cli,
                "run_task",
                side_effect=fake_run_task,
            ):
                chat_cli.main()

        self.assertEqual(
            received_calls,
            [
                (
                    "robot-arm",
                    "main",
                    "检查机械臂状态",
                )
            ],
        )

    def test_checkpoint_reader_does_not_create_missing_database(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary_directory:
            project_context = ProjectContext(
                project_id="robot-arm",
                sandbox_root=(
                    Path(temporary_directory)
                    / "projects"
                    / "robot-arm"
                ),
                checkpoint_path=(
                    Path(temporary_directory)
                    / "data"
                    / "projects"
                    / "robot-arm"
                    / "checkpoint.db"
                ),
                reports_root=(
                    Path(temporary_directory)
                    / "data"
                    / "projects"
                    / "robot-arm"
                    / "reports"
                ),
            )
            project_context.checkpoint_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with patch(
                "builtins.input",
                side_effect=["robot-arm", "main"],
            ):
                with patch.object(
                    checkpoint_reader,
                    "resolve_project_context",
                    return_value=project_context,
                ):
                    with patch.object(
                        checkpoint_reader.SqliteSaver,
                        "from_conn_string",
                    ) as open_sqlite:
                        checkpoint_reader.main()

            open_sqlite.assert_not_called()


if __name__ == "__main__":
    unittest.main()
