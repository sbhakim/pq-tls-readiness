"""A safe wrapper around subprocess.

Every external command (openssl, dig) goes through `run` so we get consistent
timeout handling and never hang the pipeline on an unresponsive host.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class CommandResult:
    """What a shell command returned."""

    ok: bool          # True if the command exited 0 within the timeout
    return_code: int | None
    stdout: str
    stderr: str
    timed_out: bool = False


def run(argv: list[str], timeout_s: int, stdin: str | None = None) -> CommandResult:
    """Run a command by argument list (never a shell string) and capture output.

    Passing an argv list avoids shell injection. `timeout_s` guarantees we
    return even if the remote endpoint stalls.
    """
    try:
        proc = subprocess.run(
            argv,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return CommandResult(
            ok=(proc.returncode == 0),
            return_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except subprocess.TimeoutExpired:
        return CommandResult(
            ok=False,
            return_code=None,
            stdout="",
            stderr="timeout",
            timed_out=True,
        )
    except FileNotFoundError as exc:
        return CommandResult(ok=False, return_code=None, stdout="", stderr=f"not found: {exc}")
