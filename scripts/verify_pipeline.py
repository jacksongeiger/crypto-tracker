"""Verify crypto-tracker pipeline health.

Reads:
  - The system crontab block managed by install_system_cron.sh
  - tail of each job's log under {repo}/logs/<job>.log for last run + status
  - DB signal counts in last 24h, broken down by source_type
  - Today's brief presence

Default output: human-readable. Pass --json for machine output.

Usage:
  backend/.venv/bin/python scripts/verify_pipeline.py
  backend/.venv/bin/python scripts/verify_pipeline.py --json

Exit code: 0 = healthy, 1 = degraded (missing job or stale run).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs"
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select  # noqa: E402

from db import SessionLocal  # noqa: E402
from models import Brief, RawSignal, Source  # noqa: E402

EXPECTED_JOBS = ["news", "onchain", "sentiment", "macro", "predictions", "synthesis"]

# Status line format produced by run_cron_job.sh:
#   STATUS 2026-05-13T13:30:00Z OK news rc=0 dur=12s
STATUS_RE = re.compile(
    r"^STATUS\s+(?P<ts>\S+)\s+(?P<status>OK|FAIL)\s+(?P<job>\S+)\s+rc=(?P<rc>\d+)\s+dur=(?P<dur>\d+)s"
)


def parse_crontab() -> dict[str, str]:
    """Return {job_name: cron_expression} for crypto-tracker entries."""
    try:
        out = subprocess.run(
            ["crontab", "-l"], capture_output=True, text=True, timeout=10
        ).stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}
    jobs: dict[str, str] = {}
    in_block = False
    for line in out.splitlines():
        if "crypto-tracker cron" in line and ">>>" in line:
            in_block = True
            continue
        if "crypto-tracker cron" in line and "<<<" in line:
            in_block = False
            continue
        if not in_block:
            continue
        if line.strip().startswith("#") or line.strip().startswith("CRON_TZ"):
            continue
        # Expression form: M H DOM MON DOW <runner> <name> <script>
        parts = line.strip().split()
        if len(parts) < 7:
            continue
        cron_expr = " ".join(parts[:5])
        try:
            runner_idx = next(
                i for i, p in enumerate(parts) if p.endswith("run_cron_job.sh")
            )
            name = parts[runner_idx + 1]
        except (StopIteration, IndexError):
            continue
        jobs[name] = cron_expr
    return jobs


def parse_log_tail(job_name: str) -> dict | None:
    log_path = LOG_DIR / f"{job_name}.log"
    if not log_path.exists():
        return None
    try:
        with log_path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 4096))
            tail = f.read().decode("utf-8", errors="replace")
    except OSError:
        return None
    for line in reversed(tail.splitlines()):
        m = STATUS_RE.match(line.strip())
        if m:
            return {
                "ts": m.group("ts"),
                "status": m.group("status"),
                "rc": int(m.group("rc")),
                "dur_s": int(m.group("dur")),
            }
    return None


def gather_db_state() -> dict:
    session = SessionLocal()
    try:
        today = datetime.now(timezone.utc).date()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        rows = session.execute(
            select(Source.source_type, func.count(RawSignal.id))
            .join(RawSignal, RawSignal.source_id == Source.id)
            .where(RawSignal.ingested_at >= cutoff)
            .group_by(Source.source_type)
        ).all()
        counts = {st.value: int(c) for st, c in rows}
        brief = (
            session.query(Brief)
            .filter(Brief.brief_date == today)
            .order_by(Brief.generated_at.desc())
            .first()
        )
        return {
            "signals_last_24h_by_type": counts,
            "signals_total_last_24h": sum(counts.values()),
            "today_brief_present": brief is not None,
            "today_brief_id": str(brief.id) if brief else None,
            "today_brief_generated_at": (
                brief.generated_at.isoformat() if brief else None
            ),
            "today_brief_theme_count": len(brief.themes) if brief else 0,
        }
    finally:
        session.close()


def build_report() -> dict:
    cron_jobs = parse_crontab()
    job_status: list[dict] = []
    for name in EXPECTED_JOBS:
        sched = cron_jobs.get(name)
        last = parse_log_tail(name)
        job_status.append({
            "name": name,
            "present": sched is not None,
            "schedule": sched,
            "last_run": last,
        })
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "host_local_now": datetime.now().isoformat(),
        "jobs": job_status,
        "db": gather_db_state(),
    }


def render_text(rep: dict) -> str:
    L: list[str] = []
    L.append("crypto-tracker pipeline status")
    L.append("=" * 60)
    L.append(f"now (local): {rep['host_local_now']}")
    L.append(f"checked at:  {rep['generated_at']}")
    L.append("")
    L.append("Cron jobs (system crontab):")
    for j in rep["jobs"]:
        mark = "✓" if j["present"] else "✗"
        sched = j.get("schedule") or "(missing)"
        last = j.get("last_run")
        if last:
            last_str = f"  last: {last['ts']} {last['status']} ({last['dur_s']}s)"
        else:
            last_str = "  last: never"
        L.append(f"  {mark} {j['name']:<12} {sched:<14}{last_str}")
    L.append("")
    db = rep["db"]
    L.append("Signals in last 24h:")
    if not db["signals_last_24h_by_type"]:
        L.append("  (none — pipeline idle)")
    else:
        for st, n in sorted(db["signals_last_24h_by_type"].items()):
            L.append(f"  {st:<22} {n:>5}")
        L.append(f"  {'total':<22} {db['signals_total_last_24h']:>5}")
    L.append("")
    L.append("Today's brief:")
    if db["today_brief_present"]:
        L.append(
            f"  ✓ brief {db['today_brief_id'][:8]}…  "
            f"generated {db['today_brief_generated_at']}  "
            f"({db['today_brief_theme_count']} themes)"
        )
    else:
        local_hour = datetime.now().hour
        if local_hour < 7:
            L.append("  • not yet — synthesis scheduled for 06:50 PT")
        else:
            L.append("  ✗ NO brief for today (synthesis may have failed)")
    return "\n".join(L)


def main() -> int:
    rep = build_report()
    if "--json" in sys.argv:
        print(json.dumps(rep, indent=2, default=str))
    else:
        print(render_text(rep))
    missing = [j for j in rep["jobs"] if not j["present"]]
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
