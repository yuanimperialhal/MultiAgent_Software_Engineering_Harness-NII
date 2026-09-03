import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from project_manager import resolve_project_context
except ModuleNotFoundError:
    resolve_project_context = None


class ProjectManagerTests(unittest.TestCase):
    def test_different_projects_have_different_storage(
        self,
    ) -> None:
        self.assertTrue(callable(resolve_project_context))

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

            self.assertNotEqual(
                robot_arm.sandbox_root,
                inspection_car.sandbox_root,
            )
            self.assertNotEqual(
                robot_arm.checkpoint_path,
                inspection_car.checkpoint_path,
            )
            self.assertNotEqual(
                robot_arm.reports_root,
                inspection_car.reports_root,
            )

    def test_creates_project_inside_managed_sandbox(
        self,
    ) -> None:
        self.assertTrue(
            callable(resolve_project_context),
            "尚未实现 resolve_project_context",
        )

        with TemporaryDirectory() as temporary_directory:
            managed_sandbox = (
                Path(temporary_directory)
                / "practice_sandbox"
            )

            context = resolve_project_context(
                managed_sandbox=managed_sandbox,
                project_id="robot-arm",
            )

            self.assertEqual(
                context.sandbox_root,
                managed_sandbox
                / "projects"
                / "robot-arm",
            )
            self.assertEqual(
                context.checkpoint_path,
                managed_sandbox
                / "data"
                / "projects"
                / "robot-arm"
                / "checkpoint.db",
            )
            self.assertEqual(
                context.reports_root,
                managed_sandbox
                / "data"
                / "projects"
                / "robot-arm"
                / "reports",
            )

            self.assertTrue(
                context.sandbox_root.is_dir()
            )
            self.assertTrue(
                context.reports_root.is_dir()
            )

    def test_rejects_project_id_that_escapes_sandbox(
        self,
    ) -> None:
        self.assertTrue(
            callable(resolve_project_context),
            "尚未实现 resolve_project_context",
        )

        with TemporaryDirectory() as temporary_directory:
            managed_sandbox = Path(
                temporary_directory
            )

            invalid_project_ids = [
                "../outside",
                "robot/arm",
                "/home/project",
                "",
            ]

            for project_id in invalid_project_ids:
                with self.subTest(project_id=project_id):
                    with self.assertRaises(ValueError):
                        resolve_project_context(
                            managed_sandbox=managed_sandbox,
                            project_id=project_id,
                        )


if __name__ == "__main__":
    unittest.main()
