"""
ExecutionService runs pytest for generated scripts and collects results/logs.
"""
import subprocess
import sys
import os
from typing import List, Tuple
from .storage_service import StorageService


class ExecutionService:
    """Run pytest for scripts residing under the scripts directory."""

    def __init__(self, storage: StorageService | None = None) -> None:
        self.storage = storage or StorageService()

    # PUBLIC_INTERFACE
    def run_scripts(self, run_id: int, script_paths: List[str]) -> Tuple[int, str, str]:
        """
        Execute pytest on given script paths.
        Returns (exit_code, junit_xml_path, log_path).
        """
        run_dir = self.storage.run_dir(run_id)
        junit_xml = os.path.join(run_dir, "results.xml")
        log_path = os.path.join(run_dir, "run.log")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            f"--junitxml={junit_xml}",
            *script_paths,
        ]
        with open(log_path, "w", encoding="utf-8") as logf:
            proc = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, cwd=os.getcwd())
            ret = proc.wait()

        return ret, junit_xml, log_path
