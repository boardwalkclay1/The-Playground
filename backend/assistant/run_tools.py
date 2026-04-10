# backend/assistant/run_tools.py

import subprocess

class RunTools:
    """
    Allows the AI to run backend/frontend/worker commands.
    """

    def run_backend(self, project_path: str):
        return self._run(["python3", "main.py"], project_path)

    def run_frontend(self, project_path: str):
        return self._run(["npm", "run", "dev"], project_path)

    def run_worker(self, project_path: str):
        return self._run(["wrangler", "dev"], project_path)

    def _run(self, cmd, cwd):
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            out, err = proc.communicate(timeout=10)
            return {"success": True, "stdout": out, "stderr": err}
        except Exception as e:
            return {"success": False, "error": str(e)}
