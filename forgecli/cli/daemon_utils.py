"""Lightweight daemon utilities — no heavy imports (FastAPI, uvicorn, graph).

Import-safe functions that don't trigger the full daemon module initialization.
"""



from __future__ import annotations

import subprocess
import sys


def check_daemon_health() -> bool:

    """Return True if the Forge daemon is running and responding."""

    try:

        import httpx

        with httpx.Client(timeout=0.5) as client:

            r = client.get("http://127.0.0.1:16868/health")

            return r.status_code == 200

    except Exception:

        return False





def start_daemon_background() -> None:

    """Launch the daemon in the background as a subprocess."""

    subprocess.Popen(

        [sys.executable, "-m", "forgecli.cli.daemon"],

        stdout=subprocess.DEVNULL,

        stderr=subprocess.DEVNULL,

        close_fds=True,

        start_new_session=True,

    )

