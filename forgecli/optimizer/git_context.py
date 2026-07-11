"""Git-aware Context Engine.

Extracts repository updates (git status, diffs, log histories) to prioritize
recently modified code files and only send delta contexts when possible.
"""



from __future__ import annotations

import subprocess
from pathlib import Path


class GitContextManager:

    """Retrieves local git status, diffs, log histories, and blames to prioritize context."""



    def __init__(self, repo_root: Path) -> None:

        self.root = Path(repo_root).resolve()



    def is_git_repo(self) -> bool:

        return (self.root / ".git").exists()



    def run_git(self, args: list[str]) -> str:

        """Run a git command in the repository root safely and return stdout."""

        if not self.is_git_repo():

            return ""

        try:

            res = subprocess.run(

                ["git", *args],

                cwd=str(self.root),

                capture_output=True,

                text=True,

                check=False,

                encoding="utf-8",

                errors="replace",

            )

            if res.returncode == 0:

                return res.stdout.strip()

        except Exception:

            pass

        return ""



    def get_modified_files(self) -> set[str]:

        """Return a list of changed/untracked relative paths from git status."""

        out = self.run_git(["status", "--porcelain"])

        files = set()

        if not out:

            return files



        for line in out.splitlines():

            if len(line) > 3:



                rel_path = line[3:].strip()



                if " -> " in rel_path:

                    rel_path = rel_path.split(" -> ")[-1]

                files.add(rel_path)

        return files



    def get_recent_commits_files(self, limit: int = 5) -> set[str]:

        """Return files touched in the last N commits."""

        out = self.run_git(["log", f"-n {limit}", "--name-only", "--pretty=format:"])

        files = set()

        if not out:

            return files



        for line in out.splitlines():

            trimmed = line.strip()

            if trimmed:

                files.add(trimmed)

        return files



    def get_diff(self, file_path: str | None = None) -> str:

        """Return the current unstaged git diff. If file_path is provided, limit to that file."""

        args = ["diff"]

        if file_path:

            args.append(file_path)

        return self.run_git(args)



    def get_staged_diff(self) -> str:

        """Return the current staged git diff."""

        return self.run_git(["diff", "--cached"])



    def get_git_summary(self) -> str:

        """Prepare a comprehensive markdown block outlining current Git deltas."""

        if not self.is_git_repo():

            return ""



        modified = self.get_modified_files()

        diff = self.get_diff()

        staged = self.get_staged_diff()



        lines = ["## Git Repository State", ""]



        if not modified:

            lines.append("No local modifications. Working tree clean.")

            return "\n".join(lines)



        lines.append("### Modified and Untracked Files:")

        for f in sorted(modified):

            lines.append(f"- `{f}`")



        if staged:

            lines.extend(["", "### Staged Changes Diff:", "```diff", staged[:8000], "```"])



        if diff:

            lines.extend(["", "### Unstaged Changes Diff:", "```diff", diff[:8000], "```"])



        return "\n".join(lines)

