"""
StorageService manages directory structure and file paths under DATA_DIR.

Layout:
- DATA_DIR/
  - uploads/         (SRS uploads)
  - scripts/         (generated test scripts)
  - runs/<run_id>/   (execution artifacts: logs, junit xml, screenshots, etc)
"""
import os
from typing import Optional
from .env import get_env


class StorageService:
    """Utility for building and creating storage paths under DATA_DIR."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        env = get_env()
        self.base = base_dir or env.data_dir
        # Ensure core dirs exist
        os.makedirs(self.uploads_dir, exist_ok=True)
        os.makedirs(self.scripts_dir, exist_ok=True)

    @property
    def uploads_dir(self) -> str:
        return os.path.join(self.base, "uploads")

    @property
    def scripts_dir(self) -> str:
        return os.path.join(self.base, "scripts")

    def runs_dir(self) -> str:
        path = os.path.join(self.base, "runs")
        os.makedirs(path, exist_ok=True)
        return path

    # PUBLIC_INTERFACE
    def path_for_upload(self, filename: str) -> str:
        """Return path for an uploaded SRS filename inside uploads/."""
        return os.path.join(self.uploads_dir, filename)

    # PUBLIC_INTERFACE
    def script_dir_for_test_case(self, test_case_id: int) -> str:
        """Return directory path for storing scripts of a test case."""
        path = os.path.join(self.scripts_dir, f"tc_{test_case_id}")
        os.makedirs(path, exist_ok=True)
        return path

    # PUBLIC_INTERFACE
    def run_dir(self, run_id: int) -> str:
        """Return directory for a specific run id, creating if needed."""
        path = os.path.join(self.runs_dir(), f"run_{run_id}")
        os.makedirs(path, exist_ok=True)
        return path

    # PUBLIC_INTERFACE
    def run_artifact(self, run_id: int, relative_name: str) -> str:
        """Return a path inside the run directory for an artifact filename."""
        return os.path.join(self.run_dir(run_id), relative_name)
