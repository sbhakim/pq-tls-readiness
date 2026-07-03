"""Write results to CSV (for analysis) and JSONL (for auditing raw probes).

Both writers are streaming: rows are appended as they complete, so a long run
that dies partway still leaves usable output.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict
from pathlib import Path

from ..models import DomainReadiness
from .schema import COLUMNS, to_row


class ResultWriter:
    """Append-only CSV + JSONL writer used across a whole run.

    With `resume=True` both files are opened in append mode and the CSV header
    is only written for a fresh file, so an interrupted long run can continue
    where it left off (the caller is responsible for skipping already-scanned
    targets; see `completed_hostnames`).
    """

    def __init__(
        self,
        csv_path: str | Path,
        jsonl_path: str | Path,
        resume: bool = False,
    ) -> None:
        self.csv_path = Path(csv_path)
        self.jsonl_path = Path(jsonl_path)
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)

        mode = "a" if resume else "w"
        fresh_csv = mode == "w" or not self.csv_path.exists() or self.csv_path.stat().st_size == 0

        self._csv_fh = self.csv_path.open(mode, newline="", encoding="utf-8")
        self._csv_writer = csv.DictWriter(self._csv_fh, fieldnames=COLUMNS)
        if fresh_csv:
            self._csv_writer.writeheader()

        self._jsonl_fh = self.jsonl_path.open(mode, encoding="utf-8")

    def write(self, record: DomainReadiness) -> None:
        """Append one result to both files and flush."""
        self._csv_writer.writerow(to_row(record))
        self._csv_fh.flush()

        # JSONL keeps the full object, including per-profile probe details.
        payload = asdict(record)
        payload["tier"] = record.tier.value
        payload["kex_class"] = record.kex_class.value
        payload["auth_class"] = record.auth_class.value
        self._jsonl_fh.write(json.dumps(payload, default=str) + "\n")
        self._jsonl_fh.flush()

    def close(self) -> None:
        self._csv_fh.close()
        self._jsonl_fh.close()

    def __enter__(self) -> "ResultWriter":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def completed_hostnames(csv_path: str | Path) -> set[str]:
    """Hostnames already present in a results CSV (for --resume runs)."""
    path = Path(csv_path)
    if not path.exists():
        return set()
    with path.open(newline="", encoding="utf-8") as fh:
        return {row["hostname"] for row in csv.DictReader(fh) if row.get("hostname")}
