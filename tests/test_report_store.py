import json
import multiprocessing
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from project_manager import (
    project_lock,
    resolve_project_context,
)
from report_store import save_quality_reports


def acquire_project_lock_in_child(
    context,
    attempted,
    acquired,
    release,
) -> None:
    attempted.set()
    with project_lock(context):
        acquired.set()
        release.wait(timeout=2)


class ReportStoreTests(unittest.TestCase):
    def test_second_process_waits_for_same_project_lock(
        self,
    ) -> None:
        process_context = multiprocessing.get_context("spawn")
        attempted = process_context.Event()
        acquired = process_context.Event()
        release = process_context.Event()

        with TemporaryDirectory() as temporary_directory:
            context = resolve_project_context(
                managed_sandbox=Path(temporary_directory),
                project_id="robot-arm",
            )
            process = process_context.Process(
                target=acquire_project_lock_in_child,
                args=(context, attempted, acquired, release),
            )

            try:
                with project_lock(context):
                    process.start()
                    self.assertTrue(attempted.wait(timeout=2))
                    self.assertFalse(acquired.wait(timeout=0.2))

                self.assertTrue(acquired.wait(timeout=2))
                release.set()
                process.join(timeout=2)
                self.assertEqual(process.exitcode, 0)
            finally:
                release.set()
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=2)

    def test_saves_three_reports_under_project_and_thread(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary_directory:
            reports_root = (
                Path(temporary_directory)
                / "reports"
            )
            result = {
                "reviewer_report": {"passed": True},
                "tester_report": {"passed": False},
                "verifier_report": None,
            }

            save_quality_reports(
                reports_root=reports_root,
                thread_id="main",
                result=result,
            )

            thread_root = reports_root / "main"
            self.assertEqual(
                json.loads(
                    (thread_root / "reviewer.json").read_text(
                        encoding="utf-8"
                    )
                ),
                {"passed": True},
            )
            self.assertEqual(
                json.loads(
                    (thread_root / "tester.json").read_text(
                        encoding="utf-8"
                    )
                ),
                {"passed": False},
            )
            self.assertIsNone(
                json.loads(
                    (thread_root / "verifier.json").read_text(
                        encoding="utf-8"
                    )
                )
            )

    def test_project_lock_file_lives_in_project_data(
        self,
    ) -> None:
        with TemporaryDirectory() as temporary_directory:
            context = resolve_project_context(
                managed_sandbox=Path(temporary_directory),
                project_id="robot-arm",
            )
            expected_lock = (
                context.checkpoint_path.parent
                / ".write.lock"
            )

            with project_lock(context):
                self.assertTrue(expected_lock.exists())


if __name__ == "__main__":
    unittest.main()
